import json
import threading
from datetime import date
from urllib.request import Request, urlopen

import pytest

from farescout.config import Settings
from farescout.dates import representative_dates
from farescout.engine import Researcher, Store
from farescout.models import DateSample, Session
from farescout.research import evolve_goal
from farescout.web import create_server
from test_engine import TestBrain, WorkingSocial, WorkingFare
from test_prices import payload
from farescout.providers import flyai_fares


def test_time_semantics_have_explicit_window_and_provenance():
    g = evolve_goal('香港 11 月飞日本哪里便宜？', today=date(2026, 10, 1))
    assert g.origins == ['HKG'] and g.region == 'JP'
    assert (g.date_from, g.date_to) == (date(2026, 11, 1), date(2026, 11, 30))
    assert g.date_mode == 'flexible'
    assert next(c for c in g.constraints if c.field == 'date_from').provenance == 'inferred'
    g = evolve_goal('不要红眼', g, today=date(2026, 10, 1))
    assert g.date_from == date(2026, 11, 1)
    assert next(c for c in g.constraints if c.field == 'date_from').provenance == 'context'
    assert '跨夜' in next(c for c in g.constraints if c.field == 'no_red_eye').rule
    g = evolve_goal('日期无所谓', g, today=date(2026, 10, 1))
    assert (g.date_to-g.date_from).days == 179
    g = evolve_goal('最近', g, today=date(2026, 10, 1))
    assert (g.date_to-g.date_from).days == 59
    g = evolve_goal('2026-11-10', g, today=date(2026, 10, 1))
    assert g.date_mode == 'fixed'


class CalendarFare(WorkingFare):
    name = 'SerpAPI'
    def __init__(self):
        self.calls = []

    async def verify(self, req):
        self.calls.append(req.outbound_date)
        # A cheap middle date; local refinement should follow observed prices.
        amount = 500 if req.outbound_date.day in {15, 16} else 1800
        data = payload(str(amount), depDateTime=f'{req.outbound_date} 10:00:00', arrDateTime=f'{req.outbound_date} 15:00:00')
        return [f.model_copy(update={'source': self.name, 'price_basis': 'total_including_taxes'}) for f in flyai_fares(data, req)]


async def test_bounded_dates_follow_prices_persist_trace_and_never_claim_month_minimum(tmp_path):
    provider = CalendarFare()
    r = Researcher(Settings(data_dir=tmp_path, max_date_calls=4, max_fare_calls=1), brain=TestBrain(),
                   social=[WorkingSocial()], fares=[provider])
    s = await r.run('香港11月日本', None, 'p1')
    t = s.turns[-1]
    c = t.opportunities[0].date_coverage
    assert len(provider.calls) == 4
    assert t.metrics['date_calls'] == 4 and t.metrics.get('verification_calls', 0) == 0
    assert t.metrics['quote_reuses'] == 1
    assert len({v.date for v in c.samples if v.stage != 'verification'}) == 4
    assert c.selected_date.day in {15, 16}
    assert any(v.stage == 'fine' for v in c.samples)
    restored = Store(tmp_path).load('p1')
    assert [e.id for e in restored.turns[-1].events] == [e.id for e in t.events]
    assert all(e.turn_id == t.id for e in t.events)
    assert any(e.duration_ms is not None for e in t.events)
    report = next(tmp_path.glob('p1-*.md')).read_text()
    assert '不是整个日期窗口' in report


async def test_range_failure_falls_back_and_records_failed_date(tmp_path):
    class RangeFailure(CalendarFare):
        name = 'FlyAI'
        async def explore(self, *_):
            raise TimeoutError()
    class DateFailure(CalendarFare):
        async def verify(self, req):
            if req.outbound_date.day == 1:
                raise TimeoutError()
            return await super().verify(req)
    r = Researcher(Settings(data_dir=tmp_path, max_date_calls=6, max_fare_calls=2), brain=TestBrain(),
                   social=[WorkingSocial()], fares=[RangeFailure(), DateFailure()])
    s = await r.run('香港11月日本', None, 'failure')
    t = s.turns[-1]
    assert t.opportunities[0].fares
    assert any(e.status == 'failed' and e.data.get('date_stage') == 'range' for e in t.events)
    assert any(x.status == 'failed' and x.date.day == 1 for x in t.opportunities[0].date_coverage.samples)
    assert t.metrics['date_calls'] <= 6


def test_old_sessions_still_load():
    s = Session.model_validate({'schema_version': 1, 'id': 'old', 'goal': {'date_from': '2026-11-01', 'date_to': '2026-11-30'}})
    assert s.goal.date_mode == 'flexible' and s.goal.constraints == []


async def test_socai_timeout_retries_once_and_counts_real_commands(tmp_path, monkeypatch):
    from farescout.providers import Socai
    attempts = []
    async def command(executable, args, settings, source):
        attempts.append(args)
        if args[0] == 'status':
            return {'browser_connected':True}
        if sum(a[0] == 'xhs' for a in attempts) == 1:
            raise TimeoutError()
        return {'notes':[{'entity':{'note_id':'12345678','title':'香港日本机票','content':'香港飞日本机票活动，须确认日期。'}}]}
    monkeypatch.setattr('farescout.providers.command_json', command)
    socai = Socai(Settings(data_dir=tmp_path, socai_mode='scan'))
    retries = []
    socai.on_retry = retries.append
    records = await socai.search('香港 日本 机票 11月 便宜')
    # Two searches, two readiness checks and one fresh post-timeout check.
    assert socai.command_calls == 5 and sum(a[0] == 'xhs' for a in attempts) == 2
    assert retries == ['香港 日本 机票']
    assert records[0].query == retries[0]


async def test_seed_stays_in_user_scope_and_keeps_agent_second_query():
    from farescout.research import Brain
    from farescout.models import SearchPlan
    brain = Brain(Settings())
    async def ask(*_):
        return SearchPlan(queries=['香港 日本 机票', '香港 日本 航空 促销'])
    brain.ask = ask
    goal = evolve_goal('香港11月日本', today=date(2026, 10, 1))
    assert await brain.plan('香港11月日本', goal) == ['香港 日本 机票', '香港 日本 航空 促销']


async def test_first_turn_defaults_remain_defaults_not_context(tmp_path):
    r = Researcher(Settings(data_dir=tmp_path), brain=TestBrain(), social=[WorkingSocial()], fares=[CalendarFare()])
    s = await r.run('香港11月日本', None, 'defaults')
    c = next(c for c in s.goal.constraints if c.field == 'trip_type')
    assert c.provenance == 'default'


async def test_missing_expansion_gets_one_grounded_repair_not_invented_routes(tmp_path):
    from farescout.models import Discovery, Expansion
    from test_research import candidate
    class RepairBrain(TestBrain):
        repairs = 0
        async def discover(self, *_):
            return Discovery(candidates=[candidate()])
        async def expand(self, *_):
            self.repairs += 1
            return [Expansion(query='香港快运 东京 促销', evidence_id='p1', discovered_term='香港快运', reason='原文航司继续调查')]
    brain = RepairBrain()
    s = await Researcher(Settings(data_dir=tmp_path), brain=brain, social=[WorkingSocial()], fares=[CalendarFare()]).run('香港11月日本', None, 'repair')
    assert brain.repairs == 1
    assert any(e.stage == 'query_expansion' and e.status == 'ok' for e in s.turns[-1].events)
    assert len(s.turns[-1].opportunities) == 1


def test_live_api_sse_history_and_cross_origin_rejection(tmp_path):
    settings = Settings(data_dir=tmp_path)
    def factory(s):
        return Researcher(s, brain=TestBrain(), social=[WorkingSocial()], fares=[CalendarFare()])
    server = create_server(settings, 0, factory)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{server.server_port}'
    try:
        req = Request(base+'/api/run', json.dumps({'session_id':'ui-test','message':'香港11月日本'}).encode(), {'Content-Type':'application/json'})
        assert urlopen(req).status == 202
        with urlopen(base+'/api/sessions/ui-test/events', timeout=15) as response:
            lines = response.read().decode()
        assert 'event: research' in lines and 'event: done' in lines and 'date_exploration' in lines
        snap = json.load(urlopen(base+'/api/sessions/ui-test'))
        events = snap['session']['turns'][-1]['events']
        last = events[-2]['id']
        replay = urlopen(Request(base+'/api/sessions/ui-test/events', headers={'Last-Event-ID':last})).read().decode()
        assert f'id: {events[-1]["id"]}' in replay and f'id: {last}' not in replay
        assert json.load(urlopen(base+'/api/sessions'))['sessions'][0]['id'] == 'ui-test'
        from urllib.error import HTTPError
        with pytest.raises(HTTPError) as e:
            urlopen(Request(base+'/api/run', b'{}', {'Origin':'https://example.com','Content-Type':'application/json'}))
        assert e.value.code == 403
    finally:
        server.shutdown()
        server.server_close()


def test_frontend_assets_are_served_with_explicit_types_and_no_arbitrary_files(tmp_path):
    from urllib.error import HTTPError
    server = create_server(Settings(data_dir=tmp_path), 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    try:
        for filename, expected in [('ui.css', 'text/css'), ('ui.mjs', 'text/javascript'), ('ui-state.mjs', 'text/javascript')]:
            with urlopen(base + '/assets/' + filename) as response:
                assert response.headers.get_content_type() == expected
                assert response.headers['X-Content-Type-Options'] == 'nosniff'
                assert response.read()
        assert b'/assets/ui.mjs' in urlopen(base).read()
        for path in ['/assets/config.py', '/assets/../config.py', '/assets/.env']:
            with pytest.raises(HTTPError) as error:
                urlopen(base + path)
            assert error.value.code == 404
    finally:
        server.shutdown()
        server.server_close()


def test_a_failed_research_does_not_show_its_error_in_another_session(tmp_path):
    import time
    from farescout.models import Goal
    class Failure:
        def __init__(self, _):
            pass
        async def run(self, *_):
            raise TimeoutError('test source failure')
    server = create_server(Settings(data_dir=tmp_path), 0, Failure)
    server.app.store.save(Session(id='historical', goal=Goal(date_from=date(2026, 11, 1), date_to=date(2026, 11, 30))))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    try:
        server.app.start('failed', 'test research')
        deadline = time.monotonic() + 5
        while server.app.active and time.monotonic() < deadline:
            time.sleep(0.01)
        assert server.app.error and server.app.error_session == 'failed'
        assert json.load(urlopen(base + '/api/sessions/historical'))['error'] is None
    finally:
        server.shutdown()
        server.server_close()
