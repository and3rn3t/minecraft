#!/usr/bin/env python3
"""Tests for the WebSocket log stream.

The stream was rewritten from a per-client `docker logs --tail` poll into a
single `docker logs -f` follower that fans lines out to every subscriber, and
then into an always-on follower that also drives the game event bus.

The behaviour that matters: one follower regardless of client count, lines
delivered in order, capture continuing with no clients attached, and the
follower stopping only when it is explicitly told to.
"""

import subprocess
import sys
from pathlib import Path as PathLib
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = PathLib(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import api.server as api_module  # noqa: E402

pytestmark = pytest.mark.skipif(
    not api_module.SOCKETIO_AVAILABLE,
    reason="Flask-SocketIO not installed, so the stream is not defined",
)


@pytest.fixture(autouse=True)
def clean_stream_state():
    """Each test starts with no subscribers and no running follower."""
    api_module.active_log_streams.clear()
    api_module._log_reader_state["running"] = False
    api_module._log_reader_state["stop"] = False
    yield
    api_module.active_log_streams.clear()
    api_module._log_reader_state["running"] = False
    api_module._log_reader_state["stop"] = False


def stop_after_first_attach(*_args, **_kwargs):
    """Side effect for socketio.sleep that ends the follower's retry loop."""
    api_module._log_reader_state["stop"] = True


class TestGetLogTail:
    def test_returns_lines_on_success(self):
        with patch("api.server.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="first\nsecond")
            assert api_module.get_log_tail(10) == ["first", "second"]

    def test_requests_the_number_of_lines_asked_for(self):
        with patch("api.server.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="")
            api_module.get_log_tail(250)

        assert "250" in mock_run.call_args.args[0]

    def test_returns_empty_when_docker_reports_failure(self):
        with patch("api.server.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            assert api_module.get_log_tail() == []

    def test_returns_empty_when_docker_is_absent(self):
        with patch("api.server.subprocess.run", side_effect=FileNotFoundError):
            assert api_module.get_log_tail() == []

    def test_returns_empty_when_docker_hangs(self):
        with patch("api.server.subprocess.run", side_effect=subprocess.TimeoutExpired("docker", 5)):
            assert api_module.get_log_tail() == []


class TestEnsureLogReader:
    """One follower, however many clients connect."""

    def test_starts_the_follower_when_none_is_running(self):
        with patch.object(api_module.socketio, "start_background_task") as start:
            api_module._ensure_log_reader()

        start.assert_called_once()
        assert api_module._log_reader_state["running"] is True

    def test_does_not_start_a_second_follower(self):
        api_module._log_reader_state["running"] = True

        with patch.object(api_module.socketio, "start_background_task") as start:
            api_module._ensure_log_reader()

        start.assert_not_called()

    def test_repeated_calls_start_only_one(self):
        with patch.object(api_module.socketio, "start_background_task") as start:
            for _ in range(5):
                api_module._ensure_log_reader()

        assert start.call_count == 1


class TestLogReader:
    def test_follows_the_log_even_with_nobody_subscribed(self):
        """Capture must not depend on a browser being open.

        Events that happen while the dashboard is closed are exactly the ones
        worth recording, so an empty subscriber set no longer stops the reader.
        """
        api_module._log_reader_state["running"] = True

        proc = MagicMock()
        proc.stdout = iter(["[16:04:23] [Server thread/INFO]: Jonah joined the game\n"])

        with patch("api.server.subprocess.Popen", return_value=proc) as popen, patch.object(
            api_module, "_publish_log_line"
        ) as publish, patch.object(api_module.socketio, "sleep", side_effect=stop_after_first_attach):
            api_module._log_reader()

        popen.assert_called_once()
        publish.assert_called_once()
        assert api_module._log_reader_state["running"] is False

    def test_stops_when_asked_to(self):
        api_module._log_reader_state["running"] = True
        api_module._log_reader_state["stop"] = True

        with patch("api.server.subprocess.Popen") as popen:
            api_module._log_reader()

        popen.assert_not_called()
        assert api_module._log_reader_state["running"] is False

    def test_stop_log_reader_sets_the_flag(self):
        api_module.stop_log_reader()
        assert api_module._log_reader_state["stop"] is True

    def test_starting_clears_a_previous_stop(self):
        api_module._log_reader_state["stop"] = True

        with patch.object(api_module.socketio, "start_background_task"):
            api_module._ensure_log_reader()

        assert api_module._log_reader_state["stop"] is False

    def test_fans_each_line_out_to_every_subscriber(self):
        api_module.active_log_streams.update({"sid-a", "sid-b"})

        proc = MagicMock()
        proc.stdout = iter(["hello\n", "world\n"])

        with patch("api.server.subprocess.Popen", return_value=proc), patch.object(
            api_module.socketio, "emit"
        ) as emit, patch.object(api_module.socketio, "sleep", side_effect=stop_after_first_attach):
            api_module._log_reader()

        rooms = [c.kwargs["room"] for c in emit.call_args_list]
        payloads = [c.args[1]["logs"][0] for c in emit.call_args_list if c.args[0] == "logs"]

        assert set(rooms) == {"sid-a", "sid-b"}
        assert payloads == ["hello", "hello", "world", "world"]

    def test_blank_lines_are_not_forwarded(self):
        api_module.active_log_streams.add("sid-a")

        proc = MagicMock()
        proc.stdout = iter(["\n", "   \n", "real\n"])

        with patch("api.server.subprocess.Popen", return_value=proc), patch.object(
            api_module.socketio, "emit"
        ) as emit, patch.object(api_module.socketio, "sleep", side_effect=stop_after_first_attach):
            api_module._log_reader()

        forwarded = [c.args[1]["logs"][0] for c in emit.call_args_list if c.args[0] == "logs"]
        assert forwarded == ["real"]

    def test_reports_and_stops_when_docker_is_absent(self):
        api_module.active_log_streams.add("sid-a")

        with patch("api.server.subprocess.Popen", side_effect=FileNotFoundError), patch.object(
            api_module.socketio, "emit"
        ) as emit:
            api_module._log_reader()

        errors = [c.args[1]["message"] for c in emit.call_args_list if c.args[0] == "error"]
        assert any("Docker" in m for m in errors)
        assert api_module._log_reader_state["running"] is False

    def test_kills_the_follower_process_on_the_way_out(self):
        api_module.active_log_streams.add("sid-a")

        proc = MagicMock()
        proc.stdout = iter([])

        with patch("api.server.subprocess.Popen", return_value=proc), patch.object(
            api_module.socketio, "emit"
        ), patch.object(api_module.socketio, "sleep", side_effect=stop_after_first_attach):
            api_module._log_reader()

        proc.kill.assert_called()


class TestDisconnect:
    def test_removing_an_unknown_session_is_harmless(self):
        """discard, not remove: a disconnect can arrive for a session that was
        already dropped, and that must not raise."""
        api_module.active_log_streams.add("sid-a")

        request = MagicMock()
        request.sid = "never-subscribed"
        with patch("api.server.request", request):
            api_module.handle_disconnect()

        assert api_module.active_log_streams == {"sid-a"}

    def test_removes_the_disconnecting_session(self):
        api_module.active_log_streams.update({"sid-a", "sid-b"})

        request = MagicMock()
        request.sid = "sid-a"
        with patch("api.server.request", request):
            api_module.handle_disconnect()

        assert api_module.active_log_streams == {"sid-b"}
