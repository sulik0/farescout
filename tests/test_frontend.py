"""Run the browser-independent frontend regressions without a JS build stack."""
import shutil
import subprocess
from pathlib import Path

import pytest


def test_frontend_state_and_evidence_regressions():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node.js is needed for the frontend regression checks')
    result = subprocess.run([node, '--test', str(Path(__file__).with_name('frontend.test.mjs'))],
                            text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
