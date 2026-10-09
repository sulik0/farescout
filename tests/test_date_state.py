import asyncio
from datetime import date

import httpx
import pytest

from farescout.config import Settings
from farescout.dates import DateExplorer
from farescout.engine import Researcher, Store
from farescout.models import DateCoverage, DateSample, Opportunity, ResearchDecision, Turn
from farescout.providers import SerpAPI, flyai_fares
from farescout.research import evolve_goal
from farescout.safety import SourceFailure
from test_engine import TestBrain, WorkingSocial
from test_prices import payload, request, serp
from test_research import candidate

HTTP_CLIENT = httpx.AsyncClient


def test_date_categories_do_not_mix_and_legacy_reuse_is_migrated():
    def sample(day, **changes):
        return DateSample(date=date(2026, 11, day), source='test', stage='coarse', status='ok', amount=900,
                          **changes) if not changes else DateSample.model_validate(dict(
                              date=f'2026-11-{day:02}', source='test', stage='coarse', status='ok', amount=900) | changes)
    coverage = DateCoverage(date_from=date(2026, 11, 1), date_to=date(2026, 11, 30), samples=[
        sample(1), sample(1, source='other'), sample(2, status='failed', amount=None),
        sample(3, stage='range'), sample(4, reused=True, request_issued=False),
        sample(5, detail='复用本轮同条件报价'), sample(6, request_issued=False, status='failed'),
        sample(7, amount=None), sample(8, amount=0)])
    state = coverage.research_state
    assert state['attempted_dates'] == ['2026-11-01', '2026-11-02', '2026-11-07', '2026-11-08']
    assert state['precise_successful_dates'] == ['2026-11-01']
    assert state['failed_dates'] == ['2026-11-02']
    assert state['range_hint_dates'] == ['2026-11-03']
    assert state['reused_quote_dates'] == ['2026-11-04', '2026-11-05']
    persisted = coverage.model_dump(mode='json')
    persisted['research_state']['precise_successful_date_count'] = 99
    assert DateCoverage.model_validate(persisted).research_state['precise_successful_date_count'] == 1


def mocked_serpapi(monkeypatch, handler):
    monkeypatch.setattr('farescout.providers.httpx.AsyncClient',
                        lambda **kwargs: HTTP_CLIENT(transport=httpx.MockTransport(handler), **kwargs))
    return SerpAPI(Settings(serpapi_key='test-key'))


async def test_zero_quota_checks_account_once_and_never_searches(monkeypatch, tmp_path):
    paths = []
    def handler(req):
        paths.append(req.url.path)
        assert req.url.path == '/account.json'
        return httpx.Response(200, json={'total_searches_left': 0})
    provider = mocked_serpapi(monkeypatch, handler)
    states = await asyncio.gather(*(provider.availability() for _ in range(4)))
    assert all(s['state'] == 'quota_exhausted' for s in states)
    for _ in range(3):
        with pytest.raises(SourceFailure, match='QUOTA_EXHAUSTED'):
            await provider.verify(request())
    r = Researcher(Settings(data_dir=tmp_path), brain=TestBrain(), social=[WorkingSocial()], fares=[provider])
    session = await r.run('香港11月日本', None, 'zero-quota')
    turn = session.turns[-1]
    assert provider.search_requests == 0 and paths == ['/account.json', '/account.json']
    assert turn.metrics['fare_availability_checks'] == 1  # New execution checks once after the standalone provider checks.
    assert not any(e.source == 'SerpAPI' and e.status == 'failed' for e in turn.events)
    assert turn.checkpoint['source_availability']['SerpAPI']['state'] == 'quota_exhausted'
    assert turn.opportunities[0].date_coverage.research_state['attempted_dates'] == []
    assert turn.metrics.get('date_calls', 0) == 0


async def test_new_turn_rechecks_quota_after_refill_without_restart(monkeypatch, tmp_path):
    state, paths = {'left':0}, []
    def handler(req):
        paths.append(req.url.path)
        return httpx.Response(200, json={'total_searches_left':state['left']} if req.url.path == '/account.json' else serp())
    provider = mocked_serpapi(monkeypatch, handler)
    r = Researcher(Settings(data_dir=tmp_path), brain=TestBrain(), social=[WorkingSocial()], fares=[provider])
    session = await r.run('香港2026-11-10日本', None, 'refill')
    assert not session.turns[-1].opportunities[0].fares
    state['left'] = 10
    session = await r.run('香港2026-11-10日本', session, 'refill')
    assert session.turns[-1].opportunities[0].fares
    assert session.turns[-1].metrics['fare_availability_checks'] == 1
    assert paths == ['/account.json', '/account.json', '/search.json']


async def test_quota_error_stops_further_search_but_rate_limit_is_distinct(monkeypatch):
    paths = []
    def handler(req):
        paths.append(req.url.path)
        return httpx.Response(200, json={'total_searches_left': 10}) if req.url.path == '/account.json' else httpx.Response(
            429, json={'error': 'Your account has run out of searches.'})
    provider = mocked_serpapi(monkeypatch, handler)
    for _ in range(3):
        with pytest.raises(SourceFailure, match='QUOTA_EXHAUSTED'):
            await provider.verify(request())
    assert paths == ['/account.json', '/search.json']
    # A failed account check is cached for this execution, not retried per date.
    def limited(req):
        return httpx.Response(503 if req.url.path == '/account.json' else 429, json={})
    provider = mocked_serpapi(monkeypatch, limited)
    with pytest.raises(SourceFailure, match='RATE_LIMITED'):
        await provider.verify(request())
    assert provider.availability_checks == 1


class RangeFare:
    name = 'FlyAI'

    def __init__(self):
        self.calls = []

    async def explore(self, origin, destination, goal):
        return [DateSample(date=date(2026, 11, day), source=self.name, stage='range', status='ok', amount=100+day)
                for day in [4, 5, 9]]

    async def verify(self, req):
        self.calls.append((req.destination, req.outbound_date.day))
        if req.outbound_date.day not in [4, 5, 9]:
            raise SourceFailure(self.name, 'API_ERROR', '测试代表日无结果')
        return flyai_fares(payload(str(800+req.outbound_date.day), arrStationCode=req.destination,
            depDateTime=f'{req.outbound_date} 10:00:00', arrDateTime=f'{req.outbound_date} 15:00:00'), req)


async def test_three_routes_get_two_real_days_without_range_or_reuse_inflation(monkeypatch, tmp_path):
    serp = mocked_serpapi(monkeypatch, lambda req: httpx.Response(200, json={'total_searches_left':0}))
    fly = RangeFare()
    goal = evolve_goal('香港11月日本', today=date(2026, 10, 1))
    turn = Turn(id='coverage', user_input='q', goal=goal)
    routes = [Opportunity(candidate=candidate(destination=code)) for code in ['NRT', 'KIX', 'OKA']]
    r = Researcher(Settings(data_dir=tmp_path, max_date_calls=15), brain=TestBrain(), social=[], fares=[serp, fly])
    explorer = DateExplorer(r, turn)
    await explorer.run(routes, progressive=True)
    assert len(fly.calls) == 9 and explorer.date_calls == 12  # 3 range + 9 exact; no full-month scan.
    assert turn.metrics['quote_reuses'] == 3 and serp.search_requests == 0
    for route in routes:
        assert route.date_coverage.research_state['precise_successful_dates'] == ['2026-11-04', '2026-11-05']
        assert route.date_coverage.research_state['failed_dates'] == ['2026-11-30']
        assert route.date_coverage.research_state['quote_reuse_count'] == 1
    assert set(turn.checkpoint['completed_routes']) == {'HKG-NRT', 'HKG-KIX', 'HKG-OKA'}


async def test_one_success_is_not_completed_and_resume_supplements_without_rescanning(tmp_path):
    class Sometimes(RangeFare):
        async def verify(self, req):
            if req.outbound_date.day == 5:
                self.calls.append((req.destination, 5))
                raise SourceFailure(self.name, 'API_ERROR', '测试第二个线索日无结果')
            return await super().verify(req)
    fly = Sometimes()
    goal = evolve_goal('香港11月日本', today=date(2026, 10, 1))
    turn = Turn(id='supplement', user_input='q', goal=goal)
    opportunity = Opportunity(candidate=candidate())
    r = Researcher(Settings(data_dir=tmp_path), brain=TestBrain(), social=[], fares=[fly])
    explorer = DateExplorer(r, turn)
    await explorer.run([opportunity], progressive=True)
    assert opportunity.date_coverage.research_state['precise_successful_date_count'] == 1
    assert 'HKG-NRT' not in turn.checkpoint.get('completed_routes', [])
    await explorer.run([opportunity], progressive=True)
    assert fly.calls == [('NRT', 4), ('NRT', 30), ('NRT', 5), ('NRT', 9)]
    assert opportunity.date_coverage.research_state['precise_successful_dates'] == ['2026-11-04', '2026-11-09']
    assert 'HKG-NRT' in turn.checkpoint['completed_routes']


async def test_agent_receives_separate_date_state_and_cannot_stop_at_one_day(tmp_path):
    class Brain(TestBrain):
        contexts = []
        async def decide(self, goal, context):
            self.contexts.append(context)
            return ResearchDecision(action='stop', reason='测试不能提前停止')
    brain = Brain()
    class FailedSecondHint(RangeFare):
        async def verify(self, req):
            if req.outbound_date.day == 5:
                self.calls.append((req.destination, 5))
                raise SourceFailure(self.name, 'API_ERROR', '测试第二线索失败')
            return await super().verify(req)
    provider = FailedSecondHint()
    r = Researcher(Settings(data_dir=tmp_path), brain=brain, social=[WorkingSocial()], fares=[provider])
    session = await r.run('香港11月日本', None, 'agent-state')
    turn = session.turns[-1]
    assert turn.opportunities[0].date_coverage.research_state['precise_successful_date_count'] == 2
    contexts = [e.data['context'] for e in turn.events if e.stage == 'research_decision' and 'context' in e.data]
    assert contexts and all('checked_dates' not in row for c in contexts for row in c['routes'])
    assert any(row['date_research_state'] for c in contexts for row in c['routes'])
    assert any(c['allowed_actions'] == ['dates'] and any(row['date_research_state']
               and row['date_research_state']['precise_successful_date_count'] == 1 for row in c['routes']) for c in contexts)
    assert all('stop' not in c['allowed_actions'] for c in contexts if c['allowed_actions'] != ['stop'])
    assert Store(tmp_path).load('agent-state').turns[-1].opportunities[0].date_coverage.research_state['precise_successful_date_count'] == 2
