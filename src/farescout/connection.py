"""Privacy-safe connection observations; never opens a second CDP connection."""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
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
    try:
        with (home / "rust-daemon.log").open("rb") as file:
            file.seek(0, 2)
            file.seek(max(0, file.tell() - 16384))
            lines = file.read().decode("utf-8", errors="replace").splitlines()
        for line in reversed(lines):
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
            if result['first_transport_terminal'] is not None:
                break
    except OSError:
        pass
    path = settings.data_dir / "browser-observation.json"
    try:
        previous = json.loads(path.read_text()) if path.exists() else {}
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
