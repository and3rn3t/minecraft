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

    def __init__(self, password=TEST_PASSWORD, responses=None, answer_sentinel=True):
        self.password = password
        self.responses = responses or {}
        self.answer_sentinel = answer_sentinel
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
        conn.settimeout(5.0)
        authenticated = False
        try:
            while not self._stop.is_set():
                packet = _read_packet(conn)
                if packet is None:
                    return
                request_id, packet_type, body = packet

                if packet_type == PACKET_TYPE_LOGIN:
                    if body == self.password:
                        authenticated = True
                        conn.sendall(_encode(request_id, PACKET_TYPE_AUTH_RESPONSE, ""))
                    else:
                        # The protocol signals a bad password with id -1.
                        conn.sendall(_encode(-1, PACKET_TYPE_AUTH_RESPONSE, ""))
                elif packet_type == PACKET_TYPE_COMMAND and authenticated:
                    self.received_commands.append(body)
                    self._send_response(conn, request_id, self.responses.get(body, f"ran: {body}"))
                elif self.answer_sentinel:
                    conn.sendall(_encode(request_id, PACKET_TYPE_RESPONSE, "Unknown request 0"))
        except (OSError, socket.timeout):
            return
        finally:
            try:
                conn.close()
            except OSError:
                pass

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
