from __future__ import annotations

import asyncio
import json
import math
import os
import re
import shutil
import socket
import errno
from dataclasses import replace
from time import monotonic
from datetime import date, datetime
from urllib.parse import quote, urlparse, parse_qs

import httpx

from .config import Settings
from .models import Comment, DateSample, Evidence, Fare, FareRequest, Goal, Segment, identity
from .safety import SourceFailure, clean_text, public_url


async def command_json(executable: str, args: list[str], settings: Settings, source: str) -> dict:
    if not shutil.which(executable):
        raise SourceFailure(source, "NOT_INSTALLED", f"未找到 {source} 可执行文件")
    env = dict(os.environ)
    # Child tools do not need the reasoning or SerpAPI credentials.
    for key in list(env):
        if key.endswith("API_KEY") and key != "FLYAI_API_KEY":
            env.pop(key)
    if source != "FlyAI":
        env.pop("FLYAI_API_KEY", None)
    elif settings.flyai_key:
        env["FLYAI_API_KEY"] = settings.flyai_key
    env["NODE_TLS_REJECT_UNAUTHORIZED"] = "1"
    env["SOCAI_RUNS_DIR"] = str((settings.data_dir / "socai-private").resolve())
    process = await asyncio.create_subprocess_exec(
        executable, *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=env,
    )
    try:
        out, err = await asyncio.wait_for(process.communicate(), settings.source_timeout)
    except (TimeoutError, asyncio.CancelledError):
        # This is the CLI client PID only, never a process group or daemon PID.
        if process.returncode is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass
        await process.communicate()
        raise
    text = out.decode("utf-8", errors="replace")
    if process.returncode:
        message = (text + err.decode("utf-8", errors="replace")).lower()
        if any(x in message for x in ["captcha", "验证码", "access denied", "forbidden"]):
            code = "ACCESS_BLOCKED"
        elif any(x in message for x in ["login", "sign in", "登录", "remote debugging", "devtools", "chrome"]):
            code = "BROWSER_OR_LOGIN_REQUIRED"
        else:
            code = "CLI_FAILED"
        raise SourceFailure(source, code, "命令未成功；请使用 doctor 检查本机配置，或切换其他来源")
    # Parse one complete JSON value, never evaluate output as code.
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        raise SourceFailure(source, "INVALID_RESPONSE", "CLI 未返回有效 JSON") from None
    if not isinstance(data, dict):
        raise SourceFailure(source, "SCHEMA_CHANGED", "预期 JSON 对象")
    return data


def socai_evidence(payload: dict, query: str) -> list[Evidence]:
    root = payload.get("data", payload)
    if not isinstance(root, dict):
        return []
    notes = root.get("notes", [])
    result: list[Evidence] = []
    if not isinstance(notes, list):
        return result
    for item in notes:
        if not isinstance(item, dict):
            continue
        # socai 0.6.1 returns opened notes as {"entity": {...}}. The
        # host-browser receipt uses {"note": {...}}. Both contain body text;
        # search cards alone never qualify as evidence.
        note = item.get("entity", item.get("note", item))
        if not isinstance(note, dict):
            continue
        body = clean_text(note.get("content"))
        if not body.strip():  # Search cards/titles cannot satisfy a body read.
            continue
        url = public_url(str(note.get("url", "")))
        if not url and re.fullmatch(r"[a-zA-Z0-9_-]{8,80}", str(note.get("note_id", ""))):
            url = f"https://www.xiaohongshu.com/explore/{note['note_id']}"
        if urlparse(url).hostname not in {"www.xiaohongshu.com", "xiaohongshu.com"}:
            continue
        comments_raw = item.get("comments", note.get("top_comments", note.get("comments", [])))
        if isinstance(comments_raw, dict):
            comments_raw = comments_raw.get("comments", comments_raw.get("items", []))
        comments = []
        for comment in (comments_raw if isinstance(comments_raw, list) else [])[:16]:
            if isinstance(comment, str):
                text = clean_text(comment, 1500)
                if text:
                    comments.append(Comment(text=text))
            elif isinstance(comment, dict):
                text = clean_text(comment.get("content", comment.get("text", "")), 1500)
                if text:
                    comments.append(Comment(text=text, published_at=clean_text(comment.get("date", comment.get("time")), 100) or None))
                for reply in comment.get("replies", [])[:5] if isinstance(comment.get("replies"), list) else []:
                    reply_text = clean_text(reply, 1500)
                    if reply_text:
                        comments.append(Comment(text=reply_text))
        result.append(Evidence(
            id=identity("socai", url, body), source="小红书 / socai", url=url, query=query,
            title=clean_text(note.get("title"), 300), body=body, comments=comments,
            published_at=clean_text(note.get("date"), 100) or None,
            warnings=(["页面显示最后编辑时间，原发帖时间未知"] if note.get("date_edited") else
                      ["发布时间为页面原文；相对时间以抓取时间为参照"] if note.get("date") else
                      ["未取得发帖时间，新鲜度未知"]),
        ))
    return result


def socai_gate(payload):
    """The CLI may exit zero while the page reports a login/access blocker."""
    if isinstance(payload, dict):
        for key in ["reason", "error", "error_code"]:
            value = str(payload.get(key, "")).lower()
            if any(word in value for word in ['login_required', 'browser_endpoint_unreachable']):
                return "BROWSER_OR_LOGIN_REQUIRED"
            if any(word in value for word in ['rate_limited', 'security_verification', 'captcha', 'access_blocked']):
                return "ACCESS_BLOCKED"
        for key in ['data', 'search', 'page_diagnostic', 'notes']:
            code = socai_gate(payload.get(key))
            if code:
                return code
    elif isinstance(payload, list):
        return next((code for item in payload if (code := socai_gate(item))), None)
    return None


def socai_page_issue(payload):
    """Map known CLI page diagnostics without exposing raw provider errors."""
    if isinstance(payload, dict):
        detail = ' '.join(str(payload.get(k, '')) for k in ['reason', 'page_error', 'error']).lower()
        if 'page.navigate timed out' in detail:
            return ('PAGE_NAVIGATION_TIMEOUT', '浏览器打开小红书页面超时；Chrome已连接仍不代表网页完成导航')
        if 'search did not transition to a valid xiaohongshu result page' in detail:
            return ('SEARCH_PAGE_TRANSITION_FAILED', '小红书搜索页未正常打开；浏览器连接状态另行记录')
        if 'note overlay did not open' in detail:
            return ('NOTE_OPEN_FAILED', '搜索卡片后的帖子页面未打开；可能是网页变化或限流，原因尚未确认')
        for key in ['data', 'search', 'page_diagnostic', 'notes']:
            issue = socai_page_issue(payload.get(key))
            if issue:
                return issue
    elif isinstance(payload, list):
        return next((issue for item in payload if (issue := socai_page_issue(item))), None)
    return None


class Socai:
    name = "小红书 / socai"

    def __init__(self, settings: Settings):
        self.settings = settings
        self.command_calls = 0
        self.on_retry = lambda query: None
        self.on_query = lambda query: None
        self.on_trace = lambda stage, status, detail, duration, data: None
        self.read_ids = set()
        self.on_evidence = lambda evidence: None
        self.blocked_code = None
        self.retry_reason = "未取得正文"
        self.timeout_seconds = settings.socai_connect_timeout + settings.source_timeout * 2 + 5

    async def browser_ready(self):
        self.command_calls += 1
        state = await command_json(self.settings.socai_bin, ['status', '--json'],
            replace(self.settings, source_timeout=5), 'socai')
        # status swallows IPC errors as DAEMON_UNAVAILABLE. Distinguish a sandbox denial
        # before a platform command attempts to spawn another daemon.
        if state.get('daemon_running') is False and os.name == 'posix':
            from pathlib import Path
            home = Path(os.getenv('SOCAI_HOME', str(Path.home() / '.socai')))
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                    client.settimeout(.2)
                    client.connect(str(home / 'rust-daemon.sock'))
            except OSError as error:
                if error.errno in {errno.EPERM, errno.EACCES}:
                    raise SourceFailure(self.name, 'DAEMON_IPC_PERMISSION_DENIED',
                        '执行环境无权连接现有socai daemon；请从正常本机终端运行，不要重建daemon') from None
        ready = state.get('browser_connected') is True
        self.on_trace('browser_connection', 'ok' if ready else 'info',
            '复用已经连接的Chrome' if ready else f'等待首次Chrome连接授权，最多{self.settings.socai_connect_timeout}秒；本轮不自动重复连接',
            0, {k:state.get(k) for k in ['browser_connected','browser_state','daemon_running','error_code']})
        return ready

    async def _command(self, args, stage, data):
        needs_connection = stage in {'social_preview', 'social_scan'} and not await self.browser_ready()
        self.command_calls += 1
        start = monotonic()
        try:
            normal_timeout = min(self.settings.source_timeout, 60 if stage == 'social_preview' else 40) if stage != 'social_scan' else self.settings.source_timeout
            timeout = self.settings.socai_connect_timeout if needs_connection else normal_timeout
            payload = await command_json(self.settings.socai_bin, args, replace(self.settings, source_timeout=timeout), self.name)
        except asyncio.CancelledError:
            self.on_trace(stage, "failed", "研究预算到达或任务取消；已读正文保留", int((monotonic()-start)*1000), data)
            raise
        except TimeoutError:
            if needs_connection:
                self.command_calls += 1
                connected = False
                try:
                    state = await command_json(self.settings.socai_bin, ['status','--json'],
                        replace(self.settings,source_timeout=5),'socai')
                    connected = state.get('browser_connected') is True
                except Exception:
                    pass
                code = 'SOCIAL_SEARCH_TIMEOUT' if connected else 'CONNECTION_APPROVAL_TIMEOUT'
                detail = 'Chrome已连接，但首次搜索超时；保留连接' if connected else '首次连接等待超时；停止该来源，避免再次弹出授权请求'
                self.on_trace(stage, 'failed', detail, int((monotonic()-start)*1000), data | {'failure_code':code})
                raise SourceFailure(self.name, code, detail) from None
            # After an actual connection attempt timed out, a cached endpoint failure is actionable.
            # Before attempting a search, disconnected status alone is not sufficient evidence.
            code = None
            if stage == "social_preview":
                self.command_calls += 1
                try:
                    state = await command_json(self.settings.socai_bin, ['status', '--json'],
                        replace(self.settings, source_timeout=5), self.name)
                    if state.get('error_code') in {'BROWSER_ENDPOINT_UNREACHABLE', 'BROWSER_DISCONNECTED'}:
                        code = 'BROWSER_OR_LOGIN_REQUIRED'
                except Exception:
                    pass
            self.on_trace(stage, "failed", "浏览器连接未建立" if code else "命令超时",
                          int((monotonic()-start)*1000), data | {"failure_code": code or "TimeoutError"})
            if code:
                raise SourceFailure(self.name, code, "搜索超时后仍无法连接 Chrome；请重新连接浏览器") from None
            raise
        except Exception as error:
            from .safety import source_error
            self.on_trace(stage, "failed", str(source_error(self.name, error)), int((monotonic()-start)*1000), data)
            raise
        self.on_trace(stage, "ok", "命令已返回；是否读到正文另行核对", int((monotonic()-start)*1000), data)
        return payload

    async def _selective(self, query):
        payload = await self._command(["xhs", "search", query, "--preview", "--pretty"], "social_preview", {"query": query})
        if code := socai_gate(payload):
            raise SourceFailure(self.name, code, "社区页面要求登录或限制访问；停止该来源")
        root = payload.get("data", payload)
        if not isinstance(root, dict):
            raise SourceFailure(self.name, 'SCHEMA_CHANGED', '搜索结果结构变化；不能读取卡片')
        search = root.get("search", root) if isinstance(root, dict) else {}
        cards = search.get("cards", root.get("cards", [])) if isinstance(search, dict) else []
        if not isinstance(cards, list):
            cards = []
        if not cards and (issue := socai_page_issue(payload)):
            raise SourceFailure(self.name, *issue)
        candidates = []
        for card in cards[:40]:
            if not isinstance(card, dict):
                continue
            note_id, token = str(card.get("note_id", "")), str(card.get("xsec_token", ""))
            # socai 0.6.1 trims xsec_token but keeps the note URL in lean cards.
            # Use its live query token in memory only; never persist the token/URL query.
            link = urlparse(str(card.get('url', card.get('link', ''))))
            if not token and link.hostname in {'www.xiaohongshu.com','xiaohongshu.com'} and link.path.rsplit('/',1)[-1] == note_id:
                token = parse_qs(link.query).get('xsec_token', [''])[0]
            card = dict(card, xsec_token=token)
            if not re.fullmatch(r"[a-zA-Z0-9_-]{8,80}", note_id) or not re.fullmatch(r"[a-zA-Z0-9_=-]{1,600}", token):
                continue
            title = str(card.get("title", ""))
            score = sum(word in title for word in query.split())
            score -= 5 * any(word in title for word in ["代订", "加微信", "联系出票"])
            candidates.append((note_id in self.read_ids, -score, card))
        # Keep browser navigation serial. A single failed note cannot discard earlier bodies.
        candidates.sort(key=lambda c: (c[0], c[1]))
        unique, selected = set(), []
        for seen, score, card in candidates:
            if card['note_id'] not in unique:
                selected.append(card)
                unique.add(card['note_id'])
            if len(selected) == self.settings.socai_notes:
                break
        result, last_error = [], None
        for card in selected:
            try:
                opened = await self._command(["xhs", "get-notes", "--note",
                    f"{card['note_id']}={card['xsec_token']}", "--num-comments",
                    str(self.settings.socai_comments), "--pretty"], "social_read", {"query": query, "note_id": card['note_id']})
                readable = socai_evidence(opened, query)
                if not readable:
                    if code := socai_gate(opened):
                        raise SourceFailure(self.name, code, "社区页面要求登录或限制访问；停止该来源")
                    if issue := socai_page_issue(opened):
                        raise SourceFailure(self.name, *issue)
                    raise SourceFailure(self.name, "EMPTY_BODY", "帖子未返回正文；卡片不计入证据")
                result.extend(readable)
                self.read_ids.add(card['note_id'])
                self.on_evidence(readable)
            except Exception as error:
                last_error = error
                if isinstance(error, SourceFailure) and error.code in {"ACCESS_BLOCKED", "BROWSER_OR_LOGIN_REQUIRED", "NOT_INSTALLED"}:
                    self.blocked_code = error.code
                    if result:
                        for item in result:
                            item.warnings.append("后续帖子读取受阻；本次仅保留已读正文")
                        return result
                    raise
                self.on_trace("social_read_result", "failed", "此篇未取得正文；继续下一篇",
                    0, {"note_id": card['note_id'], "query": query})
        if not result and last_error:
            raise last_error
        return result

    def scan_result(self, data, result, query):
        if issue := socai_page_issue(data):
            self.on_trace('social_read_result', 'failed', '完整扫描只取得部分正文；' + issue[1],
                          0, {'query':query, 'failure_code':issue[0], 'retained_bodies':len(result)})
            for item in result:
                item.warnings.append(issue[1])
        return result

    async def search(self, query: str) -> list[Evidence]:
        # Separate geographical words glued together in a natural-language
        # query. This changes formatting, not the destination or intent.
        self.retry_reason = "前次未取得可读正文"
        self.blocked_code = None
        query = re.sub(r"(香港快运|大湾区航空|大湾区|香港航空|香港|深圳|日本|东京|大阪|名古屋|福冈|冲绳|札幌|机票)", r" \1 ", query)
        query = " ".join(w for w in query.split() if w not in {"飞", "出发", "哪里", "呢", "？", "?"})
        if self.settings.socai_mode == "selective":
            self.on_query(query)
            try:
                result = await self._selective(query)
                if result:
                    return result
            except (TimeoutError, SourceFailure) as error:
                if isinstance(error, SourceFailure) and error.code not in {"EMPTY_BODY", "NO_READABLE_POSTS", "INVALID_RESPONSE", "CLI_FAILED", "SCHEMA_CHANGED", "SEARCH_PAGE_TRANSITION_FAILED", "NOTE_OPEN_FAILED", "PAGE_NAVIGATION_TIMEOUT"}:
                    raise
                self.retry_reason = "逐篇读取未成功；仅回退一次socai完整扫描"
            retry = " ".join(w for w in query.split() if not re.fullmatch(r"(?:20\d{2}年)?\d{1,2}月", w)
                             and w not in {"便宜", "特价", "是否结束"})
            self.on_retry(retry)
            self.on_query(retry)
            data = await self._command(['xhs','search',retry,'--num-notes',str(self.settings.socai_notes),
                '--num-comments',str(self.settings.socai_comments),'--pretty'], 'social_scan', {'query':retry,'fallback_from':'selective'})
            result = socai_evidence(data, retry)
            if not result:
                if code := socai_gate(data):
                    raise SourceFailure(self.name,code,'完整扫描遇登录或访问限制；停止来源')
                if issue := socai_page_issue(data):
                    raise SourceFailure(self.name, *issue)
                raise SourceFailure(self.name, "NO_READABLE_POSTS", "逐篇读取和完整扫描均未取得正文")
            return self.scan_result(data, result, retry)
        self.on_query(query)
        try:
            data = await self._command([
                "xhs", "search", query, "--num-notes", str(self.settings.socai_notes), "--num-comments", str(self.settings.socai_comments),
                "--pretty",
            ], 'social_scan', {'query':query})
        except TimeoutError:
            data = {}
            self.retry_reason = "前次命令超时"
        result = socai_evidence(data, query)
        if not result:
            if code := socai_gate(data):
                raise SourceFailure(self.name, code, "社区页面要求登录或限制访问；停止该来源")
            if data.get('reason') or data.get('page_error'):
                self.retry_reason = clean_text(str(data.get('reason') or data.get('page_error')), 350)
            # A filtered result page can fail to settle. Retry once with the
            # same intent as short keywords, without the optional sort filter.
            words = re.findall(r"香港快运|大湾区|香港|深圳|日本|东京|大阪|名古屋|福冈|冲绳|札幌|机票|促销|特价|11月", query)
            # Broaden retrieval only: date constraints still apply to fare research.
            tokens = [w for w in query.split() if w not in {"便宜", "特价", "是否结束", "哪里便宜"}
                      and not re.fullmatch(r"(?:20\d{2}年)?\d{1,2}月", w)]
            retry = " ".join(tokens[:5]) if len(tokens) >= 3 else (
                " ".join(dict.fromkeys(words)) if len(words) >= 2 else query)
            self.on_retry(retry)
            self.on_query(retry)
            data = await self._command(["xhs", "search", retry,
                "--num-notes", str(self.settings.socai_notes), "--num-comments", str(self.settings.socai_comments), "--pretty"], 'social_scan', {'query':retry})
            result = socai_evidence(data, retry)
        if not result:
            if issue := socai_page_issue(data):
                raise SourceFailure(self.name, *issue)
            reason = clean_text(str(data.get('reason') or data.get('page_error') or '来源未提供进一步原因'), 350)
            raise SourceFailure(self.name, "NO_READABLE_POSTS", "未取得可阅读的帖子正文；" + reason)
        return self.scan_result(data, result, query)


class RedditCommunity:
    """Public community fallback; full selftext/comments, never search snippets."""
    name = "Reddit public"

    def __init__(self, settings: Settings):
        self.settings = settings

    async def search(self, query: str) -> list[Evidence]:
        async with httpx.AsyncClient(timeout=min(15, self.settings.source_timeout), follow_redirects=False,
                                     headers={"User-Agent": "FareScout-POC/0.1 (read-only research)"}) as client:
            response = await client.get("https://www.reddit.com/search.json", params={
                "q": query, "sort": "new", "limit": 5, "t": "month", "type": "link",
            })
            if response.status_code in {401, 403, 429}:
                raise SourceFailure(self.name, "ACCESS_BLOCKED", "公共社区访问受限；不绕过访问控制")
            response.raise_for_status()
            listing = response.json().get("data", {}).get("children", [])
            result = []
            for item in listing[:5]:
                data = item.get("data", {})
                body = clean_text(data.get("selftext"))
                path = data.get("permalink", "")
                if not body or not re.fullmatch(r"/r/[\w]+/comments/[\w]+/[^?]*", path):
                    continue
                url = "https://www.reddit.com" + path
                comments = []
                details = await client.get(url + ".json", params={"limit": 5, "depth": 1})
                if details.status_code == 200:
                    rows = details.json()
                    if isinstance(rows, list) and len(rows) > 1:
                        for c in rows[1].get("data", {}).get("children", [])[:5]:
                            d = c.get("data", {})
                            if d.get("body"):
                                comments.append(Comment(text=clean_text(d["body"], 1500)))
                elif details.status_code in {401, 403, 429}:
                    raise SourceFailure(self.name, "ACCESS_BLOCKED", "评论读取受限，已停止该来源")
                result.append(Evidence(
                    id=identity("reddit", data.get("id"), body), source=self.name, url=public_url(url),
                    query=query, title=clean_text(data.get("title"), 300), body=body, comments=comments,
                    published_at=str(data.get("created_utc", "")) or None,
                    warnings=["公开 API 备用来源；与小红书覆盖不同"],
                ))
            if not result:
                raise SourceFailure(self.name, "NO_READABLE_POSTS", "查询未找到带正文的社区帖子")
            return result


def parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def matches_request(segments: list[Segment], request: FareRequest) -> bool:
    """Check route/date/return and conservatively exclude overnight travel."""
    if not segments:
        return False
    try:
        if segments[0].origin != request.origin or parse_datetime(segments[0].departure).date() != request.outbound_date:
            return False
        if request.return_date is None:
            if segments[-1].destination != request.destination:
                return False
        else:
            boundaries = [i for i, s in enumerate(segments[:-1]) if s.destination == request.destination
                          and segments[i + 1].origin == request.destination]
            if not boundaries:
                return False
            return_leg = segments[boundaries[0] + 1]
            if parse_datetime(return_leg.departure).date() != request.return_date or segments[-1].destination != request.origin:
                return False
        for i, segment in enumerate(segments):
            dep, arr = parse_datetime(segment.departure), parse_datetime(segment.arrival)
            if i and segments[i - 1].destination != segment.origin:
                return False
            if request.no_red_eye and (not 6 <= dep.hour < 22 or not 6 <= arr.hour < 22 or dep.date() != arr.date()):
                return False
        return True
    except (ValueError, TypeError):
        return False


def flyai_fares(payload: dict, request: FareRequest) -> list[Fare]:
    if str(payload.get("status", 0)) != "0":
        raise SourceFailure("FlyAI", "API_ERROR", "FlyAI 未返回成功状态")
    root = payload.get("data", {})
    if not isinstance(root, dict) or not isinstance(root.get("itemList", []), list):
        raise SourceFailure("FlyAI", "SCHEMA_CHANGED", "响应不含预期 itemList")
    fares = []
    for item in root.get("itemList", []):
        if not isinstance(item, dict):
            continue
        value = str(item.get("adultPrice", item.get("ticketPrice", "")))
        # adultPrice is documented in CNY. Reject unrelated currencies/product ranges.
        match = re.fullmatch(r"(?:¥|￥|CNY\s*)?([0-9]+(?:\.[0-9]{1,2})?)", value.strip())
        if not match or float(match[1]) <= 0:
            continue
        segments = []
        journeys = item.get("journeys", [])
        if not isinstance(journeys, list) or len(journeys) != (2 if request.return_date else 1):
            continue
        for journey in journeys:
            for segment in journey.get("segments", []):
                segments.append(Segment(
                    origin=str(segment.get("depStationCode", "")), destination=str(segment.get("arrStationCode", "")),
                    departure=str(segment.get("depDateTime", "")), arrival=str(segment.get("arrDateTime", "")),
                    airline=clean_text(segment.get("marketingTransportName"), 100) or "未知",
                    flight_number=clean_text(segment.get("marketingTransportNo"), 50) or "未知",
                ))
        if not matches_request(segments, request):
            continue
        if any(s.get("seatClassName") and s["seatClassName"] not in {"经济舱", "Economy", "economy"}
               for j in journeys for s in j.get("segments", [])):
            continue
        fares.append(Fare(
            id=identity("flyai", request.model_dump_json(), value, [s.model_dump() for s in segments]),
            source="FlyAI / 飞猪", request=request, amount=float(match[1]),
            source_url="https://flyai.open.fliggy.com/", segments=segments,
            price_basis="adult_fare_tax_unknown",
            restrictions=["FlyAI adultPrice/ticketPrice 报价；税费总额未确认，不能等同于含税总价",
                          "未访问 jumpUrl 或任何预订页"] + (["FlyAI 体验模式：部分结果受限"] if "体验模式" in str(payload.get("systemMessage", "")) else []),
        ))
    return sorted(fares, key=lambda f: f.amount)[:3]


class FlyAI:
    name = "FlyAI"

    def __init__(self, settings: Settings):
        self.settings = settings

    async def explore(self, origin: str, destination: str, goal: Goal) -> list[DateSample]:
        args = ["search-flight", "--origin", origin, "--destination", destination,
                "--dep-date-start", str(goal.date_from), "--dep-date-end", str(goal.date_to),
                "--seat-class-name", "economy", "--sort-type", "3"]
        if goal.trip_type == "round_trip":
            from datetime import timedelta
            args += ["--back-date-start", str(goal.date_from + timedelta(days=goal.stay_days)),
                     "--back-date-end", str(goal.date_to + timedelta(days=goal.stay_days))]
        data = await command_json(self.settings.flyai_bin, args, self.settings, self.name)
        if str(data.get("status", 0)) != "0":
            raise SourceFailure(self.name, "API_ERROR", "范围查询未返回成功状态")
        samples = {}
        for item in data.get("data", {}).get("itemList", []):
            try:
                journeys = item["journeys"]
                outbound = parse_datetime(journeys[0]["segments"][0]["depDateTime"]).date()
                returned = parse_datetime(journeys[1]["segments"][0]["depDateTime"]).date() if len(journeys) == 2 else None
                if not goal.date_from <= outbound <= goal.date_to:
                    continue
                if goal.trip_type == "round_trip" and (returned is None or (returned - outbound).days != goal.stay_days):
                    continue
                if goal.trip_type == "one_way" and returned is not None:
                    continue
                req = FareRequest(origin=origin, destination=destination, outbound_date=outbound,
                                  return_date=returned, no_red_eye=goal.no_red_eye)
                fares = flyai_fares({"status": 0, "data": {"itemList": [item]}}, req)
                if fares:
                    f = fares[0]
                    sample = DateSample(date=outbound, source=self.name, stage="range", status="ok",
                                        amount=f.amount, price_basis=f.price_basis,
                                        detail="范围返回的探索价；只计返回日期，不代表查询范围内每一天均已覆盖")
                    if outbound not in samples or sample.amount < samples[outbound].amount:
                        samples[outbound] = sample
            except (KeyError, IndexError, TypeError, ValueError):
                continue
        if not samples:
            raise SourceFailure(self.name, "NO_RANGE_DATES", "范围查询未返回可核对日期；改用有预算代表日采样")
        return sorted(samples.values(), key=lambda s: s.amount)[:5]

    async def verify(self, request: FareRequest) -> list[Fare]:
        args = ["search-flight", "--origin", request.origin, "--destination", request.destination,
                "--dep-date", str(request.outbound_date), "--seat-class-name", "economy", "--sort-type", "3"]
        if request.return_date:
            args += ["--back-date", str(request.return_date)]
        if request.no_red_eye:
            args += ["--dep-hour-start", "6", "--dep-hour-end", "21", "--arr-hour-start", "6", "--arr-hour-end", "21"]
        data = await command_json(self.settings.flyai_bin, args, self.settings, self.name)
        fares = flyai_fares(data, request)
        if not fares:
            raise SourceFailure(self.name, "NO_MATCHING_FARE", "没有路线/日期/舱位/条件均可核对的实时航班报价")
        return fares


def price_insights(payload, request, amount):
    raw = payload.get("price_insights", {})
    if not isinstance(raw, dict):
        return {}
    bounds = raw.get("typical_price_range")
    lowest = raw.get("lowest_price")
    numeric = lambda n: not isinstance(n, bool) and isinstance(n, (int, float)) and math.isfinite(n) and n > 0
    if not isinstance(bounds, list) or len(bounds) != 2 or not all(numeric(n) for n in bounds) or bounds[0] > bounds[1]:
        return {}
    params = payload.get("search_parameters", {})
    comparable = (not request.no_red_eye and numeric(lowest) and amount == lowest
                  and str(params.get("type", "2")) == "2" and str(params.get("travel_class", "1")) == "1"
                  and str(params.get("adults", "1")) == "1")
    return {"typical_price_range": bounds, "lowest_price": lowest if numeric(lowest) else None,
            "price_level": raw.get("price_level") if raw.get("price_level") in {"low", "typical", "high"} else "unknown",
            "comparable": comparable,
            "reason": "同一查询最低含税价格" if comparable else "本地红眼过滤或已选价格与来源最低价不一致；不作折扣比较",
            "basis": "Google查询价格洞察，不是FareScout完整历史数据库"}


def serpapi_fares(payload: dict, request: FareRequest) -> list[Fare]:
    if payload.get("error"):
        raise SourceFailure("SerpAPI", "API_ERROR", "Google Flights 查询失败或没有可用航班")
    metadata = payload.get("search_metadata", {})
    params = payload.get("search_parameters", {})
    expected = {"departure_id": request.origin, "arrival_id": request.destination,
                "outbound_date": str(request.outbound_date), "currency": "CNY"}
    if any(str(params.get(k)) != str(v) for k, v in expected.items()) or metadata.get("status") != "Success":
        raise SourceFailure("SerpAPI", "UNVERIFIED_PARAMETERS", "返回的搜索条件/状态与请求不一致")
    if request.return_date:
        # Google Flights first-leg prices may require departure_token selection.
        # Never mislabel a first-leg result as a complete round trip.
        raise SourceFailure("SerpAPI", "ROUND_TRIP_INCOMPLETE", "尚未实现 departure_token 回程确认；本轮往返报价改用 FlyAI")
    fares = []
    for item in [*payload.get("best_flights", []), *payload.get("other_flights", [])]:
        price = item.get("price")
        if isinstance(price, bool) or not isinstance(price, (float, int)) or price <= 0:
            continue
        segments = []
        for flight in item.get("flights", []):
            departure, arrival = flight.get("departure_airport", {}), flight.get("arrival_airport", {})
            segments.append(Segment(
                origin=str(departure.get("id", "")), destination=str(arrival.get("id", "")),
                departure=str(departure.get("time", "")), arrival=str(arrival.get("time", "")),
                airline=clean_text(flight.get("airline"), 100) or "未知",
                flight_number=clean_text(flight.get("flight_number"), 50) or "未知",
            ))
        if not matches_request(segments, request):
            continue
        if any(f.get("travel_class") and f["travel_class"] != "Economy" for f in item.get("flights", [])):
            continue
        fares.append(Fare(
            id=identity("serpapi", request.model_dump_json(), price, [s.model_dump() for s in segments]),
            source="Google Flights / SerpAPI", request=request, amount=price, segments=segments,
            source_url="https://www.google.com/travel/flights",
            price_basis="total_including_taxes",
            price_insights=price_insights(payload, request, price),
            restrictions=["航班搜索报价；额外行李/支付方式等费用可能另计", "只读搜索，未进入预订流程"],
        ))
    return sorted(fares, key=lambda f: f.amount)[:3]


class SerpAPI:
    name = "SerpAPI"

    def __init__(self, settings: Settings):
        self.settings = settings

    async def explore(self, origin: str, destination: str, goal: Goal) -> list[DateSample]:
        if not self.settings.serpapi_key:
            raise SourceFailure(self.name, "MISSING_KEY", "尚未配置 SERPAPI_API_KEY")
        if goal.trip_type != "one_way":
            raise SourceFailure(self.name, "RANGE_UNSUPPORTED", "Explore日期线索暂只接收单程；回退FlyAI")
        month = goal.date_from.month if (goal.date_from.year, goal.date_from.month) == (goal.date_to.year, goal.date_to.month) else 0
        params = dict(engine="google_travel_explore", departure_id=origin, arrival_id=destination,
            month=month, type=2, currency="CNY", hl="en", adults=1, travel_class=1, no_cache="true",
            api_key=self.settings.serpapi_key)
        async with httpx.AsyncClient(timeout=self.settings.source_timeout) as client:
            response = await client.get("https://serpapi.com/search.json", params=params)
            if response.status_code in {401,403,429}:
                raise SourceFailure(self.name, "AUTH_OR_QUOTA", "Explore鉴权或配额不可用")
            response.raise_for_status()
            samples = explore_dates(response.json(), origin, destination, goal)
        if not samples:
            raise SourceFailure(self.name, "NO_RANGE_HINT", "Explore未返回窗口内同路线单程日期线索；回退FlyAI")
        return samples

    async def verify(self, request: FareRequest) -> list[Fare]:
        if not self.settings.serpapi_key:
            raise SourceFailure(self.name, "MISSING_KEY", "尚未配置 SERPAPI_API_KEY")
        if request.return_date:
            raise SourceFailure(self.name, "ROUND_TRIP_INCOMPLETE", "往返交由 FlyAI；当前适配器仅确认完整单程价格")
        params = {
            "engine": "google_flights", "departure_id": request.origin, "arrival_id": request.destination,
            "outbound_date": str(request.outbound_date), "type": "2", "currency": "CNY", "hl": "en",
            "adults": "1", "travel_class": "1", "no_cache": "true", "api_key": self.settings.serpapi_key,
        }
        async with httpx.AsyncClient(timeout=self.settings.source_timeout) as client:
            response = await client.get("https://serpapi.com/search.json", params=params)
            if response.status_code in {401, 403, 429}:
                raise SourceFailure(self.name, "AUTH_OR_QUOTA", "鉴权/配额/访问受限，已停止该来源")
            response.raise_for_status()
            fares = serpapi_fares(response.json(), request)
        if not fares:
            raise SourceFailure(self.name, "NO_MATCHING_FARE", "没有满足全部条件且可核对的报价")
        return fares


def explore_dates(payload, origin, destination, goal):
    """Strict discovery-only parser. A hint must still pass exact fare verification."""
    params = payload.get('search_parameters', {})
    if (payload.get('search_metadata', {}).get('status') != 'Success' or
            params.get('departure_id') != origin or params.get('arrival_id') != destination or
            str(params.get('type')) != '2' or params.get('currency') != 'CNY' or payload.get('end_date')):
        return []
    try:
        outbound = date.fromisoformat(payload.get('start_date', ''))
    except (ValueError,TypeError):
        return []
    if not goal.date_from <= outbound <= goal.date_to:
        return []
    prices = [f.get('price') for f in payload.get('flights', []) if isinstance(f,dict)
              and f.get('departure_airport', {}).get('id') == origin and f.get('arrival_airport', {}).get('id') == destination]
    prices = [float(p) for p in prices if isinstance(p,(int,float)) and not isinstance(p,bool) and math.isfinite(p) and p > 0]
    return [DateSample(date=outbound, source='SerpAPI / Google Travel Explore', stage='range', status='ok',
        amount=min(prices), price_basis='adult_fare_tax_unknown',
        detail='Explore日期线索；未经精确航段、时间及含税条件核对，不能当作最终报价')] if prices else []
