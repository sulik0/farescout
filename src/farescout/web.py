from __future__ import annotations

import asyncio
import json
import threading
import time
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from .engine import Researcher, Store
from .report import render_report
from .models import Event, now
from .safety import clean_text, source_error


class Application:
    def __init__(self, settings, researcher_factory=Researcher):
        self.settings, self.factory = settings, researcher_factory
        self.store = Store(settings.data_dir)
        self.lock = threading.RLock()
        self.active = None
        self.error = None
        self.error_session = None
        self.recovery_stop = threading.Event()
        self.recovery_target = None
        self.closed = False
        # A UI reload or service restart must not require starting a new turn.
        for path in sorted(self.store.root.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                saved = self.store.load(path.stem)
                if saved and saved.turns:
                    watch = saved.turns[-1].checkpoint.get('browser_recovery', {})
                    if watch.get('state') == 'waiting':
                        self.arm_recovery(saved.id, deadline=watch['deadline'])
                        break
            except (ValueError, KeyError, OSError):
                continue

    def recovery_event(self, saved, status, detail, *, duration_ms=None, data=None):
        turn = saved.turns[-1]
        turn.events.append(Event(stage='browser_recovery', status=status, detail=detail, turn_id=turn.id, duration_ms=duration_ms, data=data or {}))
        self.store.save(saved)

    def cancel_recovery(self):
        self.recovery_stop.set()
        if self.recovery_target:
            saved = self.store.load(self.recovery_target[0])
            if saved and saved.turns[-1].id == self.recovery_target[1]:
                watch = saved.turns[-1].checkpoint.get('browser_recovery', {})
                if watch.get('state') == 'waiting':
                    watch['state'] = 'cancelled'
                    self.store.save(saved)
        self.recovery_target = None

    def arm_recovery(self, session_id, *, deadline=None):
        from .providers import Socai
        from datetime import datetime
        with self.lock:
            if self.active or self.closed:
                return
            self.cancel_recovery()
            saved = self.store.load(session_id)
            if not saved or not saved.turns or saved.turns[-1].status == 'complete':
                return
            turn = saved.turns[-1]
            end = datetime.fromisoformat(deadline) if deadline else now() + timedelta(seconds=self.settings.recovery_wait_seconds)
            managed = self.settings.social_browser == 'managed'
            turn.checkpoint['browser_recovery'] = {'state':'waiting', 'deadline':end.isoformat(), 'mode':self.settings.social_browser}
            self.recovery_event(saved, 'info', '已保留研究；专用浏览器断线后自动尝试连接一次，再继续未完成步骤。' if managed else '已保留研究；等待 Chrome 连接，确认后自动继续未完成步骤。状态检查不会反复请求授权。')
            stop = self.recovery_stop = threading.Event()
            self.recovery_target = (session_id, turn.id)
        def watch():
            source = Socai(self.settings)
            while not stop.is_set():
                try:
                    ready = asyncio.run(source.browser_ready()) if now() < end else False
                    # Never try to launch existing Chrome automatically. The managed
                    # mode is confirmed by daemon status, not just a UI preference.
                    if (not ready and managed and source.connection.get('profile_mode') == 'managed'
                            and source.connection.get('reported_browser_connected') is not True and now() < end):
                        with self.lock:
                            if stop.is_set() or self.active or self.recovery_target != (session_id, turn.id):
                                return
                            current = self.store.load(session_id)
                            if not current or current.turns[-1].id != turn.id:
                                return
                            cp = current.turns[-1].checkpoint
                            attempt = cp.get('managed_reconnect_attempts', 0)
                            if attempt < 1:
                                # Persist before dispatch; a service restart cannot
                                # create an unbounded sequence of new connections.
                                cp['managed_reconnect_attempts'] = attempt + 1
                                self.active = session_id
                                self.recovery_event(current, 'info', '正在重新连接专用 Chrome；不清理 profile，也不重启 socai daemon。')
                                query = (cp.get('queries') or ['香港 日本 机票'])[0]
                        if attempt < 1:
                            from .providers import socai_gate
                            async def connect_managed():
                                return await asyncio.wait_for(source._command(
                                    ['xhs','search',query,'--num-notes','0','--pretty'],
                                    'social_preview', {'recovery':True}), max(.01, (end-now()).total_seconds()))
                            began, commands_before = time.monotonic(), source.command_calls
                            try:
                                payload = asyncio.run(connect_managed())
                            finally:
                                with self.lock:
                                    if self.active == session_id:
                                        self.active = None
                                    if not stop.is_set():
                                        latest = self.store.load(session_id)
                                        if latest and latest.turns[-1].id == turn.id:
                                            metrics = {'connection_attempts':1, 'cli_commands':source.command_calls-commands_before,
                                                'seconds':round(time.monotonic()-began,3)}
                                            latest.turns[-1].checkpoint['browser_recovery'].update(metrics)
                                            self.recovery_event(latest, 'info', '专用浏览器连接尝试结束；接下来核对连接与页面状态。',
                                                duration_ms=int(metrics['seconds']*1000), data=metrics)
                            if socai_gate(payload):
                                with self.lock:
                                    if stop.is_set():
                                        return
                                    latest = self.store.load(session_id)
                                    if latest and latest.turns[-1].id == turn.id:
                                        latest.turns[-1].checkpoint['browser_recovery']['state'] = 'needs_user'
                                        self.recovery_event(latest, 'failed', '专用浏览器页面要求登录或验证；研究已保留，请在专用窗口处理后继续。')
                                    self.recovery_target = None
                                return
                            ready = asyncio.run(source.browser_ready())
                except Exception as error:
                    # Config/version failures must not become connection attempts.
                    failure = source_error('socai', error)
                    user_action = failure.code == 'ACCESS_BLOCKED' or (
                        failure.code == 'BROWSER_OR_LOGIN_REQUIRED' and source.connection.get('browser_connected') is True)
                    if user_action or failure.code in {'BROWSER_CONFIG_UNSUPPORTED','BROWSER_CONFIG_MISMATCH','BROWSER_CONFIG_INVALID','DAEMON_VERSION_MISMATCH'}:
                        with self.lock:
                            if stop.is_set():
                                return
                            latest = self.store.load(session_id)
                            if latest and latest.turns[-1].id == turn.id:
                                latest.turns[-1].checkpoint['browser_recovery']['state'] = 'needs_user'
                                self.recovery_event(latest, 'failed', str(failure))
                            self.recovery_target = None
                        return
                    if managed:
                        with self.lock:
                            if not stop.is_set():
                                latest = self.store.load(session_id)
                                if latest and latest.turns[-1].id == turn.id:
                                    state = latest.turns[-1].checkpoint['browser_recovery']
                                    if state.get('last_error') != failure.code:
                                        state['last_error'] = failure.code
                                        self.recovery_event(latest, 'failed', str(failure))
                    ready = False
                with self.lock:
                    if stop.is_set() or self.active or self.recovery_target != (session_id, turn.id):
                        return
                    latest = self.store.load(session_id)
                    if not latest or not latest.turns or latest.turns[-1].id != turn.id or latest.turns[-1].status == 'complete':
                        self.recovery_target = None
                        return
                    state = latest.turns[-1].checkpoint['browser_recovery']
                    if ready:
                        state.update(state='resumed', resumed_at=now().isoformat())
                        self.recovery_event(latest, 'ok', 'Chrome 已重新连接；自动恢复原轮次，保留已读正文、日期覆盖和历史失败。')
                        self.start(session_id, '', resume=True)
                        return
                    if now() >= end:
                        state['state'] = 'expired'
                        self.recovery_event(latest, 'failed', '等待连接超时；研究仍保留，可稍后点击重新连接并继续。')
                        self.recovery_target = None
                        return
                stop.wait(self.settings.recovery_poll_seconds)
        threading.Thread(target=watch, daemon=True).start()

    def reconnect(self, session_id):
        from .providers import Socai
        with self.lock:
            if self.active or self.closed:
                raise RuntimeError('已有研究或连接请求进行中')
            saved = self.store.load(session_id)
            if not saved or not saved.turns or saved.turns[-1].status == 'complete':
                raise ValueError('没有可恢复的研究')
            self.cancel_recovery()
            self.active, self.error, self.error_session = session_id, None, None
        def connect():
            async def attempt():
                source = Socai(self.settings)
                if not await source.browser_ready():
                    # One CLI request. No reconnect loop, no daemon stop or profile switch.
                    query = (saved.turns[-1].checkpoint.get('queries') or ['香港 日本 机票'])[0]
                    await source._command(['xhs','search',query,'--num-notes','0','--pretty'], 'social_preview', {'recovery':True})
            try:
                asyncio.run(attempt())
            except Exception as error:
                self.error = str(source_error('socai', error))
                self.error_session = session_id
            finally:
                with self.lock:
                    self.active = None
                self.arm_recovery(session_id)
        threading.Thread(target=connect, daemon=True).start()

    def start(self, session_id, message, *, resume=False):
        self.store.path(session_id)
        if resume:
            saved = self.store.load(session_id)
            if not saved or not saved.turns or saved.turns[-1].status == 'complete':
                raise ValueError('只能恢复已有未完成的最后一轮研究')
            message = saved.turns[-1].user_input
        if not message.strip() or len(message) > 3000:
            raise ValueError("请输入1～3000字的研究需求")
        with self.lock:
            if self.active or self.closed:
                raise RuntimeError("已有研究进行中，请等待完成再继续")
            self.cancel_recovery()
            self.active, self.error, self.error_session = session_id, None, None
        def work():
            researcher = None
            try:
                researcher = self.factory(self.settings)
                options = {'resume': True} if resume else {}
                asyncio.run(researcher.run(clean_text(message, 3000), self.store.load(session_id), session_id, **options))
            except Exception as error:
                self.error = str(source_error("research", error))
                self.error_session = session_id
            finally:
                with self.lock:
                    self.active = None
                saved = self.store.load(session_id)
                from .providers import Socai
                sources = [p for p in getattr(researcher, 'social', []) if isinstance(p, Socai)]
                if sources and saved and saved.turns:
                    cp = saved.turns[-1].checkpoint
                    # Login/anti-abuse pages on a healthy transport need user action,
                    # not an automatic research replay mistaken for reconnecting Chrome.
                    disconnected = any(p.connection.get('browser_connected') is False for p in sources)
                    if cp.get('recovery_required') in {'BROWSER_DISCONNECTED','BROWSER_OR_LOGIN_REQUIRED','CONNECTION_APPROVAL_TIMEOUT'} and disconnected:
                        self.arm_recovery(session_id)
        threading.Thread(target=work, daemon=True).start()


def create_server(settings, port=8765, researcher_factory=Researcher):
    app = Application(settings, researcher_factory)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def trusted(self):
            expected = f"127.0.0.1:{self.server.server_port}"
            host = self.headers.get("Host", "")
            origin = self.headers.get("Origin")
            return host == expected and (origin is None or origin == f"http://{expected}")

        def respond(self, body, status=200, content_type="application/json; charset=utf-8"):
            raw = body.encode() if isinstance(body, str) else json.dumps(body, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(raw)

        def do_GET(self):
            if not self.trusted():
                return self.respond({"error": "仅允许本机访问"}, 403)
            parsed = urlparse(self.path)
            if parsed.path == '/api/browser':
                from .providers import Socai
                source = Socai(app.settings)
                try:
                    ready = asyncio.run(source.browser_ready())
                    return self.respond({'ready':ready, 'connection':source.connection})
                except Exception as error:
                    return self.respond({'ready':False, 'connection':source.connection, 'error':str(source_error('socai', error))})
            path = parsed.path
            try:
                if path == "/":
                    return self.respond(Path(__file__).with_name("ui.html").read_text(), content_type="text/html; charset=utf-8")
                assets = {"/assets/ui.css": ("ui.css", "text/css"),
                          "/assets/ui.mjs": ("ui.mjs", "text/javascript"),
                          "/assets/ui-state.mjs": ("ui-state.mjs", "text/javascript")}
                if path in assets:
                    filename, content_type = assets[path]
                    return self.respond(Path(__file__).with_name(filename).read_text(),
                                        content_type=content_type + "; charset=utf-8")
                if path == "/api/sessions":
                    sessions = []
                    for file in sorted(app.store.root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
                        try:
                            session = app.store.load(file.stem)
                            if session and session.turns:
                                t = session.turns[-1]
                                sessions.append({"id": session.id, "message": t.user_input, "status": t.status,
                                                 "started_at": t.started_at.isoformat(), "turns": len(session.turns)})
                        except (ValueError, OSError):
                            continue
                    return self.respond({"sessions": sessions, "active": app.active})
                parts = path.strip("/").split("/")
                if len(parts) not in {3, 4} or parts[:2] != ["api", "sessions"]:
                    return self.respond({"error": "未找到"}, 404)
                session_id = parts[2]
                app.store.path(session_id)
                if len(parts) == 4 and parts[3] == "events":
                    return self.events(session_id)
                session = app.store.load(session_id)
                if session is None:
                    return self.respond({"error": (app.error if app.error_session == session_id else None) or "会话尚未创建",
                                         "active": app.active}, 404)
                if len(parts) == 4 and parts[3] == "report":
                    if not session.turns:
                        return self.respond({"error": "会话尚无研究轮次"}, 404)
                    turn_id = parse_qs(parsed.query).get("turn", [session.turns[-1].id])[0]
                    turn = next((t for t in session.turns if t.id == turn_id), None)
                    if turn is None:
                        return self.respond({"error": "轮次不存在"}, 404)
                    return self.respond(render_report(session, turn), content_type="text/markdown; charset=utf-8")
                if len(parts) == 4:
                    return self.respond({"error": "未找到"}, 404)
                return self.respond({"session": session.model_dump(mode="json"), "active": app.active,
                                     "error": app.error if app.error_session == session_id else None})
            except (ValueError, OSError):
                return self.respond({"error": "会话无效或无法读取"}, 400)

        def events(self, session_id):
            # Disk is the shared truth for CLI, live UI, reconnect and history replay.
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.end_headers()
            last_id = self.headers.get("Last-Event-ID", "")
            seen = set()
            resumed = not last_id
            try:
                for tick in range(3600):
                    session = app.store.load(session_id)
                    if session:
                        events = [e for t in session.turns for e in t.events]
                        if not resumed:
                            known = {e.id for e in events}
                            if last_id not in known:
                                resumed = True
                        for event in events:
                            if not resumed:
                                seen.add(event.id)
                                if event.id == last_id:
                                    resumed = True
                                continue
                            if event.id in seen:
                                continue
                            seen.add(event.id)
                            self.wfile.write(f"id: {event.id}\nevent: research\ndata: {event.model_dump_json()}\n\n".encode())
                        self.wfile.flush()
                    if app.active != session_id and (not app.recovery_target or app.recovery_target[0] != session_id):
                        self.wfile.write(b"event: done\ndata: {}\n\n")
                        self.wfile.flush()
                        return
                    if tick % 40 == 0:
                        self.wfile.write(b": heartbeat\n\n")
                        self.wfile.flush()
                    time.sleep(0.25)
            except (BrokenPipeError, ConnectionResetError):
                return

        def do_POST(self):
            if not self.trusted():
                return self.respond({"error": "仅允许本机同源请求"}, 403)
            if self.path not in {"/api/run", "/api/resume", "/api/recover"}:
                return self.respond({"error": "未找到"}, 404)
            try:
                length = int(self.headers.get("Content-Length", 0))
                if not 0 < length <= 20000:
                    raise ValueError()
                data = json.loads(self.rfile.read(length))
                session_id, message = data["session_id"], data.get("message", "")
                if not isinstance(session_id, str) or not isinstance(message, str):
                    raise ValueError()
                if self.path == '/api/recover':
                    app.reconnect(session_id)
                else:
                    app.start(session_id, message, resume=self.path == '/api/resume')
                return self.respond({"session_id": session_id, "status": "started"}, 202)
            except RuntimeError as error:
                return self.respond({"error": str(error)}, 409)
            except (ValueError, KeyError, TypeError):
                return self.respond({"error": "请求格式或会话ID无效"}, 400)
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    server.app = app
    close = server.server_close
    def stop():
        app.closed = True
        app.recovery_stop.set()
        close()
    server.server_close = stop
    return server


def serve(settings, port):
    server = create_server(settings, port)
    print(f"飞探研究界面：http://127.0.0.1:{server.server_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
