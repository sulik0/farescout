"""Privacy-safe connection observations; never opens a second CDP connection."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from .models import now


def connection_observation(state, settings):
    home = Path(os.getenv("SOCAI_HOME", str(Path.home() / ".socai")))
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
    marker = Path.home() / "Library/Application Support/Google/Chrome/DevToolsActivePort"
    try:
        raw = os.getenv("SOCAI_CDP_WS") or os.getenv("SOCAI_CDP_URL") or marker.read_text().strip()
        result["endpoint_fingerprint"] = hashlib.sha256(raw.encode()).hexdigest()[:16]
        result["endpoint_source"] = "explicit" if os.getenv("SOCAI_CDP_WS") or os.getenv("SOCAI_CDP_URL") else "existing_chrome_marker"
    except OSError:
        result["endpoint_fingerprint"] = None
    # Keep only recognized failure categories and timestamps, never raw log text/URLs.
    result["last_disconnect"] = None
    try:
        with (home / "rust-daemon.log").open("rb") as file:
            file.seek(0, 2)
            file.seek(max(0, file.tell() - 16384))
            lines = file.read().decode("utf-8", errors="replace").splitlines()
        for line in reversed(lines):
            if "cdp connection lost" not in line:
                continue
            reason = "session_closed" if "session is closed" in line else "transport_command_timeout" if "command timeout" in line else "transport_lost_unknown"
            result["last_disconnect"] = {"at": line.split()[0], "category": reason,
                "cause_confirmed": False, "note": "这是daemon观测到的传输错误，不能据此判断谁关闭了连接"}
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
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        tmp.chmod(0o600)
        tmp.replace(path)
    except (OSError, ValueError):
        result["observation_save_failed"] = True
    return result
