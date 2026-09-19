#!/usr/bin/env python3
"""In-process RCON client for the Minecraft server.

Replaces the per-command ``subprocess`` shell-out to ``scripts/rcon-client.sh``.
That path opened a fresh TCP connection and re-authenticated for every single
command, which costs roughly 50-100ms each and makes command batches
impractical. It also read a single 4096-byte chunk without length framing, so
long responses were truncated or split across reads, and it treated any reply
of four or more bytes as a successful login instead of checking for the
``-1`` request id the protocol uses to signal auth failure.

This module keeps one authenticated connection open, frames packets properly,
reassembles multi-packet responses, and reconnects transparently when the
server restarts underneath it.

Protocol reference: the Source RCON protocol as implemented by Minecraft's
``RconClient``. Responses longer than 4096 bytes are split by the server into
several packets that all carry the original request id, so a sentinel packet is
used to detect the end of a response.
"""

from __future__ import annotations

import socket
import struct
import threading
from pathlib import Path
from typing import Iterable, Optional

PROJECT_ROOT = Path(__file__).parent.parent
RCON_CONFIG_FILE = PROJECT_ROOT / "config" / "rcon.conf"

# Packet types from the Source RCON protocol
PACKET_TYPE_RESPONSE = 0
PACKET_TYPE_COMMAND = 2
PACKET_TYPE_LOGIN = 3
PACKET_TYPE_AUTH_RESPONSE = 2

# A packet is at minimum two int32 fields plus the two terminating nulls.
MIN_PACKET_LENGTH = 10
# Generous ceiling so a malformed length field cannot force a huge allocation.
MAX_PACKET_LENGTH = 64 * 1024
# Minecraft's inbound RCON buffer is 1460 bytes; longer commands are silently
# truncated by the server, so reject them here where the caller can see why.
MAX_COMMAND_LENGTH = 1400

DEFAULT_HOST = "localhost"
DEFAULT_PORT = 25575
DEFAULT_TIMEOUT = 5.0


class RconError(Exception):
    """Base class for every RCON failure."""


class RconNotConfiguredError(RconError):
    """Raised when no RCON password is available.

    Callers treat this as "fall back to the shell script" rather than as a hard
    failure, because the script can also reach ``rcon-cli`` inside the container.
    """


class RconAuthError(RconError):
    """Raised when the server rejects the RCON password."""


class RconConnectionError(RconError):
    """Raised when the socket cannot be established or is lost mid-command."""


def load_rcon_config(config_file: Optional[Path] = None) -> dict:
    """Read ``config/rcon.conf`` into a dict of connection settings.

    The file is written by ``scripts/rcon-setup.sh`` as plain ``KEY=value``
    shell assignments. Missing files yield defaults with an empty password,
    which callers detect via :class:`RconNotConfiguredError`.
    """
    path = config_file if config_file is not None else RCON_CONFIG_FILE
    settings = {"host": DEFAULT_HOST, "port": DEFAULT_PORT, "password": ""}

    if not path.exists():
        return settings

    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return settings

    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        # Shell config files may quote values; RCON passwords are generated
        # without quotes but tolerate both forms.
        value = value.strip().strip("\"'")

        if key == "RCON_HOST":
            settings["host"] = value or DEFAULT_HOST
        elif key == "RCON_PORT":
            try:
                settings["port"] = int(value)
            except ValueError:
                settings["port"] = DEFAULT_PORT
        elif key == "RCON_PASSWORD":
            settings["password"] = value

    return settings


def _encode_packet(request_id: int, packet_type: int, body: str) -> bytes:
    """Build one RCON packet, including its leading length field."""
    payload = struct.pack("<ii", request_id, packet_type) + body.encode("utf-8") + b"\x00\x00"
    return struct.pack("<i", len(payload)) + payload


def _recv_exactly(sock: socket.socket, count: int) -> bytes:
    """Read exactly ``count`` bytes, looping until the buffer is full.

    A bare ``recv`` returns whatever happens to have arrived, which is what made
    the previous implementation lose the tail of long responses.
    """
    chunks = []
    remaining = count
    while remaining > 0:
        chunk = sock.recv(remaining)
        if not chunk:
            raise RconConnectionError("Connection closed by server")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _read_packet(sock: socket.socket) -> tuple[int, int, str]:
    """Read one framed packet and return ``(request_id, packet_type, body)``."""
    (length,) = struct.unpack("<i", _recv_exactly(sock, 4))
    if length < MIN_PACKET_LENGTH or length > MAX_PACKET_LENGTH:
        raise RconConnectionError(f"Malformed RCON packet length: {length}")

    payload = _recv_exactly(sock, length)
    request_id, packet_type = struct.unpack("<ii", payload[:8])
    # Drop the two trailing null terminators. Bodies are UTF-8; replace rather
    # than raise so one odd character cannot break an otherwise good response.
    body = payload[8:-2].decode("utf-8", errors="replace")
    return request_id, packet_type, body


class RconClient:
    """A persistent, thread-safe RCON connection.

    One connection is shared by all callers and guarded by a lock, so commands
    are serialised rather than racing for the socket. If the connection has been
    dropped, typically because the Minecraft container restarted, the next
    command reconnects and retries once.
    """

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        password: str = "",
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self.host = host
        self.port = port
        self.password = password
        self.timeout = timeout
        self._sock: Optional[socket.socket] = None
        self._request_id = 0
        self._lock = threading.RLock()

    @property
    def is_connected(self) -> bool:
        """Whether a socket is currently open and authenticated."""
        return self._sock is not None

    def _next_request_id(self) -> int:
        """Return a fresh request id, wrapping well below int32 limits.

        ``-1`` is reserved by the protocol to signal auth failure, so ids stay
        positive.
        """
        self._request_id = (self._request_id % 0x3FFFFFFF) + 1
        return self._request_id

    def connect(self) -> None:
        """Open the socket and authenticate. Safe to call when already open."""
        with self._lock:
            if self._sock is not None:
                return
            if not self.password:
                raise RconNotConfiguredError("No RCON password configured; run scripts/rcon-setup.sh")

            try:
                sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
            except OSError as exc:
                raise RconConnectionError(f"Cannot connect to RCON at {self.host}:{self.port}: {exc}") from exc

            sock.settimeout(self.timeout)
            try:
                self._authenticate(sock)
            except Exception:
                _close_quietly(sock)
                raise

            self._sock = sock

    def _authenticate(self, sock: socket.socket) -> None:
        """Send the login packet and verify the server accepted it.

        The server may emit an empty RESPONSE_VALUE packet before the auth
        response, so packets are read until the auth response arrives. A request
        id of ``-1`` means the password was wrong.
        """
        request_id = self._next_request_id()
        sock.sendall(_encode_packet(request_id, PACKET_TYPE_LOGIN, self.password))

        for _ in range(3):
            try:
                response_id, packet_type, _ = _read_packet(sock)
            except socket.timeout as exc:
                raise RconConnectionError("Timed out waiting for RCON auth response") from exc

            if response_id == -1:
                raise RconAuthError("RCON authentication failed: incorrect password")
            if packet_type == PACKET_TYPE_AUTH_RESPONSE and response_id == request_id:
                return

        raise RconConnectionError("Did not receive a usable RCON auth response")

    def close(self) -> None:
        """Close the connection if one is open."""
        with self._lock:
            if self._sock is not None:
                _close_quietly(self._sock)
                self._sock = None

    def command(self, command: str) -> str:
        """Run one command and return the server's response text.

        Reconnects and retries once if the connection was dropped while idle,
        which is the normal case after a server restart.
        """
        command = (command or "").strip()
        if not command:
            raise RconError("Command must not be empty")
        if len(command.encode("utf-8")) > MAX_COMMAND_LENGTH:
            raise RconError(f"Command exceeds {MAX_COMMAND_LENGTH} bytes and would be truncated by the server")

        with self._lock:
            self.connect()
            try:
                return self._send_command(command)
            except (RconConnectionError, OSError):
                # The socket was probably closed by a server restart. Drop it
                # and try once more on a fresh connection.
                self.close()
                self.connect()
                return self._send_command(command)

    def commands(self, commands: Iterable[str]) -> list[str]:
        """Run several commands over the one connection, in order.

        The lock is held for the whole batch so nothing interleaves between
        commands that are meant to run as a unit.
        """
        with self._lock:
            return [self.command(command) for command in commands]

    def _send_command(self, command: str) -> str:
        """Send a command and reassemble a possibly multi-packet response.

        Minecraft splits responses longer than 4096 bytes into several packets
        that all carry the command's request id, and the protocol gives no
        length up front. A second packet with an unused type is sent straight
        after the command; the server answers it with a recognisable "Unknown
        request" reply, which marks the end of the real response.
        """
        sock = self._sock
        if sock is None:
            raise RconConnectionError("Not connected")

        request_id = self._next_request_id()
        sentinel_id = self._next_request_id()

        sock.sendall(_encode_packet(request_id, PACKET_TYPE_COMMAND, command))
        sock.sendall(_encode_packet(sentinel_id, PACKET_TYPE_RESPONSE, ""))

        parts: list[str] = []
        while True:
            try:
                response_id, _, body = _read_packet(sock)
            except socket.timeout:
                # Some server builds ignore the sentinel. Anything already
                # received is the real response, so return it rather than
                # failing the command.
                if parts:
                    break
                raise RconConnectionError("Timed out waiting for RCON response") from None

            if response_id == sentinel_id:
                break
            if response_id == request_id:
                parts.append(body)

        return "".join(parts)

    def __enter__(self) -> "RconClient":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()


def _close_quietly(sock: socket.socket) -> None:
    """Close a socket, ignoring errors from an already-dead connection."""
    try:
        sock.close()
    except OSError:
        pass


# Module-level shared client. Built lazily so importing this module never
# touches the network or the config file.
_client: Optional[RconClient] = None
_client_lock = threading.Lock()


def get_client(timeout: float = DEFAULT_TIMEOUT) -> RconClient:
    """Return the shared client, creating it from config on first use."""
    global _client
    with _client_lock:
        if _client is None:
            settings = load_rcon_config()
            _client = RconClient(
                host=settings["host"],
                port=settings["port"],
                password=settings["password"],
                timeout=timeout,
            )
        return _client


def reset_client() -> None:
    """Drop the shared client so the next call re-reads config.

    Used by tests and after the RCON password is rotated.
    """
    global _client
    with _client_lock:
        if _client is not None:
            _client.close()
        _client = None


def execute(command: str) -> tuple[Optional[str], Optional[str], int]:
    """Run a command, returning ``(stdout, stderr, returncode)``.

    Matches the shape of ``run_script`` in ``api/server.py`` so call sites can
    use either path. A return code of ``503`` means RCON is not configured and
    the caller should fall back to ``scripts/rcon-client.sh``, which can also
    reach ``rcon-cli`` inside the container.
    """
    try:
        return get_client().command(command), None, 0
    except RconNotConfiguredError as exc:
        return None, str(exc), 503
    except RconAuthError as exc:
        return None, str(exc), 401
    except RconConnectionError as exc:
        return None, str(exc), 502
    except RconError as exc:
        return None, str(exc), 400
