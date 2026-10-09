"""Check that the real acceptance fault cannot target another browser."""
import importlib.util
from pathlib import Path

import pytest

spec=importlib.util.spec_from_file_location('managed_acceptance', Path(__file__).parents[1]/'scripts/managed-research-acceptance.py')
probe=importlib.util.module_from_spec(spec); spec.loader.exec_module(probe)


@pytest.mark.parametrize('command',[
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome --user-data-dir=/dedicated-other --remote-debugging-port=0',
    '/Applications/Google Chrome.app/Contents/Frameworks/Google Chrome Helper --user-data-dir=/dedicated',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome --user-data-dir=/daily',
])
def test_fault_guard_rejects_other_profiles_and_helpers(monkeypatch,command):
    monkeypatch.setattr(probe.sys,'platform','darwin')
    monkeypatch.setattr(probe.subprocess,'check_output',lambda *a,**k:'123 '+command)
    killed=[]; monkeypatch.setattr(probe.os,'kill',lambda *a:killed.append(a))
    with pytest.raises(RuntimeError,match='唯一专用 Chrome'):
        probe.close_dedicated_chrome(Path('/dedicated'))
    assert not killed


def test_fault_guard_rechecks_pid_before_sending_signal(monkeypatch):
    managed='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome --user-data-dir=/dedicated'
    daily=managed.replace('/dedicated','/daily')
    monkeypatch.setattr(probe.sys,'platform','darwin')
    output=iter(['123 '+managed,daily])
    monkeypatch.setattr(probe.subprocess,'check_output',lambda *a,**k:next(output))
    killed=[]; monkeypatch.setattr(probe.os,'kill',lambda *a:killed.append(a))
    with pytest.raises(RuntimeError,match='PID 或 profile 已变化'):
        probe.close_dedicated_chrome(Path('/dedicated'))
    assert not killed


def test_preservation_cannot_claim_date_pass_without_a_successful_sample():
    session={'id':'a','evidence':{'e':{'observed_at':'2026-10-10T01:00:00Z','body':'已读正文'}},
        'turns':[{'id':'turn','events':[],'opportunities':[],'metrics':{'execution_segments':2},'checkpoint':{}}]}
    result=probe.check_preserved(probe.preserved_snapshot(session),session)
    assert result['checks']['successful_date_records_retained'] is None
    assert result['successful_date_records_checked']==0


def test_fault_gate_counts_precise_days_without_range_or_reuse_inflation():
    sample=('HKG','NRT','FlyAI','2026-11-09','range','observed')
    assert probe.precise_date_count({'successful_dates':[sample]})==0
    coarse=sample[:4]+('coarse','observed'); reused=sample[:4]+('verification','observed')
    assert probe.precise_date_count({'successful_dates':[sample,coarse,reused]})==1


def test_preservation_detects_changed_evidence_and_date_timestamps():
    session={'id':'a','evidence':{'e':{'observed_at':'2026-10-10T01:00:00Z','body':'已读正文'}},
        'turns':[{'id':'turn','events':[],'opportunities':[{'candidate':{'origin':'HKG','destination':'NRT'},
            'date_coverage':{'samples':[{'source':'FlyAI','date':'2026-11-09','stage':'coarse',
                'status':'ok','observed_at':'2026-10-10T01:00:00Z'}]}}],
            'metrics':{'execution_segments':2},'checkpoint':{}}]}
    before=probe.preserved_snapshot(session)
    assert probe.check_preserved(before,session)['checks']['successful_date_records_retained'] is True
    session['evidence']['e']['body']='重写的正文'
    session['turns'][0]['opportunities'][0]['date_coverage']['samples'][0]['observed_at']='2026-10-10T02:00:00Z'
    checks=probe.check_preserved(before,session)['checks']
    assert checks['evidence_unchanged'] is False and checks['successful_date_records_retained'] is False
