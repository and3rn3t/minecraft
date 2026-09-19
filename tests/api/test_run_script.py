#!/usr/bin/env python3
"""Tests for run_script, the subprocess wrapper every management endpoint uses.

It had no direct coverage: endpoints that call it mock it out entirely, so the
timeout handling and the not-found path were never exercised.
"""

import subprocess
import sys
from pathlib import Path as PathLib
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = PathLib(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.server import DEFAULT_SCRIPT_TIMEOUT, LONG_SCRIPT_TIMEOUT, run_script  # noqa: E402


class TestRunScriptTimeouts:
    """The timeout is what stops a real-sized backup looking like a failure."""

    def test_default_timeout_is_passed_through(self):
        with patch("api.server.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="ok", stderr="", returncode=0)
            run_script("manage.sh", "status")

        assert mock_run.call_args.kwargs["timeout"] == DEFAULT_SCRIPT_TIMEOUT

    def test_explicit_timeout_overrides_the_default(self):
        with patch("api.server.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="ok", stderr="", returncode=0)
            run_script("manage.sh", "backup", timeout=LONG_SCRIPT_TIMEOUT)

        assert mock_run.call_args.kwargs["timeout"] == LONG_SCRIPT_TIMEOUT

    def test_long_timeout_is_longer_than_the_default(self):
        """A backup of a real world takes minutes, not seconds."""
        assert LONG_SCRIPT_TIMEOUT > DEFAULT_SCRIPT_TIMEOUT

    def test_timeout_reports_504_and_names_the_budget(self):
        with patch("api.server.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="manage.sh", timeout=30)
            stdout, stderr, code = run_script("manage.sh", "backup", timeout=30)

        assert code == 504
        assert stdout is None
        assert "30" in stderr


class TestRunScriptOutcomes:
    def test_missing_script_reports_404_without_running_anything(self):
        with patch("api.server.subprocess.run") as mock_run:
            stdout, stderr, code = run_script("definitely-not-a-real-script.sh")

        assert code == 404
        assert stdout is None
        assert "not found" in stderr.lower()
        mock_run.assert_not_called()

    def test_successful_run_returns_stdout_and_returncode(self):
        with patch("api.server.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="server running", stderr="", returncode=0)
            stdout, stderr, code = run_script("manage.sh", "status")

        assert code == 0
        assert stdout == "server running"

    def test_failing_script_propagates_its_returncode(self):
        with patch("api.server.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="", stderr="boom", returncode=2)
            _, stderr, code = run_script("manage.sh", "status")

        assert code == 2
        assert stderr == "boom"

    def test_unexpected_error_reports_500(self):
        with patch("api.server.subprocess.run") as mock_run:
            mock_run.side_effect = OSError("no such executable")
            stdout, stderr, code = run_script("manage.sh", "status")

        assert code == 500
        assert stdout is None
        assert "no such executable" in stderr

    def test_arguments_are_forwarded_after_the_script_path(self):
        with patch("api.server.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)
            run_script("manage.sh", "update", "1.21.1")

        argv = mock_run.call_args.args[0]
        assert argv[-2:] == ["update", "1.21.1"]
        assert argv[0].endswith("manage.sh")

    def test_runs_from_the_project_root(self):
        """Scripts resolve config/ and data/ relative to the repository root."""
        with patch("api.server.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)
            run_script("manage.sh", "status")

        assert mock_run.call_args.kwargs["cwd"] == str(PROJECT_ROOT)

    @pytest.mark.parametrize("verb", ["start", "stop", "restart"])
    def test_output_is_captured_as_text(self, verb):
        with patch("api.server.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="", stderr="", returncode=0)
            run_script("manage.sh", verb)

        assert mock_run.call_args.kwargs["capture_output"] is True
        assert mock_run.call_args.kwargs["text"] is True
