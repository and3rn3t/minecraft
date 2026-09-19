"""Tests for bedtime mode (api/bedtime.py).

Every scheduling method takes the current time as an argument, so a whole
evening can be walked through without waiting for one.
"""

import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.bedtime import (  # noqa: E402
    ACTION_ANNOUNCE,
    ACTION_KICK,
    ACTION_STOP,
    Bedtime,
    BedtimeConfig,
    get_bedtime,
    load_bedtime_config,
    parse_clock,
    reset_bedtime,
)
from api.events import GameEvent  # noqa: E402

# 2026-09-21 is a Monday, so 09-25 is a Friday.
MONDAY = date(2026, 9, 21)
FRIDAY = date(2026, 9, 25)


def at(day, hour, minute=0):
    return datetime.combine(day, time(hour, minute))


@pytest.fixture
def sent():
    return []


@pytest.fixture
def config():
    return BedtimeConfig(
        enabled=True,
        weeknight=time(20, 30),
        weekend=time(21, 30),
        wake=time(7, 0),
        weekend_nights=("friday", "saturday"),
        warn_minutes=(30, 10, 5, 1),
        extend_minutes=15,
        max_extensions=1,
        action=ACTION_KICK,
        bossbar=False,
    )


@pytest.fixture
def bed(config, sent):
    return Bedtime(config=config, runner=sent.append)


@pytest.fixture(autouse=True)
def clean_shared_bedtime():
    reset_bedtime()
    yield
    reset_bedtime()


def messages(sent, prefix):
    return [command for command in sent if command.startswith(prefix)]


@pytest.mark.unit
class TestClockParsing:
    def test_parses_a_time(self):
        assert parse_clock("21:05", time(0, 0)) == time(21, 5)

    @pytest.mark.parametrize("value", ["", "nonsense", "25:00", "9", None, "aa:bb"])
    def test_falls_back_on_nonsense(self, value):
        assert parse_clock(value, time(20, 30)) == time(20, 30)


@pytest.mark.unit
class TestConfig:
    def test_is_disabled_without_a_config_file(self, tmp_path):
        """Something that can stop the server must not enable itself."""
        assert load_bedtime_config(tmp_path / "absent.conf").enabled is False

    def test_reads_the_settings(self, tmp_path):
        path = tmp_path / "bedtime.conf"
        path.write_text(
            "# comment\n"
            "ENABLED=true\n"
            "WEEKNIGHT_BEDTIME=19:45\n"
            "WEEKEND_BEDTIME=22:00\n"
            "WAKE_TIME=06:30\n"
            "WEEKEND_NIGHTS=friday,saturday\n"
            "WARN_MINUTES=20,5,1\n"
            "EXTEND_MINUTES=10\n"
            "MAX_EXTENSIONS=2\n"
            "ACTION=kick\n"
            "BOSSBAR=false\n"
        )
        loaded = load_bedtime_config(path)

        assert loaded.enabled is True
        assert loaded.weeknight == time(19, 45)
        assert loaded.weekend == time(22, 0)
        assert loaded.wake == time(6, 30)
        assert loaded.warn_minutes == (20, 5, 1)
        assert loaded.extend_minutes == 10
        assert loaded.max_extensions == 2
        assert loaded.action == ACTION_KICK
        assert loaded.bossbar is False

    def test_warn_minutes_are_sorted_and_deduplicated(self, tmp_path):
        path = tmp_path / "bedtime.conf"
        path.write_text("WARN_MINUTES=5,30,5,bad,10,-2\n")
        assert load_bedtime_config(path).warn_minutes == (30, 10, 5)

    def test_an_unknown_action_is_ignored(self, tmp_path):
        path = tmp_path / "bedtime.conf"
        path.write_text("ACTION=launch_missiles\n")
        assert load_bedtime_config(path).action == ACTION_STOP

    def test_unknown_weekend_nights_are_dropped(self, tmp_path):
        path = tmp_path / "bedtime.conf"
        path.write_text("WEEKEND_NIGHTS=friday,caturday\n")
        assert load_bedtime_config(path).weekend_nights == ("friday",)

    def test_weeknight_and_weekend_bedtimes_are_selected_by_day(self, config):
        assert config.bedtime_for(MONDAY) == time(20, 30)
        assert config.bedtime_for(FRIDAY) == time(21, 30)


@pytest.mark.unit
class TestTheClosedWindow:
    def test_open_before_bedtime(self, bed):
        assert bed.is_closed(at(MONDAY, 20, 29)) is False

    def test_closed_after_bedtime(self, bed):
        assert bed.is_closed(at(MONDAY, 20, 31)) is True

    def test_still_closed_after_midnight(self, bed):
        """The window spans midnight, which is where off-by-one bugs live."""
        assert bed.is_closed(at(MONDAY + timedelta(days=1), 3, 0)) is True

    def test_closed_right_up_to_the_wake_time(self, bed):
        assert bed.is_closed(at(MONDAY + timedelta(days=1), 6, 59)) is True

    def test_open_again_after_the_wake_time(self, bed):
        assert bed.is_closed(at(MONDAY + timedelta(days=1), 7, 1)) is False

    def test_friday_night_gets_the_later_bedtime(self, bed):
        assert bed.is_closed(at(FRIDAY, 21, 0)) is False
        assert bed.is_closed(at(FRIDAY, 21, 31)) is True

    def test_nothing_is_closed_when_disabled(self, config, sent):
        config.enabled = False
        disabled = Bedtime(config=config, runner=sent.append)
        assert disabled.is_closed(at(MONDAY, 23, 0)) is False


@pytest.mark.unit
class TestCountdown:
    def walk(self, bed, sent, start, minutes):
        for offset in range(minutes + 1):
            bed.tick(start + timedelta(minutes=offset))
        return sent

    def test_each_warning_fires_once_at_its_mark(self, bed, sent):
        self.walk(bed, sent, at(MONDAY, 19, 55), 35)

        titles = messages(sent, "title")
        assert len(titles) == 4
        assert "30 minutes" in titles[0]
        assert "10 minutes" in titles[1]
        assert "5 minutes" in titles[2]
        assert "1 minute" in titles[3]

    def test_the_one_minute_warning_is_singular(self, bed, sent):
        self.walk(bed, sent, at(MONDAY, 20, 29), 1)
        assert any("1 minute until" in m and "minutes" not in m for m in messages(sent, "title"))

    def test_warnings_do_not_repeat_on_every_tick(self, bed, sent):
        for _ in range(20):
            bed.tick(at(MONDAY, 20, 25))
        assert len(messages(sent, "title")) == 1

    def test_a_late_start_announces_the_time_actually_left(self, bed, sent):
        """Starting inside the window must not announce the largest mark."""
        bed.tick(at(MONDAY, 20, 20))
        titles = messages(sent, "title")
        assert len(titles) == 1
        assert "10 minutes" in titles[0]

    def test_a_late_start_does_not_fire_the_bigger_marks_afterwards(self, bed, sent):
        bed.tick(at(MONDAY, 20, 20))
        sent.clear()
        bed.tick(at(MONDAY, 20, 21))
        assert messages(sent, "title") == []

    def test_no_warnings_long_before_bedtime(self, bed, sent):
        bed.tick(at(MONDAY, 15, 0))
        assert messages(sent, "title") == []

    def test_bedtime_says_goodnight_and_saves(self, bed, sent):
        bed.tick(at(MONDAY, 20, 31))
        assert any("Goodnight" in m for m in messages(sent, "tellraw"))
        assert "save-all" in sent

    def test_kick_action_removes_everyone(self, bed, sent):
        bed.tick(at(MONDAY, 20, 31))
        assert any(m.startswith("kick @a") for m in sent)

    def test_enforcement_happens_once(self, bed, sent):
        for offset in range(10):
            bed.tick(at(MONDAY, 20, 31) + timedelta(minutes=offset))
        assert len(messages(sent, "kick @a")) == 1

    def test_announce_action_does_not_remove_anyone(self, config, sent):
        config.action = ACTION_ANNOUNCE
        Bedtime(config=config, runner=sent.append).tick(at(MONDAY, 20, 31))
        assert messages(sent, "kick") == []
        assert any("Goodnight" in m for m in messages(sent, "tellraw"))

    def test_stop_action_uses_the_stopper(self, config, sent):
        config.action = ACTION_STOP
        stops = []
        Bedtime(config=config, runner=sent.append, stopper=lambda: stops.append(1)).tick(at(MONDAY, 20, 31))
        assert stops == [1]

    def test_stop_action_falls_back_to_the_stop_command(self, config, sent):
        config.action = ACTION_STOP
        Bedtime(config=config, runner=sent.append, stopper=None).tick(at(MONDAY, 20, 31))
        assert "stop" in sent

    def test_a_failing_stopper_is_reported_not_raised(self, config, sent):
        config.action = ACTION_STOP
        errors = []

        def broken():
            raise RuntimeError("compose is unhappy")

        bed = Bedtime(config=config, runner=sent.append, stopper=broken)
        bed.set_error_logger(errors.append)
        bed.tick(at(MONDAY, 20, 31))

        assert errors and "stop the server" in errors[0]

    def test_a_failing_command_is_reported_not_raised(self, config):
        errors = []

        def broken(_command):
            raise RuntimeError("server is down")

        bed = Bedtime(config=config, runner=broken)
        bed.set_error_logger(errors.append)
        bed.tick(at(MONDAY, 20, 31))

        assert errors

    def test_nothing_happens_when_disabled(self, config, sent):
        config.enabled = False
        Bedtime(config=config, runner=sent.append).tick(at(MONDAY, 20, 31))
        assert sent == []


@pytest.mark.unit
class TestBossbar:
    @pytest.fixture
    def bossbar_bed(self, config, sent):
        config.bossbar = True
        return Bedtime(config=config, runner=sent.append)

    def test_appears_inside_the_warning_window(self, bossbar_bed, sent):
        bossbar_bed.tick(at(MONDAY, 20, 15))
        assert any(m.startswith("bossbar add") for m in sent)

    def test_stays_hidden_outside_the_window(self, bossbar_bed, sent):
        bossbar_bed.tick(at(MONDAY, 17, 0))
        assert messages(sent, "bossbar") == []

    def test_is_created_once(self, bossbar_bed, sent):
        for offset in range(10):
            bossbar_bed.tick(at(MONDAY, 20, 15) + timedelta(seconds=offset * 30))
        assert len(messages(sent, "bossbar add")) == 1

    def test_value_counts_down(self, bossbar_bed, sent):
        bossbar_bed.tick(at(MONDAY, 20, 10))
        first = [m for m in sent if m.startswith("bossbar set") and " value " in m][-1]
        sent.clear()
        bossbar_bed.tick(at(MONDAY, 20, 20))
        later = [m for m in sent if m.startswith("bossbar set") and " value " in m][-1]

        assert int(later.rsplit(" ", 1)[1]) < int(first.rsplit(" ", 1)[1])

    def test_is_removed_at_bedtime(self, bossbar_bed, sent):
        bossbar_bed.tick(at(MONDAY, 20, 15))
        sent.clear()
        bossbar_bed.tick(at(MONDAY, 20, 31))
        assert any(m.startswith("bossbar remove") for m in sent)

    def test_can_be_turned_off(self, bed, sent):
        bed.tick(at(MONDAY, 20, 15))
        assert messages(sent, "bossbar") == []


@pytest.mark.unit
class TestControls:
    def test_extend_pushes_bedtime_back(self, bed):
        ok, _ = bed.extend(at(MONDAY, 20, 25))
        assert ok is True
        assert bed.bedtime_on(MONDAY) == at(MONDAY, 20, 45)

    def test_extend_is_limited(self, bed):
        bed.extend(at(MONDAY, 20, 25))
        ok, message = bed.extend(at(MONDAY, 20, 26))
        assert ok is False
        assert "extensions left" in message

    def test_extension_re_arms_the_warnings(self, bed, sent):
        """The warnings already given no longer describe the new deadline."""
        bed.tick(at(MONDAY, 20, 25))
        assert len(messages(sent, "title")) == 1

        bed.extend(at(MONDAY, 20, 26))
        sent.clear()
        bed.tick(at(MONDAY, 20, 40))

        assert any("5 minutes" in m for m in messages(sent, "title"))

    def test_extend_is_refused_after_bedtime_has_happened(self, bed):
        bed.tick(at(MONDAY, 20, 31))
        ok, message = bed.extend(at(MONDAY, 20, 32))
        assert ok is False
        assert "already happened" in message

    def test_extend_is_refused_when_disabled_in_config(self, config, sent):
        config.max_extensions = 0
        ok, message = Bedtime(config=config, runner=sent.append).extend(at(MONDAY, 20, 0))
        assert ok is False
        assert "disabled" in message

    def test_skip_opens_the_whole_night(self, bed):
        bed.skip_tonight(at(MONDAY, 19, 0))
        assert bed.is_closed(at(MONDAY, 23, 0)) is False

    def test_skip_moves_the_next_bedtime_to_tomorrow(self, bed):
        bed.skip_tonight(at(MONDAY, 19, 0))
        assert bed.next_bedtime(at(MONDAY, 19, 0)).date() == MONDAY + timedelta(days=1)

    def test_skip_is_refused_after_bedtime_has_happened(self, bed):
        bed.tick(at(MONDAY, 20, 31))
        ok, _ = bed.skip_tonight(at(MONDAY, 20, 32))
        assert ok is False

    def test_start_now_enforces_immediately(self, bed, sent):
        ok, _ = bed.start_now(at(MONDAY, 18, 0))
        assert ok is True
        assert any(m.startswith("kick @a") for m in sent)

    def test_start_now_is_refused_twice(self, bed):
        bed.start_now(at(MONDAY, 18, 0))
        ok, _ = bed.start_now(at(MONDAY, 18, 5))
        assert ok is False

    def test_a_new_evening_resets_everything(self, bed):
        bed.extend(at(MONDAY, 20, 25))
        bed.tick(at(MONDAY, 20, 50))

        tuesday = MONDAY + timedelta(days=1)
        status = bed.status(at(tuesday, 18, 0))
        assert status["extensions_used"] == 0
        assert status["skipped_tonight"] is False


@pytest.mark.unit
class TestClosedWindowEnforcement:
    def join(self, player="Jonah"):
        return GameEvent(type="join", timestamp="t", player=player, data={})

    def test_a_join_during_the_window_is_kicked(self, bed, sent):
        bed.on_player_join(self.join(), now=at(MONDAY, 22, 0))
        bed.run_pending()

        kicks = messages(sent, "kick Jonah")
        assert kicks and "closed until 07:00" in kicks[0]

    def test_a_join_outside_the_window_is_left_alone(self, bed, sent):
        bed.on_player_join(self.join(), now=at(MONDAY, 18, 0))
        bed.run_pending()
        assert sent == []

    def test_other_events_are_ignored(self, bed, sent):
        death = GameEvent(type="death", timestamp="t", player="Jonah", data={})
        bed.on_player_join(death, now=at(MONDAY, 22, 0))
        bed.run_pending()
        assert sent == []

    def test_a_skipped_night_lets_people_in(self, bed, sent):
        bed.skip_tonight(at(MONDAY, 19, 0))
        sent.clear()
        bed.on_player_join(self.join(), now=at(MONDAY, 22, 0))
        bed.run_pending()
        assert sent == []

    def test_the_kick_is_queued_not_sent_on_the_calling_thread(self, bed, sent):
        """Bus handlers run on the log follower; a network call must not block it."""
        bed.on_player_join(self.join(), now=at(MONDAY, 22, 0))

        assert sent == []
        assert bed.pending_actions() == 1

        assert bed.run_pending() == 1
        assert len(sent) == 1

    def test_run_pending_with_nothing_queued(self, bed):
        assert bed.run_pending() == 0


@pytest.mark.unit
class TestStatus:
    def test_reports_the_countdown(self, bed):
        status = bed.status(at(MONDAY, 20, 0))
        assert status["closed"] is False
        assert status["seconds_until_bedtime"] == 30 * 60
        assert status["next_bedtime"].endswith("20:30")

    def test_reports_the_closed_window(self, bed):
        status = bed.status(at(MONDAY, 22, 0))
        assert status["closed"] is True
        assert status["seconds_until_bedtime"] is None
        assert status["opens_at"].endswith("07:00")

    def test_reports_extension_budget(self, bed):
        bed.extend(at(MONDAY, 20, 0))
        status = bed.status(at(MONDAY, 20, 1))
        assert status["extensions_used"] == 1
        assert status["extensions_allowed"] == 1

    def test_reports_the_configured_times(self, bed):
        status = bed.status(at(MONDAY, 12, 0))
        assert status["weeknight_bedtime"] == "20:30"
        assert status["weekend_bedtime"] == "21:30"
        assert status["wake_time"] == "07:00"


@pytest.mark.unit
class TestSharedInstance:
    def test_returns_a_singleton(self):
        assert get_bedtime() is get_bedtime()

    def test_reset_rebuilds(self):
        first = get_bedtime()
        reset_bedtime()
        assert get_bedtime() is not first

    def test_runner_is_attached_on_first_supply(self, sent):
        assert get_bedtime(runner=sent.append).runner is not None

    def test_thread_starts_and_stops(self, bed):
        bed.start()
        try:
            assert bed._thread is not None
        finally:
            bed.stop()
        assert bed._thread is None

    def test_starting_twice_runs_one_thread(self, bed):
        bed.start()
        first = bed._thread
        bed.start()
        try:
            assert bed._thread is first
        finally:
            bed.stop()

    def test_stopping_without_starting_is_safe(self, bed):
        bed.stop()


@pytest.mark.api
class TestBedtimeEndpoints:
    """Tests for /api/bedtime and its three controls."""

    @pytest.fixture(autouse=True)
    def shared_bedtime(self, config, sent, monkeypatch):
        instance = Bedtime(config=config, runner=sent.append)
        monkeypatch.setattr("api.bedtime.get_bedtime", lambda *_args, **_kwargs: instance)
        return instance

    def test_status_requires_authentication(self, client):
        assert client.get("/api/bedtime").status_code == 401

    def test_status_reports_the_schedule(self, client, mock_api_keys):
        response = client.get("/api/bedtime", headers={"X-API-Key": mock_api_keys})
        assert response.status_code == 200

        payload = response.get_json()
        assert payload["enabled"] is True
        assert payload["weeknight_bedtime"] == "20:30"
        assert "seconds_until_bedtime" in payload

    def test_extend_requires_authentication(self, client):
        assert client.post("/api/bedtime/extend").status_code == 401

    def test_extend_grants_more_time(self, client, mock_api_keys, shared_bedtime):
        response = client.post("/api/bedtime/extend", headers={"X-API-Key": mock_api_keys})
        assert response.status_code == 200

        payload = response.get_json()
        assert payload["success"] is True
        assert payload["status"]["extensions_used"] == 1

    def test_a_refused_extension_is_a_conflict_not_an_error(self, client, mock_api_keys):
        """The request was fine; the server simply will not do it again."""
        client.post("/api/bedtime/extend", headers={"X-API-Key": mock_api_keys})
        response = client.post("/api/bedtime/extend", headers={"X-API-Key": mock_api_keys})

        assert response.status_code == 409
        assert response.get_json()["success"] is False

    def test_skip_cancels_tonight(self, client, mock_api_keys):
        response = client.post("/api/bedtime/skip", headers={"X-API-Key": mock_api_keys})
        assert response.status_code == 200
        assert response.get_json()["status"]["skipped_tonight"] is True

    def test_start_now_enforces_immediately(self, client, mock_api_keys, sent):
        response = client.post("/api/bedtime/now", headers={"X-API-Key": mock_api_keys})
        assert response.status_code == 200
        assert any(command.startswith("kick @a") for command in sent)

    def test_start_now_twice_is_a_conflict(self, client, mock_api_keys):
        client.post("/api/bedtime/now", headers={"X-API-Key": mock_api_keys})
        response = client.post("/api/bedtime/now", headers={"X-API-Key": mock_api_keys})
        assert response.status_code == 409
