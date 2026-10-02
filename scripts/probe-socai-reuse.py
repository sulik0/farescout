"""Read-only repeated calls; record connection continuity without storing tokens."""
import asyncio
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from time import monotonic

from farescout.config import Settings
from farescout.providers import Socai, command_json, socai_evidence
from farescout.safety import source_error


async def snapshot(settings):
    try:
        state = await command_json(settings.socai_bin, ['status','--json'], settings, 'socai')
        state = {k:state.get(k) for k in ['browser_connected','browser_state','daemon_running',
            'daemon_compatible','error_code','profile_mode','active_profile_mode']}
    except Exception as error:
        state = {'error':str(source_error('socai',error))}
    try:
        rows = subprocess.check_output(['ps','-axo','pid,ppid,comm'], text=True).splitlines()
        state['processes'] = [r.strip() for r in rows if r.endswith('/socai') or r.endswith('/Google Chrome')]
        daemon_ids = [r.split()[0] for r in state['processes'] if r.endswith('/socai')]
        state['cdp_tcp_connections'] = []
        for pid in daemon_ids:
            connections = subprocess.run(['lsof','-nP','-a','-p',pid,'-iTCP:9222'],capture_output=True,text=True)
            state['cdp_tcp_connections'].extend(connections.stdout.splitlines()[1:])
    except Exception:
        state['processes'] = 'process inventory unavailable in execution sandbox'
    marker = Path.home()/'Library/Application Support/Google/Chrome/DevToolsActivePort'
    try:
        raw = marker.read_text().strip()
        state['endpoint_fingerprint'] = hashlib.sha256(raw.encode()).hexdigest()[:16]
        state['endpoint_port'] = raw.splitlines()[0]
    except Exception as error:
        state['endpoint_marker'] = type(error).__name__
    return state


async def main(args):
    settings = Settings.from_env()
    settings.source_timeout = 180  # Give first human approval enough time; do not kill after 30 seconds.
    settings.socai_mode = args.socai_mode
    settings.data_dir = Path('data/socai-reuse-probe')
    settings.data_dir.mkdir(parents=True,exist_ok=True)
    records = []
    output = settings.data_dir/args.output
    adapter = Socai(settings)
    adapter.settings.socai_notes = 1  # Connection probe, not product acceptance.
    if args.timeout_probe:
        record = {'kind':'cancel_client_while_connected','before':await snapshot(settings)}
        if record['before'].get('browser_connected') is not True:
            raise RuntimeError('Timeout probe requires an already-connected browser')
        from dataclasses import replace
        try:
            await command_json(settings.socai_bin,['xhs','search','香港 日本 机票','--num-notes','3','--pretty'],
                replace(settings,source_timeout=.5),'小红书 / socai')
        except TimeoutError:
            record['result'] = 'expected client timeout'
        record['after'] = await snapshot(settings)
        records.append(record)
        print('TIMEOUT PROBE',json.dumps(record,ensure_ascii=False),flush=True)
    queries = ['香港 日本 机票','香港 大阪 机票','香港 东京 机票'][:args.calls]
    for index,query in enumerate(queries,1):
        record = {'call':index,'query':query,'before':await snapshot(settings)}
        print('CALL',index,'BEFORE',json.dumps(record['before'],ensure_ascii=False),flush=True)
        start = monotonic()
        try:
            if args.mode == 'adapter':
                before = adapter.command_calls
                record['body_count'] = len(await adapter.search(query))
                record['actual_cli_commands'] = adapter.command_calls-before
            else:
                payload = await command_json(settings.socai_bin,['xhs','search',query,'--num-notes','1',
                    '--num-comments','0','--pretty'], settings,'小红书 / socai')
                record['body_count'] = len(socai_evidence(payload,query))
                record['payload_fields'] = sorted(payload.keys())
            record['result'] = 'ok' if record['body_count'] else 'no_body'
        except Exception as error:
            record['result'] = str(source_error('socai',error))
        record['seconds'] = round(monotonic()-start,3)
        record['after'] = await snapshot(settings)
        records.append(record)
        output.write_text(json.dumps(records,ensure_ascii=False,indent=2))
        print('CALL',index,'RESULT',record['result'],'SECONDS',record['seconds'],
              'AFTER',json.dumps(record['after'],ensure_ascii=False),flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode',choices=['direct','adapter'],default='direct')
    parser.add_argument('--socai-mode',choices=['selective','scan'],default='selective')
    parser.add_argument('--calls',type=int,choices=[1,2,3],default=3)
    parser.add_argument('--timeout-probe',action='store_true')
    parser.add_argument('--output',default='observations.json')
    asyncio.run(main(parser.parse_args()))
