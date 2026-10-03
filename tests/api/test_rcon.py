"""Tests for the in-process RCON client (api/rcon.py).

These run against a real socket server that speaks the RCON protocol, so the
framing, authentication and multi-packet reassembly are exercised end to end
rather than mocked.
"""

import socket
import struct
import sys
import threading
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.rcon import (  # noqa: E402
    MAX_COMMAND_LENGTH,
    PACKET_TYPE_AUTH_RESPONSE,
    PACKET_TYPE_COMMAND,
    PACKET_TYPE_LOGIN,
    PACKET_TYPE_RESPONSE,
    RconAuthError,
    RconClient,
    RconConnectionError,
    RconError,
    RconNotConfiguredError,
    RconNotSentError,
    RconUnknownOutcomeError,
    _encode_packet,
    execute,
    get_client,
    load_rcon_config,
    reset_client,
)

# Fixture value only. The fake server below compares against this exact
# string; it is not a credential for anything.
TEST_PASSWORD = "fake-rcon-password-for-tests"


def _encode(request_id, packet_type, body):
    return _encode_packet(request_id, packet_type, body)


class _ConnectionDropped(Exception):
    """Raised by _process_packet to end the connection immediately, the same
    way the fake server's earlier single-function _handle used a bare
    ``return`` to simulate a server dying mid-command."""


def _read_packet(sock):
    """Read one framed packet from a socket, for the fake server's use."""
    header = b""
    while len(header) < 4:
        chunk = sock.recv(4 - len(header))
        if not chunk:
            return None
        header += chunk
    (length,) = struct.unpack("<i", header)

    payload = b""
    while len(payload) < length:
        chunk = sock.recv(length - len(payload))
        if not chunk:
            return None
        payload += chunk

    request_id, packet_type = struct.unpack("<ii", payload[:8])
    return request_id, packet_type, payload[8:-2].decode("utf-8", errors="replace")


class FakeRconServer:
    """A minimal RCON server that mirrors Minecraft's behaviour.

    Responses longer than 4096 bytes are split into several packets carrying the
    original request id, exactly as Minecraft's RconClient does, and unknown
    packet types get an "Unknown request" reply so the sentinel works.
    """

    def __init__(
        self,
        password=TEST_PASSWORD,
        responses=None,
        answer_sentinel=True,
        drop_after_command=False,
        strict_ordering=False,
    ):
        self.password = password
        self.responses = responses or {}
        self.answer_sentinel = answer_sentinel
        # Simulates a server that receives a command, may well act on it, then
        # dies before the response is read.
        self.drop_after_command = drop_after_command
        # Enforces the ordering the real bug depended on, deterministically:
        # after a command packet arrives, nothing else from the client
        # should show up until this server has sent its response. Whether a
        # too-early sentinel and the command end up in the same OS-level
        # read (what actually made vanilla drop the connection) is a timing
        # race that doesn't reproduce reliably in a same-machine test setup
        # -- checking arrival order instead of buffer coalescing catches the
        # same client bug without depending on that race. See
        # test_sentinel_is_not_sent_before_the_response_is_read.
        self.strict_ordering = strict_ordering
        self.received_commands = []
        self.connection_count = 0
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(("127.0.0.1", 0))
        self._server.listen(5)
        self.host, self.port = self._server.getsockname()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._serve, daemon=True)

    def start(self):
        self._thread.start()
        return self

    def stop(self):
        self._stop.set()
        try:
            self._server.close()
        except OSError:
            # Already closed, or the accept loop closed it first. Either way
            # the listener is gone, which is what stop() is for.
            pass

    def _serve(self):
        while not self._stop.is_set():
            try:
                conn, _ = self._server.accept()
            except OSError:
                return
            self.connection_count += 1
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def _handle(self, conn):
        if self.strict_ordering:
            self._handle_strict_ordering(conn)
            return

        conn.settimeout(5.0)
        authenticated = False
        try:
            while not self._stop.is_set():
                packet = _read_packet(conn)
                if packet is None:
                    return
                request_id, packet_type, body = packet
                authenticated = self._process_packet(conn, request_id, packet_type, body, authenticated)
        except (OSError, socket.timeout, _ConnectionDropped):
            return
        finally:
            try:
                conn.close()
            except OSError:
                # The peer has usually closed first; nothing left to clean up.
                pass

    def _handle_strict_ordering(self, conn):
        conn.settimeout(5.0)
        authenticated = False
        try:
            while not self._stop.is_set():
                packet = _read_packet(conn)
                if packet is None:
                    return
                request_id, packet_type, body = packet

                if packet_type == PACKET_TYPE_COMMAND and authenticated:
                    # The one thing this mode exists to check: has the
                    # client already sent something else -- the sentinel,
                    # in the bug this guards against -- without waiting to
                    # read this command's response first? A real vanilla
                    # server can't tell "sent early" apart from "arrived in
                    # the same OS-level read as the command"; either way it
                    # drops the connection instead of parsing both, so
                    # treat both as the same violation here.
                    conn.settimeout(0.2)
                    try:
                        sent_early = conn.recv(1, socket.MSG_PEEK)
                    except socket.timeout:
                        sent_early = b""
                    conn.settimeout(5.0)
                    if sent_early:
                        return

                authenticated = self._process_packet(conn, request_id, packet_type, body, authenticated)
        except (OSError, socket.timeout, _ConnectionDropped):
            return
        finally:
            try:
                conn.close()
            except OSError:
                # The client may already have torn the socket down.
                pass

    def _process_packet(self, conn, request_id, packet_type, body, authenticated):
        """Handle one already-parsed packet; returns the (possibly updated) auth state."""
        if packet_type == PACKET_TYPE_LOGIN:
            if body == self.password:
                conn.sendall(_encode(request_id, PACKET_TYPE_AUTH_RESPONSE, ""))
                return True
            # The protocol signals a bad password with id -1.
            conn.sendall(_encode(-1, PACKET_TYPE_AUTH_RESPONSE, ""))
            return False
        if packet_type == PACKET_TYPE_COMMAND and authenticated:
            self.received_commands.append(body)
            if self.drop_after_command:
                raise _ConnectionDropped
            self._send_response(conn, request_id, self.responses.get(body, f"ran: {body}"))
        elif self.answer_sentinel:
            conn.sendall(_encode(request_id, PACKET_TYPE_RESPONSE, "Unknown request 0"))
        return authenticated

    def _send_response(self, conn, request_id, message):
        """Split into 4096-byte packets the way Minecraft does."""
        if not message:
            conn.sendall(_encode(request_id, PACKET_TYPE_RESPONSE, ""))
            return
        while message:
            chunk, message = message[:4096], message[4096:]
            conn.sendall(_encode(request_id, PACKET_TYPE_RESPONSE, chunk))


@pytest.fixture
def rcon_server():
    server = FakeRconServer().start()
    yield server
    server.stop()


@pytest.fixture(autouse=True)
def clean_shared_client():
    """Keep the module singleton from leaking between tests."""
    reset_client()
    yield
    reset_client()


@pytest.mark.unit
class TestPacketEncoding:
    """The length prefix and null terminators must match the protocol exactly."""

    def test_length_field_covers_everything_after_itself(self):
        packet = _encode_packet(7, PACKET_TYPE_COMMAND, "list")
        (length,) = struct.unpack("<i", packet[:4])
        assert length == len(packet) - 4
        assert length == 4 + 4 + len("list") + 2

    def test_fields_round_trip(self):
        packet = _encode_packet(42, PACKET_TYPE_COMMAND, "say hello")
        request_id, packet_type = struct.unpack("<ii", packet[4:12])
        assert request_id == 42
        assert packet_type == PACKET_TYPE_COMMAND
        assert packet.endswith(b"\x00\x00")

    def test_body_is_utf8_encoded(self):
        packet = _encode_packet(1, PACKET_TYPE_COMMAND, "say héllo")
        assert "héllo".encode("utf-8") in packet


@pytest.mark.unit
class TestConfigLoading:
    def test_missing_file_returns_defaults(self, tmp_path):
        settings = load_rcon_config(tmp_path / "absent.conf")
        assert settings == {"host": "localhost", "port": 25575, "password": ""}

    def test_parses_shell_assignments(self, tmp_path):
        config = tmp_path / "rcon.conf"
        config.write_text("# RCON settings\nRCON_HOST=10.0.0.5\nRCON_PORT=25580\nRCON_PASSWORD=example-value\n")
        settings = load_rcon_config(config)
        assert settings == {"host": "10.0.0.5", "port": 25580, "password": "example-value"}

    def test_strips_quotes_and_ignores_comments(self, tmp_path):
        config = tmp_path / "rcon.conf"
        config.write_text('#RCON_PASSWORD=ignored\nRCON_PASSWORD="quoted"\n')
        assert load_rcon_config(config)["password"] == "quoted"

    def test_invalid_port_falls_back_to_default(self, tmp_path):
        config = tmp_path / "rcon.conf"
        config.write_text("RCON_PORT=not-a-number\n")
        assert load_rcon_config(config)["port"] == 25575


@pytest.mark.integration
class TestCommandExecution:
    def test_simple_command_round_trip(self, rcon_server):
        with RconClient(rcon_server.host, rcon_server.port, TEST_PASSWORD) as client:
            assert client.command("list") == "ran: list"
        assert rcon_server.received_commands == ["list"]

    def test_long_response_is_reassembled(self, rcon_server):
        """The old shell fallback truncated at 4096 bytes; this must not."""
        long_body = "x" * 10000
        rcon_server.responses["dump"] = long_body
        with RconClient(rcon_server.host, rcon_server.port, TEST_PASSWORD) as client:
            assert client.command("dump") == long_body

    def test_response_exactly_at_chunk_boundary(self, rcon_server):
        body = "y" * 4096
        rcon_server.responses["edge"] = body
        with RconClient(rcon_server.host, rcon_server.port, TEST_PASSWORD) as client:
            assert client.command("edge") == body

    def test_empty_response_is_handled(self, rcon_server):
        rcon_server.responses["quiet"] = ""
        with RconClient(rcon_server.host, rcon_server.port, TEST_PASSWORD) as client:
            assert client.command("quiet") == ""

    def test_connection_is_reused_across_commands(self, rcon_server):
        """The whole point of the module: one connection, many commands."""
        with RconClient(rcon_server.host, rcon_server.port, TEST_PASSWORD) as client:
            for _ in range(5):
                client.command("list")
        assert rcon_server.connection_count == 1

    def test_batch_runs_in_order(self, rcon_server):
        with RconClient(rcon_server.host, rcon_server.port, TEST_PASSWORD) as client:
            results = client.commands(["one", "two", "three"])
        assert results == ["ran: one", "ran: two", "ran: three"]
        assert rcon_server.received_commands == ["one", "two", "three"]
        assert rcon_server.connection_count == 1

    def test_utf8_response_survives(self, rcon_server):
        rcon_server.responses["motd"] = "Bienvenüe ✦"
        with RconClient(rcon_server.host, rcon_server.port, TEST_PASSWORD) as client:
            assert client.command("motd") == "Bienvenüe ✦"


@pytest.mark.integration
class TestAuthentication:
    def test_wrong_password_raises_auth_error(self, rcon_server):
        client = RconClient(rcon_server.host, rcon_server.port, "wrong-password")
        with pytest.raises(RconAuthError):
            client.connect()
        assert not client.is_connected

    def test_missing_password_raises_not_configured(self, rcon_server):
        client = RconClient(rcon_server.host, rcon_server.port, "")
        with pytest.raises(RconNotConfiguredError):
            client.connect()

    def test_failed_auth_does_not_leak_the_socket(self, rcon_server):
        client = RconClient(rcon_server.host, rcon_server.port, "wrong-password")
        with pytest.raises(RconAuthError):
            client.connect()
        assert client._sock is None


@pytest.mark.integration
class TestConnectionHandling:
    def test_unreachable_server_raises_connection_error(self):
        # Port 1 on localhost refuses connections.
        client = RconClient("127.0.0.1", 1, TEST_PASSWORD, timeout=1.0)
        with pytest.raises(RconConnectionError):
            client.connect()

    def test_connect_is_idempotent(self, rcon_server):
        client = RconClient(rcon_server.host, rcon_server.port, TEST_PASSWORD)
        client.connect()
        client.connect()
        assert rcon_server.connection_count == 1
        client.close()

    def test_close_is_safe_when_never_connected(self):
        RconClient("127.0.0.1", 1, TEST_PASSWORD).close()

    def test_reconnects_after_server_restart(self, rcon_server):
        """A dropped connection must not turn into a failed command."""
        client = RconClient(rcon_server.host, rcon_server.port, TEST_PASSWORD)
        assert client.command("list") == "ran: list"

        # Simulate the container restarting under us.
        client._sock.close()

        assert client.command("list") == "ran: list"
        assert rcon_server.connection_count == 2
        client.close()

    def test_sentinel_timeout_still_returns_the_response(self):
        """Some servers ignore the sentinel; the real response must survive."""
        server = FakeRconServer(answer_sentinel=False).start()
        try:
            client = RconClient(server.host, server.port, TEST_PASSWORD, timeout=1.0)
            assert client.command("list") == "ran: list"
            client.close()
        finally:
            server.stop()

    def test_sentinel_is_not_sent_before_the_response_is_read(self):
        """Regression test for the real bug this class of test used to miss.

        A real vanilla 1.20.4 server drops the connection outright if it
        receives more than one RCON packet in the same OS-level read --
        which is exactly what happens if the sentinel is sent right after
        the command with nothing read in between, and the OS coalesces the
        two writes. The ordinary `rcon_server` fixture can't catch this: it
        pulls exact field sizes across as many recv() calls as it takes, so
        two coalesced packets look identical to two separately-read ones.
        `strict_ordering=True` reproduces the real quirk instead, so a
        `_send_command` that goes back to firing the sentinel before
        reading the command's first response fails here the same way it
        would against a real server.
        """
        server = FakeRconServer(strict_ordering=True).start()
        try:
            with RconClient(server.host, server.port, TEST_PASSWORD) as client:
                assert client.command("list") == "ran: list"
                assert client.command("list") == "ran: list"
        finally:
            server.stop()


@pytest.mark.unit
class TestCommandValidation:
    def test_empty_command_rejected(self, rcon_server):
        client = RconClient(rcon_server.host, rcon_server.port, TEST_PASSWORD)
        with pytest.raises(RconError):
            client.command("   ")

    def test_overlong_command_rejected_before_sending(self, rcon_server):
        """The server would silently truncate these, so fail loudly instead."""
        client = RconClient(rcon_server.host, rcon_server.port, TEST_PASSWORD)
        with pytest.raises(RconError, match="truncated"):
            client.command("a" * (MAX_COMMAND_LENGTH + 1))
        assert rcon_server.received_commands == []

    def test_request_ids_never_reach_the_reserved_value(self, rcon_server):
        client = RconClient(rcon_server.host, rcon_server.port, TEST_PASSWORD)
        client._request_id = 0x3FFFFFFF
        assert client._next_request_id() == 1


@pytest.mark.unit
class TestSharedClient:
    def test_get_client_returns_a_singleton(self):
        assert get_client() is get_client()

    def test_reset_client_forces_a_rebuild(self):
        first = get_client()
        reset_client()
        assert get_client() is not first

    def test_execute_reports_missing_config_as_503(self, monkeypatch):
        """503 is the caller's signal to fall back to the shell script."""
        monkeypatch.setattr("api.rcon.load_rcon_config", lambda *_: {"host": "h", "port": 1, "password": ""})
        stdout, stderr, code = execute("list")
        assert (stdout, code) == (None, 503)
        assert "password" in stderr.lower()

    def test_execute_reports_connection_failure_as_502(self, monkeypatch):
        monkeypatch.setattr(
            "api.rcon.load_rcon_config",
            lambda *_: {"host": "127.0.0.1", "port": 1, "password": TEST_PASSWORD},
        )
        stdout, _, code = execute("list")
        assert (stdout, code) == (None, 502)

    def test_execute_returns_zero_on_success(self, monkeypatch, rcon_server):
        monkeypatch.setattr(
            "api.rcon.load_rcon_config",
            lambda *_: {"host": rcon_server.host, "port": rcon_server.port, "password": TEST_PASSWORD},
        )
        stdout, stderr, code = execute("list")
        assert (stdout, stderr, code) == ("ran: list", None, 0)


@pytest.mark.integration
class TestRetrySafety:
    """Minecraft commands are not idempotent, so a retry must be provably safe.

    Re-sending a `give`, `summon` or `kill` after a lost response would apply
    the effect twice, so only failures that happened before the command reached
    the server may be retried.
    """

    def test_stale_connection_is_retried(self):
        """Nothing was sent, so the same command on a fresh socket is correct."""
        server = FakeRconServer().start()
        try:
            client = RconClient(server.host, server.port, TEST_PASSWORD)
            client.command("say first")
            client._sock.close()

            assert client.command("give Jonah diamond 1") == "ran: give Jonah diamond 1"
            assert server.received_commands == ["say first", "give Jonah diamond 1"]
            client.close()
        finally:
            server.stop()

    def test_lost_response_is_not_retried(self):
        """The server may already have run it, so it must not run again."""
        server = FakeRconServer(drop_after_command=True).start()
        try:
            client = RconClient(server.host, server.port, TEST_PASSWORD, timeout=1.0)
            with pytest.raises(RconUnknownOutcomeError):
                client.command("give Jonah diamond 64")

            assert server.received_commands == ["give Jonah diamond 64"]
            client.close()
        finally:
            server.stop()

    def test_not_sent_error_is_a_connection_error(self):
        """Existing callers that catch RconConnectionError keep working."""
        assert issubclass(RconNotSentError, RconConnectionError)

    def test_unknown_outcome_is_not_a_connection_error(self):
        """It must not be swept up by handlers that retry connection errors."""
        assert not issubclass(RconUnknownOutcomeError, RconConnectionError)

    def test_execute_maps_lost_response_to_500(self, monkeypatch):
        """500 tells run_rcon_command not to re-run it through the shell."""
        server = FakeRconServer(drop_after_command=True).start()
        try:
            monkeypatch.setattr(
                "api.rcon.load_rcon_config",
                lambda *_: {"host": server.host, "port": server.port, "password": TEST_PASSWORD},
            )
            stdout, stderr, code = execute("kill @e")
            assert (stdout, code) == (None, 500)
            assert "sent" in stderr.lower()
        finally:
            server.stop()


@pytest.mark.unit
class TestCredentialReload:
    def test_changed_config_rebuilds_the_client(self, tmp_path, monkeypatch):
        """Rotating the RCON password should not require an API restart."""
        config = tmp_path / "rcon.conf"
        config.write_text("RCON_HOST=localhost\nRCON_PORT=25575\nRCON_PASSWORD=first\n")
        monkeypatch.setattr("api.rcon.RCON_CONFIG_FILE", config)

        first = get_client()
        assert first.password == "first"

        # Timestamps have coarse resolution on some filesystems, so move the
        # mtime explicitly rather than relying on the write being "later".
        config.write_text("RCON_HOST=localhost\nRCON_PORT=25575\nRCON_PASSWORD=second\n")
        import os

        stat = config.stat()
        os.utime(config, (stat.st_atime + 10, stat.st_mtime + 10))

        second = get_client()
        assert second is not first
        assert second.password == "second"

    def test_unchanged_config_keeps_the_same_client(self, tmp_path, monkeypatch):
        config = tmp_path / "rcon.conf"
        config.write_text("RCON_PASSWORD=stable\n")
        monkeypatch.setattr("api.rcon.RCON_CONFIG_FILE", config)

        assert get_client() is get_client()


@pytest.mark.unit
class TestCommandTypeValidation:
    def test_non_string_command_is_rejected(self, rcon_server):
        """The length check calls str methods, so this must fail cleanly."""
        client = RconClient(rcon_server.host, rcon_server.port, TEST_PASSWORD)
        with pytest.raises(RconError, match="string"):
            client.command(42)
        assert rcon_server.received_commands == []

    def test_none_command_is_rejected(self, rcon_server):
        client = RconClient(rcon_server.host, rcon_server.port, TEST_PASSWORD)
        with pytest.raises(RconError):
            client.command(None)


@pytest.mark.api
class TestRunRconCommandFallback:
    """api/server.py falls back to the shell script only when that is safe.

    Minecraft commands are not idempotent, so the fallback must run only when
    the pooled client proved the command never reached the server.
    """

    @pytest.fixture
    def server_module(self):
        import api.server as module

        return module

    def _execute_returning(self, server_module, monkeypatch, code):
        calls = {"script": 0}

        def fake_execute(_command):
            return (None, "failed", code) if code else ("ok", None, 0)

        def fake_run_script(*_args, **_kwargs):
            calls["script"] += 1
            return "from script", None, 0

        monkeypatch.setattr(server_module.rcon, "execute", fake_execute)
        monkeypatch.setattr(server_module, "run_script", fake_run_script)
        result = server_module.run_rcon_command("give Jonah diamond 1")
        return result, calls["script"]

    @pytest.mark.parametrize("code", [502, 503])
    def test_falls_back_when_nothing_was_sent(self, server_module, monkeypatch, code):
        result, script_calls = self._execute_returning(server_module, monkeypatch, code)
        assert script_calls == 1
        assert result[0] == "from script"

    def test_does_not_fall_back_when_the_outcome_is_unknown(self, server_module, monkeypatch):
        """The server may already have run it; running it again would duplicate."""
        result, script_calls = self._execute_returning(server_module, monkeypatch, 500)
        assert script_calls == 0
        assert result[2] == 500

    @pytest.mark.parametrize("code", [400, 401])
    def test_does_not_fall_back_on_rejection(self, server_module, monkeypatch, code):
        result, script_calls = self._execute_returning(server_module, monkeypatch, code)
        assert script_calls == 0
        assert result[2] == code

    def test_success_never_touches_the_script(self, server_module, monkeypatch):
        result, script_calls = self._execute_returning(server_module, monkeypatch, 0)
        assert script_calls == 0
        assert result == ("ok", None, 0)


@pytest.mark.api
class TestCommandEndpointTypeValidation:
    def test_numeric_command_is_a_bad_request_not_a_crash(self, client, mock_api_keys):
        """The sanitizer calls string methods, which raised a 500 before."""
        response = client.post(
            "/api/server/command",
            headers={"X-API-Key": mock_api_keys},
            json={"command": 1},
        )
        assert response.status_code == 400
        assert "string" in response.get_json()["error"].lower()

    def test_object_command_is_a_bad_request(self, client, mock_api_keys):
        response = client.post(
            "/api/server/command",
            headers={"X-API-Key": mock_api_keys},
            json={"command": {"say": "hi"}},
        )
        assert response.status_code == 400
