"""
The WebSocket handlers: who may open the log/console stream, and what running
a command over it does.

Flask-SocketIO's test client can't run against this Flask version (it assigns
RequestContext.session, which Flask 3.1 made read-only), so these call the
handlers directly with request.sid mocked, as test_log_streaming.py does.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import api.server as api_module  # noqa: E402
import api.realtime as realtime  # noqa: E402
import api.auth_crypto as auth_crypto  # noqa: E402

pytestmark = pytest.mark.skipif(
    not api_module.SOCKETIO_AVAILABLE,
    reason="Flask-SocketIO not installed, so websocket handlers are not available",
)

SID = "sid-under-test"


@pytest.fixture
def socket(monkeypatch):
    """Stubs for everything a handler reaches outside itself.

    Yields the emit mock; `socket.disconnect` and `socket.rcon` are the others.
    """
    request = MagicMock()
    request.sid = SID
    request.remote_addr = "10.0.0.9"  # the audit log writes it as JSON
    with (
        patch("api.realtime.request", request), patch("api.server.request", request),
        patch.object(api_module.socketio, "emit") as emit,
        patch.object(realtime, "disconnect") as disconnect,
        patch.object(realtime, "get_log_tail", return_value=["[12:00] Done"]),
        patch.object(realtime, "ensure_log_reader"),
        patch.object(api_module, "run_rcon_command", return_value=("There are 0 players", "", 0)) as rcon,
    ):
        emit.disconnect = disconnect
        emit.rcon = rcon
        yield emit
    realtime._stream_keys.pop(SID, None)
    realtime.active_log_streams.discard(SID)


@pytest.fixture
def key(monkeypatch):
    def make(role="admin", enabled=True, name="dash", **extra):
        value = f"ws-{role}-{name}"
        monkeypatch.setitem(api_module.API_KEYS, value, {"name": name, "enabled": enabled, "role": role, **extra})
        return value

    return make


def _events(emit, name):
    return [c.args[1] for c in emit.call_args_list if c.args[0] == name]


class TestConnect:
    def _refused(self, socket, auth, message):
        accepted = realtime.handle_connect(auth)
        assert accepted is False
        assert _events(socket, "error") == [{"message": message}]
        socket.disconnect.assert_called_once_with(SID)
        assert SID not in realtime.active_log_streams

    def test_needs_a_key_or_token(self, socket):
        self._refused(socket, None, "API key or token required")

    def test_an_unknown_key_is_refused(self, socket):
        self._refused(socket, {"api_key": "nope"}, "Invalid API key")

    def test_a_disabled_key_is_refused(self, socket, key):
        self._refused(socket, {"api_key": key(enabled=False)}, "API key disabled")

    def test_a_key_without_logs_view_is_refused(self, socket, key):
        self._refused(socket, {"api_key": key(permissions=["server.view"])}, "Permission denied: logs.view")

    def test_an_invalid_token_is_refused(self, socket):
        with patch.object(auth_crypto, "verify_token", return_value=None):
            self._refused(socket, {"token": "bad"}, "Invalid or expired token")

    def test_a_disabled_user_is_refused(self, socket, monkeypatch):
        monkeypatch.setitem(api_module.USERS, "gone", {"username": "gone", "role": "admin", "enabled": False})
        with patch.object(auth_crypto, "verify_token", return_value="gone"):
            self._refused(socket, {"token": "t"}, "Account disabled")

    def test_a_valid_key_gets_the_backlog_then_the_live_stream(self, socket, key):
        accepted = realtime.handle_connect({"api_key": key()})
        assert accepted is True

        assert _events(socket, "logs") == [{"logs": ["[12:00] Done"], "type": "initial"}]
        assert _events(socket, "connected")
        assert SID in realtime.active_log_streams
        socket.disconnect.assert_not_called()

    def test_a_signed_in_user_can_connect_with_their_token(self, socket, monkeypatch):
        monkeypatch.setitem(api_module.USERS, "alice", {"username": "alice", "role": "user", "enabled": True})
        with patch.object(auth_crypto, "verify_token", return_value="alice"):
            accepted = realtime.handle_connect({"token": "t"})
            assert accepted is True
        assert realtime._stream_keys[SID] == ("user", "alice")

    def test_disconnecting_forgets_the_socket(self, socket, key):
        realtime.handle_connect({"api_key": key()})

        realtime.handle_disconnect()

        assert SID not in realtime.active_log_streams
        assert SID not in realtime._stream_keys


class TestRequestLogs:
    def test_sends_the_requested_tail(self, socket, key):
        realtime.handle_connect({"api_key": key()})
        socket.reset_mock()

        with patch.object(realtime, "get_log_tail", return_value=["a", "b"]) as tail:
            realtime.handle_request_logs({"lines": 2})

        tail.assert_called_once_with(2)
        assert _events(socket, "logs") == [{"logs": ["a", "b"], "type": "request"}]


class TestExecuteCommand:
    @pytest.fixture
    def audit(self, tmp_path, monkeypatch):
        path = tmp_path / "audit.log"
        monkeypatch.setattr(api_module, "AUDIT_LOG_FILE", path)
        return lambda: [json.loads(line) for line in path.read_text().splitlines()]

    def _connect(self, key_value):
        realtime._stream_keys[SID] = ("api_key", key_value)

    def test_runs_the_command_and_returns_the_response(self, socket, key):
        self._connect(key())

        realtime.handle_execute_command({"command": "list"})

        socket.rcon.assert_called_once_with("list")
        assert _events(socket, "command_response") == [
            {"command": "list", "response": "There are 0 players", "success": True}
        ]

    def test_a_failed_command_is_reported_as_such(self, socket, key):
        self._connect(key())
        socket.rcon.return_value = ("", "Unknown command", 1)

        realtime.handle_execute_command({"command": "list"})

        assert _events(socket, "command_response") == [
            {"command": "list", "response": "Unknown command", "success": False}
        ]

    def test_an_exception_becomes_a_command_error(self, socket, key):
        self._connect(key())
        socket.rcon.side_effect = ConnectionError("RCON down")

        realtime.handle_execute_command({"command": "list"})

        assert _events(socket, "command_error") == [{"message": "Failed to execute command", "command": "list"}]

    def test_a_key_without_server_command_cannot_run_anything(self, socket, key):
        self._connect(key(role="user"))

        realtime.handle_execute_command({"command": "list"})

        socket.rcon.assert_not_called()
        assert _events(socket, "command_error") == [{"message": "Permission denied: server.command"}]

    def test_the_audit_log_names_the_key_that_ran_it(self, socket, key, audit):
        """Every socket command used to be recorded as "__api_key__"."""
        self._connect(key(name="phone-shortcut"))

        realtime.handle_execute_command({"command": "say hi"})

        assert audit()[-1]["username"] == "api_key:phone-shortcut"
        assert audit()[-1]["action"] == "server.command"

    def test_the_audit_log_names_the_user_that_ran_it(self, socket, audit, monkeypatch):
        monkeypatch.setitem(api_module.USERS, "boss", {"username": "boss", "role": "admin", "enabled": True})
        realtime._stream_keys[SID] = ("user", "boss")

        realtime.handle_execute_command({"command": "say hi; reboot"})

        socket.rcon.assert_not_called()
        assert audit()[-1] == {**audit()[-1], "username": "boss", "action": "server.command.rejected"}
