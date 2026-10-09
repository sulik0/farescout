import json
from pathlib import Path

import pytest

from farescout.config import Settings
from farescout.providers import Socai, command_json
from farescout.safety import SourceFailure
from farescout.social_browser import prepare_managed


def configured(tmp_path):
    return Settings(socai_home=tmp_path/'daemon', socai_config_path=tmp_path/'daemon/config.json',
        socai_profile_dir=tmp_path/'profile', data_dir=tmp_path/'data')


def test_managed_provisions_isolated_config_but_never_overwrites_selection(tmp_path):
    settings = configured(tmp_path)
    prepare_managed(settings)
    assert json.loads(settings.socai_config_path.read_text())['chrome']['profile_dir'] == str(settings.socai_profile_dir)
    assert settings.socai_config_path.stat().st_mode & 0o777 == 0o600
    existing = '{"chrome":{"profile":"existing"}}'
    settings.socai_config_path.write_text(existing)
    with pytest.raises(SourceFailure, match='BROWSER_CONFIG_MISMATCH'):
        prepare_managed(settings)
    assert settings.socai_config_path.read_text() == existing


async def test_unpatched_cli_cannot_fall_back_to_daily_chrome(tmp_path, monkeypatch):
    settings = configured(tmp_path)
    calls = []
    async def command(executable, args, settings, source):
        calls.append(args)
        return {'config_path':str(tmp_path/'global/config.json')}
    monkeypatch.setattr('farescout.providers.command_json', command)
    with pytest.raises(SourceFailure, match='BROWSER_CONFIG_UNSUPPORTED'):
        await Socai(settings).search('香港 日本 机票')
    assert calls == [['config','path']]


async def test_child_browser_isolation_overrides_env_without_changing_parent(tmp_path, monkeypatch):
    import sys
    settings = configured(tmp_path)
    settings.socai_bin = sys.executable
    monkeypatch.setenv('SOCAI_HOME','daily-daemon')
    monkeypatch.setenv('SOCAI_CDP_URL','http://127.0.0.1:9999')
    result = await command_json(sys.executable, ['-c',
        'import json,os; print(json.dumps({k:os.getenv(k) for k in ["SOCAI_HOME","SOCAI_CONFIG_PATH","SOCAI_CDP_URL"]}))'],settings,'socai')
    assert result == {'SOCAI_HOME':str(settings.socai_home), 'SOCAI_CONFIG_PATH':str(settings.socai_config_path), 'SOCAI_CDP_URL':None}
    import os
    assert os.getenv('SOCAI_HOME') == 'daily-daemon'


def test_default_startup_selects_managed_without_creating_browser_data(tmp_path, monkeypatch):
    monkeypatch.setattr('farescout.config.load_dotenv', lambda *args, **kwargs: None)
    for key in ['SOCAI_HOME','SOCAI_CONFIG_PATH','FARESCOUT_SOCIAL_BROWSER']:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv('FARESCOUT_BROWSER_ROOT', str(tmp_path/'local-browser'))
    settings = Settings.from_env()
    assert settings.social_browser == 'managed'
    assert settings.socai_profile_dir == tmp_path/'local-browser/chrome-managed'
    assert not settings.socai_home.exists()
    monkeypatch.setenv('FARESCOUT_SOCIAL_BROWSER','existing')
    alternate = Settings.from_env()
    assert alternate.socai_home is None and alternate.socai_config_path is None


async def test_missing_flyai_node_has_actionable_failure(tmp_path):
    tool=tmp_path/'flyai'; tool.write_text('#!/bin/sh\necho "env: node: No such file or directory" >&2\nexit 127\n')
    tool.chmod(0o700)
    with pytest.raises(SourceFailure,match='NODE_NOT_INSTALLED'):
        await command_json(str(tool), [], Settings(data_dir=tmp_path), 'FlyAI')
