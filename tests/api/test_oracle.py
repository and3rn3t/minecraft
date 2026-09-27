"""Tests for The Oracle (api/oracle.py)."""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.events import GameEvent  # noqa: E402
from api.oracle import (  # noqa: E402
    MAX_TELLRAW_LENGTH,
    ClaudeOracleResponder,
    Oracle,
    OracleConfig,
    OracleTriage,
    QuestSpec,
    build_tellraw_to_player,
    get_oracle,
    load_oracle_config,
    reset_oracle,
    save_oracle_config,
)


def chat_event(player="Jonah", message="hello oracle", timestamp="2026-09-19T12:00:00+00:00"):
    return GameEvent(
        type="chat",
        timestamp=timestamp,
        player=player,
        data={"message": message, "log_time": "12:00:00"},
        raw=f"[12:00:00] [Server thread/INFO]: <{player}> {message}",
    )


class FakeResponder:
    """Stands in for ClaudeOracleResponder -- no network, no key, no cost."""

    def __init__(self, triage_result=None, quest_result=None, raise_on_triage=None, raise_on_quest=None):
        self.triage_result = triage_result or OracleTriage(outcome="no_reply")
        self.quest_result = quest_result
        self.raise_on_triage = raise_on_triage
        self.raise_on_quest = raise_on_quest
        self.triage_calls = []
        self.quest_calls = []

    def triage(self, player, message):
        self.triage_calls.append((player, message))
        if self.raise_on_triage:
            raise self.raise_on_triage
        return self.triage_result

    def generate_quest(self, player, request_text):
        self.quest_calls.append((player, request_text))
        if self.raise_on_quest:
            raise self.raise_on_quest
        return self.quest_result


def make_quest(**overrides):
    defaults = dict(
        title="Diamond Dash",
        description="Mine 5 diamonds before sundown.",
        objective_type="gather",
        target="diamond",
        quantity=5,
        difficulty="easy",
        reward_suggestion="a glowing pickaxe",
    )
    defaults.update(overrides)
    return QuestSpec(**defaults)


@pytest.fixture
def commands():
    return []


@pytest.fixture
def oracle_instance(tmp_path, commands):
    config = OracleConfig(enabled=True, allowlist=("Jonah", "Silas"), rate_limit_per_minute=4)
    return Oracle(runner=commands.append, oracle_dir=tmp_path / "oracle", config=config)


@pytest.fixture(autouse=True)
def clean_shared_oracle():
    reset_oracle()
    yield
    reset_oracle()


@pytest.mark.unit
class TestTellrawToPlayer:
    def test_builds_a_valid_command(self):
        command = build_tellraw_to_player("Jonah", "Hi there!")
        assert command.startswith("tellraw Jonah ")
        payload = json.loads(command[len("tellraw Jonah ") :])
        assert payload["text"] == "Hi there!"
        assert payload["color"] == "aqua"

    def test_colour_is_configurable(self):
        payload = json.loads(build_tellraw_to_player("Jonah", "x", color="red")[len("tellraw Jonah ") :])
        assert payload["color"] == "red"

    def test_quotes_are_escaped_not_interpolated(self):
        command = build_tellraw_to_player("Jonah", 'She said "hi" to you.')
        payload = json.loads(command[len("tellraw Jonah ") :])
        assert payload["text"] == 'She said "hi" to you.'

    def test_backslash_is_escaped(self):
        command = build_tellraw_to_player("Jonah", "a\\b")
        assert json.loads(command[len("tellraw Jonah ") :])["text"] == "a\\b"

    def test_overlong_text_is_truncated(self):
        command = build_tellraw_to_player("Jonah", "x" * 500)
        text = json.loads(command[len("tellraw Jonah ") :])["text"]
        assert len(text) <= MAX_TELLRAW_LENGTH
        assert text.endswith("…")

    @pytest.mark.parametrize("bad_name", ["", "ab", "a" * 17, "bad name", "bad;name", 'bad"name'])
    def test_invalid_player_name_is_refused(self, bad_name):
        with pytest.raises(ValueError):
            build_tellraw_to_player(bad_name, "hi")

    def test_valid_player_name_boundaries(self):
        # 3 and 16 characters are the shortest/longest real Minecraft names.
        build_tellraw_to_player("abc", "hi")
        build_tellraw_to_player("a" * 16, "hi")


@pytest.mark.unit
class TestConfig:
    def test_missing_config_uses_defaults(self, tmp_path):
        settings = load_oracle_config(tmp_path / "absent.conf")
        assert settings.enabled is False
        assert settings.allowlist == ()
        assert settings.rate_limit_per_minute == 4

    def test_config_is_parsed(self, tmp_path):
        config = tmp_path / "oracle.conf"
        config.write_text(
            "# comment\nENABLED=true\nALLOWLIST=Jonah, Silas\nRATE_LIMIT_PER_MINUTE=10\nCOLOR=red\n"
            "RETENTION_DAYS=30\nHAIKU_MODEL=claude-haiku-4-5\nSONNET_MODEL=claude-sonnet-5\n"
        )
        settings = load_oracle_config(config)
        assert settings.enabled is True
        assert settings.allowlist == ("Jonah", "Silas")
        assert settings.rate_limit_per_minute == 10
        assert settings.color == "red"
        assert settings.retention_days == 30

    def test_invalid_rate_limit_falls_back(self, tmp_path):
        config = tmp_path / "oracle.conf"
        config.write_text("RATE_LIMIT_PER_MINUTE=lots\n")
        assert load_oracle_config(config).rate_limit_per_minute == 4

    def test_save_and_load_round_trip(self, tmp_path):
        config_file = tmp_path / "oracle.conf"
        original = OracleConfig(enabled=True, allowlist=("Jonah",), rate_limit_per_minute=7, color="blue")
        save_oracle_config(original, config_file)

        loaded = load_oracle_config(config_file)
        assert loaded.enabled is True
        assert loaded.allowlist == ("Jonah",)
        assert loaded.rate_limit_per_minute == 7
        assert loaded.color == "blue"


@pytest.mark.unit
class TestAllowlist:
    def test_non_allowlisted_player_never_reaches_the_responder(self, oracle_instance, commands):
        responder = FakeResponder()
        oracle_instance.responder = responder

        result = oracle_instance.handle_event(chat_event(player="Stranger", message="hi"))

        assert result == {"outcome": "not_allowed"}
        assert responder.triage_calls == []
        assert commands == []
        assert oracle_instance.read_exchanges() == []

    def test_allowlisted_player_reaches_the_responder(self, oracle_instance):
        responder = FakeResponder(triage_result=OracleTriage(outcome="no_reply"))
        oracle_instance.responder = responder

        oracle_instance.handle_event(chat_event(player="Jonah", message="hi"))

        assert responder.triage_calls == [("Jonah", "hi")]

    def test_disabled_oracle_ignores_everything(self, tmp_path, commands):
        config = OracleConfig(enabled=False, allowlist=("Jonah",))
        orc = Oracle(runner=commands.append, oracle_dir=tmp_path / "oracle", config=config)
        responder = FakeResponder()
        orc.responder = responder

        assert orc.handle_event(chat_event(player="Jonah")) is None
        assert responder.triage_calls == []

    def test_non_allowlisted_chat_is_never_queued_when_a_worker_is_running(self, oracle_instance):
        # The allowlist check must happen before queueing, not after: a
        # griefer's or a visitor's chat should never sit in the worker's
        # backlog at all, since it could never get a reply anyway.
        responder = FakeResponder()
        oracle_instance.responder = responder
        oracle_instance.start_worker()
        try:
            result = oracle_instance.handle_event(chat_event(player="Stranger", message="hi"))
            assert result == {"outcome": "not_allowed"}
            assert oracle_instance._pending == 0
            assert oracle_instance.drain(timeout=1) is True
        finally:
            oracle_instance.stop_worker()
        assert responder.triage_calls == []


@pytest.mark.unit
class TestRateLimit:
    def test_nth_plus_one_message_is_skipped(self, oracle_instance):
        responder = FakeResponder(triage_result=OracleTriage(outcome="no_reply"))
        oracle_instance.responder = responder
        oracle_instance.config.rate_limit_per_minute = 2

        for _ in range(2):
            oracle_instance.handle_event(chat_event(player="Jonah"))
        result = oracle_instance.handle_event(chat_event(player="Jonah"))

        assert result == {"outcome": "rate_limited"}
        assert len(responder.triage_calls) == 2

    def test_a_different_player_is_unaffected(self, oracle_instance):
        responder = FakeResponder(triage_result=OracleTriage(outcome="no_reply"))
        oracle_instance.responder = responder
        oracle_instance.config.rate_limit_per_minute = 1

        oracle_instance.handle_event(chat_event(player="Jonah"))
        oracle_instance.handle_event(chat_event(player="Jonah"))  # rate-limited
        oracle_instance.handle_event(chat_event(player="Silas"))  # different bucket

        assert len(responder.triage_calls) == 2
        assert responder.triage_calls[1][0] == "Silas"

    def test_window_resets_after_time_passes(self, oracle_instance, monkeypatch):
        import time

        responder = FakeResponder(triage_result=OracleTriage(outcome="no_reply"))
        oracle_instance.responder = responder
        oracle_instance.config.rate_limit_per_minute = 1

        now = [1_000_000.0]
        monkeypatch.setattr(time, "time", lambda: now[0])

        oracle_instance.handle_event(chat_event(player="Jonah"))
        oracle_instance.handle_event(chat_event(player="Jonah"))  # rate-limited
        now[0] += 61
        oracle_instance.handle_event(chat_event(player="Jonah"))  # window reset

        assert len(responder.triage_calls) == 2


@pytest.mark.unit
class TestOutcomeRouting:
    def test_disabling_stops_a_message_already_queued(self, oracle_instance):
        # The kill switch must stop the Oracle from answering immediately,
        # not just once whatever was already queued happens to drain --
        # _process() re-checks config.enabled itself rather than trusting
        # the check handle_event made at enqueue time.
        responder = FakeResponder(triage_result=OracleTriage(outcome="banter", reply="hi"))
        oracle_instance.responder = responder
        oracle_instance.config.enabled = False

        result = oracle_instance._process(chat_event(player="Jonah", message="hi oracle"))

        assert result == {"outcome": "disabled"}
        assert responder.triage_calls == []
        assert oracle_instance.read_exchanges()[0]["outcome"] == "disabled"

    def test_disabling_mid_backlog_stops_the_next_queued_message(self, oracle_instance):
        # An end-to-end version of the same guarantee: a message queued
        # while enabled must not reach the responder if the Oracle is
        # disabled before the worker gets to it.
        import threading

        responder = FakeResponder(triage_result=OracleTriage(outcome="no_reply"))
        oracle_instance.responder = responder
        gate = threading.Event()
        real_process = oracle_instance._process

        def gated_process(event):
            gate.wait(5)
            return real_process(event)

        oracle_instance._process = gated_process
        oracle_instance.start_worker()
        try:
            oracle_instance.handle_event(chat_event(player="Jonah", message="hi"))
            oracle_instance.config.enabled = False
            gate.set()
            assert oracle_instance.drain(timeout=5) is True
        finally:
            oracle_instance.stop_worker()

        assert responder.triage_calls == []
        assert oracle_instance.read_exchanges()[0]["outcome"] == "disabled"

    def test_rate_limited_messages_are_audit_logged(self, oracle_instance):
        oracle_instance.responder = FakeResponder(triage_result=OracleTriage(outcome="no_reply"))
        oracle_instance.config.rate_limit_per_minute = 1
        audits = []
        oracle_instance.set_audit_logger(lambda player, action, details: audits.append((player, action, details)))

        oracle_instance.handle_event(chat_event(player="Jonah", message="one"))
        oracle_instance.handle_event(chat_event(player="Jonah", message="two"))

        rate_limited_audits = [a for a in audits if a[1] == "oracle.rate_limited"]
        assert len(rate_limited_audits) == 1
        assert oracle_instance.read_exchanges()[0]["outcome"] == "rate_limited"

    def test_no_reply_sends_nothing(self, oracle_instance, commands):
        oracle_instance.responder = FakeResponder(triage_result=OracleTriage(outcome="no_reply"))

        result = oracle_instance.handle_event(chat_event(player="Jonah", message="just chatting"))

        assert result == {"outcome": "no_reply"}
        assert commands == []
        exchanges = oracle_instance.read_exchanges()
        assert len(exchanges) == 1
        assert exchanges[0]["outcome"] == "no_reply"

    def test_banter_replies_to_the_player(self, oracle_instance, commands):
        oracle_instance.responder = FakeResponder(
            triage_result=OracleTriage(outcome="banter", reply="Hello, adventurer!")
        )
        audits = []
        oracle_instance.set_audit_logger(lambda player, action, details: audits.append((player, action, details)))

        oracle_instance.handle_event(chat_event(player="Jonah", message="hi oracle"))

        assert len(commands) == 1
        assert commands[0].startswith("tellraw Jonah ")
        assert json.loads(commands[0][len("tellraw Jonah ") :])["text"] == "Hello, adventurer!"
        exchanges = oracle_instance.read_exchanges()
        assert exchanges[0]["outcome"] == "banter"
        assert exchanges[0]["summary"] == "Hello, adventurer!"
        assert audits and audits[0][1] == "oracle.banter"

    def test_quest_request_delivers_and_persists_a_quest(self, oracle_instance, commands):
        quest = make_quest()
        oracle_instance.responder = FakeResponder(
            triage_result=OracleTriage(outcome="quest_request"), quest_result=quest
        )

        oracle_instance.handle_event(chat_event(player="Jonah", message="give me a quest"))

        assert len(commands) == 1
        assert commands[0].startswith("tellraw Jonah ")
        quests = oracle_instance.read_quests()
        assert len(quests) == 1
        assert quests[0]["title"] == "Diamond Dash"
        assert quests[0]["player"] == "Jonah"
        assert quests[0]["delivered"] is True
        assert quests[0]["claimed"] is False
        assert quests[0]["id"]

    def test_a_triage_exception_is_recorded_as_an_error(self, oracle_instance, commands):
        oracle_instance.responder = FakeResponder(raise_on_triage=RuntimeError("boom"))
        errors = []
        oracle_instance.set_error_logger(errors.append)

        result = oracle_instance.handle_event(chat_event(player="Jonah"))

        assert result == {"outcome": "error"}
        assert commands == []
        assert errors
        assert oracle_instance.read_exchanges()[0]["outcome"] == "error"

    def test_a_quest_generation_exception_is_recorded_as_an_error(self, oracle_instance, commands):
        oracle_instance.responder = FakeResponder(
            triage_result=OracleTriage(outcome="quest_request"), raise_on_quest=RuntimeError("boom")
        )
        errors = []
        oracle_instance.set_error_logger(errors.append)

        result = oracle_instance.handle_event(chat_event(player="Jonah"))

        assert result == {"outcome": "error"}
        assert commands == []
        assert oracle_instance.read_quests() == []

    def test_no_responder_configured_is_recorded_not_just_logged(self, oracle_instance, commands):
        # A missing key is a bounded, observable disabled state -- visible
        # as a "skipped" exchange -- not a per-message error that would
        # flood the log at chat's own pace.
        oracle_instance.responder = None
        audits = []
        oracle_instance.set_audit_logger(lambda player, action, details: audits.append((player, action, details)))

        result = oracle_instance.handle_event(chat_event(player="Jonah"))

        assert result == {"outcome": "skipped", "reason": "no_responder"}
        assert commands == []
        exchanges = oracle_instance.read_exchanges()
        assert exchanges[0]["outcome"] == "skipped"
        assert audits and audits[0][1] == "oracle.skipped"


@pytest.mark.unit
class TestBackgroundWorker:
    def test_handler_returns_immediately_when_a_worker_is_running(self, oracle_instance):
        import threading

        released = threading.Event()

        class SlowResponder:
            def triage(self, player, message):
                released.wait(5)
                return OracleTriage(outcome="no_reply")

            def generate_quest(self, player, request_text):
                raise NotImplementedError

        oracle_instance.responder = SlowResponder()
        oracle_instance.start_worker()
        try:
            assert oracle_instance.handle_event(chat_event(player="Jonah")) is None
        finally:
            released.set()
            oracle_instance.stop_worker()

    def test_queued_message_is_eventually_recorded(self, oracle_instance):
        oracle_instance.responder = FakeResponder(triage_result=OracleTriage(outcome="no_reply"))
        oracle_instance.start_worker()
        try:
            oracle_instance.handle_event(chat_event(player="Jonah"))
            assert oracle_instance.drain(timeout=5) is True
            assert len(oracle_instance.read_exchanges()) == 1
        finally:
            oracle_instance.stop_worker()

    def test_several_messages_are_all_recorded(self, oracle_instance):
        oracle_instance.config.rate_limit_per_minute = 100
        oracle_instance.responder = FakeResponder(triage_result=OracleTriage(outcome="no_reply"))
        oracle_instance.start_worker()
        try:
            for index in range(5):
                oracle_instance.handle_event(
                    chat_event(
                        player="Jonah", message=f"msg{index}", timestamp="2026-09-19T10:0" + str(index) + ":00+00:00"
                    )
                )
            assert oracle_instance.drain(timeout=5) is True
            assert len(oracle_instance.read_exchanges()) == 5
        finally:
            oracle_instance.stop_worker()

    def test_a_failing_responder_does_not_kill_the_worker(self, oracle_instance):
        oracle_instance.responder = FakeResponder(raise_on_triage=RuntimeError("boom"))
        errors = []
        oracle_instance.set_error_logger(errors.append)
        oracle_instance.start_worker()
        try:
            oracle_instance.handle_event(chat_event(player="Jonah", message="one"))
            assert oracle_instance.drain(timeout=5) is True
            assert errors
        finally:
            oracle_instance.stop_worker()

    def test_starting_twice_runs_one_worker(self, oracle_instance):
        oracle_instance.start_worker()
        first = oracle_instance._worker
        oracle_instance.start_worker()
        try:
            assert oracle_instance._worker is first
        finally:
            oracle_instance.stop_worker()

    def test_stopping_without_starting_is_safe(self, oracle_instance):
        oracle_instance.stop_worker()

    def test_drain_without_a_worker_returns_immediately(self, oracle_instance):
        assert oracle_instance.drain(timeout=0.1) is True

    def test_stopping_lets_queued_messages_finish(self, oracle_instance):
        oracle_instance.responder = FakeResponder(triage_result=OracleTriage(outcome="no_reply"))
        oracle_instance.config.rate_limit_per_minute = 100
        oracle_instance.start_worker()

        for index in range(5):
            oracle_instance.handle_event(
                chat_event(
                    player="Jonah", message=f"msg{index}", timestamp="2026-09-19T10:0" + str(index) + ":00+00:00"
                )
            )
        oracle_instance.stop_worker(timeout=5)

        assert len(oracle_instance.read_exchanges()) == 5


@pytest.mark.unit
class TestClaudeOracleResponder:
    """Pins down the refusal contract with a hand-built fake client -- no network, no key, no cost."""

    class _FakeResponse:
        def __init__(self, stop_reason, parsed_output):
            self.stop_reason = stop_reason
            self.parsed_output = parsed_output

    class _FakeMessages:
        def __init__(self, response):
            self._response = response

        def parse(self, **kwargs):
            return self._response

    class _FakeClient:
        def __init__(self, response):
            self.messages = TestClaudeOracleResponder._FakeMessages(response)

    def test_a_refusal_becomes_no_reply(self):
        client = self._FakeClient(self._FakeResponse("refusal", None))
        responder = ClaudeOracleResponder(client=client)

        result = responder.triage("Jonah", "anything")

        assert result == OracleTriage(outcome="no_reply")

    def test_no_parsed_output_becomes_no_reply(self):
        client = self._FakeClient(self._FakeResponse("end_turn", None))
        responder = ClaudeOracleResponder(client=client)

        result = responder.triage("Jonah", "anything")

        assert result == OracleTriage(outcome="no_reply")

    def test_a_normal_response_is_returned_as_is(self):
        triage = OracleTriage(outcome="banter", reply="Hi!")
        client = self._FakeClient(self._FakeResponse("end_turn", triage))
        responder = ClaudeOracleResponder(client=client)

        assert responder.triage("Jonah", "anything") is triage

    def test_quest_refusal_raises(self):
        client = self._FakeClient(self._FakeResponse("refusal", None))
        responder = ClaudeOracleResponder(client=client)

        with pytest.raises(RuntimeError):
            responder.generate_quest("Jonah", "give me a quest")


@pytest.mark.unit
class TestSharedOracle:
    def test_get_oracle_returns_a_singleton(self):
        assert get_oracle() is get_oracle()

    def test_reset_forces_a_rebuild(self):
        first = get_oracle()
        reset_oracle()
        assert get_oracle() is not first

    def test_runner_is_attached_on_first_supply(self):
        runner = []
        orc = get_oracle(runner=runner.append)
        assert orc.runner is not None

    def test_no_api_key_means_no_responder(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
        assert get_oracle().responder is None

    def test_status_reports_has_api_key(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
        assert get_oracle().status()["has_api_key"] is False

        reset_oracle()
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-not-real")
        assert get_oracle().status()["has_api_key"] is True


@pytest.mark.unit
class TestSettings:
    def test_update_settings_persists(self, tmp_path, monkeypatch):
        config_file = tmp_path / "oracle.conf"
        orc = Oracle(config=OracleConfig())
        monkeypatch.setattr("api.oracle.ORACLE_CONFIG_FILE", config_file)

        orc.update_settings(allowlist=["Jonah", "Silas"], rate_limit_per_minute=8)
        reloaded = load_oracle_config(config_file)
        assert reloaded.allowlist == ("Jonah", "Silas")
        assert reloaded.rate_limit_per_minute == 8

    def test_set_enabled_persists(self, tmp_path, monkeypatch):
        config_file = tmp_path / "oracle.conf"
        orc = Oracle(config=OracleConfig(enabled=False))
        monkeypatch.setattr("api.oracle.ORACLE_CONFIG_FILE", config_file)

        orc.set_enabled(True)
        assert load_oracle_config(config_file).enabled is True

    def test_rate_limit_is_clamped(self, oracle_instance):
        oracle_instance.update_settings(rate_limit_per_minute=1000)
        assert oracle_instance.config.rate_limit_per_minute == 60
        oracle_instance.update_settings(rate_limit_per_minute=-5)
        assert oracle_instance.config.rate_limit_per_minute == 1


@pytest.mark.api
class TestOracleEndpoints:
    """Tests for GET/PUT /api/oracle*."""

    @pytest.fixture(autouse=True)
    def oracle_with_history(self, tmp_path, monkeypatch, commands):
        config = OracleConfig(enabled=True, allowlist=("Jonah",), rate_limit_per_minute=4)
        orc = Oracle(runner=commands.append, oracle_dir=tmp_path / "oracle", config=config)
        orc.responder = FakeResponder(triage_result=OracleTriage(outcome="banter", reply="hi"))
        orc.handle_event(chat_event(player="Jonah", message="hello"))

        monkeypatch.setattr("api.oracle.get_oracle", lambda *_args, **_kwargs: orc)
        return orc

    def test_status_requires_authentication(self, client):
        assert client.get("/api/oracle").status_code == 401

    def test_status_reports_enabled_and_allowlist(self, client, mock_api_keys):
        response = client.get("/api/oracle", headers={"X-API-Key": mock_api_keys})
        assert response.status_code == 200
        data = response.get_json()
        assert data["enabled"] is True
        assert data["allowlist"] == ["Jonah"]

    def test_exchanges_are_returned(self, client, mock_api_keys):
        response = client.get("/api/oracle/exchanges", headers={"X-API-Key": mock_api_keys})
        assert response.status_code == 200
        assert len(response.get_json()) == 1

    def test_enable_and_disable_round_trip(self, client, mock_api_keys, oracle_with_history):
        response = client.put("/api/oracle/disable", headers={"X-API-Key": mock_api_keys})
        assert response.status_code == 200
        assert oracle_with_history.config.enabled is False

        response = client.put("/api/oracle/enable", headers={"X-API-Key": mock_api_keys})
        assert response.status_code == 200
        assert oracle_with_history.config.enabled is True

    def test_settings_rejects_invalid_usernames(self, client, mock_api_keys):
        response = client.put(
            "/api/oracle/settings",
            json={"allowlist": ["bad name"]},
            headers={"X-API-Key": mock_api_keys},
        )
        assert response.status_code == 400

    def test_settings_rejects_out_of_range_rate_limit(self, client, mock_api_keys):
        response = client.put(
            "/api/oracle/settings",
            json={"rate_limit_per_minute": 0},
            headers={"X-API-Key": mock_api_keys},
        )
        assert response.status_code == 400

    def test_settings_update_applies(self, client, mock_api_keys, oracle_with_history):
        response = client.put(
            "/api/oracle/settings",
            json={"allowlist": ["Jonah", "Silas"], "rate_limit_per_minute": 10},
            headers={"X-API-Key": mock_api_keys},
        )
        assert response.status_code == 200
        assert oracle_with_history.config.allowlist == ("Jonah", "Silas")
        assert oracle_with_history.config.rate_limit_per_minute == 10
