import asyncio
from datetime import timedelta
import json
import threading
from urllib.request import Request, urlopen

import pytest

from farescout.config import Settings
from farescout.engine import Researcher, Store
from farescout.models import ResearchDecision, now
from farescout.providers import Socai
from farescout.safety import SourceFailure
from farescout.web import create_server
from test_engine import TestBrain, WorkingSocial
from test_p1 import CalendarFare
from test_research import evidence


async def test_first_quote_is_saved_while_second_community_search_runs(tmp_path):
    class Delayed(WorkingSocial):
        async def search(self, query):
            if query == '深圳 国际机票':
                await asyncio.sleep(.08)
            return await super().search(query)
    snapshots = []
    store = Store(tmp_path)
    def observe(event):
        if event.stage == 'result_available':
            snapshots.append(store.load('overlap'))
    session = await Researcher(Settings(data_dir=tmp_path), brain=TestBrain(), social=[Delayed()],
        fares=[CalendarFare()], on_event=observe).run('香港11月日本', None, 'overlap')
    turn = session.turns[-1]
    first = next(i for i,e in enumerate(turn.events) if e.stage == 'result_available')
    second_done = next(i for i,e in enumerate(turn.events) if e.stage == 'community_search' and e.status == 'ok' and e.data['query'] == '深圳 国际机票')
    assert first < second_done
    assert snapshots[0].turns[-1].opportunities[0].fares
    assert snapshots[0].turns[-1].metrics['first_result_seconds'] >= 0
    assert 'third_result_seconds' not in turn.metrics


class Interrupted(WorkingSocial):
    name = 'recoverable community'
    def __init__(self):
        self.ready = False
        self.calls = []
    async def search(self, query):
        self.calls.append(query)
        if query != '香港 便宜机票' and not self.ready:
            raise SourceFailure(self.name, 'BROWSER_DISCONNECTED', 'CDP断开')
        return await super().search(query)


async def test_resume_retries_partially_read_query_without_losing_body(tmp_path):
    class Partial(WorkingSocial):
        blocked_code = None
        calls = []
        ready = False
        record = evidence()
        async def search(self, query):
            self.calls.append(query)
            self.blocked_code = None if self.ready else 'BROWSER_DISCONNECTED'
            return [self.record]
    source = Partial()
    settings = Settings(data_dir=tmp_path)
    first = await Researcher(settings, brain=TestBrain(), social=[source], fares=[CalendarFare()]).run('香港11月日本', None, 'half-read')
    event = next(e for e in first.turns[-1].events if e.stage == 'community_search' and e.status == 'ok')
    assert event.data['complete'] is False
    observed = first.evidence['p1'].observed_at
    source.ready = True
    await Researcher(settings, brain=TestBrain(), social=[source], fares=[CalendarFare()]).run('', first, 'half-read', resume=True)
    assert source.calls.count('香港 便宜机票') == 2
    assert first.evidence['p1'].observed_at == observed


async def test_resume_keeps_turn_successful_search_dates_and_quote_time(tmp_path):
    source, fares = Interrupted(), CalendarFare()
    settings = Settings(data_dir=tmp_path)
    first = await Researcher(settings, brain=TestBrain(), social=[source], fares=[fares]).run('香港11月日本', None, 'recover')
    turn_id = first.turns[-1].id
    quote_time = first.turns[-1].opportunities[0].fares[0].observed_at
    count = len(fares.calls)
    assert first.turns[-1].checkpoint['recovery_required'] == 'BROWSER_DISCONNECTED'
    source.ready = True
    restored = Store(tmp_path).load('recover')
    result = await Researcher(settings, brain=TestBrain(), social=[source], fares=[fares]).run('', restored, 'recover', resume=True)
    turn = result.turns[-1]
    assert len(result.turns) == 1 and turn.id == turn_id
    assert source.calls.count('香港 便宜机票') == 1
    assert len(fares.calls) == count
    assert turn.opportunities[0].fares[0].observed_at == quote_time
    assert turn.metrics['execution_segments'] == 2
    assert any(e.stage == 'checkpoint' for e in turn.events)
    assert any(e.status == 'failed' and e.source == source.name for e in turn.events)


async def test_resume_refreshes_stale_final_quote_without_repeating_date_exploration(tmp_path):
    settings = Settings(data_dir=tmp_path)
    fares = CalendarFare()
    first = await Researcher(settings, brain=TestBrain(), social=[WorkingSocial()], fares=[fares]).run('香港11月日本', None, 'stale')
    turn = first.turns[-1]
    for rows in turn.checkpoint['quotes'].values():
        for row in rows:
            row['observed_at'] = (now()-timedelta(minutes=5)).isoformat()
    before_calls = len(fares.calls)
    # A restored selected day is authoritative; old cached prices must not rerank it.
    selected = turn.goal.date_from
    turn.opportunities[0].date_coverage.selected_date = selected
    dates = turn.metrics['date_calls']
    await Researcher(settings, brain=TestBrain(), social=[WorkingSocial()], fares=[fares]).run('', first, 'stale', resume=True)
    assert len(fares.calls) == before_calls + 1
    assert fares.calls[-1] == selected
    assert turn.metrics['date_calls'] == dates
    assert (now()-turn.opportunities[0].fares[0].observed_at).total_seconds() < 2


async def test_agent_choice_is_checked_and_promotion_uses_existing_source(tmp_path):
    class DecisionBrain(TestBrain):
        contexts = []
        async def decide(self, goal, context):
            self.contexts.append(context)
            # Stopping before needed work is not allowed; program must reject it.
            return ResearchDecision(action='stop', reason='测试不符合允许操作的停止选择')
    brain = DecisionBrain()
    session = await Researcher(Settings(data_dir=tmp_path), brain=brain, social=[WorkingSocial()], fares=[CalendarFare()]).run('香港11月日本', None, 'decisions')
    assert session.turns[-1].opportunities[0].fares
    assert any(e.stage == 'research_decision' and e.status == 'failed' for e in session.turns[-1].events)
    assert any(e.stage == 'query_expansion' and e.status == 'ok' for e in session.turns[-1].events)
    assert all(set(c['allowed_actions']) <= {'community','dates','promotion','stop'} for c in brain.contexts)


async def test_cancelled_pipeline_has_no_late_quote_after_conclusion(tmp_path):
    class Slow(CalendarFare):
        async def verify(self, request):
            await asyncio.sleep(2)
            return await super().verify(request)
    session = await Researcher(Settings(data_dir=tmp_path, max_seconds=.02), brain=TestBrain(), social=[WorkingSocial()], fares=[Slow()]).run('香港11月日本', None, 'cancel')
    turn = session.turns[-1]
    assert turn.events[-1].stage == 'conclusion'
    assert not turn.opportunities[0].fares
    assert 'first_result_seconds' not in turn.metrics


async def test_mismatch_stops_before_socai_can_restart_daemon(tmp_path, monkeypatch):
    calls = []
    async def command(executable, args, settings, source):
        calls.append(args)
        return {'daemon_running':True, 'daemon_compatible':False, 'browser_connected':False}
    monkeypatch.setattr('farescout.providers.command_json', command)
    with pytest.raises(SourceFailure, match='DAEMON_VERSION_MISMATCH'):
        await Socai(Settings(data_dir=tmp_path)).search('香港 日本 机票')
    assert calls == [['status','--json']]


async def test_recovery_retains_read_note_without_reopening_or_updating_time(tmp_path, monkeypatch):
    item = evidence().model_copy(update={'url':'https://www.xiaohongshu.com/explore/12345678'})
    source = Socai(Settings(data_dir=tmp_path))
    source.known_notes = {'12345678':item}
    calls=[]
    async def command(executable,args,settings,name):
        calls.append(args)
        if args[0] == 'status':
            return {'browser_connected':True}
        return {'cards':[{'note_id':'12345678','xsec_token':'SECRET'}]}
    monkeypatch.setattr('farescout.providers.command_json',command)
    records=await source.search('香港 日本 机票')
    assert records == [item] and records[0].observed_at == item.observed_at
    assert not any('get-notes' in call for call in calls)


def test_connection_observation_sanitizes_log_and_marks_transition(tmp_path, monkeypatch):
    from farescout.connection import connection_observation
    socai_home=tmp_path/'socai'; socai_home.mkdir()
    (socai_home/'rust-daemon.pid').write_text('12')
    (socai_home/'rust-daemon.log').write_text('2026-10-04T01:00:00Z WARN cdp connection lost CDP session is closed ws://secret/key\n')
    monkeypatch.setenv('SOCAI_HOME', str(socai_home))
    monkeypatch.setenv('SOCAI_CDP_WS','ws://secret/key')
    settings=Settings(data_dir=tmp_path/'data')
    connection_observation({'browser_connected':True},settings)
    after=connection_observation({'browser_connected':False},settings)
    assert after['connection_lost_since_check']
    assert after['authorization']=='unknown' and not after['last_disconnect']['cause_confirmed']
    assert 'secret' not in json.dumps(after)


def test_http_resume_stays_in_same_turn_and_browser_check_does_not_search(tmp_path, monkeypatch):
    source=Interrupted()
    settings=Settings(data_dir=tmp_path)
    def factory(config):
        return Researcher(config, brain=TestBrain(), social=[source], fares=[CalendarFare()])
    server=create_server(settings,0,factory)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    def post(path,body):
        return urlopen(Request(base+path,json.dumps(body).encode(),{'Content-Type':'application/json'}))
    async def command(executable,args,settings,name):
        assert args == ['status','--json']
        return {'browser_connected':True}
    monkeypatch.setattr('farescout.providers.command_json',command)
    try:
        assert post('/api/run',{'session_id':'ui-recovery','message':'香港11月日本'}).status==202
        urlopen(base+'/api/sessions/ui-recovery/events').read()
        before=json.load(urlopen(base+'/api/sessions/ui-recovery'))['session']
        source.ready=True
        assert json.load(urlopen(base+'/api/browser'))['ready']
        assert post('/api/resume',{'session_id':'ui-recovery'}).status==202
        urlopen(base+'/api/sessions/ui-recovery/events').read()
        after=json.load(urlopen(base+'/api/sessions/ui-recovery'))['session']
        assert len(after['turns'])==len(before['turns'])==1
        assert after['turns'][0]['id']==before['turns'][0]['id']
        assert source.calls.count('香港 便宜机票')==1
    finally:
        server.shutdown(); server.server_close()


async def test_cli_connection_exception_is_classified_after_status_check(tmp_path, monkeypatch):
    calls=[]
    async def command(executable,args,settings,name):
        calls.append(args)
        if args[0] == 'status':
            return {'daemon_running':True, 'daemon_compatible':True,
                'browser_connected':False, 'browser_state':'disconnected'}
        raise SourceFailure(name, 'BROWSER_OR_LOGIN_REQUIRED', 'websocket握手失败')
    monkeypatch.setattr('farescout.providers.command_json', command)
    with pytest.raises(SourceFailure, match='BROWSER_DISCONNECTED'):
        await Socai(Settings(data_dir=tmp_path)).search('香港 日本 机票')
    assert sum(args[0]=='xhs' for args in calls)==1
    assert calls[-1] == ['status','--json']


async def test_missing_origin_is_an_explicit_gap_and_not_an_accepted_route(tmp_path):
    from farescout.models import Discovery, Signal
    from farescout.research import grounded
    from test_research import candidate
    class Leads(WorkingSocial):
        async def search(self, query):
            return [evidence().model_copy(update={'title':'大湾区日本促销',
                'body':'大湾区促销日本航点：冲绳、大阪、东京、福冈。'})]
    class LeadsBrain(TestBrain):
        async def discover(self, goal, sources):
            return grounded(Discovery(candidates=[candidate(destination='OKA',
                signals=[Signal(evidence_id='p1',excerpt='冲绳、大阪、东京、福冈')])]), sources, goal)
    session=await Researcher(Settings(data_dir=tmp_path),brain=LeadsBrain(),
        social=[Leads()],fares=[CalendarFare()]).run('香港11月日本',None,'origin-gap')
    turn=session.turns[-1]
    assert not turn.opportunities
    assert 'OKA' in turn.checkpoint['evidence_gaps'][0]['named_destinations']
    assert any(e.stage=='research_decision' and e.data['context']['evidence_gaps'] for e in turn.events)


async def test_first_and_third_result_times_require_three_distinct_cited_routes(tmp_path):
    from farescout.models import Discovery, Signal
    from farescout.research import grounded
    from test_research import candidate
    class Three(WorkingSocial):
        async def search(self, query):
            return [evidence().model_copy(update={'body':'香港快运从香港去东京、大阪、冲绳。'})]
    class ThreeBrain(TestBrain):
        async def discover(self, goal, sources):
            return grounded(Discovery(candidates=[candidate(destination=code,
                signals=[Signal(evidence_id='p1',excerpt='香港去东京、大阪、冲绳')]) for code in ['NRT','KIX','OKA']]),sources,goal)
    class MatchingCalendar(CalendarFare):
        async def verify(self, req):
            from test_prices import payload
            from farescout.providers import flyai_fares
            self.calls.append(req.outbound_date)
            return flyai_fares(payload('1200',arrStationCode=req.destination,
                depDateTime=f'{req.outbound_date} 10:00:00',arrDateTime=f'{req.outbound_date} 15:00:00'),req)
    session=await Researcher(Settings(data_dir=tmp_path),brain=ThreeBrain(),
        social=[Three()],fares=[MatchingCalendar()]).run('香港11月日本',None,'three')
    turn=session.turns[-1]
    assert turn.metrics['first_result_seconds'] <= turn.metrics['third_result_seconds']
    assert len([e for e in turn.events if e.stage=='result_available'])==2
    assert sum(bool(o.fares) for o in turn.opportunities)==3
