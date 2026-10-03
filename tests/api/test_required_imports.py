"""The security dependencies are required: a missing one must stop startup.

api/server.py used to catch ImportError for flask-cors, flask-limiter and
api.security and substitute no-ops, so a broken install ran with no
brute-force protection or command sanitising and said nothing. These tests
start the module in a subprocess with one dependency made unimportable and
assert that it fails instead.
"""

import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.real_subprocess
@pytest.mark.parametrize("missing", ["flask_cors", "flask_limiter", "api.security"])
def test_server_refuses_to_start_without(missing):
    code = (
        "import sys\n"
        f"sys.modules[{missing!r}] = None\n"  # None in sys.modules makes the import raise ImportError
        "import api.server\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        env={"PYTEST_RUNNING": "1", "PATH": "/usr/bin:/bin"},
    )
    assert result.returncode != 0
    assert f"import of {missing} halted" in result.stderr
