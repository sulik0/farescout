"""Observe real workbench runs; optionally close only its dedicated Chrome once.

This script does not replace models or sources, change research checkpoints,
kill socai, or manufacture a disconnected response. The fault is an actual
SIGTERM to a Chrome process whose executable and user-data-dir are verified.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from farescout.config import Settings
from farescout.models import now


def request(base, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    return json.load(urlopen(Request(base + path, data, {'Content-Type':'application/json'}), timeout=15))


def preserved_snapshot(session):
    turn = session['turns'][-1]
    searches = [event for event in turn['events'] if event['stage'] in {'community_search','query_expansion'}
        and event['status'] == 'ok' and event.get('evidence_ids') and event.get('data', {}).get('complete', True)]
    return {'session_id':session['id'], 'turn_id':turn['id'], 'turn_count':len(session['turns']),
        'evidence':{key:{'observed_at':e['observed_at'],
            'body_sha256':hashlib.sha256(e['body'].encode()).hexdigest()} for key,e in session['evidence'].items()},
        'completed_searches':[{'stage':e['stage'], 'query':e['data']['query'], 'event_id':e['id']} for e in searches],
        'successful_dates':[(o['candidate']['origin'],o['candidate']['destination'],s['source'],s['date'],s['stage'],s['observed_at'])
            for o in turn['opportunities'] for s in (o.get('date_coverage') or {}).get('samples',[]) if s['status']=='ok'],
        'fares':[(o['candidate']['origin'],o['candidate']['destination'],f['id'],f['source'],f['observed_at'],f['amount'],f['currency'])
            for o in turn['opportunities'] for f in o.get('fares',[])]}


def active_community_query(turn):
    events = turn['events']
    finished = {e['action_id'] for e in events if e.get('phase') == 'completed'}
    return next((e for e in reversed(events) if e['stage'] in {'community_search','query_expansion'}
        and e.get('phase') == 'started' and e.get('source') == '小红书 / socai'
        and e['action_id'] not in finished), None)


def precise_date_count(snapshot):
    # Reused verification of one day is not an additional explored date.
    return len({tuple(row[:4]) for row in snapshot['successful_dates'] if row[4]!='range'})


def close_dedicated_chrome(profile):
    if sys.platform != 'darwin' or profile is None:
        raise RuntimeError('受控关闭测试仅支持已配置专用 profile 的 macOS')
    expected = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
    argument = '--user-data-dir=' + str(profile.resolve())
    def matches(command):
        return command.startswith(expected + ' ') and re.search(re.escape(argument) + r'(?:\s--|$)',command)
    rows = subprocess.check_output(['ps','-axo','pid=,args='],text=True).splitlines()
    candidates = []
    for row in rows:
        match = re.match(r'\s*(\d+)\s+(.+)',row)
        if match and matches(match[2]):
            candidates.append(int(match[1]))
    if len(candidates) != 1:
        raise RuntimeError('未找到唯一专用 Chrome；不关闭任何进程')
    pid = candidates[0]
    current = subprocess.check_output(['ps','-p',str(pid),'-o','args='],text=True).strip()
    if not matches(current):
        raise RuntimeError('Chrome PID 或 profile 已变化；不关闭任何进程')
    os.kill(pid,signal.SIGTERM)
    return {'chrome_pid':pid, 'signal':'SIGTERM', 'exact_profile_verified':True,
        'daemon_signalled':False, 'profile_deleted':False, 'at':now().isoformat()}


def check_preserved(before, after):
    turn = after['turns'][-1]
    current = preserved_snapshot(after)
    old_dates = {tuple(x) for x in before['successful_dates']}
    old_precise = {x for x in old_dates if x[4]!='range'}
    old_fares = {tuple(x) for x in before.get('fares',[])}
    current_dates = {tuple(x) for x in current['successful_dates']}
    checks = {'same_session':before['session_id']==after['id'], 'same_turn':before['turn_id']==turn['id'],
        'same_turn_count':before['turn_count']==len(after['turns']),
        'evidence_unchanged':all(current['evidence'].get(key)==value for key,value in before['evidence'].items()),
        'successful_date_records_retained':old_dates.issubset(current_dates) if old_dates else None,
        'precise_date_records_retained':old_precise.issubset(current_dates) if old_precise else None,
        'original_fares_retained':old_fares.issubset({tuple(x) for x in current['fares']}) if old_fares else None}
    repeated = []
    # An earlier successful query may have an earlier failed attempt. Count
    # only started events after the recorded successful completion.
    events = turn['events']; positions = {e['id']:index for index,e in enumerate(events)}
    for prior in before['completed_searches']:
        cutoff = positions.get(prior['event_id'], -1)
        if any(e.get('phase')=='started' and e['stage']==prior['stage'] and e.get('data',{}).get('query')==prior['query']
            for e in events[cutoff+1:]):
            repeated.append({'stage':prior['stage'],'query':prior['query']})
    checks['completed_searches_not_repeated'] = not repeated
    return {'checks':checks, 'successful_date_records_checked':len(old_dates),
        'precise_date_records_checked':len(old_precise), 'fare_records_checked':len(old_fares),
        'date_check_note':'没有可比较的成功日期记录；此项未实测' if not old_dates else '按路线、来源、日期、阶段和原观察时间比较',
        'repeated_completed_searches':repeated,
        'resume_events':sum(e['stage']=='resume' for e in events),
        'execution_segments':turn['metrics'].get('execution_segments'),
        'browser_recovery':turn['checkpoint'].get('browser_recovery')}


def main(args):
    settings = Settings.from_env()
    if settings.social_browser != 'managed':
        raise SystemExit('验收只使用 managed 模式')
    if args.inject_disconnect and not args.allow_managed_chrome_close:
        raise SystemExit('受控断线需显式 --allow-managed-chrome-close')
    base = f'http://127.0.0.1:{args.port}'
    output = Path(args.output); output.parent.mkdir(parents=True,exist_ok=True)
    result = {'kind':'real_managed_research_acceptance', 'started_at':now().isoformat(),
        'session_id':args.session, 'manual_reauthorization':'unknown', 'repeated_login':'unknown',
        'research_input':args.message, 'controlled_disconnect':None, 'observations':[]}
    if not args.attach:
        request(base,'/api/run',{'session_id':args.session,'message':args.message})
    began = time.monotonic(); last_log = 0; terminal_since = None; before_fault = None
    while time.monotonic()-began < args.timeout:
        try:
            data = request(base,'/api/sessions/'+args.session)
        except HTTPError as error:
            if error.code != 404:
                raise
            time.sleep(.5); continue
        session = data.get('session'); turn = session['turns'][-1] if session else None
        if not turn:
            time.sleep(.5); continue
        observation = {'at':now().isoformat(),'status':turn['status'],'active':data.get('active'),
            'evidence_count':len(session['evidence']), 'quoted_routes':sum(bool(o['fares']) for o in turn['opportunities']),
            'last_stage':turn['events'][-1]['stage'] if turn['events'] else None,
            'recovery_state':turn['checkpoint'].get('browser_recovery',{}).get('state'),
            'execution_segments':turn['metrics'].get('execution_segments')}
        if time.monotonic()-last_log > 25 or not result['observations']:
            result['observations'].append(observation); last_log=time.monotonic()
            print(json.dumps(observation,ensure_ascii=False),flush=True)
            output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        if args.inject_disconnect and result['controlled_disconnect'] is None:
            snapshot = preserved_snapshot(session); active_query = active_community_query(turn)
            if (snapshot['completed_searches'] and active_query and
                    precise_date_count(snapshot) >= args.min_precise_dates_before_fault):
                time.sleep(1)  # Let the current CLI begin navigation, then recheck.
                refreshed = request(base,'/api/sessions/'+args.session)['session']
                if (active_community_query(refreshed['turns'][-1]) and
                        precise_date_count(preserved_snapshot(refreshed)) >= args.min_precise_dates_before_fault):
                    browser = request(base,'/api/browser')
                    if browser.get('ready') and browser['connection'].get('profile_mode')=='managed':
                        local_pid=(settings.socai_home/'rust-daemon.pid').read_text().strip() if settings.socai_home else ''
                        if local_pid != str(browser['connection'].get('daemon_pid')):
                            raise RuntimeError('工作台与验收脚本的 daemon 不一致；不关闭浏览器')
                        before_fault = preserved_snapshot(refreshed)
                        result['before_fault'] = before_fault
                        result['controlled_disconnect'] = close_dedicated_chrome(settings.socai_profile_dir)
                        result['controlled_disconnect']['daemon_pid_before'] = browser['connection'].get('daemon_pid')
                        print(json.dumps({'fault_injected':result['controlled_disconnect']},ensure_ascii=False),flush=True)
                        output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        waiting = observation['recovery_state']=='waiting'
        if before_fault and waiting and turn['status']!='running' and not result.get('before_resume'):
            # Date work may finish independently after Chrome is closed. Capture
            # the pause checkpoint too, rather than claiming a vacuous date PASS.
            result['before_resume'] = preserved_snapshot(session)
            result['before_resume_metrics'] = dict(turn['metrics'])
            output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        done = turn['status']!='running' and data.get('active')!=args.session and not waiting
        if done:
            terminal_since = terminal_since or time.monotonic()
            if time.monotonic()-terminal_since >= 3:
                result.update(finished_at=now().isoformat(), status=turn['status'],stop_reason=turn['stop_reason'],
                    metrics=turn['metrics'], browser_recovery=turn['checkpoint'].get('browser_recovery'),
                    recovery_required=turn['checkpoint'].get('recovery_required'))
                if before_fault:
                    result['preservation'] = check_preserved(before_fault,session)
                if result.get('before_resume'):
                    result['pause_checkpoint_preservation'] = check_preserved(result['before_resume'],session)
                result['fault_not_injected'] = args.inject_disconnect and result['controlled_disconnect'] is None
                result['observations'].append(observation)
                output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
                print(json.dumps({'finished':True,'status':turn['status'],'metrics':turn['metrics'],
                    'preservation':result.get('preservation')},ensure_ascii=False),flush=True)
                if result['fault_not_injected']:
                    raise SystemExit('研究结束前未满足断线条件；不能算断线恢复验收通过')
                return
        else:
            terminal_since = None
        time.sleep(.5)
    result.update(observer_timeout=True, finished_at=now().isoformat())
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    raise SystemExit('观察超时；不取消研究，也不修改 checkpoint')


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8768)
    parser.add_argument('--session',required=True)
    parser.add_argument('--message',default='香港 11 月飞日本哪里便宜？')
    parser.add_argument('--attach',action='store_true')
    parser.add_argument('--inject-disconnect',action='store_true')
    parser.add_argument('--allow-managed-chrome-close',action='store_true')
    parser.add_argument('--min-precise-dates-before-fault',type=int,choices=range(0,26),default=0)
    parser.add_argument('--timeout',type=int,default=1260)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    if not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}',args.session) or not 1<=args.port<=65535 or not 60<=args.timeout<=1800:
        parser.error('session / port / timeout 不合法')
    main(args)
