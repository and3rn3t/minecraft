"""api/event_capture.py: the game-event features are created, handed their helpers and
subscribed to the bus when the API starts, and each optional one is skipped when absent."""

from unittest.mock import MagicMock

import pytest

import api.event_capture as event_capture
import api.server as api_module

FEATURES = {
    "DEATHS_AVAILABLE": "hall_of_deaths",
    "PET_CEMETERY_AVAILABLE": "pet_cemetery",
    "BEDTIME_AVAILABLE": "bedtime_mode",
    "ORACLE_AVAILABLE": "oracle",
}


@pytest.fixture
def wired(monkeypatch):
    """Every feature present and faked; the bus and the log follower are doubles."""
    bus = MagicMock(name="bus")
    events = MagicMock(name="game_events")
    events.get_bus.return_value = bus
    monkeypatch.setattr(api_module, "SOCKETIO_AVAILABLE", True)
    monkeypatch.setattr(api_module, "socketio", MagicMock(name="socketio"))
    monkeypatch.setattr(api_module, "EVENTS_AVAILABLE", True)
    monkeypatch.setattr(api_module, "game_events", events)
    modules = {}
    for flag, attr in FEATURES.items():
        module = MagicMock(name=attr)
        monkeypatch.setattr(api_module, flag, True)
        monkeypatch.setattr(api_module, attr, module)
        modules[attr] = module
    ensure = MagicMock(name="ensure_log_reader")
    monkeypatch.setattr(event_capture.realtime, "ensure_log_reader", ensure)
    return {"bus": bus, "modules": modules, "ensure": ensure}


def _feature(wired, attr):
    """The object a faked feature module handed out."""
    getter = {
        "hall_of_deaths": "get_hall",
        "pet_cemetery": "get_cemetery",
        "bedtime_mode": "get_bedtime",
        "oracle": "get_oracle",
    }[attr]
    return getattr(wired["modules"][attr], getter).return_value


class TestStartEventCapture:
    def test_wires_every_feature_and_starts_the_follower(self, wired):
        assert event_capture.start_event_capture() is True

        bus = wired["bus"]
        bus.set_error_logger.assert_called_once()
        bus.start_periodic_flush.assert_called_once()
        subscribed = {call.args[0] for call in bus.subscribe.call_args_list}
        assert subscribed == {
            _feature(wired, "hall_of_deaths").handle_event,
            _feature(wired, "pet_cemetery").handle_event,
            _feature(wired, "bedtime_mode").on_player_join,
            _feature(wired, "oracle").handle_event,
        }
        for attr in ("hall_of_deaths", "pet_cemetery", "oracle"):
            _feature(wired, attr).start_worker.assert_called_once()
            _feature(wired, attr).set_error_logger.assert_called_once()
        _feature(wired, "bedtime_mode").start.assert_called_once()
        wired["ensure"].assert_called_once()

    @pytest.mark.parametrize("missing", ["SOCKETIO_AVAILABLE", "EVENTS_AVAILABLE"])
    def test_does_nothing_without_websockets_or_events(self, wired, monkeypatch, missing):
        monkeypatch.setattr(api_module, missing, False)

        assert event_capture.start_event_capture() is False
        wired["bus"].subscribe.assert_not_called()
        wired["ensure"].assert_not_called()

    def test_does_nothing_when_the_socketio_instance_is_missing(self, wired, monkeypatch):
        monkeypatch.setattr(api_module, "socketio", None)

        assert event_capture.start_event_capture() is False
        wired["ensure"].assert_not_called()

    @pytest.mark.parametrize("flag", list(FEATURES))
    def test_a_missing_feature_is_skipped_and_the_rest_still_start(self, wired, monkeypatch, flag):
        monkeypatch.setattr(api_module, flag, False)

        assert event_capture.start_event_capture() is True

        skipped = FEATURES[flag]
        wired["modules"][skipped].assert_not_called()
        assert wired["bus"].subscribe.call_count == len(FEATURES) - 1
        wired["ensure"].assert_called_once()

    def test_the_hall_announces_through_the_shared_helper(self, wired):
        event_capture.start_event_capture()

        kwargs = wired["modules"]["hall_of_deaths"].get_hall.call_args.kwargs
        assert kwargs["announcer"] is event_capture._announce_in_game

    def test_the_game_features_run_commands_through_the_shared_helper(self, wired):
        event_capture.start_event_capture()

        for attr, getter in (("pet_cemetery", "get_cemetery"), ("oracle", "get_oracle")):
            kwargs = getattr(wired["modules"][attr], getter).call_args.kwargs
            assert kwargs["runner"] is event_capture._run_game_command
        bedtime_kwargs = wired["modules"]["bedtime_mode"].get_bedtime.call_args.kwargs
        assert bedtime_kwargs["runner"] is event_capture._run_game_command
        assert bedtime_kwargs["stopper"] is event_capture._stop_server_for_bedtime

    def test_the_oracle_audits_with_a_fixed_address_not_a_request(self, wired, monkeypatch):
        """The worker thread has no Flask request, so the audit entry must carry its own address."""
        audit = MagicMock(name="log_audit_event")
        monkeypatch.setattr(api_module, "log_audit_event", audit)
        event_capture.start_event_capture()

        logger = _feature(wired, "oracle").set_audit_logger.call_args.args[0]
        logger("steve", "oracle_reply", {"q": "x"})

        audit.assert_called_once_with("steve", "oracle_reply", {"q": "x"}, ip_address="minecraft-chat")


class TestHelpers:
    @pytest.mark.parametrize("helper", ["_run_game_command", "_announce_in_game"])
    def test_a_command_that_succeeds_returns_quietly(self, monkeypatch, helper):
        run = MagicMock(return_value=("ok", "", 0))
        monkeypatch.setattr(api_module, "run_rcon_command", run)

        assert getattr(event_capture, helper)("say hi") is None
        run.assert_called_once_with("say hi")

    @pytest.mark.parametrize("helper", ["_run_game_command", "_announce_in_game"])
    def test_a_failed_command_raises_with_the_scripts_message(self, monkeypatch, helper):
        monkeypatch.setattr(api_module, "run_rcon_command", MagicMock(return_value=(None, "server is down", 503)))

        with pytest.raises(RuntimeError, match="server is down"):
            getattr(event_capture, helper)("say hi")

    @pytest.mark.parametrize("helper", ["_run_game_command", "_announce_in_game"])
    def test_a_failure_without_a_message_names_the_code(self, monkeypatch, helper):
        monkeypatch.setattr(api_module, "run_rcon_command", MagicMock(return_value=(None, "", 502)))

        with pytest.raises(RuntimeError, match="RCON returned 502"):
            getattr(event_capture, helper)("say hi")

    def test_stopping_for_bedtime_runs_manage_stop_with_a_long_timeout(self, monkeypatch):
        run = MagicMock(return_value=("", "", 0))
        monkeypatch.setattr(api_module, "run_script", run)

        event_capture._stop_server_for_bedtime()

        run.assert_called_once_with("manage.sh", "stop", timeout=600)

    def test_a_failed_stop_raises(self, monkeypatch):
        monkeypatch.setattr(api_module, "run_script", MagicMock(return_value=("", "no container", 1)))

        with pytest.raises(RuntimeError, match="no container"):
            event_capture._stop_server_for_bedtime()
