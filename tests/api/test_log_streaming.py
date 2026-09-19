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


class TestBacklogIsNotReplayed:
    """The follower persists what it reads, so a replayed tail duplicates events.

    Attaching with `--tail 200` meant every API restart and every re-attach
    recorded the same chat, join and death lines again, and the counts climbed
    with each one. New clients still get scrollback from `get_log_tail()` at
    connect time, which does not touch the bus.
    """

    def test_follower_attaches_with_no_backlog(self):
        api_module._log_reader_state["running"] = True

        proc = MagicMock()
        proc.stdout = iter([])

        with patch("api.server.subprocess.Popen", return_value=proc) as popen, patch.object(
            api_module.socketio, "emit"
        ), patch.object(api_module.socketio, "sleep", side_effect=stop_after_first_attach):
            api_module._log_reader()

        command = popen.call_args.args[0]
        assert "--tail" in command
        assert command[command.index("--tail") + 1] == "0"

    def test_reattaching_does_not_republish_old_lines(self):
        """Two attaches in a row must publish each line exactly once."""
        api_module._log_reader_state["running"] = True

        attaches = []

        def make_proc(*_args, **_kwargs):
            proc = MagicMock()
            # A replaying tail would hand back the same line on every attach.
            proc.stdout = iter(["[16:04:23] [Server thread/INFO]: Jonah joined the game\n"])
            attaches.append(proc)
            return proc

        def stop_on_second_attach(*_args, **_kwargs):
            if len(attaches) >= 2:
                api_module._log_reader_state["stop"] = True

        with patch("api.server.subprocess.Popen", side_effect=make_proc), patch.object(
            api_module, "_publish_log_line"
        ) as publish, patch.object(api_module.socketio, "emit"), patch.object(
            api_module.socketio, "sleep", side_effect=stop_on_second_attach
        ):
            api_module._log_reader()

        # Two attaches, one line each, because neither replays a backlog.
        assert publish.call_count == len(attaches)

    def test_connecting_client_still_receives_scrollback(self):
        """Dropping the follower's tail must not cost the UI its history."""
        api_module.API_KEYS["scrollback-key"] = {"enabled": True, "role": "admin"}
        request = MagicMock()
        request.sid = "sid-scrollback"

        try:
            with patch("api.server.request", request), patch.object(
                api_module, "get_log_tail", return_value=["old line"]
            ) as tail, patch.object(api_module.socketio, "emit") as emit, patch.object(
                api_module, "_ensure_log_reader"
            ):
                api_module.handle_connect({"api_key": "scrollback-key"})

            tail.assert_called_once()
            initial = [c.args[1] for c in emit.call_args_list if c.args[0] == "logs"]
            assert initial and initial[0]["type"] == "initial"
            assert initial[0]["logs"] == ["old line"]
        finally:
            api_module.API_KEYS.pop("scrollback-key", None)
            api_module.active_log_streams.discard("sid-scrollback")


class TestStoppingTheReader:
    def test_stop_kills_the_running_process(self):
        """A quiet server blocks in the read, so the flag alone cannot stop it."""
        proc = MagicMock()
        api_module._log_reader_state["proc"] = proc

        try:
            api_module.stop_log_reader()
            assert api_module._log_reader_state["stop"] is True
            proc.kill.assert_called_once()
        finally:
            api_module._log_reader_state["proc"] = None

    def test_stop_is_safe_when_no_process_is_running(self):
        api_module._log_reader_state["proc"] = None
        api_module.stop_log_reader()
        assert api_module._log_reader_state["stop"] is True

    def test_stop_survives_a_process_that_already_exited(self):
        proc = MagicMock()
        proc.kill.side_effect = ProcessLookupError
        api_module._log_reader_state["proc"] = proc

        try:
            api_module.stop_log_reader()
            assert api_module._log_reader_state["stop"] is True
        finally:
            api_module._log_reader_state["proc"] = None

    def test_process_reference_is_cleared_when_the_reader_exits(self):
        api_module._log_reader_state["running"] = True

        proc = MagicMock()
        proc.stdout = iter([])

        with patch("api.server.subprocess.Popen", return_value=proc), patch.object(
            api_module.socketio, "emit"
        ), patch.object(api_module.socketio, "sleep", side_effect=stop_after_first_attach):
            api_module._log_reader()

        assert api_module._log_reader_state["proc"] is None


class TestCommandInputValidation:
    """A truthy non-string command raised inside the sanitizer, which sits
    outside the handler's try block, so the client got no error at all."""

    def _emit_for(self, payload, permissions=("server.command",), enabled=True):
        request = MagicMock()
        request.sid = "sid-a"
        # The handler re-reads the scope of the key that opened the connection,
        # so register one with the command permission; these cases are about
        # what the sanitizer does with a bad payload, not about authorisation.
        stream_key = "stream-test-key"
        api_module.API_KEYS[stream_key] = {
            "name": "stream",
            "enabled": enabled,
            "permissions": list(permissions),
        }
        api_module._stream_keys["sid-a"] = stream_key
        try:
            with patch("api.server.request", request), patch.object(api_module.socketio, "emit") as emit, patch.object(
                api_module, "run_rcon_command"
            ) as run:
                api_module.handle_execute_command(payload)
        finally:
            api_module._stream_keys.pop("sid-a", None)
            api_module.API_KEYS.pop(stream_key, None)
        return emit, run

    def test_a_disabled_key_cannot_run_commands_on_an_open_socket(self):
        """Disabling a key has to reach the sockets it already opened"""
        emit, run = self._emit_for({"command": "say hi"}, enabled=False)

        errors = [c.args[1]["message"] for c in emit.call_args_list if c.args[0] == "command_error"]
        assert errors and "server.command" in errors[0]
        run.assert_not_called()

    def test_a_revoked_key_cannot_run_commands_on_an_open_socket(self):
        """A key deleted mid-connection loses the socket it was holding"""
        request = MagicMock()
        request.sid = "sid-gone"
        api_module._stream_keys["sid-gone"] = "deleted-key"
        try:
            with patch("api.server.request", request), patch.object(api_module.socketio, "emit") as emit, patch.object(
                api_module, "run_rcon_command"
            ) as run:
                api_module.handle_execute_command({"command": "say hi"})
        finally:
            api_module._stream_keys.pop("sid-gone", None)

        assert any(c.args[0] == "command_error" for c in emit.call_args_list)
        run.assert_not_called()

    def test_a_key_without_server_command_cannot_run_commands(self):
        emit, run = self._emit_for({"command": "say hi"}, permissions=("logs.view",))

        errors = [c.args[1]["message"] for c in emit.call_args_list if c.args[0] == "command_error"]
        assert errors and "server.command" in errors[0]
        run.assert_not_called()

    def test_numeric_command_returns_an_error(self):
        emit, run = self._emit_for({"command": 1})

        errors = [c.args[1]["message"] for c in emit.call_args_list if c.args[0] == "command_error"]
        assert errors and "string" in errors[0].lower()
        run.assert_not_called()

    def test_list_command_returns_an_error(self):
        emit, run = self._emit_for({"command": ["say", "hi"]})

        assert any(c.args[0] == "command_error" for c in emit.call_args_list)
        run.assert_not_called()

    def test_missing_command_still_returns_an_error(self):
        emit, run = self._emit_for({})

        assert any(c.args[0] == "command_error" for c in emit.call_args_list)
        run.assert_not_called()
