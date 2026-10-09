from __future__ import annotations

import asyncio
from datetime import timedelta
from time import monotonic

from .models import DateCoverage, DateSample, Fare, FareRequest, identity, now
from .research import today_local
from .safety import source_error


def comparable_quotes(quotes):
    inclusive = [f for f in quotes if f.price_basis == "total_including_taxes"]
    if inclusive:
        return inclusive
    groups = {}
    for fare in quotes:
        groups.setdefault((fare.source, fare.price_basis, fare.currency), []).append(fare)
    # Unknown-tax quotes from different sources cannot form a price ranking.
    return max(groups.values(), key=lambda rows: len({f.request.outbound_date for f in rows}), default=[])


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
        self.quotes = {}
        self.http_slots = asyncio.Semaphore(researcher.settings.fare_concurrency)
        self.cli_slot = asyncio.Semaphore(1)
        self.disabled = set()
        self.sources_prepared = False

    async def prepare_sources(self):
        if self.sources_prepared:
            return
        self.sources_prepared = True
        states = self.turn.checkpoint.setdefault('source_availability', {})
        for provider in self.r.fares:
            if not hasattr(provider, 'availability'):
                continue
            try:
                state = await provider.availability()
            except Exception as error:
                state = {'state': 'unknown', 'reason': str(source_error(provider.name, error))}
            states[provider.name] = state
            unavailable = state['state'] in {'quota_exhausted', 'unconfigured', 'auth_unavailable'}
            if unavailable:
                self.disabled.add(provider.name)
            self.turn.metrics['fare_availability_checks'] = self.turn.metrics.get('fare_availability_checks', 0) + provider.availability_checks
            self.r.emit(self.turn, 'source_availability', 'skipped' if unavailable else 'info',
                state.get('reason', '来源可用性检查完成') + ('；本轮降级，不再调用此票价来源' if unavailable else ''),
                provider.name, data=state)

    def saved_quotes(self, opportunity):
        candidate = opportunity.candidate
        return [f for rows in self.turn.checkpoint.get('quotes', {}).values()
                for f in [Fare.model_validate(row) for row in rows]
                if f.request.origin == candidate.origin and f.request.destination == candidate.destination
                and f.request.no_red_eye == self.turn.goal.no_red_eye
                and self.turn.goal.date_from <= f.request.outbound_date <= self.turn.goal.date_to]

    def supplement_dates(self, opportunity):
        coverage, goal = opportunity.date_coverage, self.turn.goal
        if not coverage or goal.date_mode != 'flexible':
            return []
        checked = set(coverage.research_state['attempted_dates'])
        hints = sorted((s for s in coverage.samples if s.stage == 'range' and s.status == 'ok' and s.amount is not None),
                       key=lambda s: s.amount)
        selected = coverage.selected_date or goal.date_from
        candidates = [s.date for s in hints] + [selected + timedelta(days=d) for d in [-1, 1]] + representative_dates(goal)
        return list(dict.fromkeys(d for d in candidates if goal.date_from <= d <= goal.date_to
                    and d >= today_local() and str(d) not in checked))

    def can_supplement(self, opportunity):
        return (self.date_calls < self.r.settings.max_date_calls and any(p.name not in self.disabled for p in self.r.fares)
                and bool(self.supplement_dates(opportunity)))

    async def supplement(self, opportunity):
        for outbound in self.supplement_dates(opportunity)[:max(1, self.r.settings.fine_dates)]:
            for provider in sorted(self.r.fares, key=lambda p: p.name != 'SerpAPI'):
                if provider.name not in self.disabled and await self.quote(provider, opportunity, outbound, 'fine'):
                    break
        quotes = self.saved_quotes(opportunity)
        comparable = comparable_quotes(quotes)
        if comparable:
            opportunity.date_coverage.selected_date = min(comparable, key=lambda f: f.amount).request.outbound_date
        await self.finish(opportunity, quotes, refine=False)

    async def quote(self, provider, opportunity, outbound, stage):
        await self.prepare_sources()
        goal = self.turn.goal
        request = FareRequest(origin=opportunity.candidate.origin, destination=opportunity.candidate.destination,
                              outbound_date=outbound,
                              return_date=outbound + timedelta(days=goal.stay_days) if goal.trip_type == "round_trip" else None,
                              no_red_eye=goal.no_red_eye)
        category = "verification_calls" if stage == "verification" else "date_calls"
        if provider.name in self.disabled:
            self.r.emit(self.turn, "fare" if stage == "verification" else "date_exploration", "skipped",
                        "本轮此来源配置或配额不可用；不重复调用", provider.name,
                        data={"route": opportunity.candidate.key, "date_stage": stage})
            return []
        cache_key = (provider.name, request.model_dump_json())
        # Saved quotes use provider keys, not human display names.
        saved = self.turn.checkpoint.get('quotes', {}).get(provider.name + '|' + request.model_dump_json())
        if saved and cache_key not in self.quotes:
            fares = [Fare.model_validate(row) for row in saved]
            age = max(0, (now() - min(f.observed_at for f in fares)).total_seconds())
            self.quotes[cache_key] = (monotonic() - age, fares)
        cached = self.quotes.get(cache_key)
        if cached and monotonic() - cached[0] <= self.r.settings.quote_reuse_seconds:
            fares = cached[1]
            cheapest = min(fares, key=lambda f: f.amount)
            self.turn.metrics["quote_reuses"] = self.turn.metrics.get("quote_reuses", 0) + 1
            opportunity.date_coverage.samples.append(DateSample(date=outbound, source=provider.name, stage=stage,
                status="ok", amount=cheapest.amount, price_basis=cheapest.price_basis, observed_at=cheapest.observed_at,
                reused=True, request_issued=False, detail="复用本轮同条件报价；未增加API调用，抓取时间不变"))
            self.r.emit(self.turn, "fare" if stage == "verification" else "date_exploration", "ok",
                "复用本轮刚取得的同条件报价；保留原抓取时间", provider.name, phase="completed", duration_ms=0,
                data={"route": opportunity.candidate.key, "request": request.model_dump(mode="json"),
                      "date_stage": stage, "reused": True, "fare_ids": [f.id for f in fares]})
            return fares
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
        action = identity(self.turn.id, stage, opportunity.candidate.key, str(outbound), provider.name)
        trace_stage = "fare" if stage == "verification" else "date_exploration"
        data = {"route": opportunity.candidate.key, "request": request.model_dump(mode="json"), "date_stage": stage}
        self.r.emit(self.turn, trace_stage, "info", f"{stage}：{opportunity.candidate.key} {outbound}", provider.name,
                    action_id=action, phase="started", data=data)
        start = monotonic()
        issued = False
        try:
            async with asyncio.timeout(self.r.settings.source_timeout + 5):
                async with self.http_slots if provider.name == "SerpAPI" else self.cli_slot:
                    if provider.name in self.disabled:
                        return []
                    issued = True
                    self.turn.metrics[category] = self.turn.metrics.get(category, 0) + 1
                    fares = await provider.verify(request)
            if not fares:
                raise ValueError("empty fare result")
            self.quotes[cache_key] = (monotonic(), fares)
            self.turn.checkpoint.setdefault('quotes', {})[provider.name + '|' + request.model_dump_json()] = [f.model_dump(mode='json') for f in fares]
            cheapest = min(fares, key=lambda f: f.amount)
            if stage != "verification":
                opportunity.fares.extend(fares)
            else:
                sources = {f.source for f in fares}
                opportunity.fares = [f for f in opportunity.fares if f.source not in sources] + fares
            opportunity.date_coverage.samples.append(DateSample(date=outbound, source=provider.name, stage=stage,
                status="ok", amount=cheapest.amount, price_basis=cheapest.price_basis, observed_at=cheapest.observed_at))
            self.r.emit(self.turn, trace_stage, "ok", f"{opportunity.candidate.key} {outbound}：{len(fares)} 条匹配报价",
                        provider.name, action_id=action, phase="completed", duration_ms=int((monotonic()-start)*1000),
                      data=data | {"fare_ids": [f.id for f in fares], "amount": cheapest.amount, "price_basis": cheapest.price_basis})
            if hasattr(self.r, 'publish_results'):
                self.r.publish_results(self.turn)
            return fares
        except asyncio.CancelledError:
            if issued:
                opportunity.date_coverage.samples.append(DateSample(date=outbound, source=provider.name, stage=stage,
                    status="failed", detail="研究时间预算到达；本次未取得报价"))
            self.r.emit(self.turn, trace_stage, "failed", "研究时间预算到达；本次未取得报价", provider.name,
                action_id=action, phase="completed", duration_ms=int((monotonic()-start)*1000), data=data | {"request_issued":issued})
            raise
        except Exception as error:
            failure = source_error(provider.name, error)
            if failure.code in {"AUTH_OR_QUOTA", "QUOTA_EXHAUSTED", "AUTH_FAILED", "RATE_LIMITED", "MISSING_KEY", "NOT_INSTALLED", "NODE_NOT_INSTALLED", "ROUND_TRIP_INCOMPLETE"}:
                self.disabled.add(provider.name)
            if failure.code == 'QUOTA_EXHAUSTED':
                state = {'state': 'quota_exhausted', 'searches_left': 0, 'reason': '票价来源额度已用完'}
                self.turn.checkpoint.setdefault('source_availability', {})[provider.name] = state
                self.r.emit(self.turn, trace_stage, 'skipped', '额度已用完；保留结果并使用其他来源', provider.name,
                    action_id=action, phase='completed', duration_ms=int((monotonic()-start)*1000), data=data | state)
                return []
            detail = str(failure)
            if issued:
                opportunity.date_coverage.samples.append(DateSample(date=outbound, source=provider.name, stage=stage,
                    status="failed", detail=detail))
            else:
                detail = "等待调用空位超时；尚未发起API请求"
            self.r.emit(self.turn, trace_stage, "failed", detail, provider.name, action_id=action, phase="completed",
                        duration_ms=int((monotonic()-start)*1000), data=data | {"request_issued":issued})
            return []

    async def run(self, opportunities, *, progressive=False):
        await self.prepare_sources()
        goal = self.turn.goal
        for opportunity in opportunities:
            if opportunity.date_coverage is None:
                opportunity.date_coverage = DateCoverage(date_from=goal.date_from, date_to=goal.date_to,
                    notes=["有预算粗筛→精查；未遍历全日期窗口，不能称为全月最低。"])
        # Give every evidence-grounded route coarse coverage before refining any route.
        shortlist = {}
        for opportunity in opportunities:
            candidate = opportunity.candidate
            coverage = opportunity.date_coverage
            completed = (candidate.key in self.turn.checkpoint.get('completed_routes', [])
                         and (goal.date_mode == 'fixed' or coverage.research_state['precise_successful_date_count'] >= 2))
            if completed:
                # Keep successful date exploration; only refresh/recover selected-day verification.
                await self.finish(opportunity, [f for rows in self.turn.checkpoint.get('quotes', {}).values()
                    for f in [Fare.model_validate(row) for row in rows]
                    if f.request.origin == candidate.origin and f.request.destination == candidate.destination], refine=False)
                continue
            if candidate.key in self.turn.checkpoint.get('initialized_date_routes', []) or candidate.key in self.turn.checkpoint.get('date_plans', {}):
                await self.supplement(opportunity)
                continue
            returned = []
            plans = self.turn.checkpoint.setdefault('date_plans', {})
            if goal.date_mode == "flexible" and candidate.key not in plans and self.date_calls < self.r.settings.max_date_calls:
                range_providers = [p for p in self.r.fares if hasattr(p, "explore") and p.name not in self.disabled]
                preferred = "SerpAPI" if self.r.settings.date_hint_source == "explore" else "FlyAI"
                range_providers.sort(key=lambda p: p.name != preferred)
                for provider in range_providers:
                    if self.date_calls >= self.r.settings.max_date_calls:
                        break
                    self.date_calls += 1
                    self.turn.metrics["date_calls"] = self.turn.metrics.get("date_calls", 0) + 1
                    action = identity(self.turn.id, "range", candidate.key, provider.name)
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
                        if returned:
                            break
                    except Exception as error:
                        failure = source_error(provider.name, error)
                        if failure.code in {"AUTH_OR_QUOTA", "QUOTA_EXHAUSTED", "AUTH_FAILED", "RATE_LIMITED", "MISSING_KEY", "NOT_INSTALLED", "NODE_NOT_INSTALLED"}:
                            self.disabled.add(provider.name)
                        if failure.code == 'QUOTA_EXHAUSTED':
                            self.turn.checkpoint.setdefault('source_availability', {})[provider.name] = {
                                'state':'quota_exhausted', 'searches_left':0, 'reason':'票价来源额度已用完'}
                        self.r.emit(self.turn, "date_exploration", "skipped" if failure.code == 'QUOTA_EXHAUSTED' else "failed", str(failure), provider.name,
                                    action_id=action, phase="completed", duration_ms=int((monotonic()-started)*1000), data=data)
            coarse = representative_dates(goal, self.r.settings.coarse_dates, candidate.date_hint)
            # A provider-returned date is a lead; exact quotes still establish valid coverage.
            if returned and len(coarse) > 1 and min(returned, key=lambda s: s.amount).date not in coarse:
                coarse[len(coarse)//2] = min(returned, key=lambda s: s.amount).date
                coarse = sorted(set(coarse))
            if returned and len(coarse) > 2:
                hinted = min(returned, key=lambda s: s.amount).date
                # Range is a lead, not coverage. Check its cheapest date plus a distant anchor.
                anchor = max(coarse, key=lambda d: abs((d-hinted).days))
                coarse = sorted({hinted, anchor})
            if candidate.key in plans:
                from datetime import date
                coarse = [date.fromisoformat(d) for d in plans[candidate.key]]
            else:
                plans[candidate.key] = list(map(str, coarse))
            self.r.emit(self.turn, "date_plan", "info", f"{candidate.key} 代表日：{', '.join(map(str, coarse))}；预留少量邻近精查",
                        data={"route": candidate.key, "dates": list(map(str, coarse)), "basis": "有范围线索时查线索日和远端代表日；否则窗口首/中/尾"})
            quotes = []
            # A precise global source is preferred for comparable coarse prices.
            providers = sorted(self.r.fares, key=lambda p: p.name != "SerpAPI")
            async def coarse_quote(outbound):
                if self.date_calls >= self.r.settings.max_date_calls or goal.date_mode == "fixed":
                    return []
                for provider in providers:
                    previous = [Fare.model_validate(row) for key, rows in self.turn.checkpoint.get('quotes', {}).items()
                        if key.startswith(provider.name + '|') for row in rows]
                    previous = [f for f in previous if f.request.origin == candidate.origin and f.request.destination == candidate.destination
                        and f.request.outbound_date == outbound and f.request.no_red_eye == goal.no_red_eye]
                    if previous:
                        self.r.emit(self.turn, 'checkpoint', 'skipped', '保留已经完成的日期探索；选定日仍按新鲜度验价', provider.name,
                            data={'route':candidate.key, 'date':str(outbound)})
                        return previous
                    fares = await self.quote(provider, opportunity, outbound, "coarse")
                    if fares:
                        return fares
                return []
            for result in await asyncio.gather(*(coarse_quote(outbound) for outbound in coarse)):
                quotes.extend(result)
            shortlist[candidate.key] = quotes
            self.turn.checkpoint.setdefault('initialized_date_routes', []).append(candidate.key)
            if progressive:
                await self.finish(opportunity, quotes)
        if progressive:
            return
        for opportunity in opportunities:
            candidate = opportunity.candidate
            coverage = opportunity.date_coverage
            if candidate.key not in shortlist:
                continue
            quotes = shortlist[candidate.key]
            await self.finish(opportunity, quotes)

    async def finish(self, opportunity, quotes, *, refine=True):
        goal = self.turn.goal
        candidate = opportunity.candidate
        coverage = opportunity.date_coverage
        # Select within one tax basis; never rank an unknown-tax quote against a tax-inclusive quote.
        comparable = comparable_quotes(quotes)
        selected = coverage.selected_date if not refine and coverage.selected_date else (
            min(comparable, key=lambda f: f.amount).request.outbound_date if comparable else (
                min((s for s in coverage.samples if s.status == "ok"), key=lambda s: s.amount).date
                if any(s.status == "ok" for s in coverage.samples) else representative_dates(goal, 3, candidate.date_hint)[1 if goal.date_from != goal.date_to else 0]))
        if refine and goal.date_mode == "flexible" and comparable:
            checked = {s.date for s in coverage.samples if s.stage != "range"}
            neighbors = [selected + timedelta(days=d) for d in [-1, 1]]
            neighbors = [d for d in neighbors if goal.date_from <= d <= goal.date_to and d >= today_local() and d not in checked]
            midpoint = goal.date_from + (goal.date_to - goal.date_from) / 2
            neighbors.sort(key=lambda d: abs((d-midpoint).days))
            if coverage.research_state['precise_successful_date_count'] == 1:
                # Returned range prices guide the next request but never establish coverage.
                neighbors = self.supplement_dates(opportunity)
            for outbound in neighbors[:self.r.settings.fine_dates]:
                for provider in sorted(self.r.fares, key=lambda p: p.name != 'SerpAPI'):
                    if provider.name in self.disabled:
                        continue
                    fares = await self.quote(provider, opportunity, outbound, 'fine')
                    if fares:
                        quotes.extend(fares)
                        break
            comparable = comparable_quotes(quotes)
            selected = min(comparable, key=lambda f: f.amount).request.outbound_date
        coverage.selected_date = selected
        # Preserve valid sampled quotes if the final refresh fails, keeping their timestamps.
        opportunity.fares = [f for f in quotes if f.request.outbound_date == selected]
        self.r.emit(self.turn, "date_selected", "ok", f"{candidate.key} 选 {selected} 精确复验；仅为已查样本中的选择",
                    data={"route": candidate.key, "selected_date": str(selected), **coverage.research_state})
        for provider in self.r.fares:
            fares = await self.quote(provider, opportunity, selected, "verification")
            if fares:
                sources = {f.source for f in fares}
                opportunity.fares = [f for f in opportunity.fares if f.source not in sources] + fares
        self.r.emit(self.turn, "coverage", "info", f"{candidate.key} 已取得 {coverage.research_state['precise_successful_date_count']} 个不同日期的精确报价；未覆盖部分保持未知",
                    data={"route": candidate.key, "coverage": coverage.model_dump(mode="json")})
        completed = self.turn.checkpoint.setdefault('completed_routes', [])
        if candidate.key in completed and goal.date_mode != 'fixed' and coverage.research_state['precise_successful_date_count'] < 2:
            completed.remove(candidate.key)
        if (goal.date_mode == 'fixed' or coverage.research_state['precise_successful_date_count'] >= 2) and candidate.key not in completed:
            self.turn.checkpoint['completed_routes'].append(candidate.key)
        if hasattr(self.r, 'publish_results'):
            self.r.publish_results(self.turn)
