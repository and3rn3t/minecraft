#!/usr/bin/env python3
"""Print how many players are online, using the server list ping.

This is the same status request the multiplayer screen sends, so it needs no
RCON password and works on every server type. It exists so the update scripts
can ask "is anyone playing?" before restarting the server.

Exit status: 0 with the count on stdout, or 1 when the server did not answer
(stopped, still starting, or not reachable).
"""

import json
import os
import socket
import struct
import sys

DEFAULT_TIMEOUT = 5.0


def _varint(value: int) -> bytes:
    """Encode an int as a Minecraft protocol VarInt."""
    value &= 0xFFFFFFFF
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def _read_exact(sock: socket.socket, length: int) -> bytes:
    """Read exactly `length` bytes or raise ConnectionError."""
    data = bytearray()
    while len(data) < length:
        chunk = sock.recv(length - len(data))
        if not chunk:
            raise ConnectionError("connection closed mid-packet")
        data.extend(chunk)
    return bytes(data)


def _read_varint(sock: socket.socket) -> int:
    """Read one VarInt from the socket."""
    result = 0
    for shift in range(0, 35, 7):
        byte = _read_exact(sock, 1)[0]
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result
    raise ValueError("VarInt too long")


def _packet(packet_id: int, payload: bytes) -> bytes:
    """Frame a packet: length, id, payload."""
    body = _varint(packet_id) + payload
    return _varint(len(body)) + body


def query_status(host: str, port: int, timeout: float = DEFAULT_TIMEOUT) -> dict:
    """Return the server's status response as a dict."""
    with socket.create_connection((host, port), timeout=timeout) as sock:
        host_bytes = host.encode("utf-8")
        # Handshake: protocol version -1 (any), address, port, next state 1 (status)
        handshake = _varint(-1) + _varint(len(host_bytes)) + host_bytes + struct.pack(">H", port) + _varint(1)
        sock.sendall(_packet(0x00, handshake))
        sock.sendall(_packet(0x00, b""))  # status request

        _read_varint(sock)  # packet length
        if _read_varint(sock) != 0x00:
            raise ValueError("unexpected packet id in status response")
        length = _read_varint(sock)
        return json.loads(_read_exact(sock, length).decode("utf-8"))


def main() -> int:
    """Print the online player count, or exit 1 if the server did not answer."""
    host = os.environ.get("SERVER_HOST", "127.0.0.1")
    try:
        port = int(os.environ.get("SERVER_PORT", "25565"))
    except ValueError:
        port = 25565
    try:
        status = query_status(host, port)
        print(int(status["players"]["online"]))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"server did not answer the status ping: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
