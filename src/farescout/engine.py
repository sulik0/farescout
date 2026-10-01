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
from .models import Discovery, Event, Opportunity, Session, Turn, identity, now
from .providers import FlyAI, RedditCommunity, SerpAPI, Socai
from .quality import assess_evidence, deal_strength
from .report import render_report, synthesize
from .research import Brain, default_queries, evolve_goal, grounded, today_local
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

    async def search(self, query: str, turn: Turn, session: Session, stage="community_search"):
        for provider in self.social:
            if provider.name in self._blocked_social:
                self.emit(turn, stage, "skipped", "本轮此备用来源已不可达，避免重复消耗等待预算", provider.name)
                continue
            action = identity(turn.id, stage, query, provider.name)
            started = monotonic()
            turn.metrics["community_calls"] = turn.metrics.get("community_calls", 0) + 1
            before_commands = getattr(provider, "command_calls", 0)
            if isinstance(provider, Socai):
                provider.on_retry = lambda retry: self.emit(turn, "source_retry", "failed", f"{provider.retry_reason}；有界重试：{retry}",
                    provider.name, data={"original_query": query, "retry_query": retry})
                provider.on_query = lambda actual: self.emit(turn, "source_query", "info", f"实际社区关键词：{actual}", provider.name,
                    data={"planned_query": query, "actual_query": actual, "command_number": provider.command_calls + 1})
            self.emit(turn, stage, "info", f"只读搜索：{query}", provider.name,
                      action_id=action, phase="started", data={"query": query})
            try:
                async with asyncio.timeout(getattr(provider, "timeout_seconds", self.settings.source_timeout + 5)):
                    evidence = await provider.search(query)
                for item in evidence:
                    session.evidence[item.id] = item
                    if item.id not in turn.evidence_ids:
                        turn.evidence_ids.append(item.id)
                if self.settings.evidence_quality:
                    assess_evidence(session.evidence)
                self.emit(turn, stage, "ok", f"查询 {query}；已阅读 {len(evidence)} 篇正文/评论", provider.name,
                          action_id=action, phase="completed", evidence_ids=[e.id for e in evidence],
                          duration_ms=int((monotonic()-started)*1000), data={"query": query, "count": len(evidence)})
                for item in evidence:
                    self.emit(turn, "evidence", "ok", item.title or item.source, provider.name,
                              evidence_ids=[item.id], data={"url": item.url, "published_at": item.published_at})
                    if item.quality:
                        self.emit(turn, "quality", "info", "；".join(item.quality.get("flags", [])) or "已读取正文；暂无命中风险词，仍需验价",
                                  evidence_ids=[item.id], data=item.quality)
                if evidence:
                    turn.metrics["socai_commands"] = turn.metrics.get("socai_commands", 0) + getattr(provider, "command_calls", 0)-before_commands
                    return
            except Exception as error:
                if isinstance(provider, RedditCommunity):
                    self._blocked_social.add(provider.name)
                self.emit(turn, stage, "failed", str(source_error(provider.name, error)), provider.name,
                          action_id=action, phase="completed", duration_ms=int((monotonic()-started)*1000), data={"query": query})
            turn.metrics["socai_commands"] = turn.metrics.get("socai_commands", 0) + getattr(provider, "command_calls", 0)-before_commands
        self.emit(turn, stage, "info", "所有本轮社区来源失败；保留并尝试使用已有社区证据")

    async def run(self, message: str, session: Session | None, session_id: str, *, resume: bool = False) -> Session:
        self._session = session
        self._blocked_social = set()
        usage = getattr(self.brain, "usage", None)
        model_start = (usage.requests, usage.input_tokens, usage.output_tokens) if usage else None
        if resume:
            if not session or not session.turns:
                raise ValueError("没有可续跑的会话")
            turn = session.turns[-1]
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
            searches = [e for e in history if e.stage == "community_search" and e.status == "ok"]
            expanded = any(e.stage == "query_expansion" and e.status == "ok" for e in history)
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
                turn.stop_reason = "已完成有预算日期探索与候选验证；未覆盖日期保持未知" if turn.status == "complete" else "；".join(missing)
            turn.metrics["elapsed_seconds"] = round((turn.finished_at-turn.started_at).total_seconds(), 3)
            turn.metrics["evidence_count"] = len(session.evidence)
            turn.metrics["verified_routes"] = verified
            if model_start:
                turn.metrics.update(model_requests=usage.requests-model_start[0],
                                    model_input_tokens=usage.input_tokens-model_start[1],
                                    model_output_tokens=usage.output_tokens-model_start[2])
            self.emit(turn, "conclusion", "ok" if verified else "failed", turn.stop_reason,
                      phase="completed", data={"status": turn.status, "metrics": turn.metrics})
            self.store.save(session)
        return session

    async def _research(self, message, session, turn, *, resume=False):
        goal = turn.goal
        if goal.date_to < today_local():
            self.emit(turn, "goal", "failed", "指定日期已过去；不能验证历史日期的当前票价")
            return
        # Deterministic common follow-ups remain usable when the model source fails.
        try:
            turn.metrics["model_operations"] = turn.metrics.get("model_operations", 0) + 1
            initial_constraints = {c.field: c for c in goal.constraints}
            goal = await self.brain.patch(message, goal)
            goal = evolve_goal(message, goal)  # Preserve explicit example constraints.
            goal.constraints = [initial_constraints[c.field] if c.provenance == "context" and c.field in initial_constraints
                                and initial_constraints[c.field].value == c.value else c for c in goal.constraints]
            turn.goal = goal
            session.goal = goal
        except Exception as error:
            self.emit(turn, "goal", "failed", str(source_error("model", error)), "model")
        self.emit(turn, "goal", "ok", f"保留上下文：{goal.origins}；地区 {goal.region or '不限'}；{goal.date_from}～{goal.date_to}；排除红眼 {goal.no_red_eye}",
                  data={"constraints": [c.model_dump(mode="json") for c in goal.constraints]})
        queries = []
        if not session.evidence:
            try:
                turn.metrics["model_operations"] = turn.metrics.get("model_operations", 0) + 1
                queries = await self.brain.plan(message, goal)
            except Exception as error:
                queries = default_queries(goal)
                self.emit(turn, "plan", "failed", str(source_error("model", error)) + "；使用宽查询", "model")
            for query in queries[:3]:
                await self.search(query, turn, session)
            if session.evidence and sum(e.stage == "community_search" and e.status == "ok" for e in turn.events) < 2:
                rescue = next((q for q in default_queries(goal) if q not in queries), None)
                if rescue:
                    self.emit(turn, "plan", "info", "宽查询来源失败，补一次更短的同范围社区查询", data={"query": rescue})
                    await self.search(rescue, turn, session)
        else:
            self.emit(turn, "context", "ok", f"沿用 {len(session.evidence)} 篇原始社区证据；按本轮约束重新筛选并重新验价")
            if self.settings.evidence_quality:
                assess_evidence(session.evidence)
        # Existing evidence is not discarded on source failure, but its original timestamp remains.
        if not session.evidence:
            turn.stop_reason = "未取得任何可读取的社区正文，不能凭模型知识生成候选航线"
            return
        try:
            turn.metrics["model_operations"] = turn.metrics.get("model_operations", 0) + 1
            discovery = await self.brain.discover(goal, session.evidence)
        except Exception as error:
            self.emit(turn, "extract", "failed", str(source_error("model", error)), "model")
            previous = [o.candidate for t in session.turns[:-1] for o in t.opportunities]
            discovery = grounded(Discovery(candidates=previous[-12:]), session.evidence, goal)
        self.emit(turn, "extract", "ok", f"从 {len(session.evidence)} 篇已读内容筛选 {len(discovery.candidates)} 个有引用的候选")
        turn.opportunities = [Opportunity(candidate=c) for c in discovery.candidates[:5]]
        if not discovery.expansions and (len(session.turns) == 1 or resume) and hasattr(self.brain, 'expand'):
            self.emit(turn, 'extract', 'info', '尚无可校验查询扩展；最多补一次基于原文的模型提议')
            try:
                turn.metrics['model_operations'] = turn.metrics.get('model_operations', 0) + 1
                discovery.expansions = await self.brain.expand(goal, session.evidence)
                if not discovery.expansions:
                    self.emit(turn, 'expansion_plan', 'failed', '补充扩展仍未通过原文校验；不编造扩展')
            except Exception as error:
                self.emit(turn, 'expansion_plan', 'failed', str(source_error('model', error)), 'model')
        for expansion in discovery.expansions[:1]:
            if (len(session.turns) > 1 and not resume) or expansion.query in queries:
                continue
            turn.expansions.append(expansion)
            self.emit(turn, "expansion_plan", "info", expansion.reason, evidence_ids=[expansion.evidence_id],
                      data=expansion.model_dump(mode="json"))
            await self.search(expansion.query, turn, session, "query_expansion")
        if turn.expansions:
            try:
                turn.metrics["model_operations"] = turn.metrics.get("model_operations", 0) + 1
                second = await self.brain.discover(goal, session.evidence)
                if second.candidates:
                    discovery = second
            except Exception as error:
                self.emit(turn, "extract", "failed", str(source_error("model", error)) + "；保留第一轮候选", "model")
        turn.opportunities = [Opportunity(candidate=c) for c in discovery.candidates[:5]]
        for candidate in discovery.candidates[:5]:
            self.emit(turn, "candidate", "ok", candidate.why, evidence_ids=[s.evidence_id for s in candidate.signals],
                      data={"route": candidate.key, "destination_name": candidate.destination_name})
        await DateExplorer(self, turn).run(turn.opportunities)
        # Verified directions first; evidence ordering remains the tie-breaker.
        turn.opportunities.sort(key=lambda o: bool(o.fares), reverse=True)
