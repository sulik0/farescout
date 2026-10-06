"""Measure a configured social browser; never restart it or read cookies."""
import argparse
import asyncio
import json
from pathlib import Path
import runpy
from time import monotonic

from farescout.config import Settings
from farescout.models import now
from farescout.providers import Socai
from farescout.safety import source_error


async def main(args):
    snapshot = runpy.run_path(str(Path(__file__).with_name('probe-socai-reuse.py')))['snapshot']
    settings = Settings.from_env()
    settings.data_dir = Path(args.private_data_dir)
    settings.source_timeout = 90
    settings.socai_notes = 1
    settings.socai_comments = 0
    settings.socai_mode = args.socai_mode
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    result = {'kind':'real_social_browser_stability_probe', 'scenario':args.scenario,
        'started_at':now().isoformat(), 'manual_reauthorization':args.reauthorization,
        'login_observation':args.login_observation, 'calls':[],
        'count_note':'provider_cli_commands includes search/read/readiness/retries; each before/after snapshot adds one separate status command. No model or fare API is called.',
        'browser_control_note':'This probe never kills or launches Chrome itself and never calls socai stop. A read-only socai search may reconnect or launch its configured browser.'}
    for index in range(args.calls):
        if index:
            print(f'IDLE {args.interval}s; no keepalive during this interval', flush=True)
            await asyncio.sleep(args.interval)
        query = ['香港 日本 机票','香港 大阪 机票','香港 东京 机票'][index % 3]
        before = await snapshot(settings)
        # Rebuild the adapter so every probe reads a body, rather than using
        # an in-memory evidence checkpoint from the preceding invocation.
        source = Socai(settings)
        transitions = []
        began = monotonic()
        def trace(stage, status, detail, duration, data):
            if stage == 'browser_connection':
                transitions.append({'seconds':round(monotonic()-began,3),
                    'connected':data.get('browser_connected'), 'state':data.get('browser_state')})
        source.on_trace = trace
        start_count = source.command_calls
        item = {'query':query, 'before':before}
        try:
            evidence = await asyncio.wait_for(source.search(query), timeout=240)
            item.update(body_count=len(evidence), evidence=[{'id':e.id,'url':e.url,
                'title':e.title,'body_chars':len(e.body),'observed_at':e.observed_at.isoformat()} for e in evidence],
                result='ok' if evidence else 'no_body', blocked_code=source.blocked_code)
        except Exception as error:
            failure = source_error(source.name,error)
            item.update(result='failed',failure_code=failure.code,body_count=0)
        item.update(seconds=round(monotonic()-began,3),
            provider_cli_commands=source.command_calls-start_count,
            status_observation_commands=2,
            connection_transitions=transitions)
        item['after'] = await snapshot(settings)
        ready = next((x['seconds'] for x in transitions if x['connected'] is True),None)
        item['connection_recovery_seconds'] = 0 if before.get('browser_connected') else ready
        result['calls'].append(item)
        result['successes'] = sum(x['body_count'] > 0 for x in result['calls'])
        result['read_success_rate'] = result['successes']/len(result['calls'])
        result['finished_at'] = now().isoformat()
        output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'call':index+1,'scenario':args.scenario,'result':item['result'],
            'body_count':item['body_count'],'seconds':item['seconds'],
            'before_connected':before.get('browser_connected'),'after_connected':item['after'].get('browser_connected')},ensure_ascii=False),flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--scenario',required=True)
    parser.add_argument('--calls',type=int,choices=range(1,7),default=2)
    parser.add_argument('--interval',type=int,default=30)
    parser.add_argument('--socai-mode',choices=['selective','scan'],default='selective')
    parser.add_argument('--reauthorization',choices=['unknown','none','prompted'],default='unknown')
    parser.add_argument('--login-observation',choices=['unknown','user_reported','visible_logged_in','visible_logged_out'],default='unknown')
    parser.add_argument('--private-data-dir',default='data/browser-stability-probe')
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    if not 0 <= args.interval <= 3600: parser.error('interval must be between 0 and 3600 seconds')
    asyncio.run(main(args))
