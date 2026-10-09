import asyncio
from datetime import timedelta
import json
import threading
import time

import pytest

from farescout.config import Settings
from farescout.connection import connection_observation
from farescout.engine import Researcher, Store
from farescout.models import now
from farescout.providers import Socai
from farescout.safety import SourceFailure
from farescout.web import Application
from test_engine import TestBrain
from test_p1 import CalendarFare
from test_recovery_loop import Interrupted
from test_research import evidence


def wait_for(predicate):
    end = time.monotonic() + 3
    while time.monotonic() < end:
        if predicate():
            return
        time.sleep(.01)
    raise AssertionError('recovery did not reach expected state')


def setup(tmp_path):
    class Preserved(Interrupted):
        record = evidence()
        async def search(self, query):
            await super().search(query)
            return [self.record]
    source = Preserved()
    settings = Settings(data_dir=tmp_path, recovery_poll_seconds=.01, social_browser='existing')
    def factory(config):
        return Researcher(config, brain=TestBrain(), social=[source], fares=[CalendarFare()])
    asyncio.run(factory(settings).run('香港11月日本',None,'saved'))
    return settings, source, factory


def test_authorization_recovery_is_once_in_same_turn_with_original_evidence(tmp_path, monkeypatch):
    settings, source, factory = setup(tmp_path)
    approved = threading.Event()
    checks = []
    async def ready(self):
        checks.append('status_only')
        return approved.is_set()
    monkeypatch.setattr('farescout.providers.Socai.browser_ready',ready)
    app = Application(settings,factory)
    before = app.store.load('saved')
    app.arm_recovery('saved')
    wait_for(lambda: len(checks)>1)
    assert app.store.load('saved').turns[-1].checkpoint['browser_recovery']['state']=='waiting'
    source.ready=True; approved.set()
    wait_for(lambda: app.store.load('saved').turns[-1].metrics['execution_segments']==2 and not app.active)
    after=app.store.load('saved')
    assert len(after.turns)==1 and after.turns[0].id==before.turns[0].id
    assert after.evidence['p1'].observed_at==before.evidence['p1'].observed_at
    assert source.calls.count('香港 便宜机票')==1
    assert after.turns[0].checkpoint['browser_recovery']['state']=='resumed'
    assert sum(e.stage=='resume' for e in after.turns[0].events)==1
    app.recovery_stop.set()


def test_wait_timeout_keeps_all_research_without_requesting_a_connection(tmp_path, monkeypatch):
    settings, source, factory=setup(tmp_path)
    async def forbidden(self):
        raise AssertionError('an expired watch must not contact Chrome')
    monkeypatch.setattr('farescout.providers.Socai.browser_ready',forbidden)
    app=Application(settings,factory)
    before=app.store.load('saved')
    app.arm_recovery('saved',deadline=(now()-timedelta(seconds=1)).isoformat())
    wait_for(lambda: app.store.load('saved').turns[0].checkpoint['browser_recovery']['state']=='expired')
    after=app.store.load('saved')
    assert after.turns[0].id==before.turns[0].id and after.turns[0].opportunities==before.turns[0].opportunities
    assert source.calls==['香港 便宜机票','深圳 国际机票']


def test_pending_wait_survives_service_restart(tmp_path,monkeypatch):
    settings,source,factory=setup(tmp_path)
    approved=threading.Event()
    async def ready(self): return approved.is_set()
    monkeypatch.setattr('farescout.providers.Socai.browser_ready',ready)
    first=Application(settings,factory); first.arm_recovery('saved')
    deadline=first.store.load('saved').turns[0].checkpoint['browser_recovery']['deadline']
    first.recovery_stop.set()
    second=Application(settings,factory)
    assert second.store.load('saved').turns[0].checkpoint['browser_recovery']['deadline']==deadline
    source.ready=True; approved.set()
    wait_for(lambda: second.store.load('saved').turns[0].metrics['execution_segments']==2 and not second.active)
    second.recovery_stop.set()


def test_reconnect_is_one_request_and_duplicate_click_is_rejected(tmp_path,monkeypatch):
    settings,source,factory=setup(tmp_path)
    connected=threading.Event(); release=threading.Event(); calls=[]
    async def ready(self): return connected.is_set()
    async def request(self,args,stage,data):
        calls.append(args)
        while not release.is_set(): await asyncio.sleep(.01)
        connected.set()
        return {}
    monkeypatch.setattr('farescout.providers.Socai.browser_ready',ready)
    monkeypatch.setattr('farescout.providers.Socai._command',request)
    source.ready=True
    app=Application(settings,factory); app.reconnect('saved')
    with pytest.raises(RuntimeError): app.reconnect('saved')
    release.set()
    wait_for(lambda: app.store.load('saved').turns[0].metrics['execution_segments']==2 and not app.active)
    assert len(calls)==1 and calls[0][:2]==['xhs','search']
    assert len(app.store.load('saved').turns)==1
    app.recovery_stop.set()


def test_terminal_log_has_close_code_and_no_private_reason(tmp_path,monkeypatch):
    home=tmp_path/'socai';home.mkdir()
    (home/'rust-daemon.log').write_text('2026-10-04T10:10:00Z WARN cdp_ws_terminal connection_id=2 pid=12 kind="close_frame" close_code=1000 reason_bytes=22 pending_commands=0 uptime_ms=45000\n2026-10-04T10:10:02Z WARN cdp connection lost CDP session is closed ws://secret/token\n')
    monkeypatch.setenv('SOCAI_HOME',str(home))
    state=connection_observation({'browser_connected':False},Settings(data_dir=tmp_path/'data'))
    terminal=state['first_transport_terminal']
    assert terminal['close_code']=='1000' and terminal['pending_commands']=='0'
    assert terminal['kind']=='close_frame'
    assert terminal['at'] < state['last_disconnect']['at']
    assert 'secret' not in json.dumps(state)


def test_healthy_transport_with_login_gate_does_not_auto_replay_research(tmp_path):
    class LoginRequired(Socai):
        async def search(self, query):
            self.connection={'browser_connected':True}
            raise SourceFailure(self.name,'BROWSER_OR_LOGIN_REQUIRED','需要小红书登录')
    settings=Settings(data_dir=tmp_path)
    source=LoginRequired(settings)
    def factory(config):
        return Researcher(config,brain=TestBrain(),social=[source],fares=[])
    app=Application(settings,factory); app.start('login','香港11月日本')
    wait_for(lambda: not app.active)
    turn=app.store.load('login').turns[0]
    assert turn.status=='blocked'
    assert app.recovery_target is None and 'browser_recovery' not in turn.checkpoint
    assert turn.metrics['execution_segments']==1


def test_closed_service_does_not_arm_a_late_connection_attempt(tmp_path):
    settings,source,factory=setup(tmp_path)
    app=Application(settings,factory); app.closed=True
    app.arm_recovery('saved')
    assert app.recovery_target is None
    assert 'browser_recovery' not in app.store.load('saved').turns[0].checkpoint


def test_managed_default_marker_and_unknown_log_fields_are_sanitized(tmp_path,monkeypatch):
    from farescout.connection import endpoint_marker
    config=tmp_path/'config.json';config.write_text('{"chrome":{"profile":"managed"}}')
    monkeypatch.setenv('SOCAI_CONFIG_PATH',str(config))
    marker,source=endpoint_marker()
    assert marker.name=='DevToolsActivePort' and marker.parent.name=='chrome-profile'
    assert source=='managed_chrome_marker'
    home=tmp_path/'socai';home.mkdir()
    (home/'rust-daemon.log').write_text('2026-10-04T10:10:00Z WARN cdp_ws_terminal connection_id=private-token kind="ws://secret" error_class="private-token"\n')
    monkeypatch.setenv('SOCAI_HOME',str(home))
    state=connection_observation({},Settings(data_dir=tmp_path/'data'))
    assert 'secret' not in json.dumps(state) and 'private-token' not in json.dumps(state)


@pytest.mark.parametrize('failure',[TimeoutError(),SourceFailure('socai','CLI_FAILED','命令失败')])
async def test_read_failure_checks_transport_and_retains_previously_read_body(tmp_path,monkeypatch,failure):
    reads=[]
    async def command(executable,args,settings,name):
        if args[0]=='status':
            return {'browser_connected':len(reads)<2,'browser_state':'disconnected' if len(reads)>=2 else 'connected'}
        if '--preview' in args:
            return {'cards':[{'note_id':'12345678','xsec_token':'private'},{'note_id':'87654321','xsec_token':'private'}]}
        reads.append(args)
        if len(reads)==2: raise failure
        return {'notes':[{'entity':{'note_id':'12345678','title':'香港东京机票','content':'香港飞东京机票，11月出发价格便宜。'}}]}
    monkeypatch.setattr('farescout.providers.command_json',command)
    source=Socai(Settings(data_dir=tmp_path,socai_notes=2))
    saved=[]; source.on_evidence=saved.extend
    records=await source.search('香港 东京 机票')
    assert len(records)==1 and records==saved
    assert source.blocked_code=='BROWSER_DISCONNECTED'
    assert source.connection['browser_connected'] is False


def test_managed_reconnects_then_resumes_original_turn_once(tmp_path, monkeypatch):
    settings, source, factory = setup(tmp_path)
    settings.social_browser = 'managed'
    connected = threading.Event()
    calls = []
    async def ready(self):
        self.connection = {'profile_mode':'managed', 'browser_connected':connected.is_set()}
        return connected.is_set()
    async def request(self, args, stage, data):
        calls.append(args)
        source.ready = True
        connected.set()
        return {}
    monkeypatch.setattr(Socai, 'browser_ready', ready)
    monkeypatch.setattr(Socai, '_command', request)
    app = Application(settings, factory)
    before = app.store.load('saved')
    app.arm_recovery('saved')
    wait_for(lambda: not app.active and app.store.load('saved').turns[-1].metrics['execution_segments'] == 2)
    after = app.store.load('saved')
    assert len(calls) == 1 and len(after.turns) == 1
    assert after.turns[0].id == before.turns[0].id
    assert after.evidence['p1'].observed_at == before.evidence['p1'].observed_at
    assert source.calls.count('香港 便宜机票') == 1
    assert after.turns[0].checkpoint['managed_reconnect_attempts'] == 1
    assert after.turns[0].checkpoint['browser_recovery']['state'] == 'resumed'
    app.recovery_stop.set()


def test_managed_failed_attempt_is_not_repeated_after_service_restart(tmp_path, monkeypatch):
    settings, source, factory = setup(tmp_path)
    settings.social_browser = 'managed'
    calls = []
    async def ready(self):
        self.connection = {'profile_mode':'managed','browser_connected':False}
        return False
    async def request(self, *args):
        calls.append(args)
        raise TimeoutError()
    monkeypatch.setattr(Socai, 'browser_ready', ready)
    monkeypatch.setattr(Socai, '_command', request)
    first = Application(settings, factory)
    first.arm_recovery('saved')
    wait_for(lambda: len(calls) == 1)
    first.recovery_stop.set()
    second = Application(settings, factory)
    time.sleep(.08)
    assert len(calls) == 1
    assert second.store.load('saved').turns[0].checkpoint['managed_reconnect_attempts'] == 1
    second.recovery_stop.set()


@pytest.mark.parametrize('as_exception', [False, True])
def test_managed_login_gate_during_reconnect_requires_user_without_resume(tmp_path, monkeypatch, as_exception):
    settings, source, factory = setup(tmp_path)
    settings.social_browser = 'managed'
    async def ready(self):
        self.connection = {'profile_mode':'managed','browser_connected':False}
        return False
    async def request(self, *args):
        if as_exception:
            self.connection['browser_connected'] = True
            raise SourceFailure('socai','BROWSER_OR_LOGIN_REQUIRED','页面要求重新登录')
        return {'reason':'login_required'}
    monkeypatch.setattr(Socai, 'browser_ready', ready)
    monkeypatch.setattr(Socai, '_command', request)
    app = Application(settings, factory)
    app.arm_recovery('saved')
    wait_for(lambda: app.store.load('saved').turns[0].checkpoint['browser_recovery']['state'] == 'needs_user')
    assert app.store.load('saved').turns[0].metrics['execution_segments'] == 1
    assert not app.active


def test_managed_does_not_reconnect_a_daemon_in_existing_mode(tmp_path, monkeypatch):
    settings, source, factory = setup(tmp_path)
    settings.social_browser = 'managed'
    async def ready(self):
        self.connection = {'profile_mode':'existing','browser_connected':False}
        return False
    async def forbidden(self, *args):
        raise AssertionError('must not initiate authorization on existing Chrome')
    monkeypatch.setattr(Socai, 'browser_ready', ready)
    monkeypatch.setattr(Socai, '_command', forbidden)
    app = Application(settings, factory)
    app.arm_recovery('saved')
    time.sleep(.08)
    assert app.store.load('saved').turns[0].checkpoint.get('managed_reconnect_attempts', 0) == 0
    app.recovery_stop.set()


def test_managed_connection_attempt_serializes_new_research(tmp_path, monkeypatch):
    settings, source, factory = setup(tmp_path)
    settings.social_browser = 'managed'
    entered, release = threading.Event(), threading.Event()
    async def ready(self):
        self.connection = {'profile_mode':'managed','browser_connected':False}
        return False
    async def request(self, *args):
        entered.set()
        while not release.is_set():
            await asyncio.sleep(.01)
        return {'reason':'login_required'}
    monkeypatch.setattr(Socai, 'browser_ready', ready)
    monkeypatch.setattr(Socai, '_command', request)
    app = Application(settings, factory)
    app.arm_recovery('saved')
    assert entered.wait(2)
    try:
        with pytest.raises(RuntimeError):
            app.start('new', '香港 日本')
    finally:
        release.set()
    wait_for(lambda: not app.active)
    app.recovery_stop.set()


def test_service_restart_ignores_probe_array_and_retains_session(tmp_path):
    settings, source, factory = setup(tmp_path)
    (tmp_path/'probe-log.json').write_text('[{"browser_connected":false}]')
    app = Application(settings, factory)
    assert app.store.load('saved').evidence['p1'].body == source.record.body
    with pytest.raises(ValueError):
        app.store.load('probe-log')


def test_terminal_detects_stale_status_then_releases_after_daemon_acknowledges(tmp_path):
    home = tmp_path/'daemon'; home.mkdir()
    (home/'rust-daemon.pid').write_text('12')
    settings = Settings(data_dir=tmp_path/'data', socai_home=home)
    state = {'browser_connected':True, 'browser_state':'connected'}
    connection_observation(state, settings)
    # INFO logging can be disabled, so no ws_open line is required when a
    # healthy observation precedes the current daemon's first terminal log.
    (home/'rust-daemon.log').write_text(f'{now().isoformat()} WARN cdp_ws_terminal connection_id=1 pid=12 kind="stream_ended"\n')
    first = connection_observation(state, settings)
    assert first['reported_browser_connected'] is True and first['browser_connected'] is False
    assert first['transport_pending_disconnect'] and first['authorization']=='unknown'
    assert connection_observation(state, settings)['browser_connected'] is False
    connection_observation({'browser_connected':False}, settings)
    assert connection_observation(state, settings)['browser_connected'] is True


@pytest.mark.parametrize('suffix', [
    '2026-10-10T10:00:02Z INFO cdp_ws_open connection_id=2 pid=12\n',
    '2026-10-10T10:00:02Z WARN cdp_ws_terminal connection_id=1 pid=99 kind="stream_ended"\n',
])
def test_old_terminal_does_not_invalidate_new_connection(tmp_path, suffix):
    home = tmp_path/'daemon'; home.mkdir()
    (home/'rust-daemon.pid').write_text('12')
    (home/'rust-daemon.log').write_text('2026-10-10T10:00:00Z INFO cdp_ws_open connection_id=1 pid=12\n'
        '2026-10-10T10:00:01Z WARN cdp_ws_terminal connection_id=1 pid=12 kind="stream_ended"\n'+suffix)
    result = connection_observation({'browser_connected':True}, Settings(data_dir=tmp_path/'data', socai_home=home))
    assert result['browser_connected'] is True


async def test_cli_failure_during_stale_daemon_status_is_disconnected(tmp_path, monkeypatch):
    home=tmp_path/'daemon'; home.mkdir(); (home/'rust-daemon.pid').write_text('12')
    settings=Settings(data_dir=tmp_path/'data', socai_home=home)
    async def command(executable, args, settings, name):
        if args[0]=='status':
            return {'browser_connected':True, 'browser_state':'connected'}
        (home/'rust-daemon.log').write_text(f'{now().isoformat()} WARN cdp_ws_terminal connection_id=1 pid=12 kind="stream_ended"\n')
        raise SourceFailure('socai','CLI_FAILED','连接关闭')
    monkeypatch.setattr('farescout.providers.command_json',command)
    source=Socai(settings)
    with pytest.raises(SourceFailure,match='BROWSER_DISCONNECTED'):
        await source._command(['xhs','search','香港'], 'social_preview', {})
    assert source.connection['reported_browser_connected'] is True
    assert source.connection['browser_connected'] is False


def test_managed_waits_for_daemon_before_spending_reconnect_attempt(tmp_path, monkeypatch):
    settings, source, factory=setup(tmp_path); settings.social_browser='managed'
    acknowledged, connected=threading.Event(),threading.Event(); calls=[]; checks=[]
    async def ready(self):
        checks.append(True)
        self.connection={'profile_mode':'managed', 'browser_connected':connected.is_set(),
            'reported_browser_connected':not acknowledged.is_set() or connected.is_set()}
        return connected.is_set()
    async def request(self,*args):
        assert acknowledged.is_set()
        calls.append(args); connected.set(); source.ready=True
        return {}
    monkeypatch.setattr(Socai,'browser_ready',ready)
    monkeypatch.setattr(Socai,'_command',request)
    app=Application(settings,factory); app.arm_recovery('saved')
    wait_for(lambda:len(checks)>2)
    assert not calls and not app.store.load('saved').turns[0].checkpoint.get('managed_reconnect_attempts')
    acknowledged.set()
    wait_for(lambda:not app.active and app.store.load('saved').turns[0].metrics['execution_segments']==2)
    assert len(calls)==1 and len(app.store.load('saved').turns)==1
    app.recovery_stop.set()
