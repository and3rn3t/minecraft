"""Tests for the Hall of Deaths (api/hall_of_deaths.py)."""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.events import GameEvent  # noqa: E402
from api.hall_of_deaths import (  # noqa: E402
    MAX_ANNOUNCEMENT_LENGTH,
    HallOfDeaths,
    build_tellraw,
    get_hall,
    load_deaths_config,
    reset_hall,
)


def death_event(player="Jonah", cause="was slain by Zombie", timestamp="2026-09-19T12:00:00+00:00"):
    return GameEvent(
        type="death",
        timestamp=timestamp,
        player=player,
        data={"cause": cause, "message": f"{player} {cause}", "log_time": "12:00:00"},
        raw=f"[12:00:00] [Server thread/INFO]: {player} {cause}",
    )


@pytest.fixture
def announcements():
    return []


@pytest.fixture
def hall(tmp_path, announcements):
    return HallOfDeaths(deaths_dir=tmp_path / "deaths", announcer=announcements.append)


@pytest.fixture(autouse=True)
def clean_shared_hall():
    reset_hall()
    yield
    reset_hall()


@pytest.mark.unit
class TestTellraw:
    def test_builds_a_valid_command(self):
        command = build_tellraw("Here lies Jonah.")
        assert command.startswith("tellraw @a ")
        payload = json.loads(command[len("tellraw @a ") :])
        assert payload["text"] == "Here lies Jonah."
        assert payload["italic"] is True

    def test_colour_is_configurable(self):
        payload = json.loads(build_tellraw("x", color="red")[len("tellraw @a ") :])
        assert payload["color"] == "red"

    def test_quotes_are_escaped_not_interpolated(self):
        """An epitaph with a quote must not break the command."""
        command = build_tellraw('Jonah said "goodbye" and left.')
        payload = json.loads(command[len("tellraw @a ") :])
        assert payload["text"] == 'Jonah said "goodbye" and left.'

    def test_backslash_is_escaped(self):
        command = build_tellraw("a\\b")
        assert json.loads(command[len("tellraw @a ") :])["text"] == "a\\b"

    def test_overlong_text_is_truncated(self):
        """The server silently truncates long commands, so do it deliberately."""
        command = build_tellraw("x" * 500)
        text = json.loads(command[len("tellraw @a ") :])["text"]
        assert len(text) <= MAX_ANNOUNCEMENT_LENGTH
        assert text.endswith("…")


@pytest.mark.unit
class TestRecording:
    def test_death_event_is_recorded(self, hall):
        record = hall.handle_event(death_event())
        assert record is not None
        assert record.player == "Jonah"
        assert record.category == "combat"
        assert record.culprit == "Zombie"
        assert "Jonah" in record.epitaph

    def test_non_death_events_are_ignored(self, hall):
        joined = GameEvent(type="join", timestamp="t", player="Jonah", data={})
        assert hall.handle_event(joined) is None
        assert hall.read() == []

    def test_death_without_a_player_is_ignored(self, hall):
        anonymous = GameEvent(type="death", timestamp="t", player=None, data={"cause": "drowned"})
        assert hall.handle_event(anonymous) is None

    def test_record_is_persisted(self, hall, tmp_path):
        hall.handle_event(death_event())
        files = list((tmp_path / "deaths").glob("*.jsonl"))
        assert len(files) == 1

        stored = json.loads(files[0].read_text().strip())
        assert stored["player"] == "Jonah"
        assert stored["epitaph"]

    def test_records_are_filed_by_the_death_date(self, hall, tmp_path):
        hall.handle_event(death_event(timestamp="2026-03-04T09:00:00+00:00"))
        assert (tmp_path / "deaths" / "2026-03-04.jsonl").exists()

    def test_reading_returns_newest_first(self, hall):
        hall.handle_event(death_event(player="Jonah", timestamp="2026-09-19T10:00:00+00:00"))
        hall.handle_event(death_event(player="Silas", timestamp="2026-09-19T11:00:00+00:00"))
        assert [r["player"] for r in hall.read()] == ["Silas", "Jonah"]

    def test_reading_filters_by_player(self, hall):
        hall.handle_event(death_event(player="Jonah"))
        hall.handle_event(death_event(player="Silas"))
        assert len(hall.read(player="Silas")) == 1

    def test_reading_filters_by_category(self, hall):
        hall.handle_event(death_event(cause="was slain by Zombie"))
        hall.handle_event(death_event(cause="fell from a high place"))
        assert len(hall.read(category="fall")) == 1

    def test_reading_respects_the_limit(self, hall):
        for index in range(10):
            hall.handle_event(death_event(timestamp=f"2026-09-19T10:0{index}:00+00:00"))
        assert len(hall.read(limit=3)) == 3

    def test_torn_final_line_is_skipped(self, hall, tmp_path):
        hall.handle_event(death_event())
        target = next((tmp_path / "deaths").glob("*.jsonl"))
        target.write_text(target.read_text() + '{"player": "broken"\n')
        assert len(hall.read()) == 1


@pytest.mark.unit
class TestAnnouncing:
    def test_epitaph_is_announced_in_game(self, hall, announcements):
        record = hall.handle_event(death_event())
        assert len(announcements) == 1
        assert announcements[0].startswith("tellraw @a ")
        assert record.announced is True

    def test_announcement_can_be_disabled(self, tmp_path, announcements):
        quiet = HallOfDeaths(deaths_dir=tmp_path / "deaths", announcer=announcements.append, announce=False)
        record = quiet.handle_event(death_event())
        assert announcements == []
        assert record.announced is False
        # The record is still kept for the dashboard.
        assert len(quiet.read()) == 1

    def test_a_failed_announcement_still_records_the_death(self, tmp_path):
        """The server being down must not cost us the epitaph."""

        def broken(_command):
            raise RuntimeError("server is stopped")

        errors = []
        hall = HallOfDeaths(deaths_dir=tmp_path / "deaths", announcer=broken)
        hall.set_error_logger(errors.append)

        record = hall.handle_event(death_event())

        assert record.announced is False
        assert len(hall.read()) == 1
        assert errors and "announce" in errors[0]

    def test_no_announcer_configured_is_harmless(self, tmp_path):
        hall = HallOfDeaths(deaths_dir=tmp_path / "deaths", announcer=None)
        assert hall.handle_event(death_event()) is not None

    def test_the_announced_text_is_the_epitaph(self, hall, announcements):
        record = hall.handle_event(death_event())
        payload = json.loads(announcements[0][len("tellraw @a ") :])
        assert payload["text"] == record.epitaph


@pytest.mark.unit
class TestLeaderboard:
    def test_ranks_by_death_count(self, hall):
        for index in range(3):
            hall.handle_event(death_event(player="Jonah", timestamp=f"2026-09-19T10:0{index}:00+00:00"))
        hall.handle_event(death_event(player="Silas", timestamp="2026-09-19T11:00:00+00:00"))

        board = hall.leaderboard()
        assert [entry["player"] for entry in board] == ["Jonah", "Silas"]
        assert board[0]["deaths"] == 3

    def test_reports_the_favourite_way_to_die(self, hall):
        hall.handle_event(death_event(cause="fell from a high place", timestamp="2026-09-19T10:00:00+00:00"))
        hall.handle_event(death_event(cause="hit the ground too hard", timestamp="2026-09-19T10:01:00+00:00"))
        hall.handle_event(death_event(cause="drowned", timestamp="2026-09-19T10:02:00+00:00"))

        assert hall.leaderboard()[0]["favourite_cause"] == "fall"

    def test_a_real_favourite_reports_its_count(self, hall):
        hall.handle_event(death_event(cause="drowned", timestamp="2026-09-19T10:00:00+00:00"))
        hall.handle_event(death_event(cause="drowned", timestamp="2026-09-19T10:01:00+00:00"))

        entry = hall.leaderboard()[0]
        assert entry["favourite_cause"] == "drowning"
        assert entry["favourite_cause_count"] == 2

    def test_no_repeated_cause_is_reported_as_a_count_of_one(self, hall):
        """Three deaths three ways has no mode, and callers must be able to tell."""
        hall.handle_event(death_event(cause="drowned", timestamp="2026-09-19T10:00:00+00:00"))
        hall.handle_event(death_event(cause="blew up", timestamp="2026-09-19T10:01:00+00:00"))
        hall.handle_event(death_event(cause="fell from a high place", timestamp="2026-09-19T10:02:00+00:00"))

        assert hall.leaderboard()[0]["favourite_cause_count"] == 1

    def test_tied_causes_resolve_the_same_way_every_time(self, hall):
        """Without a stable tie-break this followed dict insertion order."""
        hall.handle_event(death_event(cause="drowned", timestamp="2026-09-19T10:00:00+00:00"))
        hall.handle_event(death_event(cause="blew up", timestamp="2026-09-19T10:01:00+00:00"))

        assert hall.leaderboard()[0]["favourite_cause"] == hall.leaderboard()[0]["favourite_cause"]
        # Sorted by count then name, so the alphabetically first wins a tie.
        assert hall.leaderboard()[0]["favourite_cause"] == "drowning"

    def test_reports_the_latest_category(self, hall):
        hall.handle_event(death_event(cause="drowned", timestamp="2026-09-19T10:00:00+00:00"))
        hall.handle_event(death_event(cause="blew up", timestamp="2026-09-19T11:00:00+00:00"))

        assert hall.leaderboard()[0]["last_category"] == "explosion"

    def test_carries_the_most_recent_epitaph(self, hall):
        hall.handle_event(death_event(timestamp="2026-09-19T10:00:00+00:00"))
        hall.handle_event(death_event(cause="drowned", timestamp="2026-09-19T11:00:00+00:00"))

        entry = hall.leaderboard()[0]
        assert entry["last_epitaph"] in [r["epitaph"] for r in hall.read()]

    def test_ties_are_broken_by_name(self, hall):
        hall.handle_event(death_event(player="Silas", timestamp="2026-09-19T10:00:00+00:00"))
        hall.handle_event(death_event(player="Jonah", timestamp="2026-09-19T10:01:00+00:00"))
        assert [entry["player"] for entry in hall.leaderboard()] == ["Jonah", "Silas"]

    def test_respects_the_limit(self, hall):
        for name in ("Jonah", "Silas", "Alex"):
            hall.handle_event(death_event(player=name))
        assert len(hall.leaderboard(limit=2)) == 2

    def test_empty_hall_has_an_empty_leaderboard(self, hall):
        assert hall.leaderboard() == []


@pytest.mark.unit
class TestStats:
    def test_counts_deaths_and_players(self, hall):
        hall.handle_event(death_event(player="Jonah", timestamp="2026-09-19T10:00:00+00:00"))
        hall.handle_event(death_event(player="Silas", timestamp="2026-09-19T10:01:00+00:00"))

        stats = hall.stats()
        assert stats["total_deaths"] == 2
        assert stats["players"] == 2

    def test_reports_the_most_common_cause(self, hall):
        hall.handle_event(death_event(cause="drowned", timestamp="2026-09-19T10:00:00+00:00"))
        hall.handle_event(death_event(cause="drowned", timestamp="2026-09-19T10:01:00+00:00"))
        hall.handle_event(death_event(cause="blew up", timestamp="2026-09-19T10:02:00+00:00"))

        assert hall.stats()["most_common_cause"] == "drowning"

    def test_empty_hall_reports_nothing(self, hall):
        stats = hall.stats()
        assert stats["total_deaths"] == 0
        assert stats["most_common_cause"] is None


@pytest.mark.unit
class TestConfigAndRetention:
    def test_missing_config_uses_defaults(self, tmp_path):
        settings = load_deaths_config(tmp_path / "absent.conf")
        assert settings["announce"] is True
        assert settings["color"] == "gray"

    def test_config_is_parsed(self, tmp_path):
        config = tmp_path / "deaths.conf"
        config.write_text("# comment\nANNOUNCE_IN_GAME=false\nANNOUNCE_COLOR=red\nRETENTION_DAYS=30\n")

        settings = load_deaths_config(config)
        assert settings == {"announce": False, "color": "red", "retention_days": 30}

    @pytest.mark.parametrize("value", ["true", "TRUE", "yes", "on", "1"])
    def test_truthy_announce_values(self, tmp_path, value):
        config = tmp_path / "deaths.conf"
        config.write_text(f"ANNOUNCE_IN_GAME={value}\n")
        assert load_deaths_config(config)["announce"] is True

    def test_invalid_retention_falls_back(self, tmp_path):
        config = tmp_path / "deaths.conf"
        config.write_text("RETENTION_DAYS=forever\n")
        assert load_deaths_config(config)["retention_days"] == 365

    def test_old_files_are_pruned(self, tmp_path):
        deaths_dir = tmp_path / "deaths"
        deaths_dir.mkdir()
        (deaths_dir / "2020-01-01.jsonl").write_text("{}\n")
        (deaths_dir / "2999-01-01.jsonl").write_text("{}\n")

        assert HallOfDeaths(deaths_dir=deaths_dir, retention_days=30).prune() == 1
        assert (deaths_dir / "2999-01-01.jsonl").exists()

    def test_retention_can_be_disabled(self, tmp_path):
        deaths_dir = tmp_path / "deaths"
        deaths_dir.mkdir()
        (deaths_dir / "2020-01-01.jsonl").write_text("{}\n")
        assert HallOfDeaths(deaths_dir=deaths_dir, retention_days=0).prune() == 0


@pytest.mark.unit
class TestSharedHall:
    def test_get_hall_returns_a_singleton(self):
        assert get_hall() is get_hall()

    def test_reset_forces_a_rebuild(self):
        first = get_hall()
        reset_hall()
        assert get_hall() is not first

    def test_announcer_is_attached_on_first_supply(self):
        announcer = []
        hall = get_hall(announcer=announcer.append)
        assert hall.announcer is not None

    def test_unwritable_directory_does_not_raise(self, tmp_path):
        blocker = tmp_path / "deaths"
        blocker.write_text("a file, not a directory")

        errors = []
        hall = HallOfDeaths(deaths_dir=blocker)
        hall.set_error_logger(errors.append)
        hall.handle_event(death_event())

        assert errors and "record" in errors[0]


@pytest.mark.unit
class TestEndToEndThroughTheBus:
    def test_a_log_line_becomes_an_announced_epitaph(self, tmp_path, announcements):
        """The whole path: raw log line, typed event, epitaph, tellraw."""
        from api.events import EventBus

        bus = EventBus(events_dir=tmp_path / "events", flush_every_events=1)
        hall = HallOfDeaths(deaths_dir=tmp_path / "deaths", announcer=announcements.append)
        bus.subscribe(hall.handle_event)

        bus.handle_line("[16:06:40] [Server thread/INFO]: Jonah fell from a high place")

        assert len(announcements) == 1
        stored = hall.read()
        assert len(stored) == 1
        assert stored[0]["category"] == "fall"
        assert "Jonah" in stored[0]["epitaph"]

    def test_chat_that_mimics_a_death_produces_no_epitaph(self, tmp_path, announcements):
        """A kid typing a fake death message must not appear in the Hall."""
        from api.events import EventBus

        bus = EventBus(events_dir=tmp_path / "events", flush_every_events=1)
        hall = HallOfDeaths(deaths_dir=tmp_path / "deaths", announcer=announcements.append)
        bus.subscribe(hall.handle_event)

        bus.handle_line("[16:06:44] [Server thread/INFO]: <Silas> Jonah was slain by Zombie")

        assert announcements == []
        assert hall.read() == []


@pytest.mark.api
class TestDeathsEndpoints:
    """Tests for GET /api/deaths and GET /api/deaths/leaderboard."""

    @pytest.fixture(autouse=True)
    def hall_with_deaths(self, tmp_path, monkeypatch):
        hall = HallOfDeaths(deaths_dir=tmp_path / "deaths", announcer=None)
        hall.handle_event(death_event(player="Jonah", timestamp="2026-09-19T10:00:00+00:00"))
        hall.handle_event(
            death_event(player="Jonah", cause="fell from a high place", timestamp="2026-09-19T10:01:00+00:00")
        )
        hall.handle_event(death_event(player="Silas", cause="drowned", timestamp="2026-09-19T10:02:00+00:00"))

        monkeypatch.setattr("api.hall_of_deaths.get_hall", lambda *_args, **_kwargs: hall)
        return hall

    def test_requires_authentication(self, client):
        assert client.get("/api/deaths").status_code == 401

    def test_returns_deaths_newest_first(self, client, mock_api_keys):
        response = client.get("/api/deaths", headers={"X-API-Key": mock_api_keys})
        assert response.status_code == 200

        payload = response.get_json()
        assert [death["player"] for death in payload["deaths"]] == ["Silas", "Jonah", "Jonah"]
        assert payload["stats"]["total_deaths"] == 3

    def test_every_death_carries_an_epitaph(self, client, mock_api_keys):
        payload = client.get("/api/deaths", headers={"X-API-Key": mock_api_keys}).get_json()
        assert all(death["epitaph"] for death in payload["deaths"])

    def test_filters_by_player(self, client, mock_api_keys):
        payload = client.get("/api/deaths?player=Jonah", headers={"X-API-Key": mock_api_keys}).get_json()
        assert len(payload["deaths"]) == 2

    def test_filters_by_category(self, client, mock_api_keys):
        payload = client.get("/api/deaths?category=drowning", headers={"X-API-Key": mock_api_keys}).get_json()
        assert len(payload["deaths"]) == 1
        assert payload["deaths"][0]["player"] == "Silas"

    def test_respects_the_limit(self, client, mock_api_keys):
        payload = client.get("/api/deaths?limit=1", headers={"X-API-Key": mock_api_keys}).get_json()
        assert len(payload["deaths"]) == 1

    def test_limit_is_capped(self, client, mock_api_keys):
        response = client.get("/api/deaths?limit=100000", headers={"X-API-Key": mock_api_keys})
        assert response.status_code == 200

    def test_rejects_a_non_numeric_limit(self, client, mock_api_keys):
        assert client.get("/api/deaths?limit=many", headers={"X-API-Key": mock_api_keys}).status_code == 400

    def test_leaderboard_requires_authentication(self, client):
        assert client.get("/api/deaths/leaderboard").status_code == 401

    def test_leaderboard_ranks_players(self, client, mock_api_keys):
        payload = client.get("/api/deaths/leaderboard", headers={"X-API-Key": mock_api_keys}).get_json()
        board = payload["leaderboard"]
        assert board[0]["player"] == "Jonah"
        assert board[0]["deaths"] == 2
        assert "favourite_cause" in board[0]

    def test_leaderboard_rejects_a_non_numeric_limit(self, client, mock_api_keys):
        response = client.get("/api/deaths/leaderboard?limit=lots", headers={"X-API-Key": mock_api_keys})
        assert response.status_code == 400


@pytest.mark.unit
class TestAnnouncedIsPersisted:
    """`announced` has to survive the write, or the field is decorative.

    The record used to be written before the announcement was attempted, so the
    stored value was always false even when players had seen the epitaph.
    """

    def test_successful_announcement_is_stored_as_true(self, hall):
        hall.handle_event(death_event())
        assert hall.read()[0]["announced"] is True

    def test_failed_announcement_is_stored_as_false(self, tmp_path):
        def broken(_command):
            raise RuntimeError("server is stopped")

        hall = HallOfDeaths(deaths_dir=tmp_path / "deaths", announcer=broken)
        hall.set_error_logger(lambda _message: None)
        hall.handle_event(death_event())

        assert hall.read()[0]["announced"] is False

    def test_disabled_announcement_is_stored_as_false(self, tmp_path, announcements):
        hall = HallOfDeaths(deaths_dir=tmp_path / "deaths", announcer=announcements.append, announce=False)
        hall.handle_event(death_event())
        assert hall.read()[0]["announced"] is False

    def test_a_death_is_written_exactly_once(self, hall, tmp_path):
        """Patching the record afterwards must not append a second copy."""
        hall.handle_event(death_event())
        lines = [
            line
            for path in (tmp_path / "deaths").glob("*.jsonl")
            for line in path.read_text().splitlines()
            if line.strip()
        ]
        assert len(lines) == 1


@pytest.mark.unit
class TestBackgroundWorker:
    """Announcing must not run on the thread that follows the server log.

    In production the announcer goes through RCON with a connection timeout and
    then a shell fallback with its own, so an unreachable server could stall the
    follower for tens of seconds per death and hold up every later event.
    """

    def test_handler_returns_immediately_when_a_worker_is_running(self, tmp_path):
        import threading

        released = threading.Event()

        def slow(_command):
            released.wait(5)

        hall = HallOfDeaths(deaths_dir=tmp_path / "deaths", announcer=slow)
        hall.start_worker()
        try:
            # Would block for the announcer's duration without the worker.
            assert hall.handle_event(death_event()) is None
        finally:
            released.set()
            hall.stop_worker()

    def test_queued_death_is_eventually_recorded(self, tmp_path, announcements):
        hall = HallOfDeaths(deaths_dir=tmp_path / "deaths", announcer=announcements.append)
        hall.start_worker()
        try:
            hall.handle_event(death_event())
            assert hall.drain(timeout=5) is True
            assert len(hall.read()) == 1
            assert len(announcements) == 1
        finally:
            hall.stop_worker()

    def test_several_deaths_are_all_recorded(self, tmp_path, announcements):
        hall = HallOfDeaths(deaths_dir=tmp_path / "deaths", announcer=announcements.append)
        hall.start_worker()
        try:
            for index in range(5):
                hall.handle_event(death_event(timestamp=f"2026-09-19T10:0{index}:00+00:00"))
            assert hall.drain(timeout=5) is True
            assert len(hall.read()) == 5
        finally:
            hall.stop_worker()

    def test_a_failing_announcement_does_not_kill_the_worker(self, tmp_path):
        calls = {"count": 0}

        def sometimes_broken(_command):
            calls["count"] += 1
            if calls["count"] == 1:
                raise RuntimeError("first one fails")

        hall = HallOfDeaths(deaths_dir=tmp_path / "deaths", announcer=sometimes_broken)
        hall.set_error_logger(lambda _message: None)
        hall.start_worker()
        try:
            hall.handle_event(death_event(timestamp="2026-09-19T10:00:00+00:00"))
            hall.handle_event(death_event(timestamp="2026-09-19T10:01:00+00:00"))
            assert hall.drain(timeout=5) is True
            assert len(hall.read()) == 2
        finally:
            hall.stop_worker()

    def test_work_is_processed_inline_without_a_worker(self, hall):
        """Nothing starts a worker by default, so the handler stays synchronous."""
        assert hall.handle_event(death_event()) is not None

    def test_starting_twice_runs_one_worker(self, tmp_path, announcements):
        hall = HallOfDeaths(deaths_dir=tmp_path / "deaths", announcer=announcements.append)
        hall.start_worker()
        first = hall._worker
        hall.start_worker()
        try:
            assert hall._worker is first
        finally:
            hall.stop_worker()

    def test_stopping_without_starting_is_safe(self, tmp_path):
        HallOfDeaths(deaths_dir=tmp_path / "deaths").stop_worker()

    def test_drain_without_a_worker_returns_immediately(self, hall):
        assert hall.drain(timeout=0.1) is True

    def test_stopping_lets_queued_deaths_finish(self, tmp_path, announcements):
        hall = HallOfDeaths(deaths_dir=tmp_path / "deaths", announcer=announcements.append)
        hall.start_worker()
        hall.handle_event(death_event())
        hall.stop_worker(timeout=5)

        assert len(hall.read()) == 1
