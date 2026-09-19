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
from api.server import app  # noqa: E402


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
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

    def test_a_disabled_schedule_is_never_run(self, client, auth, schedule_file):
        """The enable/disable endpoints are only meaningful if the daemon
        honours the flag they write."""
        schedule_id = _create(client, auth, type="interval", interval_minutes=1).get_json()["schedule"]["id"]
        client.put(f"/api/scheduler/schedules/{schedule_id}/disable", headers=auth)
        scheduler = self._scheduler_module()

        stored = json.loads(schedule_file.read_text())["schedules"][0]

        assert scheduler.should_run_schedule(stored, datetime.now(timezone.utc)) is False


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
