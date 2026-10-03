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


@pytest.mark.real_subprocess
@pytest.mark.parametrize(
    "missing, flag_off, flag_on",
    [
        ("bcrypt", "BCRYPT_AVAILABLE", "JWT_AVAILABLE"),
        ("jwt", "JWT_AVAILABLE", "BCRYPT_AVAILABLE"),
        ("qrcode", "QRCODE_AVAILABLE", "PYOTP_AVAILABLE"),
        ("pyotp", "PYOTP_AVAILABLE", "QRCODE_AVAILABLE"),
    ],
)
def test_one_missing_auth_library_does_not_disable_the_other(missing, flag_off, flag_on):
    """bcrypt/PyJWT and pyotp/qrcode used to share a try/except, so losing either lost both."""
    code = (
        "import sys\n"
        f"sys.modules[{missing!r}] = None\n"
        "import api.auth_crypto as c\n"
        f"print(c.{flag_off}, c.{flag_on})\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        env={"PYTEST_RUNNING": "1", "PATH": "/usr/bin:/bin"},
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines()[-1] == "False True"
