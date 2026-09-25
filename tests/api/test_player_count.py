#!/usr/bin/env python3
"""
Unit Tests: scripts/player-count.py

The update scripts restart the game server only when this says nobody is
online, so the failure direction matters: a server that does not answer must
be reported as unknown (exit 1), never as zero players.
"""

import importlib.util
import json
import socket
import threading
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

# player-count.py has a hyphenated filename, so it needs importlib
spec = importlib.util.spec_from_file_location("player_count", SCRIPTS_DIR / "player-count.py")
player_count = importlib.util.module_from_spec(spec)
spec.loader.exec_module(player_count)


def _read_varint(conn):
    """Read a VarInt from a socket, as the real server does."""
    result = 0
    for shift in range(0, 35, 7):
        byte = conn.recv(1)[0]
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result
    raise ValueError("VarInt too long")


def _read_packet(conn):
    """Read one framed packet and return its body."""
    length = _read_varint(conn)
    body = b""
    while len(body) < length:
        body += conn.recv(length - len(body))
    return body


@pytest.fixture
def fake_server():
    """A one-shot server that answers a status request with the given players."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]
    received = {}

    def serve(online):
        conn, _ = listener.accept()
        with conn:
            received["handshake"] = _read_packet(conn)
            received["request"] = _read_packet(conn)
            status = json.dumps(
                {"version": {"name": "1.20.4", "protocol": 765}, "players": {"max": 20, "online": online}}
            ).encode("utf-8")
            payload = player_count._varint(len(status)) + status
            conn.sendall(player_count._packet(0x00, payload))

    def start(online):
        thread = threading.Thread(target=serve, args=(online,), daemon=True)
        thread.start()
        return port

    yield start, received
    listener.close()


def _free_port():
    """A port with nothing listening on it."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.mark.unit
def test_varint_encoding_matches_the_protocol():
    """Known VarInt encodings from the protocol documentation."""
    assert player_count._varint(0) == b"\x00"
    assert player_count._varint(1) == b"\x01"
    assert player_count._varint(127) == b"\x7f"
    assert player_count._varint(128) == b"\x80\x01"
    assert player_count._varint(25565) == b"\xdd\xc7\x01"
    assert player_count._varint(-1) == b"\xff\xff\xff\xff\x0f"


@pytest.mark.unit
@pytest.mark.parametrize("online", [0, 1, 7])
def test_query_status_reads_the_player_count(fake_server, online):
    """The online count comes back from a real status exchange."""
    start, received = fake_server
    port = start(online)

    status = player_count.query_status("127.0.0.1", port, timeout=5)

    assert status["players"]["online"] == online
    # Next state 1 (status) ends the handshake; the request is an empty packet 0
    assert received["handshake"].endswith(b"\x01")
    assert received["request"] == b"\x00"


@pytest.mark.unit
def test_main_prints_the_count(fake_server, monkeypatch, capsys):
    """The command prints just the number, which the shell scripts compare."""
    start, _ = fake_server
    monkeypatch.setenv("SERVER_PORT", str(start(3)))

    assert player_count.main() == 0
    assert capsys.readouterr().out.strip() == "3"


@pytest.mark.unit
def test_main_fails_rather_than_reporting_zero_when_nothing_answers(monkeypatch, capsys):
    """A stopped or starting server is 'unknown', never 'empty'."""
    monkeypatch.setenv("SERVER_PORT", str(_free_port()))

    assert player_count.main() == 1
    assert capsys.readouterr().out == ""
