from __future__ import annotations

import asyncio
from datetime import timedelta
from time import monotonic

from .models import DateCoverage, DateSample, FareRequest, identity
from .research import today_local
from .safety import source_error


def representative_dates(goal, count=3, hint=None):
    start = max(goal.date_from, today_local())
    end = goal.date_to
    if start > end:
        return []
    span = (end - start).days
    dates = [start + timedelta(days=round(span * i / max(1, count - 1))) for i in range(count)]
    if hint and start <= hint <= end and hint not in dates:
        dates[count // 2] = hint
    return sorted(set(dates))


class DateExplorer:
    """Bounded range/coarse/fine discovery; exact quotes remain provider facts."""
    def __init__(self, researcher, turn):
        self.r = researcher
        self.turn = turn
        self.date_calls = 0
        self.fare_calls = 0

    async def quote(self, provider, opportunity, outbound, stage):
        goal = self.turn.goal
        request = FareRequest(origin=opportunity.candidate.origin, destination=opportunity.candidate.destination,
                              outbound_date=outbound,
                              return_date=outbound + timedelta(days=goal.stay_days) if goal.trip_type == "round_trip" else None,
                              no_red_eye=goal.no_red_eye)
        category = "verification_calls" if stage == "verification" else "date_calls"
        limit = self.r.settings.max_fare_calls if stage == "verification" else self.r.settings.max_date_calls
        used = self.fare_calls if stage == "verification" else self.date_calls
        if used >= limit:
            self.r.emit(self.turn, "budget", "skipped", f"{category} 达到 {limit} 次预算；跳过 {opportunity.candidate.key} {outbound}", provider.name,
                        data={"route": opportunity.candidate.key, "date_stage": stage, "date": str(outbound)})
            return []
        if stage == "verification":
            self.fare_calls += 1
        else:
            self.date_calls += 1
        self.turn.metrics[category] = used + 1
        action = identity(self.turn.id, stage, opportunity.candidate.key, str(outbound), provider.name)
        trace_stage = "fare" if stage == "verification" else "date_exploration"
        data = {"route": opportunity.candidate.key, "request": request.model_dump(mode="json"), "date_stage": stage}
        self.r.emit(self.turn, trace_stage, "info", f"{stage}：{opportunity.candidate.key} {outbound}", provider.name,
                    action_id=action, phase="started", data=data)
        start = monotonic()
        try:
            async with asyncio.timeout(self.r.settings.source_timeout + 5):
                fares = await provider.verify(request)
            if not fares:
                raise ValueError("empty fare result")
            cheapest = min(fares, key=lambda f: f.amount)
            if stage != "verification":
                opportunity.fares.extend(fares)
            opportunity.date_coverage.samples.append(DateSample(date=outbound, source=provider.name, stage=stage,
                status="ok", amount=cheapest.amount, price_basis=cheapest.price_basis))
            self.r.emit(self.turn, trace_stage, "ok", f"{opportunity.candidate.key} {outbound}：{len(fares)} 条匹配报价",
                        provider.name, action_id=action, phase="completed", duration_ms=int((monotonic()-start)*1000),
                        data=data | {"fare_ids": [f.id for f in fares], "amount": cheapest.amount, "price_basis": cheapest.price_basis})
            return fares
        except Exception as error:
            detail = str(source_error(provider.name, error))
            opportunity.date_coverage.samples.append(DateSample(date=outbound, source=provider.name, stage=stage,
                status="failed", detail=detail))
            self.r.emit(self.turn, trace_stage, "failed", detail, provider.name, action_id=action, phase="completed",
                        duration_ms=int((monotonic()-start)*1000), data=data)
            return []

    async def run(self, opportunities):
        goal = self.turn.goal
        for opportunity in opportunities:
            opportunity.date_coverage = DateCoverage(date_from=goal.date_from, date_to=goal.date_to,
                notes=["有预算粗筛→精查；未遍历全日期窗口，不能称为全月最低。"])
        # Give every evidence-grounded route coarse coverage before refining any route.
        shortlist = {}
        for opportunity in opportunities:
            candidate = opportunity.candidate
            coverage = opportunity.date_coverage
            returned = []
            if goal.date_mode == "flexible" and self.date_calls < self.r.settings.max_date_calls:
                provider = next((p for p in self.r.fares if hasattr(p, "explore")), None)
                if provider:
                    self.date_calls += 1
                    self.turn.metrics["date_calls"] = self.date_calls
                    action = identity(self.turn.id, "range", candidate.key)
                    started = monotonic()
                    data = {"route": candidate.key, "date_from": str(goal.date_from), "date_to": str(goal.date_to), "date_stage": "range"}
                    self.r.emit(self.turn, "date_exploration", "info", f"范围粗筛 {candidate.key}；不假定逐日覆盖", provider.name,
                                action_id=action, phase="started", data=data)
                    try:
                        async with asyncio.timeout(self.r.settings.source_timeout + 5):
                            returned = await provider.explore(candidate.origin, candidate.destination, goal)
                        coverage.samples.extend(returned)
                        coverage.returned_dates = sorted({s.date for s in returned})
                        self.r.emit(self.turn, "date_exploration", "ok", f"范围结果实际含 {len(coverage.returned_dates)} 个日期",
                                    provider.name, action_id=action, phase="completed", duration_ms=int((monotonic()-started)*1000),
                                    data=data | {"returned_dates": list(map(str, coverage.returned_dates))})
                    except Exception as error:
                        self.r.emit(self.turn, "date_exploration", "failed", str(source_error(provider.name, error)), provider.name,
                                    action_id=action, phase="completed", duration_ms=int((monotonic()-started)*1000), data=data)
            coarse = representative_dates(goal, self.r.settings.coarse_dates, candidate.date_hint)
            # Only range results with a verified date can replace a representative day.
            if returned and len(coarse) > 1 and min(returned, key=lambda s: s.amount).date not in coarse:
                coarse[len(coarse)//2] = min(returned, key=lambda s: s.amount).date
                coarse = sorted(set(coarse))
            self.r.emit(self.turn, "date_plan", "info", f"{candidate.key} 代表日：{', '.join(map(str, coarse))}；预留少量邻近精查",
                        data={"route": candidate.key, "dates": list(map(str, coarse)), "basis": "窗口首/中/尾及证据/范围线索"})
            quotes = []
            # A precise global source is preferred for comparable coarse prices.
            providers = sorted(self.r.fares, key=lambda p: p.name != "SerpAPI")
            for outbound in coarse:
                if self.date_calls >= self.r.settings.max_date_calls or goal.date_mode == "fixed":
                    break
                for provider in providers:
                    fares = await self.quote(provider, opportunity, outbound, "coarse")
                    if fares:
                        quotes.extend(fares)
                        break
            shortlist[candidate.key] = quotes
        for opportunity in opportunities:
            candidate = opportunity.candidate
            coverage = opportunity.date_coverage
            quotes = shortlist[candidate.key]
            # Select within one tax basis; never rank an unknown-tax quote against a tax-inclusive quote.
            comparable = [f for f in quotes if f.price_basis == "total_including_taxes"] or quotes
            selected = min(comparable, key=lambda f: f.amount).request.outbound_date if comparable else (
                min((s for s in coverage.samples if s.status == "ok"), key=lambda s: s.amount).date
                if any(s.status == "ok" for s in coverage.samples) else representative_dates(goal, 3, candidate.date_hint)[1 if goal.date_from != goal.date_to else 0])
            if goal.date_mode == "flexible" and comparable:
                checked = {s.date for s in coverage.samples if s.stage != "range"}
                neighbors = [selected + timedelta(days=d) for d in [-1, 1]]
                neighbors = [d for d in neighbors if goal.date_from <= d <= goal.date_to and d >= today_local() and d not in checked]
                for outbound in neighbors[:self.r.settings.fine_dates]:
                    provider = next((p for p in self.r.fares if p.name == "SerpAPI"), self.r.fares[0] if self.r.fares else None)
                    if provider:
                        quotes.extend(await self.quote(provider, opportunity, outbound, "fine"))
                comparable = [f for f in quotes if f.price_basis == "total_including_taxes"] or quotes
                selected = min(comparable, key=lambda f: f.amount).request.outbound_date
            coverage.selected_date = selected
            # Preserve valid sampled quotes if the final refresh fails, keeping their timestamps.
            opportunity.fares = [f for f in quotes if f.request.outbound_date == selected]
            self.r.emit(self.turn, "date_selected", "ok", f"{candidate.key} 选 {selected} 精确复验；仅为已查样本中的选择",
                        data={"route": candidate.key, "selected_date": str(selected), "attempted_dates": sorted({str(s.date) for s in coverage.samples if s.stage != "range"})})
            for provider in self.r.fares:
                fares = await self.quote(provider, opportunity, selected, "verification")
                if fares:
                    sources = {f.source for f in fares}
                    opportunity.fares = [f for f in opportunity.fares if f.source not in sources] + fares
            self.r.emit(self.turn, "coverage", "info", f"{candidate.key} 日期探索结束；未覆盖部分保持未知",
                        data={"route": candidate.key, "coverage": coverage.model_dump(mode="json")})
