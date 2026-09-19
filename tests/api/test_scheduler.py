#!/usr/bin/env python3
"""
Tests for the command scheduler API.

Two HTTP surfaces used to front config/command-schedule.json: /api/scheduler/*
and /api/commands/schedule*. The second dropped every option it was given, so
the first is the one that survives; these tests pin the behaviour that made
that the right choice.
"""

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path as PathLib

import pytest

PROJECT_ROOT = PathLib(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import api.server as api_module  # noqa: E402


@pytest.fixture
def client():
    api_module.app.config["TESTING"] = True
    with api_module.app.test_client() as client:
        yield client


@pytest.fixture
def schedule_file(tmp_path, monkeypatch):
    """Point the API at a throwaway schedule file."""
    path = tmp_path / "command-schedule.json"
    monkeypatch.setattr(api_module, "SCHEDULE_FILE", path)
    return path


@pytest.fixture
def auth(monkeypatch):
    """An admin-scoped key, since scheduling needs server.command."""
    key = "scheduler-test-key"
    monkeypatch.setitem(api_module.API_KEYS, key, {"name": "t", "enabled": True, "role": "admin"})
    return {"X-API-Key": key}


def _create(client, auth, **body):
    body.setdefault("command", "list")
    return client.post("/api/scheduler/schedules", headers=auth, json=body)


class TestCreateSchedule:
    def test_interval_minutes_are_kept(self, client, auth, schedule_file):
        """The old /api/commands/schedule piped options to a script that never
        read stdin, so a 5-minute interval was silently stored as 60."""
        response = _create(client, auth, type="interval", interval_minutes=5)

        assert response.status_code == 201
        assert response.get_json()["schedule"]["interval_minutes"] == 5

        stored = json.loads(schedule_file.read_text())["schedules"][0]
        assert stored["interval_minutes"] == 5

    def test_a_real_id_comes_back(self, client, auth, schedule_file):
        """The removed endpoint returned the script's chatter,
        'Schedule created: <uuid>', as if it were the id."""
        schedule_id = _create(client, auth, type="interval").get_json()["schedule"]["id"]

        assert "Schedule created" not in schedule_id
        assert len(schedule_id) == 36

    @pytest.mark.parametrize(
        "body,field",
        [
            ({"type": "interval", "interval_minutes": 15}, "interval_minutes"),
            ({"type": "daily", "run_time": "03:30"}, "run_time"),
            ({"type": "weekly", "day_of_week": 5, "run_time": "21:00"}, "run_time"),
            ({"type": "cron", "cron_expression": "0 3 * * *"}, "cron_expression"),
            ({"type": "once", "run_datetime": "2027-01-01T00:00:00+00:00"}, "run_datetime"),
        ],
    )
    def test_every_type_the_scheduler_understands(self, client, auth, schedule_file, body, field):
        """All five types the daemon can fire are creatable through the API"""
        response = _create(client, auth, **body)

        assert response.status_code == 201
        assert field in response.get_json()["schedule"]

    def test_unknown_type_is_rejected(self, client, auth, schedule_file):
        """A type the scheduler cannot fire would sit in the file forever"""
        response = _create(client, auth, type="hourly")

        assert response.status_code == 400
        assert not schedule_file.exists()

    def test_cron_requires_an_expression(self, client, auth, schedule_file):
        """A cron with no expression is skipped silently by the scheduler"""
        response = _create(client, auth, type="cron")

        assert response.status_code == 400

    def test_once_requires_a_datetime(self, client, auth, schedule_file):
        response = _create(client, auth, type="once")

        assert response.status_code == 400

    def test_command_is_required(self, client, auth, schedule_file):
        response = client.post("/api/scheduler/schedules", headers=auth, json={"type": "interval"})

        assert response.status_code == 400

    def test_a_condition_is_carried_through(self, client, auth, schedule_file):
        """Conditions were only offered by the endpoint that discarded them"""
        response = _create(client, auth, type="interval", condition={"min_players": 1})

        assert response.status_code == 201
        assert response.get_json()["schedule"]["condition"] == {"min_players": 1}

    def test_record_matches_what_the_script_writes(self, client, auth, schedule_file):
        """run_count is set by the script's own writer; a record created here
        has to be indistinguishable from one it wrote."""
        schedule = _create(client, auth, type="interval").get_json()["schedule"]

        assert schedule["run_count"] == 0
        assert schedule["last_run"] is None
        assert schedule["enabled"] is True


class TestEnableDisable:
    def test_disable_then_enable(self, client, auth, schedule_file):
        """These only existed on the removed surface, so the web UI had no
        way to pause a schedule."""
        schedule_id = _create(client, auth, type="interval").get_json()["schedule"]["id"]

        disabled = client.put(f"/api/scheduler/schedules/{schedule_id}/disable", headers=auth)
        assert disabled.status_code == 200
        assert json.loads(schedule_file.read_text())["schedules"][0]["enabled"] is False

        enabled = client.put(f"/api/scheduler/schedules/{schedule_id}/enable", headers=auth)
        assert enabled.status_code == 200
        assert json.loads(schedule_file.read_text())["schedules"][0]["enabled"] is True

    def test_unknown_id_is_not_found(self, client, auth, schedule_file):
        _create(client, auth, type="interval")

        response = client.put("/api/scheduler/schedules/nope/disable", headers=auth)
        assert response.status_code == 404


class TestUpdateSchedule:
    def test_changing_type_drops_the_old_type_fields(self, client, auth, schedule_file):
        """A daily switched to interval must not keep a stale run_time"""
        schedule_id = _create(client, auth, type="daily", run_time="04:00").get_json()["schedule"]["id"]

        response = client.put(
            f"/api/scheduler/schedules/{schedule_id}",
            headers=auth,
            json={"type": "interval", "interval_minutes": 30},
        )

        assert response.status_code == 200
        updated = response.get_json()["schedule"]
        assert updated["interval_minutes"] == 30
        assert "run_time" not in updated

    def test_switching_to_cron_without_an_expression_is_refused(self, client, auth, schedule_file):
        """Otherwise the schedule becomes one the daemon skips forever"""
        schedule_id = _create(client, auth, type="interval").get_json()["schedule"]["id"]

        response = client.put(
            f"/api/scheduler/schedules/{schedule_id}", headers=auth, json={"type": "cron"}
        )

        assert response.status_code == 400
        assert json.loads(schedule_file.read_text())["schedules"][0]["type"] == "interval"

    def test_unknown_id_is_not_found(self, client, auth, schedule_file):
        response = client.put(
            "/api/scheduler/schedules/nope", headers=auth, json={"enabled": False}
        )

        assert response.status_code == 404


class TestDeleteSchedule:
    def test_delete_removes_it(self, client, auth, schedule_file):
        schedule_id = _create(client, auth, type="interval").get_json()["schedule"]["id"]

        response = client.delete(f"/api/scheduler/schedules/{schedule_id}", headers=auth)

        assert response.status_code == 200
        assert json.loads(schedule_file.read_text())["schedules"] == []

    def test_deleting_an_unknown_id_is_not_found(self, client, auth, schedule_file):
        """The old handler filtered the list and reported success either way,
        so a typo looked like a successful delete."""
        _create(client, auth, type="interval")

        response = client.delete("/api/scheduler/schedules/nope", headers=auth)

        assert response.status_code == 404
        assert len(json.loads(schedule_file.read_text())["schedules"]) == 1


class TestRemovedSurface:
    @pytest.mark.parametrize(
        "method,path",
        [
            ("get", "/api/commands/schedules"),
            ("post", "/api/commands/schedule"),
            ("delete", "/api/commands/schedule/abc"),
            ("put", "/api/commands/schedule/abc/enable"),
            ("put", "/api/commands/schedule/abc/disable"),
        ],
    )
    def test_the_duplicate_api_is_gone(self, client, auth, method, path):
        """One HTTP surface per file, so the two cannot drift apart again"""
        response = getattr(client, method)(path, headers=auth)

        assert response.status_code == 404


class TestSchedulerDaemonAgreement:
    """The API writes the file; scripts/command-scheduler.py reads it. If they
    disagree about field names a schedule is accepted and then never fires."""

    @staticmethod
    def _scheduler_module():
        spec = importlib.util.spec_from_file_location(
            "command_scheduler", PROJECT_ROOT / "scripts" / "command-scheduler.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    @pytest.mark.parametrize(
        "body",
        [
            {"type": "interval", "interval_minutes": 15},
            {"type": "daily", "run_time": "03:30"},
            {"type": "weekly", "day_of_week": 5, "run_time": "21:00"},
            {"type": "once", "run_datetime": "2027-01-01T00:00:00+00:00"},
        ],
    )
    def test_the_daemon_understands_what_the_api_writes(self, client, auth, schedule_file, body):
        """should_run_schedule returns a decision rather than failing on a
        record it doesn't recognise."""
        _create(client, auth, **body)
        scheduler = self._scheduler_module()

        stored = json.loads(schedule_file.read_text())["schedules"][0]
        decision = scheduler.should_run_schedule(stored, datetime.now(timezone.utc))

        assert decision in (True, False)

    def test_a_cron_schedule_runs_more_than_once(self, client, auth, schedule_file):
        """The cron branch read a last_run_time it never assigned, so the
        first run raised into its own except and the schedule was skipped
        silently from then on."""
        from datetime import timedelta

        scheduler = self._scheduler_module()
        if not scheduler.CRONITER_AVAILABLE:
            pytest.skip("croniter not installed")

        _create(client, auth, type="cron", cron_expression="* * * * *")
        stored = json.loads(schedule_file.read_text())["schedules"][0]
        now = datetime.now(timezone.utc)

        # Having already run five minutes ago, a per-minute cron is due again.
        stored["last_run"] = (now - timedelta(minutes=5)).isoformat()

        assert scheduler.should_run_schedule(stored, now) is True

    def test_a_cron_that_just_ran_is_not_due_again(self, client, auth, schedule_file):
        """The other half: it must not fire on every pass either"""
        from datetime import timedelta

        scheduler = self._scheduler_module()
        if not scheduler.CRONITER_AVAILABLE:
            pytest.skip("croniter not installed")

        _create(client, auth, type="cron", cron_expression="0 3 * * *")
        stored = json.loads(schedule_file.read_text())["schedules"][0]
        now = datetime.now(timezone.utc)
        stored["last_run"] = (now - timedelta(seconds=30)).isoformat()

        assert scheduler.should_run_schedule(stored, now) is False

    def test_one_bad_record_does_not_stop_the_others(self, client, auth, schedule_file, monkeypatch):
        """A malformed condition used to raise out of the loop, skipping every
        remaining schedule and losing the last_run of ones already run."""
        scheduler = self._scheduler_module()
        monkeypatch.setattr(scheduler, "SCHEDULE_FILE", schedule_file)
        monkeypatch.setattr(scheduler, "execute_command", lambda command: (True, "ok"))
        monkeypatch.setattr(scheduler, "log_execution", lambda *a, **k: None)

        schedule_file.write_text(
            json.dumps(
                {
                    "schedules": [
                        {
                            "id": "bad",
                            "type": "interval",
                            "enabled": True,
                            "interval_minutes": 1,
                            "condition": "whenever",
                            "command": "list",
                        },
                        {
                            "id": "good",
                            "type": "interval",
                            "enabled": True,
                            "interval_minutes": 1,
                            "command": "list",
                        },
                    ]
                }
            )
        )

        scheduler.check_and_run_schedules()

        after = {s["id"]: s for s in json.loads(schedule_file.read_text())["schedules"]}
        assert after["good"]["run_count"] == 1, "the healthy schedule still ran"
        assert after["good"]["last_run"] is not None, "and the pass still saved its result"

    def test_a_disabled_schedule_is_never_run(self, client, auth, schedule_file):
        """The enable/disable endpoints are only meaningful if the daemon
        honours the flag they write."""
        schedule_id = _create(client, auth, type="interval", interval_minutes=1).get_json()["schedule"]["id"]
        client.put(f"/api/scheduler/schedules/{schedule_id}/disable", headers=auth)
        scheduler = self._scheduler_module()

        stored = json.loads(schedule_file.read_text())["schedules"][0]

        assert scheduler.should_run_schedule(stored, datetime.now(timezone.utc)) is False


class TestConditionValidation:
    """A condition that is not an object reaches check_condition() and raises
    on .get(), out through should_run_schedule() and into the timer loop."""

    @pytest.mark.parametrize("condition", ["whenever", 42, ["a", "b"], True])
    def test_a_non_object_condition_is_refused(self, client, auth, schedule_file, condition):
        response = _create(client, auth, type="interval", condition=condition)

        assert response.status_code == 400
        assert not schedule_file.exists()

    def test_update_refuses_a_non_object_condition(self, client, auth, schedule_file):
        schedule_id = _create(client, auth, type="interval").get_json()["schedule"]["id"]

        response = client.put(
            f"/api/scheduler/schedules/{schedule_id}", headers=auth, json={"condition": "whenever"}
        )

        assert response.status_code == 400
        assert "condition" not in json.loads(schedule_file.read_text())["schedules"][0]

    def test_an_object_condition_is_still_accepted(self, client, auth, schedule_file):
        response = _create(client, auth, type="interval", condition={"type": "player_count", "value": 1})

        assert response.status_code == 201


class TestAtomicWrites:
    """The daemon writes this file too, on every pass."""

    def test_concurrent_writers_do_not_lose_entries(self, schedule_file):
        """Read-modify-write without a lock drops entries when two writers
        interleave, and Flask serves requests on threads.

        This drives the store helpers rather than the HTTP client, because a
        Flask test client cannot be shared across threads — the failure would
        be the harness, not the thing under test.
        """
        import threading

        errors = []

        def add(i):
            try:
                with api_module._schedule_lock():
                    data = api_module._load_schedules()
                    data.setdefault("schedules", []).append({"id": str(i), "command": f"say {i}"})
                    api_module._save_schedules(data)
            except Exception as exc:  # noqa: BLE001 - surfaced by the assert below
                errors.append(exc)

        threads = [threading.Thread(target=add, args=(i,)) for i in range(25)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == []
        stored = json.loads(schedule_file.read_text())["schedules"]
        assert len(stored) == 25, "an unlocked read-modify-write loses entries here"
        assert len({s["id"] for s in stored}) == 25

    def test_the_daemon_and_the_api_take_the_same_lock(self, schedule_file, monkeypatch):
        """The two processes only exclude each other if they agree on the path"""
        spec = importlib.util.spec_from_file_location(
            "command_scheduler_lock", PROJECT_ROOT / "scripts" / "command-scheduler.py"
        )
        scheduler = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scheduler)
        monkeypatch.setattr(scheduler, "SCHEDULE_FILE", schedule_file)

        with api_module._schedule_lock():
            pass
        with scheduler.schedule_lock():
            pass

        locks = list(schedule_file.parent.glob("*.lock"))
        assert len(locks) == 1, f"expected one shared lock file, found {locks}"

    def test_no_temp_files_are_left_behind(self, client, auth, schedule_file):
        """The atomic write renames a sibling into place"""
        _create(client, auth, type="interval")

        assert list(schedule_file.parent.glob(".schedule-*.tmp")) == []

    def test_an_unreadable_file_does_not_take_the_api_down(self, client, auth, schedule_file):
        """A truncated file should read as empty, the way the daemon treats it"""
        schedule_file.write_text("{ not json")

        response = client.get("/api/scheduler/schedules", headers=auth)

        assert response.status_code == 200
        assert response.get_json()["schedules"] == []


class TestSchedulerPermissions:
    def test_scheduling_requires_authentication(self, client, schedule_file):
        response = client.post("/api/scheduler/schedules", json={"command": "list"})

        assert response.status_code in (401, 403)

    def test_a_read_only_key_cannot_schedule(self, client, schedule_file, monkeypatch):
        """Scheduling runs commands, so it needs server.command"""
        key = "readonly-scheduler-key"
        monkeypatch.setitem(api_module.API_KEYS, key, {"name": "ro", "enabled": True, "role": "user"})

        response = client.post(
            "/api/scheduler/schedules", headers={"X-API-Key": key}, json={"command": "list"}
        )

        assert response.status_code == 403
