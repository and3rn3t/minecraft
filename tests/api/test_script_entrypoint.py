#!/usr/bin/env python3
"""
The deployed service runs `python api/server.py`, which loads server.py as
`__main__` rather than as `api.server`. Every other test imports it as a
module, so a startup failure specific to the script entry point -- which the
blueprint split once had: a circular ImportError from `from api import server`
loading a second copy -- passes the whole suite and only shows up as a failed
deploy health check on the Pi.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent


@pytest.mark.real_subprocess
def test_server_starts_when_run_as_a_script():
    # Reaching the "Starting" line means every blueprint imported. The server
    # then keeps running, so the timeout firing is the expected outcome; an
    # early exit (ImportError, or the port being taken) leaves the output to
    # explain why.
    try:
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "api" / "server.py")],
            cwd=PROJECT_ROOT / "api",
            capture_output=True,
            text=True,
            timeout=12,
            # As the systemd unit sets it; otherwise a piped stdout is
            # block-buffered and the kill discards the "Starting" line.
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
            check=False,
        )
        output = (result.stdout or "") + (result.stderr or "")
    except subprocess.TimeoutExpired as exc:
        out, err = exc.stdout or b"", exc.stderr or b""
        output = (
            out.decode(errors="replace") if isinstance(out, bytes) else out
        ) + (err.decode(errors="replace") if isinstance(err, bytes) else err)

    assert "ImportError" not in output, output[-2000:]
    assert "Starting Minecraft Server API" in output, output[-2000:]
