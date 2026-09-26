"""Tests for the game event bus (api/events.py)."""

import json
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.events import (  # noqa: E402
    EVENT_ADVANCEMENT,
    EVENT_CHAT,
    EVENT_COMMAND,
    EVENT_CONNECT,
    EVENT_DEATH,
    EVENT_PET_DEATH,
    EVENT_JOIN,
    EVENT_LEAVE,
    EVENT_SERVER_READY,
    EVENT_SERVER_STOPPING,
    EventBus,
    GameEvent,
    get_bus,
    parse_line,
    reset_bus,
)


def line(message, thread="Server thread/INFO", time="16:04:23"):
    """Build a realistic server log line around a message."""
    return f"[{time}] [{thread}]: {message}"


@pytest.fixture
def bus(tmp_path):
    """A bus writing to a temp directory, flushing on every event."""
    return EventBus(events_dir=tmp_path / "events", flush_every_events=1)


@pytest.fixture(autouse=True)
def clean_shared_bus():
    reset_bus()
    yield
    reset_bus()


@pytest.mark.unit
class TestParsingPlayerEvents:
    def test_chat_message(self):
        event = parse_line(line("<Jonah> hello silas"))
        assert event.type == EVENT_CHAT
        assert event.player == "Jonah"
        assert event.data["message"] == "hello silas"

    def test_chat_preserves_inner_punctuation(self):
        event = parse_line(line("<Silas> wait... what?! >:)"))
        assert event.data["message"] == "wait... what?! >:)"

    def test_empty_chat_message_still_parses(self):
        event = parse_line(line("<Jonah> "))
        assert event.type == EVENT_CHAT
        assert event.data["message"] == ""

    def test_join(self):
        event = parse_line(line("Jonah joined the game"))
        assert (event.type, event.player) == (EVENT_JOIN, "Jonah")

    def test_leave(self):
        event = parse_line(line("Silas left the game"))
        assert (event.type, event.player) == (EVENT_LEAVE, "Silas")

    def test_login_line_is_a_connect_not_a_join(self):
        """One session logs two lines; counting joins must not double-count."""
        event = parse_line(line("Jonah[/192.168.1.40:54321] logged in with entity id 214 at (1.5, 64.0, -9.5)"))
        assert event.type == EVENT_CONNECT
        assert event.player == "Jonah"
        assert event.data["address"] == "192.168.1.40:54321"

    def test_a_full_session_produces_exactly_one_join(self):
        raws = [
            line("Jonah[/192.168.1.40:54321] logged in with entity id 214 at (1.5, 64.0, -9.5)"),
            line("Jonah joined the game"),
        ]
        types = [parse_line(raw).type for raw in raws]
        assert types.count(EVENT_JOIN) == 1
        assert types.count(EVENT_CONNECT) == 1

    def test_issued_command(self):
        event = parse_line(line("Jonah issued server command: /gamemode creative"))
        assert event.type == EVENT_COMMAND
        assert event.data["command"] == "/gamemode creative"

    def test_advancement(self):
        event = parse_line(line("Silas has made the advancement [Stone Age]"))
        assert event.type == EVENT_ADVANCEMENT
        assert event.data["advancement"] == "Stone Age"

    def test_challenge_and_goal_are_advancements_too(self):
        challenge = parse_line(line("Jonah has completed the challenge [Adventuring Time]"))
        goal = parse_line(line("Silas has reached the goal [Sky's the Limit]"))
        assert challenge.type == EVENT_ADVANCEMENT
        assert goal.data["advancement"] == "Sky's the Limit"


@pytest.mark.unit
class TestParsingDeaths:
    @pytest.mark.parametrize(
        "message,player",
        [
            ("Jonah was slain by Zombie", "Jonah"),
            ("Silas fell from a high place", "Silas"),
            ("Jonah drowned", "Jonah"),
            ("Silas blew up", "Silas"),
            ("Jonah was blown up by Creeper", "Jonah"),
            ("Silas tried to swim in lava", "Silas"),
            ("Jonah was shot by Skeleton", "Jonah"),
            ("Silas burned to death", "Silas"),
            ("Jonah starved to death", "Jonah"),
            ("Silas suffocated in a wall", "Silas"),
            ("Jonah withered away", "Jonah"),
            ("Silas froze to death", "Silas"),
            ("Jonah hit the ground too hard", "Jonah"),
            ("Silas fell out of the world", "Silas"),
            ("Jonah was killed by magic", "Jonah"),
            ("Silas was pricked to death", "Silas"),
            ("Jonah was squashed by a falling anvil", "Jonah"),
            ("Silas went up in flames", "Silas"),
            ("Jonah was struck by lightning", "Jonah"),
            ("Silas was impaled on a stalagmite", "Silas"),
            ("Jonah was poked to death by a sweet berry bush", "Jonah"),
            ("Silas discovered the floor was lava", "Silas"),
            ("Jonah was obliterated by a sonically-charged shriek", "Jonah"),
            ("Silas fell off scaffolding", "Silas"),
        ],
    )
    def test_vanilla_death_messages(self, message, player):
        event = parse_line(line(message))
        assert event is not None, f"not recognised as a death: {message}"
        assert event.type == EVENT_DEATH
        assert event.player == player
        assert event.data["message"] == message

    def test_death_cause_is_captured(self):
        event = parse_line(line("Jonah was slain by Zombie using Iron Sword"))
        assert event.data["cause"] == "was slain by Zombie using Iron Sword"

    def test_chat_that_looks_like_a_death_is_still_chat(self):
        """A kid typing a fake death message must not fake a death event."""
        event = parse_line(line("<Silas> Jonah was slain by Zombie"))
        assert event.type == EVENT_CHAT
        assert event.player == "Silas"

    def test_ordinary_sentence_is_not_a_death(self):
        assert parse_line(line("Jonah is building something")) is None


@pytest.mark.unit
class TestParsingPetDeaths:
    """A named (tamed) mob's death, logged to console but never broadcast."""

    def test_named_wolf_death(self):
        message = (
            "Named entity EntityWolf['Biscuit'/99, uuid='238608e0-adfc-4fad-8e07-22dad27c9550', "
            "l='ServerLevel[minecraft:overworld]', x=1.00, y=64.00, z=1.00, cpos=[0, 0], tl=1, "
            "v=true, rR=null] died: Biscuit was slain by Skeleton"
        )
        event = parse_line(line(message))
        assert event is not None
        assert event.type == EVENT_PET_DEATH
        assert event.player is None
        assert event.data["entity_type"] == "EntityWolf"
        assert event.data["name"] == "Biscuit"
        assert event.data["cause"] == "was slain by Skeleton"

    def test_cause_with_brackets_in_it(self):
        """A weapon name in the cause ('using [Bow]') must not break the match."""
        message = (
            "Named entity EntityWolf['Biscuit'/99, uuid='abc', l='ServerLevel[minecraft:overworld]', "
            "x=1.0, y=2.0, z=3.0, cpos=[0, 0], tl=1, v=true, rR=null] "
            "died: Biscuit was slain by Skeleton using [Bow]"
        )
        event = parse_line(line(message))
        assert event.data["cause"] == "was slain by Skeleton using [Bow]"

    def test_an_ordinary_player_death_is_not_a_pet_death(self):
        event = parse_line(line("Jonah was slain by Zombie"))
        assert event.type == EVENT_DEATH


@pytest.mark.unit
class TestParsingServerEvents:
    def test_server_ready(self):
        event = parse_line(line('Done (21.174s)! For help, type "help"'))
        assert event.type == EVENT_SERVER_READY
        assert event.data["startup_time"] == "21.174s"
        assert event.player is None

    def test_server_stopping(self):
        assert parse_line(line("Stopping the server")).type == EVENT_SERVER_STOPPING


@pytest.mark.unit
class TestParsingNonEvents:
    @pytest.mark.parametrize(
        "raw",
        [
            "",
            "   ",
            "not a log line at all",
            "[16:04:23] [Server thread/INFO]: ",
            "[16:04:23] [Server thread/INFO]: Preparing spawn area: 82%",
            "[16:04:23] [Server thread/WARN]: Can't keep up! Is the server overloaded?",
            "[16:04:23] [Worker-Main-3/INFO]: Preparing spawn area: 4%",
        ],
    )
    def test_uninteresting_lines_produce_nothing(self, raw):
        assert parse_line(raw) is None

    def test_malformed_line_does_not_raise(self):
        assert parse_line("[[[]]]") is None

    def test_other_thread_names_still_parse(self):
        """Paper logs chat from an async thread, not the main server thread."""
        event = parse_line(line("<Jonah> hi", thread="Async Chat Thread-#0/INFO"))
        assert event.type == EVENT_CHAT

    def test_log_time_is_kept_separate_from_ingest_time(self):
        event = parse_line(line("Jonah joined the game", time="23:59:58"))
        assert event.data["log_time"] == "23:59:58"
        assert event.timestamp.endswith("+00:00")


@pytest.mark.unit
class TestDispatch:
    def test_handler_receives_event(self, bus):
        seen = []
        bus.subscribe(seen.append)
        bus.handle_line(line("Jonah joined the game"))
        assert [event.player for event in seen] == ["Jonah"]

    def test_non_event_lines_are_not_dispatched(self, bus):
        seen = []
        bus.subscribe(seen.append)
        bus.handle_line(line("Preparing spawn area: 82%"))
        assert seen == []

    def test_multiple_handlers_all_fire(self, bus):
        first, second = [], []
        bus.subscribe(first.append)
        bus.subscribe(second.append)
        bus.handle_line(line("Silas left the game"))
        assert len(first) == len(second) == 1

    def test_subscribing_twice_does_not_double_deliver(self, bus):
        seen = []
        bus.subscribe(seen.append)
        bus.subscribe(seen.append)
        bus.handle_line(line("Jonah joined the game"))
        assert len(seen) == 1

    def test_unsubscribe_stops_delivery(self, bus):
        seen = []
        bus.subscribe(seen.append)
        bus.unsubscribe(seen.append)
        bus.handle_line(line("Jonah joined the game"))
        assert seen == []

    def test_failing_handler_does_not_stop_the_others(self, bus):
        """One broken feature must not silence the whole bus."""
        errors = []
        survived = []

        def broken(_event):
            raise RuntimeError("handler exploded")

        bus.set_error_logger(errors.append)
        bus.subscribe(broken)
        bus.subscribe(survived.append)

        bus.handle_line(line("Jonah joined the game"))

        assert len(survived) == 1
        assert "handler exploded" in errors[0]

    def test_failing_handler_still_persists_the_event(self, bus):
        def broken(_event):
            raise RuntimeError("nope")

        bus.set_error_logger(lambda _message: None)
        bus.subscribe(broken)
        bus.handle_line(line("Jonah joined the game"))

        assert len(bus.read()) == 1


@pytest.mark.unit
class TestPersistence:
    def test_event_is_written_as_jsonl(self, bus, tmp_path):
        bus.handle_line(line("Jonah joined the game"))
        files = list((tmp_path / "events").glob("*.jsonl"))
        assert len(files) == 1

        record = json.loads(files[0].read_text().strip())
        assert record["type"] == EVENT_JOIN
        assert record["player"] == "Jonah"
        assert record["raw"].endswith("Jonah joined the game")

    def test_writes_are_buffered_until_the_threshold(self, tmp_path):
        """Batching exists to spare the Pi's SD card."""
        buffered = EventBus(events_dir=tmp_path / "events", flush_every_events=5, flush_every_seconds=3600)
        for _ in range(4):
            buffered.handle_line(line("Jonah joined the game"))
        assert not list((tmp_path / "events").glob("*.jsonl"))

        buffered.handle_line(line("Jonah joined the game"))
        assert len(list((tmp_path / "events").glob("*.jsonl"))) == 1

    def test_flush_returns_the_count_written(self, tmp_path):
        buffered = EventBus(events_dir=tmp_path / "events", flush_every_events=100, flush_every_seconds=3600)
        for _ in range(3):
            buffered.handle_line(line("Jonah joined the game"))
        assert buffered.flush() == 3
        assert buffered.flush() == 0

    def test_read_returns_newest_first(self, bus):
        bus.handle_line(line("Jonah joined the game"))
        bus.handle_line(line("Silas joined the game"))
        assert [record["player"] for record in bus.read()] == ["Silas", "Jonah"]

    def test_read_filters_by_type(self, bus):
        bus.handle_line(line("Jonah joined the game"))
        bus.handle_line(line("Jonah was slain by Zombie"))
        deaths = bus.read(event_type=EVENT_DEATH)
        assert len(deaths) == 1
        assert deaths[0]["data"]["cause"].startswith("was slain")

    def test_read_filters_by_player(self, bus):
        bus.handle_line(line("Jonah joined the game"))
        bus.handle_line(line("Silas joined the game"))
        assert len(bus.read(player="Silas")) == 1

    def test_read_respects_the_limit(self, bus):
        for _ in range(10):
            bus.handle_line(line("Jonah joined the game"))
        assert len(bus.read(limit=4)) == 4

    def test_read_flushes_pending_events_first(self, tmp_path):
        buffered = EventBus(events_dir=tmp_path / "events", flush_every_events=100, flush_every_seconds=3600)
        buffered.handle_line(line("Jonah joined the game"))
        assert len(buffered.read()) == 1

    def test_read_is_empty_when_nothing_was_recorded(self, bus):
        assert bus.read() == []

    def test_torn_final_line_is_skipped(self, bus, tmp_path):
        bus.handle_line(line("Jonah joined the game"))
        target = next((tmp_path / "events").glob("*.jsonl"))
        target.write_text(target.read_text() + '{"type": "death", "incomplete"\n')
        assert len(bus.read()) == 1

    def test_unwritable_directory_does_not_raise(self, tmp_path):
        """A full or read-only disk must not take the server down."""
        blocker = tmp_path / "events"
        blocker.write_text("this is a file, not a directory")

        errors = []
        broken = EventBus(events_dir=blocker, flush_every_events=1)
        broken.set_error_logger(errors.append)
        broken.handle_line(line("Jonah joined the game"))

        assert errors and "Could not persist" in errors[0]


@pytest.mark.unit
class TestRetention:
    def test_old_files_are_pruned(self, tmp_path):
        events_dir = tmp_path / "events"
        events_dir.mkdir()
        (events_dir / "2020-01-01.jsonl").write_text("{}\n")
        (events_dir / "2999-01-01.jsonl").write_text("{}\n")

        assert EventBus(events_dir=events_dir, retention_days=30).prune() == 1
        assert not (events_dir / "2020-01-01.jsonl").exists()
        assert (events_dir / "2999-01-01.jsonl").exists()

    def test_unrecognised_filenames_are_left_alone(self, tmp_path):
        events_dir = tmp_path / "events"
        events_dir.mkdir()
        (events_dir / "notes.jsonl").write_text("{}\n")
        EventBus(events_dir=events_dir, retention_days=1).prune()
        assert (events_dir / "notes.jsonl").exists()

    def test_retention_can_be_disabled(self, tmp_path):
        events_dir = tmp_path / "events"
        events_dir.mkdir()
        (events_dir / "2020-01-01.jsonl").write_text("{}\n")
        assert EventBus(events_dir=events_dir, retention_days=0).prune() == 0


@pytest.mark.unit
class TestSharedBus:
    def test_get_bus_returns_a_singleton(self):
        assert get_bus() is get_bus()

    def test_reset_forces_a_rebuild(self):
        first = get_bus()
        reset_bus()
        assert get_bus() is not first

    def test_event_serialises_cleanly(self):
        event = GameEvent(type=EVENT_CHAT, timestamp="2026-01-01T00:00:00+00:00", player="Jonah", data={"a": 1})
        assert json.loads(event.to_json())["player"] == "Jonah"


@pytest.mark.api
class TestEventsEndpoints:
    """Tests for GET /api/events and GET /api/events/types."""

    @pytest.fixture(autouse=True)
    def bus_with_events(self, tmp_path, monkeypatch):
        """Point the shared bus at a temp directory holding known events."""
        temp_bus = EventBus(events_dir=tmp_path / "events", flush_every_events=1)
        temp_bus.handle_line(line("Jonah joined the game"))
        temp_bus.handle_line(line("Silas was slain by Zombie"))
        temp_bus.handle_line(line("<Jonah> gg"))

        monkeypatch.setattr("api.events.get_bus", lambda: temp_bus)
        return temp_bus

    def test_requires_authentication(self, client):
        assert client.get("/api/events").status_code == 401

    def test_returns_events_newest_first(self, client, mock_api_keys):
        response = client.get("/api/events", headers={"X-API-Key": mock_api_keys})
        assert response.status_code == 200

        payload = response.get_json()
        assert payload["count"] == 3
        assert [event["type"] for event in payload["events"]] == [EVENT_CHAT, EVENT_DEATH, EVENT_JOIN]

    def test_filters_by_type(self, client, mock_api_keys):
        response = client.get("/api/events?type=death", headers={"X-API-Key": mock_api_keys})
        payload = response.get_json()
        assert payload["count"] == 1
        assert payload["events"][0]["player"] == "Silas"

    def test_filters_by_player(self, client, mock_api_keys):
        response = client.get("/api/events?player=Jonah", headers={"X-API-Key": mock_api_keys})
        assert response.get_json()["count"] == 2

    def test_respects_limit(self, client, mock_api_keys):
        response = client.get("/api/events?limit=1", headers={"X-API-Key": mock_api_keys})
        assert response.get_json()["count"] == 1

    def test_rejects_unknown_type(self, client, mock_api_keys):
        response = client.get("/api/events?type=nonsense", headers={"X-API-Key": mock_api_keys})
        assert response.status_code == 400
        assert "valid_types" in response.get_json()

    def test_rejects_non_numeric_limit(self, client, mock_api_keys):
        response = client.get("/api/events?limit=lots", headers={"X-API-Key": mock_api_keys})
        assert response.status_code == 400

    def test_limit_is_capped_at_500(self, client, mock_api_keys, bus_with_events):
        """An unbounded limit would let one request read every stored event."""
        for _ in range(600):
            bus_with_events.handle_line(line("Jonah joined the game"))

        response = client.get("/api/events?limit=99999", headers={"X-API-Key": mock_api_keys})
        assert response.status_code == 200
        assert response.get_json()["count"] == 500

    def test_types_endpoint_lists_every_type(self, client, mock_api_keys):
        response = client.get("/api/events/types", headers={"X-API-Key": mock_api_keys})
        assert response.status_code == 200
        assert set(response.get_json()["types"]) == {
            EVENT_CHAT,
            EVENT_CONNECT,
            EVENT_JOIN,
            EVENT_LEAVE,
            EVENT_DEATH,
            EVENT_PET_DEATH,
            EVENT_ADVANCEMENT,
            EVENT_COMMAND,
            EVENT_SERVER_READY,
            EVENT_SERVER_STOPPING,
        }


@pytest.mark.unit
class TestFlushSafety:
    """Concurrency and quiet-period behaviour of the buffered writer."""

    def test_concurrent_flushes_do_not_interleave(self, tmp_path):
        """Two flushes racing must not write half a line inside another."""
        bus = EventBus(events_dir=tmp_path / "events", flush_every_events=10000, flush_every_seconds=3600)
        for index in range(200):
            bus.publish(GameEvent(type=EVENT_JOIN, timestamp="t", player=f"p{index}"))

        barrier = threading.Barrier(4)

        def flush_now():
            barrier.wait()
            bus.flush()

        threads = [threading.Thread(target=flush_now) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        written = (tmp_path / "events").glob("*.jsonl")
        lines = [ln for path in written for ln in path.read_text().splitlines() if ln.strip()]

        assert len(lines) == 200
        # Every line must be a complete, parseable record.
        players = {json.loads(ln)["player"] for ln in lines}
        assert players == {f"p{index}" for index in range(200)}

    def test_periodic_flush_writes_without_further_events(self, tmp_path):
        """A quiet server previously left the last events buffered forever."""
        bus = EventBus(
            events_dir=tmp_path / "events",
            flush_every_events=10000,
            flush_every_seconds=0.1,
        )
        bus.handle_line(line("Jonah joined the game"))
        assert not list((tmp_path / "events").glob("*.jsonl"))

        bus.start_periodic_flush()
        try:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                if list((tmp_path / "events").glob("*.jsonl")):
                    break
                time.sleep(0.05)
            assert list((tmp_path / "events").glob("*.jsonl"))
        finally:
            bus.stop_periodic_flush()

    def test_starting_the_timer_twice_arms_only_one(self, tmp_path):
        bus = EventBus(events_dir=tmp_path / "events", flush_every_seconds=3600)
        bus.start_periodic_flush()
        first = bus._flush_timer
        bus.start_periodic_flush()
        try:
            assert bus._flush_timer is first
        finally:
            bus.stop_periodic_flush()

    def test_stopping_the_timer_flushes_what_is_left(self, tmp_path):
        bus = EventBus(events_dir=tmp_path / "events", flush_every_events=10000, flush_every_seconds=3600)
        bus.start_periodic_flush()
        bus.handle_line(line("Jonah joined the game"))
        bus.stop_periodic_flush()

        assert len(bus.read()) == 1
        assert bus._flush_timer is None

    def test_stopping_without_starting_is_safe(self, tmp_path):
        EventBus(events_dir=tmp_path / "events").stop_periodic_flush()


class TestStorageLocationIsConfigurable:
    """The Pi boots from an SD card and this is the one directory written to
    continuously, so it has to be movable onto an SSD without editing code."""

    @staticmethod
    def _reload(monkeypatch, **env):
        """Re-import api.events with the given environment.

        The module is taken from sys.modules rather than imported again: the
        top of this file already imports from it, and a second `import api.events`
        would be the same module reached two different ways.
        """
        import importlib
        import sys as _sys

        for key in ("MC_EVENTS_DIR", "MC_EVENTS_RETENTION_DAYS"):
            monkeypatch.delenv(key, raising=False)
        for key, value in env.items():
            monkeypatch.setenv(key, value)
        return importlib.reload(_sys.modules["api.events"])

    def test_defaults_to_the_project_data_directory(self, monkeypatch):
        module = self._reload(monkeypatch)

        assert module.EVENTS_DIR == module.PROJECT_ROOT / "data" / "events"

    def test_mc_events_dir_moves_the_files(self, monkeypatch, tmp_path):
        """Setting the variable is the whole SSD migration"""
        target = tmp_path / "ssd" / "events"
        module = self._reload(monkeypatch, MC_EVENTS_DIR=str(target))

        assert module.EVENTS_DIR == target

    def test_a_new_bus_writes_where_the_variable_points(self, monkeypatch, tmp_path):
        """The setting has to reach the files, not just the constant"""
        target = tmp_path / "ssd" / "events"
        module = self._reload(monkeypatch, MC_EVENTS_DIR=str(target))

        bus = module.EventBus()
        bus.publish(
            module.GameEvent(
                type=module.EVENT_JOIN,
                timestamp=datetime.now(timezone.utc).isoformat(),
                player="Jonah",
                raw="Jonah joined the game",
            )
        )
        bus.flush()

        written = list(target.glob("*.jsonl"))
        assert written, f"nothing written under {target}"
        assert json.loads(written[0].read_text().splitlines()[0])["player"] == "Jonah"

    def test_a_home_relative_path_is_expanded(self, monkeypatch):
        """~ is what anyone actually types for a mount point under home"""
        module = self._reload(monkeypatch, MC_EVENTS_DIR="~/mc-events")

        assert "~" not in str(module.EVENTS_DIR)
        assert module.EVENTS_DIR.is_absolute()

    def test_retention_defaults_to_thirty_days(self, monkeypatch):
        module = self._reload(monkeypatch)

        assert module.DEFAULT_RETENTION_DAYS == 30

    def test_retention_can_be_raised_off_the_card(self, monkeypatch):
        """On an SSD there is no card to protect, and the history is the point"""
        module = self._reload(monkeypatch, MC_EVENTS_RETENTION_DAYS="365")

        assert module.DEFAULT_RETENTION_DAYS == 365

    def test_a_malformed_retention_falls_back(self, monkeypatch):
        """A typo must not turn pruning off by accident"""
        module = self._reload(monkeypatch, MC_EVENTS_RETENTION_DAYS="a fortnight")

        assert module.DEFAULT_RETENTION_DAYS == 30

    def test_zero_retention_disables_pruning(self, monkeypatch, tmp_path):
        """prune() already treats <= 0 as 'keep everything'; keep that reachable"""
        module = self._reload(monkeypatch, MC_EVENTS_RETENTION_DAYS="0")
        assert module.DEFAULT_RETENTION_DAYS == 0

        events_dir = tmp_path / "events"
        events_dir.mkdir()
        old_file = events_dir / "2020-01-01.jsonl"
        old_file.write_text('{"type": "join"}\n')

        bus = module.EventBus(events_dir=events_dir, retention_days=0)
        bus.prune()

        assert old_file.exists(), "pruning should be off"
