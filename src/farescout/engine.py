from __future__ import annotations

import asyncio
import json
import os
import re
from time import monotonic
from pathlib import Path
from typing import Callable

from .config import Settings
from .dates import DateExplorer
from .models import Discovery, Event, Opportunity, Session, Turn, Expansion, ResearchDecision, identity, now
from .providers import FlyAI, RedditCommunity, SerpAPI, Socai
from .quality import assess_evidence, deal_strength
from .report import render_report, synthesize
from .research import Brain, default_queries, evolve_goal, grounded, today_local, AIRPORTS, appears
from .safety import clean_text, source_error


class Store:
    def __init__(self, root: Path):
        self.root = root
        root.mkdir(parents=True, exist_ok=True)

    def path(self, session_id: str) -> Path:
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", session_id):
            raise ValueError("session ID 仅允许字母、数字、下划线和短横线，最长 64 字符")
        return self.root / f"{session_id}.json"

    def load(self, session_id: str) -> Session | None:
        path = self.path(session_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        for turn in data.get("turns", []):
            for index, event in enumerate(turn.get("events", [])):
                event.setdefault("id", identity(session_id, turn.get("id"), index, event.get("time")))
                event.setdefault("turn_id", turn.get("id", ""))
            for opportunity in turn.get("opportunities", []):
                coverage = opportunity.get("date_coverage") or {}
                for sample in coverage.get("samples", []):
                    # Loading an older session must never create a fresh observation.
                    sample.setdefault("observed_at", None)
        return Session.model_validate(data)

    def save(self, session: Session, *, report: bool = True) -> None:
        path = self.path(session.id)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(session.model_dump_json(indent=2), encoding="utf-8")
        os.chmod(tmp, 0o600)
        tmp.replace(path)
        if session.turns and report:
            report = self.root / f"{session.id}-{session.turns[-1].id}.md"
            report.write_text(render_report(session, session.turns[-1]), encoding="utf-8")


class Researcher:
    def __init__(self, settings: Settings, *, brain=None, social=None, fares=None,
                 on_event: Callable[[Event], None] | None = None):
        self.settings = settings
        self.brain = brain if brain is not None else Brain(settings)
        self.social = social if social is not None else [Socai(settings)] + ([RedditCommunity(settings)] if settings.web_fallback else [])
        self.fares = fares if fares is not None else [FlyAI(settings), SerpAPI(settings)]
        self.on_event = on_event or (lambda event: None)
        self.store = Store(settings.data_dir)
        self._session = None
        self._blocked_social = set()

    def emit(self, turn, stage, status, detail, source=None, **fields):
        event = Event(stage=stage, source=source, status=status, detail=clean_text(detail, 1200),
                      turn_id=turn.id, parent_action_id=turn.id, **fields)
        turn.events.append(event)
        if self._session:
            self.store.save(self._session, report=False)
        self.on_event(event)

    def ingest_evidence(self, evidence, turn, session):
        added = []
        for item in evidence:
            session.evidence[item.id] = item
            if item.id not in turn.evidence_ids:
                turn.evidence_ids.append(item.id)
                added.append(item)
        if self.settings.evidence_quality:
            assess_evidence(session.evidence)
        for item in added:
            self.emit(turn, "evidence", "ok", item.title or item.source, item.source,
                      evidence_ids=[item.id], data={"url": item.url, "published_at": item.published_at})
            if item.quality:
                self.emit(turn, "quality", "info", "；".join(item.quality.get("flags", [])) or "已读取正文；暂无命中风险词，仍需验价",
                          evidence_ids=[item.id], data=item.quality)

    def publish_results(self, turn):
        """A milestone requires a cited route and a real exact quote, never a range hint."""
        count = sum(bool(o.fares) and bool(o.candidate.signals) for o in turn.opportunities)
        changed = False
        for threshold, name in [(1, 'first_result'), (3, 'third_result')]:
            if count >= threshold and name + '_seconds' not in turn.metrics:
                turn.metrics[name + '_seconds'] = round((now() - turn.started_at).total_seconds(), 3)
                turn.metrics[name + '_execution_seconds'] = round(getattr(self, '_previous_execution', 0) + monotonic() - getattr(self, '_execution_started', monotonic()), 3)
                self.emit(turn, 'result_available', 'ok', f'已有{count}条有社区引用、具体日期和精确报价的结果；研究可能仍在继续',
                    data={'milestone':name, 'count':count, 'seconds':turn.metrics[name + '_seconds']})
                changed = True
        if not changed and self._session:
            self.store.save(self._session, report=False)

    async def model_call(self, turn, operation, *args):
        start = monotonic()
        turn.metrics['model_operations'] = int(turn.metrics.get('model_operations', 0)) + 1
        status = "ok"
        try:
            return await getattr(self.brain, operation)(*args)
        except BaseException:
            status = "failed"
            raise
        finally:
            self.emit(turn, "model", status, f"模型操作：{operation}", "model", phase="completed",
                      duration_ms=int((monotonic()-start)*1000), data={"operation": operation})

    async def search(self, query: str, turn: Turn, session: Session, stage="community_search"):
        for provider in self.social:
            if provider.name in self._blocked_social:
                self.emit(turn, stage, "skipped", "本轮此备用来源已不可达，避免重复消耗等待预算", provider.name)
                continue
            reserve = min(120, self.settings.max_seconds / 4)
            remaining = getattr(self, '_research_deadline', monotonic() + self.settings.max_seconds) - monotonic()
            if remaining <= reserve:
                self.emit(turn, 'budget', 'skipped', '社区阶段时间预算已用完；把剩余时间留给候选提取和验价',
                          provider.name, data={'query':query, 'reserved_seconds':reserve})
                return
            search_timeout = min(getattr(provider, 'timeout_seconds', self.settings.source_timeout + 5), remaining-reserve)
            action = identity(turn.id, stage, query, provider.name)
            started = monotonic()
            turn.metrics["community_calls"] = turn.metrics.get("community_calls", 0) + 1
            before_commands = getattr(provider, "command_calls", 0)
            if isinstance(provider, Socai):
                provider.on_evidence = lambda evidence: self.ingest_evidence(evidence, turn, session)
                provider.on_trace = lambda substage, status, detail, duration, data: self.emit(
                    turn, substage, status, detail, provider.name, phase="completed", duration_ms=duration, data=data)
                provider.on_retry = lambda retry: self.emit(turn, "source_retry", "failed", f"{provider.retry_reason}；有界重试：{retry}",
                    provider.name, data={"original_query": query, "retry_query": retry})
                provider.on_query = lambda actual: self.emit(turn, "source_query", "info", f"实际社区关键词：{actual}", provider.name,
                    data={"planned_query": query, "actual_query": actual})
            self.emit(turn, stage, "info", f"只读搜索：{query}", provider.name,
                      action_id=action, phase="started", data={"query": query})
            try:
                async with asyncio.timeout(search_timeout):
                    evidence = await provider.search(query)
                self.ingest_evidence(evidence, turn, session)
                if getattr(provider, 'blocked_code', None):
                    self._blocked_social.add(provider.name)
                    turn.checkpoint['recovery_required'] = provider.blocked_code
                self.emit(turn, stage, "ok", f"查询 {query}；已阅读 {len(evidence)} 篇正文/评论", provider.name,
                          action_id=action, phase="completed", evidence_ids=[e.id for e in evidence],
                          duration_ms=int((monotonic()-started)*1000), data={"query": query, "count": len(evidence),
                              "complete": not bool(getattr(provider, 'blocked_code', None))})
                if evidence:
                    return
            except asyncio.CancelledError:
                self.emit(turn, stage, "failed", "研究预算到达；已读正文保留", provider.name,
                    action_id=action, phase="completed", duration_ms=int((monotonic()-started)*1000), data={"query": query})
                raise
            except Exception as error:
                if isinstance(error, TimeoutError) and getattr(self, '_research_deadline', float('inf')) - monotonic() <= reserve + .1:
                    self.emit(turn, 'budget', 'info', '社区阶段时间预算到达；已读正文保留，接着提取候选和验价',
                              provider.name, data={'query':query, 'reserved_seconds':reserve})
                failure = source_error(provider.name, error)
                if isinstance(provider, RedditCommunity) or failure.code in {"ACCESS_BLOCKED", "BROWSER_OR_LOGIN_REQUIRED", "BROWSER_DISCONNECTED", "DAEMON_VERSION_MISMATCH", "NOT_INSTALLED", "CONNECTION_APPROVAL_TIMEOUT", "DAEMON_IPC_PERMISSION_DENIED"}:
                    self._blocked_social.add(provider.name)
                self.emit(turn, stage, "failed", str(source_error(provider.name, error)), provider.name,
                          action_id=action, phase="completed", duration_ms=int((monotonic()-started)*1000), data={"query": query})
                if failure.code in {'BROWSER_DISCONNECTED', 'BROWSER_OR_LOGIN_REQUIRED', 'CONNECTION_APPROVAL_TIMEOUT', 'DAEMON_IPC_PERMISSION_DENIED', 'DAEMON_VERSION_MISMATCH'}:
                    turn.checkpoint['recovery_required'] = failure.code
            finally:
                turn.metrics["socai_commands"] = turn.metrics.get("socai_commands", 0) + getattr(provider, "command_calls", 0)-before_commands
        self.emit(turn, stage, "info", "所有本轮社区来源失败；保留并尝试使用已有社区证据")

    async def run(self, message: str, session: Session | None, session_id: str, *, resume: bool = False) -> Session:
        execution_started = monotonic()
        self._execution_started = execution_started
        self._research_deadline = execution_started + self.settings.max_seconds
        self._session = session
        self._blocked_social = set()
        usage = getattr(self.brain, "usage", None)
        model_start = (usage.requests, usage.input_tokens, usage.output_tokens) if usage else None
        if resume:
            if not session or not session.turns:
                raise ValueError("没有可续跑的会话")
            turn = session.turns[-1]
            for provider in self.social:
                if isinstance(provider, Socai):
                    provider.known_notes = {e.url.rsplit('/', 1)[-1]:e for e in session.evidence.values() if e.source == provider.name}
            message = turn.user_input
            for provider in self.social:
                if not hasattr(provider, "recover"):
                    continue
                for stage, query, records in provider.recover(turn):
                    new = [r for r in records if r.id not in session.evidence]
                    for record in new:
                        session.evidence[record.id] = record
                        turn.evidence_ids.append(record.id)
                    if new:
                        self.emit(turn, stage, "ok", f"续跑接收迟到回执：{query}；{len(new)} 篇，保留原读取时间", provider.name)
            turn.stop_reason = ""
            turn.status = "running"
            self.emit(turn, "resume", "info", "从已有证据继续；历史失败记录保留，本段重新计时")
        else:
            goal = evolve_goal(message, session.goal if session else None)
            session = session or Session(id=session_id, goal=goal)
            turn = Turn(id=identity(session_id, now().isoformat()), user_input=clean_text(message, 3000), goal=goal)
            session.turns.append(turn)
            session.goal = goal
            self._session = session
            self.emit(turn, "discovery", "ok", "已直接开始探索，无需先填写目的地或完整日期")
        self._previous_execution = turn.metrics.get('execution_seconds', 0) if resume else 0
        turn.finished_at = None
        turn.checkpoint.pop('recovery_required', None)
        try:
            async with asyncio.timeout(self.settings.max_seconds):
                await self._research(message, session, turn, resume=resume)
        except TimeoutError:
            turn.stop_reason = "达到研究时间预算，保留已取得的证据和报价"
            self.emit(turn, "stop", "info", turn.stop_reason)
        except Exception as error:
            turn.stop_reason = str(source_error("research", error))
            self.emit(turn, "stop", "failed", turn.stop_reason)
        finally:
            turn.finished_at = now()
            for opportunity in turn.opportunities:
                if self.settings.deal_strength:
                    opportunity.deal = deal_strength(opportunity)
                synthesize(opportunity, session.evidence)
                if opportunity.comparison:
                    self.emit(turn, "conflict", "info", "；".join(opportunity.comparison),
                              data={"route": opportunity.candidate.key})
                if opportunity.deal:
                    self.emit(turn, "deal", "info", opportunity.deal["label"], data={"route": opportunity.candidate.key, **opportunity.deal})
            verified = sum(bool(o.fares) for o in turn.opportunities)
            history = [e for t in session.turns for e in t.events]
            searches = [e for e in history if e.stage == "community_search" and e.status == "ok" and e.evidence_ids]
            expanded = any(e.stage == "query_expansion" and e.status == "ok" and e.evidence_ids for e in history)
            covered = sum(bool(o.date_coverage and len({s.date for s in o.date_coverage.samples
                          if s.stage != "range" and s.status == "ok"}) >= 2) for o in turn.opportunities if o.fares)
            date_ok = turn.goal.date_mode == "fixed" or covered >= 3
            turn.status = "complete" if verified >= 3 and expanded and len(searches) >= 2 and date_ok else (
                "partial" if turn.opportunities or turn.evidence_ids else "blocked")
            if not turn.stop_reason:
                missing = []
                if verified < 3:
                    missing.append("有当前报价的候选不足3条")
                if not expanded:
                    missing.append("查询扩展未成功取得正文")
                if len(searches) < 2:
                    missing.append("成功宽社区查询不足2次")
                if not date_ok:
                    missing.append("至少3条路线的多日期有效覆盖尚未满足")
                if any(e.stage == 'budget' and '社区阶段时间预算' in e.detail for e in turn.events):
                    missing.append('社区阶段时间预算已用完，已优先保留时间验价')
                turn.stop_reason = "已完成有预算日期探索与候选验证；未覆盖日期保持未知" if turn.status == "complete" else "；".join(missing)
            turn.metrics["elapsed_seconds"] = round((turn.finished_at-turn.started_at).total_seconds(), 3)
            turn.metrics["execution_seconds"] = round(self._previous_execution + monotonic()-execution_started, 3)
            turn.metrics['execution_segments'] = int(turn.metrics.get('execution_segments', 0)) + 1
            turn.metrics["evidence_count"] = len(session.evidence)
            turn.metrics["verified_routes"] = verified
            # Parent search events include child preview/read time; do not add both to stage totals.
            for stage in {e.stage for e in turn.events if e.duration_ms is not None}:
                turn.metrics[f"stage_{stage}_seconds"] = round(sum(e.duration_ms or 0 for e in turn.events if e.stage == stage) / 1000, 3)
            accounted = sum(turn.metrics.get(f"stage_{stage}_seconds", 0) for stage in ["model", "community_search", "query_expansion", "date_phase"])
            turn.metrics["unattributed_seconds"] = round(max(0, turn.metrics["execution_seconds"]-accounted), 3)
            turn.metrics['overlapped_stage_seconds'] = round(max(0, accounted-turn.metrics['execution_seconds']), 3)
            turn.metrics["independence_groups"] = len({e.quality.get("independence_group", e.id) for e in session.evidence.values()})
            if model_start:
                turn.metrics.update(model_requests=turn.metrics.get('model_requests', 0)+usage.requests-model_start[0],
                                    model_input_tokens=turn.metrics.get('model_input_tokens', 0)+usage.input_tokens-model_start[1],
                                    model_output_tokens=turn.metrics.get('model_output_tokens', 0)+usage.output_tokens-model_start[2])
            self.emit(turn, "conclusion", "ok" if verified else "failed", turn.stop_reason,
                      phase="completed", data={"status": turn.status, "metrics": turn.metrics})
            self.store.save(session)
        return session

    async def _research(self, message, session, turn, *, resume=False):
        goal = turn.goal
        if goal.date_to < today_local():
            self.emit(turn, "goal", "failed", "指定日期已过去；不能验证历史日期的当前票价")
            return
        if resume:
            self.emit(turn, 'goal', 'ok', '恢复本轮既有条件，不重新解释需求或创建新一轮',
                data={'constraints':[c.model_dump(mode='json') for c in goal.constraints]})
            await self.research_loop(message, session, turn, resume=True)
            return
        # Deterministic common follow-ups remain usable when the model source fails.
        try:
            initial_constraints = {c.field: c for c in goal.constraints}
            goal = await self.model_call(turn, "patch", message, goal)
            goal = evolve_goal(message, goal)  # Preserve explicit example constraints.
            goal.constraints = [initial_constraints[c.field] if c.provenance == "context" and c.field in initial_constraints
                                and initial_constraints[c.field].value == c.value else c for c in goal.constraints]
            turn.goal = goal
            session.goal = goal
        except Exception as error:
            self.emit(turn, "goal", "failed", str(source_error("model", error)), "model")
        self.emit(turn, "goal", "ok", f"保留上下文：{goal.origins}；地区 {goal.region or '不限'}；{goal.date_from}～{goal.date_to}；排除红眼 {goal.no_red_eye}",
                  data={"constraints": [c.model_dump(mode="json") for c in goal.constraints]})
        await self.research_loop(message, session, turn, resume=resume)

    async def research_loop(self, message, session, turn, *, resume=False):
        goal, cp = turn.goal, turn.checkpoint
        queries = cp.get('queries', [])
        if 'queries' not in cp:
            if not session.evidence:
                try:
                    queries = await self.model_call(turn, 'plan', message, goal)
                except Exception as error:
                    queries = default_queries(goal)[:2]
                    self.emit(turn, 'plan', 'failed', str(source_error('model', error)) + '；使用同范围宽查询')
            cp['queries'] = queries[:3]
        succeeded = {(e.stage, e.data.get('query')) for e in turn.events
                     if e.stage in {'community_search', 'query_expansion'} and e.status == 'ok' and e.evidence_ids and e.data.get('complete', True)}
        attempted = set()
        scheduled = set()
        task = None
        explorer = DateExplorer(self, turn)
        if session.evidence:
            self.emit(turn, 'context', 'ok', f'沿用{len(session.evidence)}篇原文；保留原时间，成功步骤不整轮重做')
            await self.refresh_candidates(session, turn)
        try:
            for step in range(self.settings.max_research_steps):
                if task and task.done():
                    await task
                    task = None
                pending = [q for q in queries if ('community_search', q) not in succeeded and ('community_search', q) not in attempted]
                expansions = [Expansion.model_validate(e) for e in cp.get('expansions', [])]
                expansion = next((e for e in expansions if ('query_expansion', e.query) not in succeeded
                                  and ('query_expansion', e.query) not in attempted and e.query not in queries), None)
                available_social = any(p.name not in self._blocked_social for p in self.social)
                waiting_routes = [o for o in turn.opportunities if o.candidate.key not in scheduled]
                remaining = self._research_deadline - monotonic()
                allowed = []
                if pending and available_social and remaining > min(120, self.settings.max_seconds/4):
                    allowed.append('community')
                if waiting_routes and task is None:
                    allowed.append('dates')
                promotion_attempts = sum(stage == 'query_expansion' for stage, query in attempted)
                if expansion and available_social and promotion_attempts < 2 and not (waiting_routes and promotion_attempts) and remaining > min(120, self.settings.max_seconds/4):
                    allowed.append('promotion')
                if not allowed and task:
                    await task
                    task = None
                    continue
                if not allowed:
                    allowed = ['stop']
                # A successful bounded discovery may stop before exhausting every optional query.
                if 'stop' not in allowed and len([o for o in turn.opportunities if o.fares]) >= 3 and any(s == 'query_expansion' for s,q in succeeded) and len([s for s,q in succeeded if s == 'community_search']) >= 2:
                    allowed.append('stop')
                fallback = 'dates' if 'dates' in allowed else 'community' if 'community' in allowed else allowed[0]
                context = {'allowed_actions':allowed, 'remaining_seconds':round(remaining, 1),
                    'pending_community_queries':pending, 'promotion_query':expansion.model_dump(mode='json') if expansion else None,
                    'community_bodies':len(session.evidence), 'evidence_gaps':cp.get('evidence_gaps', []), 'date_calls':turn.metrics.get('date_calls', 0),
                    'routes':[{'route':o.candidate.key, 'evidence_ids':[s.evidence_id for s in o.candidate.signals],
                               'has_exact_price':bool(o.fares), 'checked_dates':len(o.date_coverage.samples) if o.date_coverage else 0,
                               'date_work_running':o.candidate.key in scheduled and task is not None} for o in turn.opportunities],
                    'blocked_sources':sorted(self._blocked_social), 'recovery_required':cp.get('recovery_required')}
                decision = ResearchDecision(action=fallback, reason='先补足当前缺少的报价或正文；已完成操作不重复执行')
                if hasattr(self.brain, 'decide') and len(allowed) > 1:
                    try:
                        proposed = await self.model_call(turn, 'decide', goal, context)
                        if proposed.action not in allowed:
                            raise ValueError('action not allowed')
                        decision = proposed
                    except Exception as error:
                        self.emit(turn, 'research_decision', 'failed', str(source_error('model', error)) + '；采用预算内的缺口处理规则')
                self.emit(turn, 'research_decision', 'info', clean_text(decision.reason, 800),
                    data={'action':decision.action, 'allowed_actions':allowed, 'step':step+1, 'context':context})
                if decision.action == 'stop':
                    self.emit(turn, 'stop', 'info', '必要操作已经尝试，或来源/时间预算不允许继续；保留已取得结果')
                    break
                if decision.action == 'dates':
                    scheduled.update(o.candidate.key for o in waiting_routes)
                    async def date_work(rows):
                        started = monotonic()
                        try:
                            await explorer.run(rows, progressive=True)
                        finally:
                            self.emit(turn, 'date_phase', 'info', '日期任务实际用时；与社区读取可能重叠，不能把两者相加',
                                duration_ms=int((monotonic()-started)*1000), phase='completed')
                    task = asyncio.create_task(date_work(waiting_routes))
                    continue
                stage = 'community_search' if decision.action == 'community' else 'query_expansion'
                query = pending[0] if stage == 'community_search' else expansion.query
                if stage == 'query_expansion':
                    if all(e.query != expansion.query for e in turn.expansions):
                        turn.expansions.append(expansion)
                    self.emit(turn, 'expansion_plan', 'info', expansion.reason,
                        evidence_ids=[expansion.evidence_id], data=expansion.model_dump(mode='json'))
                attempted.add((stage, query))
                await self.search(query, turn, session, stage)
                succeeded.update((e.stage, e.data.get('query')) for e in turn.events
                    if e.stage in {'community_search', 'query_expansion'} and e.status == 'ok' and e.evidence_ids and e.data.get('complete', True))
                if session.evidence:
                    await self.refresh_candidates(session, turn)
            else:
                self.emit(turn, 'stop', 'info', '达到本段研究动作上限；保留结果，可按缺口继续', data={'max_steps':self.settings.max_research_steps})
            if task:
                await task
                task = None
            if not session.evidence:
                turn.stop_reason = '未取得任何可读取的社区正文，不能凭模型知识生成候选航线'
        finally:
            if task and not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)

    async def refresh_candidates(self, session, turn):
        cp = turn.checkpoint
        fingerprint = identity(turn.goal.model_dump_json(), [(e.id,e.readable_text()) for e in session.evidence.values()])
        if cp.get('discovery_fingerprint') == fingerprint:
            self.emit(turn, 'checkpoint', 'skipped', '正文和条件没有变化，保留已筛选候选，不重复模型提取')
            return
        # A destination list without the requested origin is a lead, not a route.
        gaps = []
        for item in session.evidence.values():
            text = item.title + '\n' + item.readable_text()
            destinations = [code for code, value in AIRPORTS.items()
                if (not turn.goal.region or value[1] == turn.goal.region)
                and code not in turn.goal.origins and value[1] not in {'CN', 'HK', 'MO'} and appears(code, text)]
            if destinations and not any(appears(origin, text) for origin in turn.goal.origins):
                gaps.append({'evidence_id':item.id, 'named_destinations':destinations,
                    'missing':'原文没有写明用户要求的出发地；需要另找正文确认，不能推定航线'})
        cp['evidence_gaps'] = gaps
        if isinstance(self.brain, Brain):
            self.brain.discovery_context = {
                'accepted_routes':[o.candidate.key for o in turn.opportunities],
                'previous_queries':[e.data.get('query') for e in turn.events
                    if e.stage in {'community_search', 'query_expansion'} and e.phase == 'completed'],
                'evidence_gaps':gaps}
        try:
            discovery = await self.model_call(turn, 'discover', turn.goal, session.evidence)
        except Exception as error:
            self.emit(turn, 'extract', 'failed', str(source_error('model', error)), 'model')
            previous = [o.candidate for t in session.turns for o in t.opportunities]
            discovery = grounded(Discovery(candidates=previous[-12:]), session.evidence, turn.goal)
        if not discovery.expansions and not cp.get('expansion_repair_attempted') and hasattr(self.brain, 'expand'):
            cp['expansion_repair_attempted'] = True
            try:
                discovery.expansions = await self.model_call(turn, 'expand', turn.goal, session.evidence)
            except Exception as error:
                self.emit(turn, 'expansion_plan', 'failed', str(source_error('model', error)), 'model')
        cp['expansions'] = [e.model_dump(mode='json') for e in discovery.expansions] or cp.get('expansions', [])
        previous = {o.candidate.key:o for o in turn.opportunities}
        for candidate in discovery.candidates[:5]:
            if candidate.key in previous:
                previous[candidate.key].candidate = candidate
            elif len(previous) < 5:
                previous[candidate.key] = Opportunity(candidate=candidate)
            self.emit(turn, 'candidate', 'ok', candidate.why, evidence_ids=[s.evidence_id for s in candidate.signals],
                data={'route':candidate.key, 'destination_name':candidate.destination_name})
        turn.opportunities = list(previous.values())[:5]
        self.emit(turn, 'extract', 'ok', f'从{len(session.evidence)}篇原文保留{len(turn.opportunities)}条有引用候选')
        cp['discovery_fingerprint'] = fingerprint
        self.store.save(session, report=False)
