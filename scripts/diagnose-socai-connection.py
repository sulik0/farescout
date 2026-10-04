"""Read-only local diagnostics. Does not search, connect CDP, restart, or change power settings."""
import argparse
from datetime import date, datetime, timezone
import hashlib
import json
import plistlib
from pathlib import Path
import re
import subprocess

from farescout.config import Settings


def command(args, seconds=20):
    return subprocess.run(args, capture_output=True, text=True, timeout=seconds)


def inspect(day, start_hour=0, end_hour=24):
    settings = Settings.from_env()
    result = {'kind':'read_only_socai_connection_diagnosis', 'day':day, 'local_hour_window':[start_hour,end_hour],
              'observed_at':datetime.now(timezone.utc).isoformat(),
              'manual_confirmation_count':'not_observable_by_status'}
    try:
        status = json.loads(command([settings.socai_bin, 'status', '--json'], 8).stdout)
        result['status'] = {key:status.get(key) for key in ['cli_version','daemon_running',
            'daemon_compatible','browser_connected','browser_state','profile_mode','active_profile_mode','error_code']}
    except Exception as error:
        result['status_error'] = type(error).__name__
    socai_home = Path.home()/'.socai'
    try:
        pid = (socai_home/'rust-daemon.pid').read_text().strip()
        if pid.isdigit():
            rows = command(['ps','-p',pid,'-o','pid=,ppid=,lstart=']).stdout.strip()
            result['daemon_process'] = rows
            tcp = command(['lsof','-nP','-a','-p',pid,'-iTCP:9222']).stdout.splitlines()[1:]
            result['daemon_cdp_tcp_9222'] = [row.split()[-2:] for row in tcp]
            result['tcp_note'] = 'Only checks port 9222; absence alone does not identify a disconnect cause.'
        chrome = command(['pgrep','-x','Google Chrome']).stdout.split()
        result['chrome_processes'] = [command(['ps','-p',p,'-o','pid=,ppid=,lstart=']).stdout.strip() for p in chrome if p.isdigit()]
        info = plistlib.loads(Path('/Applications/Google Chrome.app/Contents/Info.plist').read_bytes())
        result['chrome_version'] = info.get('CFBundleShortVersionString')
    except Exception as error:
        result['process_error'] = type(error).__name__
    marker = Path.home()/'Library/Application Support/Google/Chrome/DevToolsActivePort'
    try:
        result['default_chrome_endpoint_fingerprint'] = hashlib.sha256(marker.read_bytes().strip()).hexdigest()[:16]
        result['endpoint_note'] = 'Marker is not proof of a live socket or permission.'
    except OSError:
        result['default_chrome_endpoint_fingerprint'] = None
    result['daemon_events'] = []
    try:
        for line in (socai_home/'rust-daemon.log').read_text(errors='replace').splitlines():
            try:
                timestamp = datetime.fromisoformat(line.split()[0].replace('Z','+00:00'))
            except (ValueError, IndexError):
                continue
            if timestamp.astimezone().date().isoformat() != day or not start_hour <= timestamp.astimezone().hour < end_hour:
                continue
            category = None
            if 'cdp connection lost' in line:
                category = 'cdp_session_closed' if 'session is closed' in line else 'cdp_transport_lost'
            elif 'cdp connect attempt failed' in line:
                category = 'connect_inventory_timeout' if 'did not respond within 20s' in line else 'connect_attempt_failed'
            elif 'releasing idle remote browser session' in line:
                category = 'remote_browser_idle_release'
            if category:
                result['daemon_events'].append({'time':timestamp.astimezone().isoformat(),'category':category,
                    'attempt':(re.search(r'attempt=(\d+)',line).group(1) if re.search(r'attempt=(\d+)',line) else None)})
    except OSError as error:
        result['log_error'] = type(error).__name__
    result['power_events'] = []
    result['darkwake_count'] = 0
    result['maintenance_sleep_count'] = 0
    try:
        for line in command(['pmset','-g','log']).stdout.splitlines():
            match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} [+-]\d{4})\s+(Sleep|Wake|DarkWake)\s+\t(.*)',line)
            if not match or not match[1].startswith(day) or not start_hour <= int(match[1][11:13]) < end_hour:
                continue
            if match[2] == 'DarkWake':
                result['darkwake_count'] += 1
                continue
            if match[2] == 'Sleep' and "'Idle Sleep'" not in match[3]:
                result['maintenance_sleep_count'] += 1
                continue
            # Store transition times and coarse reasons, not battery, devices or app activity.
            detail = 'idle_sleep' if "'Idle Sleep'" in match[3] else 'sleep' if match[2]=='Sleep' else 'wake'
            result['power_events'].append({'time':datetime.strptime(match[1],'%Y-%m-%d %H:%M:%S %z').isoformat(),
                'event':match[2], 'reason':detail})
    except Exception as error:
        result['power_error'] = type(error).__name__
    result['causality_note'] = 'Timestamp correlation is not proof that sleep closed the socket.'
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--day', default=date.today().isoformat())
    parser.add_argument('--output', required=True)
    parser.add_argument('--from-hour',type=int,default=0)
    parser.add_argument('--to-hour',type=int,default=24)
    args = parser.parse_args()
    date.fromisoformat(args.day)
    if not 0 <= args.from_hour < args.to_hour <= 24:
        parser.error('hour window must satisfy 0 <= from-hour < to-hour <= 24')
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(inspect(args.day,args.from_hour,args.to_hour),ensure_ascii=False,indent=2))
    print(output)
