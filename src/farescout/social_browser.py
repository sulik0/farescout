"""Select an isolated socai profile without changing the user's global config."""
from __future__ import annotations

import json
from pathlib import Path

from .safety import SourceFailure


def browser_env(settings):
    return {key: str(path) for key, path in (
        ('SOCAI_HOME', settings.socai_home), ('SOCAI_CONFIG_PATH', settings.socai_config_path)
    ) if path is not None}


def prepare_managed(settings):
    """Only provision new config; never rewrite an existing browser selection."""
    if settings.social_browser != 'managed' or settings.socai_config_path is None:
        return
    home, config, profile = settings.socai_home, settings.socai_config_path, settings.socai_profile_dir
    if home is None or profile is None:
        raise SourceFailure('socai', 'BROWSER_CONFIG_INVALID', '专用浏览器目录配置不完整')
    for directory in (home, config.parent, profile):
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    desired = {'chrome': {'profile': 'managed', 'profile_dir': str(profile.resolve())}}
    try:
        # Exclusive creation protects a profile selection made by another process.
        with config.open('x') as file:
            config.chmod(0o600)
            file.write(json.dumps(desired, ensure_ascii=False) + '\n')
    except FileExistsError:
        pass
    try:
        chrome = json.loads(config.read_text())['chrome']
        valid = chrome.get('profile') == 'managed' and Path(chrome['profile_dir']).expanduser().resolve() == profile.resolve()
    except (ValueError, KeyError, TypeError):
        valid = False
    if not valid:
        raise SourceFailure('socai', 'BROWSER_CONFIG_MISMATCH', '专用配置与预期 profile 不一致；保留原文件，请先检查配置')
