import asyncio
from datetime import date

import pytest

from farescout.config import Settings
from farescout.dates import DateExplorer
from farescout.engine import Researcher
from farescout.models import DateCoverage, Opportunity, Turn
from farescout.providers import Socai
from farescout.quality import assess_evidence
from farescout.research import evolve_goal
from farescout.safety import SourceFailure
from test_engine import TestBrain, WorkingSocial
from test_p1 import CalendarFare
from test_research import candidate, evidence


async def test_preview_is_not_evidence_and_one_failed_body_preserves_others(tmp_path, monkeypatch):
    calls, traces = [], []
    async def command(executable, args, settings, source):
        calls.append(args)
        if args[0] == 'status':
            return {'browser_connected':True}
        if 'search' in args:
            return {'data': {'cards': [{'note_id':f'1234567{i}', 'xsec_token':'SECRET', 'title':'香港日本机票'} for i in range(3)]}}
        note_id = args[args.index('--note')+1].split('=')[0]
        if note_id.endswith('1'):
            raise TimeoutError()
        return {'data': {'notes': [{'entity': {'note_id':note_id, 'content':'香港飞大阪促销，日期需验价'}}]}}
    monkeypatch.setattr('farescout.providers.command_json', command)
    source = Socai(Settings(data_dir=tmp_path))
    source.on_trace = lambda *args: traces.append(args)
    records = await source.search('香港 日本 机票')
    assert len(records) == 2 and len(calls) == source.command_calls == 5
    assert all(e.body for e in records)
    assert 'SECRET' not in str(traces) + str(records)
    assert any(t[1] == 'failed' for t in traces)


async def test_login_failure_is_not_retried_and_circuit_skips_second_query(tmp_path, monkeypatch):
    attempts = []
    async def command(*args):
        attempts.append(args)
        raise SourceFailure('小红书 / socai', 'BROWSER_OR_LOGIN_REQUIRED', '浏览器未连接')
    monkeypatch.setattr('farescout.providers.command_json', command)
    r = Researcher(Settings(data_dir=tmp_path), brain=TestBrain(), social=[Socai(Settings(data_dir=tmp_path)), WorkingSocial()], fares=[])
    session = await r.run('香港11月日本', None, 'browser-failure')
    assert len(attempts) == 1
    assert session.evidence
    assert any(e.status == 'skipped' and e.source == '小红书 / socai' for e in session.turns[-1].events)


async def test_cards_missing_tokens_cannot_count_as_body(monkeypatch):
    async def command(*args):
        return {'cards':[{'note_id':'12345678', 'title':'香港日本600元'}]}
    monkeypatch.setattr('farescout.providers.command_json', command)
    source = Socai(Settings())
    with pytest.raises(SourceFailure, match='NO_READABLE_POSTS'):
        await source.search('香港 日本 机票')
    assert source.command_calls == 6  # pre/post connection checks plus each bounded platform command


async def test_quote_reuse_preserves_time_and_stale_quote_refreshes(tmp_path):
    provider = CalendarFare()
    settings = Settings(data_dir=tmp_path, quote_reuse_seconds=120)
    r = Researcher(settings, brain=TestBrain(), social=[], fares=[provider])
    goal = evolve_goal('香港11月日本', today=date(2026,10,1))
    turn = Turn(id='reuse', user_input='q', goal=goal)
    opportunity = Opportunity(candidate=candidate(), date_coverage=DateCoverage(date_from=goal.date_from, date_to=goal.date_to))
    explorer = DateExplorer(r, turn)
    first = await explorer.quote(provider, opportunity, goal.date_from, 'coarse')
    second = await explorer.quote(provider, opportunity, goal.date_from, 'verification')
    assert first[0].observed_at == second[0].observed_at
    assert len(provider.calls) == 1 and turn.metrics['quote_reuses'] == 1
    for key, value in explorer.quotes.items():
        explorer.quotes[key] = (value[0]-121, value[1])
    third = await explorer.quote(provider, opportunity, goal.date_from, 'verification')
    assert len(provider.calls) == 2 and third[0].observed_at >= second[0].observed_at
    assert turn.metrics['verification_calls'] == 1


async def test_parallel_quotes_obey_slots_and_actual_call_budget(tmp_path):
    class Slow(CalendarFare):
        active = maximum = 0
        async def verify(self, req):
            self.active += 1
            self.maximum = max(self.maximum, self.active)
            try:
                await asyncio.sleep(.02)
                return await super().verify(req)
            finally:
                self.active -= 1
    provider = Slow()
    r = Researcher(Settings(data_dir=tmp_path, fare_concurrency=2, max_date_calls=3, fine_dates=0),
                   brain=TestBrain(), social=[WorkingSocial()], fares=[provider])
    session = await r.run('香港11月日本', None, 'parallel')
    assert provider.maximum == 2
    assert len(provider.calls) == session.turns[-1].metrics['date_calls'] == 3


def test_different_wording_same_campaign_groups_but_different_sales_do_not():
    a = evidence().model_copy(update={'body':'Peach大促\n抢票时间\n9月17日～9月20日\n出发日期\n2026/9/22～2027/1/31'})
    b = evidence().model_copy(update={'id':'copy', 'body':'乐桃香港大阪好价\n抢票时间：9月17日～9月20日\n出发日期2026/9/22～2027/1/31'})
    c = evidence().model_copy(update={'id':'other', 'body':b.body.replace('9月20日','9月25日')})
    d = evidence().model_copy(update={'id':'airline', 'body':'香港大阪乐桃便宜机票，11月适合出发'})
    assess_evidence({'a':a,'b':b,'c':c,'d':d})
    assert b.quality['campaign_duplicate_of'] == a.id
    assert len(b.quality['campaign_match_basis']) == 3
    assert b.body.startswith('乐桃')
    assert c.quality['independence_group'] != a.quality['independence_group']
    assert d.quality['independence_group'] != a.quality['independence_group']


@pytest.mark.parametrize('change', [ {'start_date':'2027-02-10'}, {'end_date':'2026-11-10'},
    {'search_parameters':{'departure_id':'HKG','arrival_id':'NRT','type':2,'currency':'CNY'}},
    {'flights':[{'departure_airport':{'id':'HKG'},'arrival_airport':{'id':'KIX'},'price':True}]} ])
def test_explore_rejects_outside_window_return_trip_wrong_route_and_invalid_prices(change):
    from farescout.providers import explore_dates
    payload = {'search_metadata':{'status':'Success'}, 'start_date':'2026-11-04','end_date':None,
        'search_parameters':{'departure_id':'HKG','arrival_id':'KIX','type':2,'currency':'CNY'},
        'flights':[{'departure_airport':{'id':'HKG'}, 'arrival_airport':{'id':'KIX'}, 'price':952}]}
    goal = evolve_goal('香港11月日本', today=date(2026,10,1))
    valid = explore_dates(payload,'HKG','KIX',goal)
    assert len(valid) == 1 and valid[0].stage == 'range'
    assert '不能当作最终报价' in valid[0].detail
    assert not explore_dates(payload | change,'HKG','KIX',goal)


async def test_zero_exit_login_payload_is_not_retried(monkeypatch):
    attempts = []
    async def command(*args):
        attempts.append(args)
        return {'data':{'reason':'login_required','cards':[]}}
    monkeypatch.setattr('farescout.providers.command_json', command)
    with pytest.raises(SourceFailure, match='BROWSER_OR_LOGIN_REQUIRED'):
        await Socai(Settings()).search('香港 日本 机票')
    assert len(attempts) == 3  # status + one platform command + status, never a second search


async def test_range_hint_reduces_calls_but_requires_two_exact_dates(tmp_path):
    from farescout.models import DateSample
    class Range(CalendarFare):
        async def explore(self, origin, destination, goal):
            return [DateSample(date=date(2026,11,15), source='hint', stage='range',status='ok',amount=100)]
    provider = Range()
    r = Researcher(Settings(data_dir=tmp_path, fine_dates=1), brain=TestBrain(), social=[WorkingSocial()], fares=[provider])
    session = await r.run('香港11月日本',None,'range-efficient')
    coverage = session.turns[-1].opportunities[0].date_coverage
    assert len(provider.calls) == 3  # two coarse, one fine, final quote reused
    assert len({s.date for s in coverage.samples if s.stage == 'coarse' and s.status == 'ok'}) == 2
    assert all(f.amount != 100 for f in session.turns[-1].opportunities[0].fares)


async def test_browser_timeout_then_disconnected_status_does_not_retry(monkeypatch):
    attempts = []
    async def command(executable, args, settings, source):
        attempts.append(args)
        if args[0] == 'status':
            return {'error_code':'BROWSER_DISCONNECTED'}
        raise TimeoutError()
    monkeypatch.setattr('farescout.providers.command_json', command)
    source = Socai(Settings())
    with pytest.raises(SourceFailure,match='CONNECTION_APPROVAL_TIMEOUT'):
        await source.search('香港 日本 机票')
    assert len(attempts) == source.command_calls == 3  # readiness, attempted search, final state


async def test_first_connection_has_grace_and_later_queries_keep_short_timeout(monkeypatch):
    timeouts, ready = [], False
    async def command(executable, args, settings, source):
        nonlocal ready
        if args[0] == 'status':
            return {'browser_connected':ready}
        timeouts.append(settings.source_timeout)
        ready = True
        if args[1] == 'search':
            return {'cards':[{'note_id':'12345678','xsec_token':'SECRET'}]}
        return {'notes':[{'entity':{'note_id':'12345678','content':'香港大阪机票正文'}}]}
    monkeypatch.setattr('farescout.providers.command_json', command)
    source = Socai(Settings(socai_connect_timeout=180))
    await source.search('香港 日本 机票')
    await source.search('香港 大阪 机票')
    assert timeouts == [180,40,60,40]


async def test_ipc_permission_denied_never_attempts_platform_command(monkeypatch):
    import errno
    attempts = []
    async def command(*args):
        attempts.append(args[1])
        return {'daemon_running':False,'browser_connected':False}
    class DeniedSocket:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def settimeout(self,*args): pass
        def connect(self,*args): raise PermissionError(errno.EPERM,'operation not permitted')
    monkeypatch.setattr('farescout.providers.command_json',command)
    monkeypatch.setattr('farescout.providers.socket.socket',lambda *args:DeniedSocket())
    with pytest.raises(SourceFailure,match='DAEMON_IPC_PERMISSION_DENIED'):
        await Socai(Settings()).search('香港 日本 机票')
    assert attempts == [['status','--json']]


async def test_connected_after_first_call_timeout_is_not_labeled_authorization_failure(monkeypatch):
    connected = False
    attempts = []
    async def command(executable,args,settings,source):
        nonlocal connected
        attempts.append(args)
        if args[0] == 'status':
            return {'browser_connected':connected}
        connected = True
        raise TimeoutError()
    monkeypatch.setattr('farescout.providers.command_json',command)
    with pytest.raises(SourceFailure,match='SOCIAL_SEARCH_TIMEOUT'):
        await Socai(Settings()).search('香港 日本 机票')
    assert len(attempts) == 3


async def test_lean_card_url_token_reads_body_without_leaking(monkeypatch):
    calls, traces = [], []
    async def command(executable, args, settings, source):
        calls.append(args)
        if args[0] == 'status':
            return {'browser_connected': True}
        if '--preview' in args:
            assert '--num-notes' not in args  # first page only, no forced scrolling
            return {'cards': [
                {'note_id':'12345678', 'url':'https://www.xiaohongshu.com/explore/12345678?xsec_token=SECRET'},
                {'note_id':'87654321', 'url':'https://example.com/explore/87654321?xsec_token=BAD'},
                {'note_id':'99999999', 'url':'https://www.xiaohongshu.com/explore/88888888?xsec_token=BAD'}]}
        assert args[args.index('--note')+1] == '12345678=SECRET'
        return {'notes':[{'entity':{'note_id':'12345678', 'content':'香港飞大阪活动需要重新验价'}}]}
    monkeypatch.setattr('farescout.providers.command_json', command)
    source = Socai(Settings())
    source.on_trace = lambda *args: traces.append(args)
    records = await source.search('香港 日本 机票')
    assert len(records) == 1 and len(calls) == 3
    assert 'SECRET' not in str(traces) + str(records)


async def test_unreadable_preview_falls_back_to_scan_once(monkeypatch):
    calls = []
    async def command(executable, args, settings, source):
        calls.append(args)
        if args[0] == 'status':
            return {'browser_connected':True}
        if '--preview' in args:
            return {'cards':[]}
        return {'notes':[{'entity':{'note_id':'12345678', 'content':'香港飞大阪活动需要重新验价'}}]}
    monkeypatch.setattr('farescout.providers.command_json', command)
    records = await Socai(Settings()).search('香港 日本 机票')
    assert len(records) == 1
    assert sum('--preview' in c for c in calls) == 1
    assert sum(c[:2] == ['xhs','search'] and '--preview' not in c for c in calls) == 1


def test_similar_campaign_body_and_transitive_group_cannot_hide_sale_conflict():
    repeated = '香港飞大阪乐桃机票促销，须查看出行日期并实时核对价格。' * 8
    a = evidence().model_copy(update={'id':'a', 'body': repeated + '\n抢票时间9月17日～9月20日'})
    b = evidence().model_copy(update={'id':'b', 'body': repeated})
    c = evidence().model_copy(update={'id':'c', 'body': repeated + '\n抢票时间9月17日～9月25日'})
    assess_evidence({'a':a,'b':b,'c':c})
    assert b.quality['independence_group'] == a.quality['independence_group']
    assert c.quality['independence_group'] != a.quality['independence_group']

async def test_cancelled_queued_quote_is_not_counted_as_api_call(tmp_path):
    provider = CalendarFare()
    r = Researcher(Settings(data_dir=tmp_path), brain=TestBrain(), social=[], fares=[provider])
    goal = evolve_goal('香港11月日本', today=date(2026,10,1))
    turn = Turn(id='cancel', user_input='q', goal=goal)
    opportunity = Opportunity(candidate=candidate(), date_coverage=DateCoverage(date_from=goal.date_from, date_to=goal.date_to))
    explorer = DateExplorer(r, turn)
    await explorer.http_slots.acquire()
    await explorer.http_slots.acquire()
    task = asyncio.create_task(explorer.quote(provider, opportunity, goal.date_from, 'coarse'))
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    explorer.http_slots.release()
    explorer.http_slots.release()
    assert not provider.calls and turn.metrics.get('date_calls', 0) == 0
    assert not opportunity.date_coverage.samples
    assert turn.events[-1].data['request_issued'] is False


def test_greater_bay_distinct_posts_same_sale_and_travel_dates_group():
    a = evidence().model_copy(update={'id':'gb1', 'body':'大湾区航空推出77折\n优惠日期2026年9月30日至2026年10月11日\n适用出行日期2026年10月3日至2027年1月21日'})
    b = evidence().model_copy(update={'id':'gb2', 'body':'大湾区促销日本航点！\n优惠日期2026年9月30日至2026年10月11日\n适用出行日期2026年10月3日至2027年1月21日\n大阪东京往返退税后1.6k'})
    c = evidence().model_copy(update={'id':'gb3', 'body': b.body.replace('10月11日','10月12日')})
    assess_evidence({'a':a,'b':b,'c':c})
    assert b.quality['campaign_duplicate_of'] == a.id
    assert c.quality['independence_group'] != a.quality['independence_group']


async def test_page_transition_diagnostic_survives_bounded_fallback(monkeypatch):
    calls = []
    async def command(executable, args, settings, source):
        calls.append(args)
        if args[0] == 'status':
            return {'browser_connected':True}
        return {'ok':False, 'reason':'Search did not transition to a valid Xiaohongshu result page', 'cards':[]}
    monkeypatch.setattr('farescout.providers.command_json', command)
    with pytest.raises(SourceFailure, match='SEARCH_PAGE_TRANSITION_FAILED'):
        await Socai(Settings()).search('大湾区航空 香港 札幌 11月')
    queries = [c[2] for c in calls if c[:2] == ['xhs','search']]
    assert queries == ['大湾区航空 香港 札幌 11月','大湾区航空 香港 札幌']


async def test_partial_scan_keeps_good_bodies_and_records_unopened_note(monkeypatch):
    traces = []
    async def command(executable, args, settings, source):
        if args[0] == 'status':
            return {'browser_connected':True}
        return {'notes':[{'entity':{'note_id':'12345678','content':'香港飞大阪活动需验价'}}],
                'page_error':'Note overlay did not open after card-click attempts; site may be throttling or layout changed'}
    monkeypatch.setattr('farescout.providers.command_json', command)
    source = Socai(Settings(socai_mode='scan'))
    source.on_trace = lambda *args: traces.append(args)
    result = await source.search('香港 日本 机票')
    assert len(result) == 1 and result[0].warnings
    assert any(t[-1].get('failure_code') == 'NOTE_OPEN_FAILED' for t in traces)


async def test_social_budget_reserves_time_for_existing_evidence_verification(tmp_path):
    from time import monotonic
    from farescout.models import Session
    class Unused(WorkingSocial):
        calls = 0
        async def search(self, query):
            self.calls += 1
            return await super().search(query)
    source = Unused()
    r = Researcher(Settings(data_dir=tmp_path), brain=TestBrain(), social=[source], fares=[])
    goal = evolve_goal('香港11月日本', today=date(2026,10,1))
    session = Session(id='reserve', goal=goal, evidence={'p1':evidence()})
    turn = Turn(id='reserve', user_input='q', goal=goal)
    session.turns.append(turn)
    r._session = session
    r._research_deadline = monotonic() + 100
    await r.search('香港 日本 机票', turn, session)
    assert source.calls == 0 and session.evidence['p1'].body
    assert turn.events[-1].stage == 'budget' and turn.events[-1].status == 'skipped'
    assert turn.metrics.get('community_calls', 0) == 0


def test_navigation_timeout_is_distinct_from_connection_approval():
    from farescout.providers import socai_page_issue
    issue = socai_page_issue({'ok':False,'reason':'search_failed','error':'Page.navigate timed out after 15s'})
    assert issue[0] == 'PAGE_NAVIGATION_TIMEOUT'
    assert '15s' not in issue[1]  # no raw exception copied into public output
