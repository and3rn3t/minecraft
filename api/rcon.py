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


class RconNotSentError(RconConnectionError):
    """Raised when a command failed before any of it reached the server.

    Safe to retry: the server never saw it. This is the ordinary case of a
    pooled connection that went stale while idle, where the first write fails
    with a broken pipe or a reset.
    """


class RconUnknownOutcomeError(RconError):
    """Raised when a command reached the server but its result was not read.

    Must not be retried. The server may well have run it, so repeating a
    ``give``, ``summon``, ``kill`` or ``stop`` would apply the effect twice.
    """


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

        Retries exactly once, and only when the command provably never left
        this process. Minecraft commands are not idempotent: re-sending a
        ``give`` or a ``summon`` after a lost response would apply it twice, so
        a failure that happens after the command reached the server is reported
        as :class:`RconUnknownOutcomeError` rather than retried.

        The retry therefore covers the one case that is both common and safe: a
        pooled connection that went stale while idle, where the first write
        fails before any bytes reach the server.
        """
        if not isinstance(command, str):
            raise RconError("Command must be a string")
        command = command.strip()
        if not command:
            raise RconError("Command must not be empty")
        if len(command.encode("utf-8")) > MAX_COMMAND_LENGTH:
            raise RconError(f"Command exceeds {MAX_COMMAND_LENGTH} bytes and would be truncated by the server")

        with self._lock:
            self.connect()
            try:
                return self._send_command(command)
            except RconNotSentError:
                # Nothing reached the server, so a fresh connection can safely
                # carry the same command.
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
        length up front. A sentinel packet is sent to find the end of the real
        response; the server answers it with a recognisable "Unknown request"
        reply once every prior packet has actually been delivered.

        The sentinel is sent only *after* the command's first response packet
        has been read, not immediately after the command itself. Verified
        empirically against a real vanilla 1.20.4 server (the fake server in
        tests/api/test_rcon.py does not reproduce this): two ``sendall()``
        calls back to back, with nothing read in between, can be coalesced by
        the OS into a single write, and vanilla's own packet reader cannot
        handle two framed packets arriving in one read -- it drops the
        connection instead of parsing both, deterministically, every time.
        Reading the command's response before sending the sentinel forces a
        real round trip between the two writes, which is what actually
        prevents the coalescing; an arbitrary delay would too, but is a
        magic number chasing a timing assumption instead of a guarantee.
        """
        sock = self._sock
        if sock is None:
            raise RconNotSentError("Not connected")

        request_id = self._next_request_id()
        sentinel_id = self._next_request_id()

        try:
            sock.sendall(_encode_packet(request_id, PACKET_TYPE_COMMAND, command))
        except OSError as exc:
            # A command packet is well under one segment, so a stale socket
            # fails here with nothing delivered. This is the retryable case.
            raise RconNotSentError(f"Could not send command: {exc}") from exc

        # Past this point the server has the command. Every failure below leaves
        # the outcome unknown and must not be retried.
        parts: list[str] = []
        try:
            response_id, _, body = _read_packet(sock)
        except socket.timeout:
            raise RconUnknownOutcomeError("Command was sent but no response arrived") from None
        except (OSError, RconConnectionError) as exc:
            raise RconUnknownOutcomeError(f"Command was sent but the response was lost: {exc}") from exc
        if response_id == request_id:
            parts.append(body)

        try:
            sock.sendall(_encode_packet(sentinel_id, PACKET_TYPE_RESPONSE, ""))
        except OSError as exc:
            raise RconUnknownOutcomeError(f"Command was sent but the connection failed: {exc}") from exc

        while True:
            try:
                response_id, _, body = _read_packet(sock)
            except socket.timeout:
                # Some server builds ignore the sentinel. Anything already
                # received is the real response, so return it rather than
                # failing the command.
                if parts:
                    break
                raise RconUnknownOutcomeError("Command was sent but no response arrived") from None
            except (OSError, RconConnectionError) as exc:
                raise RconUnknownOutcomeError(f"Command was sent but the response was lost: {exc}") from exc

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
        # The connection is being discarded either way. A socket that is
        # already closed, reset, or whose fd is gone raises here, and there is
        # nothing useful left to do about it.
        pass


# Module-level shared client. Built lazily so importing this module never
# touches the network or the config file.
_client: Optional[RconClient] = None
_client_config_mtime: Optional[float] = None
_client_lock = threading.Lock()


def _config_mtime() -> Optional[float]:
    """Last-modified time of the RCON config, or None if it is absent."""
    try:
        return RCON_CONFIG_FILE.stat().st_mtime
    except OSError:
        return None


def get_client(timeout: float = DEFAULT_TIMEOUT) -> RconClient:
    """Return the shared client, creating it from config on first use.

    The config file is re-read when it changes on disk, so rotating the RCON
    password with ``scripts/rcon-setup.sh`` takes effect without restarting the
    API.
    """
    global _client, _client_config_mtime
    with _client_lock:
        mtime = _config_mtime()
        if _client is not None and mtime != _client_config_mtime:
            _client.close()
            _client = None

        if _client is None:
            settings = load_rcon_config()
            _client = RconClient(
                host=settings["host"],
                port=settings["port"],
                password=settings["password"],
                timeout=timeout,
            )
            _client_config_mtime = mtime
        return _client


def reset_client() -> None:
    """Drop the shared client so the next call re-reads config.

    Used by tests, and available for forcing a reconnect.
    """
    global _client, _client_config_mtime
    with _client_lock:
        if _client is not None:
            _client.close()
        _client = None
        _client_config_mtime = None


def execute(command: str) -> tuple[Optional[str], Optional[str], int]:
    """Run a command, returning ``(stdout, stderr, returncode)``.

    Matches the shape of ``run_script`` in ``api/server.py`` so call sites can
    use either path.

    The code tells the caller whether retrying elsewhere is safe:

    * ``503`` — not configured, nothing was sent. Falling back to
      ``scripts/rcon-client.sh`` is safe, and worthwhile because that script can
      also reach ``rcon-cli`` inside the container.
    * ``502`` — could not reach the server, nothing was sent. Fallback is safe.
    * ``500`` — the command reached the server but its result was lost. The
      outcome is unknown, so it must **not** be run again by any other path.
    * ``401`` / ``400`` — rejected. Retrying repeats the same failure.
    """
    try:
        return get_client().command(command), None, 0
    except RconNotConfiguredError as exc:
        return None, str(exc), 503
    except RconAuthError as exc:
        return None, str(exc), 401
    except RconUnknownOutcomeError as exc:
        return None, str(exc), 500
    except RconConnectionError as exc:
        return None, str(exc), 502
    except RconError as exc:
        return None, str(exc), 400


if __name__ == "__main__":
    # A thin CLI so scripts/rcon-client.sh can shell out to the one correct
    # RCON implementation instead of re-encoding the wire protocol itself.
    # It used to: see this module's own docstring for the bugs that approach
    # had (no length-prefix framing, auth-failure detection that only
    # triggered on a suspiciously short reply instead of checking the
    # protocol's own -1 request id).
    import sys

    if len(sys.argv) < 2:
        print("Usage: rcon.py <command> [args...]", file=sys.stderr)
        sys.exit(1)

    out, err, returncode = execute(" ".join(sys.argv[1:]))
    if out:
        print(out)
    if returncode != 0:
        print(err or f"RCON returned {returncode}", file=sys.stderr)
    sys.exit(0 if returncode == 0 else 1)
