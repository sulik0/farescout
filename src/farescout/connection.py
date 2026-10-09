"""Privacy-safe connection observations; never opens a second CDP connection."""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

from .models import now


def endpoint_marker(settings=None):
    config_path = getattr(settings, 'socai_config_path', None) or Path(os.getenv('SOCAI_CONFIG_PATH', str(Path.home()/'.socai/config.json')))
    try:
        config = json.loads(config_path.read_text())['chrome']
        if config.get('profile') == 'managed':
            profile = Path(config['profile_dir']) if config.get('profile_dir') else Path.home()/'.socai/chrome-profile'
            return profile / 'DevToolsActivePort', 'managed_chrome_marker'
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return Path.home() / 'Library/Application Support/Google/Chrome/DevToolsActivePort', 'existing_chrome_marker'


def connection_observation(state, settings):
    home = settings.socai_home or Path(os.getenv("SOCAI_HOME", str(Path.home() / ".socai")))
    result = {key: state.get(key) for key in ["browser_connected", "browser_state", "daemon_running",
        "daemon_compatible", "cli_version", "error_code", "profile_mode", "active_profile_mode"]}
    result["observed_at"] = now().isoformat()
    result['reported_browser_connected'] = state.get('browser_connected')
    result["authorization"] = "active_connection" if state.get("browser_connected") is True else "unknown"
    result["authorization_note"] = "已有有效连接；本次状态检查没有发起连接" if state.get("browser_connected") else "未连接不代表用户拒绝；CLI不能报告授权弹窗是否出现"
    try:
        pid = (home / "rust-daemon.pid").read_text().strip()
        result["daemon_pid"] = int(pid) if pid.isdigit() else None
    except OSError:
        result["daemon_pid"] = None
    marker, marker_source = endpoint_marker(settings)
    try:
        explicit = None if settings.social_browser == 'managed' and settings.socai_config_path else (os.getenv("SOCAI_CDP_WS") or os.getenv("SOCAI_CDP_URL"))
        raw = explicit or marker.read_text().strip()
        result["endpoint_fingerprint"] = hashlib.sha256(raw.encode()).hexdigest()[:16]
        result["endpoint_source"] = "explicit" if explicit else marker_source
    except OSError:
        result["endpoint_fingerprint"] = None
    # Keep only recognized failure categories and timestamps, never raw log text/URLs.
    result["last_disconnect"] = None
    result['first_transport_terminal'] = None
    result['last_transport_open'] = None
    try:
        with (home / "rust-daemon.log").open("rb") as file:
            file.seek(0, 2)
            file.seek(max(0, file.tell() - 16384))
            lines = file.read().decode("utf-8", errors="replace").splitlines()
        for line in reversed(lines):
            line = re.sub(r'\x1b\[[0-9;]*m', '', line)
            try:
                timestamp = datetime.fromisoformat(line.split()[0])
                if timestamp.tzinfo is None:
                    continue
            except (IndexError, ValueError):
                continue
            if 'cdp_ws_open' in line and result['last_transport_open'] is None:
                fields = dict(re.findall(r'(connection_id|pid)=(\d+)\b', line))
                result['last_transport_open'] = {'at':line.split()[0], **fields}
            if 'cdp_ws_terminal' in line and result['first_transport_terminal'] is None:
                parsed = {k:v.strip('"') for k,v in re.findall(r'(connection_id|pid|kind|error_class|close_code|reason_bytes|pending_commands|uptime_ms)=([^\s]+)', re.sub(r'\x1b\[[0-9;]*m', '', line))}
                fields = {k:v for k,v in parsed.items() if k not in {'kind','error_class'} and v.isdigit()}
                kinds = {'command_channel_closed','websocket_send_failed','close_frame','stream_ended','websocket_receive_failed'}
                if parsed.get('kind') in kinds:
                    fields['kind'] = parsed['kind']
                errors = {'none','protocol','connection_closed','already_closed','tls','other',
                    'io_BrokenPipe','io_ConnectionReset','io_UnexpectedEof','io_TimedOut','io_NotConnected','io_WouldBlock','io_Interrupted','io_Other'}
                if parsed.get('error_class') in errors:
                    fields['error_class'] = parsed['error_class']
                result['first_transport_terminal'] = {'at':line.split()[0], **fields,
                    'cause_confirmed':False, 'note':'WebSocket 终止时记录；关闭原因文字未保存。事件说明连接如何结束，不证明谁触发了断线。'}
            if "cdp connection lost" not in line:
                continue
            if result['last_disconnect'] is not None:
                continue
            reason = "session_closed" if "session is closed" in line else "transport_command_timeout" if "command timeout" in line else "transport_lost_unknown"
            result["last_disconnect"] = {"at": line.split()[0], "category": reason,
                "cause_confirmed": False, "note": "这是daemon观测到的传输错误，不能据此判断谁关闭了连接"}
    except OSError:
        pass
    path = settings.data_dir / "browser-observation.json"
    try:
        previous = json.loads(path.read_text()) if path.exists() else {}
        if not isinstance(previous, dict):
            previous = {}
        # The daemon can report a connected session for several seconds after
        # its WebSocket has ended. Match the current PID and a new terminal
        # event; never let an old daemon's log invalidate a new connection.
        terminal, opened = result['first_transport_terminal'], result['last_transport_open']
        def later(left, right):
            try:
                return datetime.fromisoformat(left) > datetime.fromisoformat(right)
            except (TypeError, ValueError):
                return False
        current_terminal = bool(terminal and terminal.get('kind') and terminal.get('connection_id') and
            str(result.get('daemon_pid')) == terminal.get('pid'))
        terminal_key = {key:terminal.get(key) for key in ('pid','connection_id','at')} if current_terminal else None
        acknowledged = previous.get('acknowledged_terminal')
        if current_terminal and state.get('browser_connected') is False:
            acknowledged = terminal_key
        result['acknowledged_terminal'] = acknowledged
        newly_ended = current_terminal and terminal_key != acknowledged and (
            (previous.get('daemon_pid') == result.get('daemon_pid') and
             later(terminal['at'], previous.get('observed_at'))) or
            (opened and opened.get('pid') == terminal.get('pid') and
             opened.get('connection_id') == terminal.get('connection_id') and
             later(terminal['at'], opened['at'])))
        pending = current_terminal and previous.get('transport_pending_disconnect') and (
            previous.get('daemon_pid') == result.get('daemon_pid'))
        newer_open = bool(current_terminal and opened and opened.get('pid') == terminal.get('pid') and
            later(opened['at'], terminal['at']))
        result['transport_pending_disconnect'] = bool(state.get('browser_connected') is True and
            (newly_ended or pending) and not newer_open)
        if result['transport_pending_disconnect']:
            result.update(browser_connected=False, browser_state='disconnected', authorization='unknown',
                authorization_note='WebSocket 已终止；daemon 的连接状态尚未更新。等待其确认断线后再连接。')
        result["previous_observed_at"] = previous.get("observed_at")
        result["daemon_changed"] = bool(previous.get("daemon_pid") and result.get("daemon_pid") and previous["daemon_pid"] != result["daemon_pid"])
        result["endpoint_changed"] = bool(previous.get("endpoint_fingerprint") and result.get("endpoint_fingerprint") and previous["endpoint_fingerprint"] != result["endpoint_fingerprint"])
        result["connection_lost_since_check"] = previous.get("browser_connected") is True and result.get("browser_connected") is not True
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, prefix='.browser-observation-', delete=False) as file:
            file.write(json.dumps(result, ensure_ascii=False, indent=2))
            tmp = Path(file.name)
        try:
            tmp.chmod(0o600)
            tmp.replace(path)
        finally:
            tmp.unlink(missing_ok=True)
    except (OSError, ValueError):
        result["observation_save_failed"] = True
    return result
