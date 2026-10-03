"""The api modules that depend on each other import cleanly in either order.

api.server imports auth_guard while auth_guard reads state from api.server, and
the blueprints use auth_guard's decorators as api.server finishes loading. The
test suite always imports api.server first, which hid that importing
api.auth_guard first failed with "partially initialized module".
"""

import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.real_subprocess
@pytest.mark.parametrize(
    "module",
    ["api.server", "api.auth_guard", "api.auth_crypto", "api.paths", "api.config_redaction", "api.rbac", "api.realtime"],
)
def test_module_imports_first(module):
    result = subprocess.run(
        [sys.executable, "-W", "ignore", "-c", f"import {module}"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        env={"PYTEST_RUNNING": "1", "PATH": "/usr/bin:/bin"},
        check=False,
    )
    assert result.returncode == 0, result.stderr
