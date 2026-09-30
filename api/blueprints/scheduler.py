"""Scheduled commands: config/command-schedule.json CRUD, guarded by a file
lock shared with scripts/command-scheduler.py, the daemon that actually fires
them.
"""

import fcntl
import json
import os
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from flask import Blueprint, jsonify, request

from api import server

bp = Blueprint("scheduler", __name__)


@bp.route("/api/scheduler/schedules", methods=["GET"])
@server.require_permission("server.command")
def list_schedules():
    """List all scheduled commands"""
    return jsonify({"success": True, "schedules": _load_schedules().get("schedules", [])}), 200


# The types scripts/command-scheduler.py knows how to fire. Anything else would
# be written to the file and then silently never run.
SCHEDULE_TYPES = ("interval", "daily", "weekly", "cron", "once")


@contextmanager
def _schedule_lock():
    """Hold an exclusive lock for the length of a read-modify-write.

    scripts/command-scheduler.py writes this file too, recording last_run and
    run_count on every pass. Without a lock, a pass that started before an API
    write lands will write the pre-edit list back over it, and a reader can
    catch the file mid-truncate. The daemon takes the same lock on the same
    path, so the two exclude each other.
    """
    server.SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
    lock_path = server.SCHEDULE_FILE.with_name(server.SCHEDULE_FILE.name + ".lock")
    with open(lock_path, "w") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)


def _load_schedules():
    """Read the schedule file the scheduler daemon runs from."""
    if not server.SCHEDULE_FILE.exists():
        return {"schedules": []}
    try:
        with open(server.SCHEDULE_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        # Matches the daemon, which also treats an unreadable file as empty
        # rather than refusing to run at all.
        server.app.logger.error("Schedule file is not valid JSON; treating it as empty")
        return {"schedules": []}


def _save_schedules(schedule_data):
    """Write the schedule file back, atomically.

    Truncating in place lets the daemon read half a document; writing a
    sibling and renaming means it sees either the old file or the new one.
    """
    server.SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(server.SCHEDULE_FILE.parent), prefix=".schedule-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(schedule_data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, server.SCHEDULE_FILE)
    except BaseException:
        Path(tmp_path).unlink(missing_ok=True)
        raise


def _schedule_type_fields(schedule_type, data):
    """Pick out the fields a given schedule type needs.

    Returns (fields, error). The defaults match
    ``scripts/command-scheduler.py``'s own reader, so a record written here
    behaves the same as one the script wrote.
    """
    if schedule_type == "interval":
        return {"interval_minutes": data.get("interval_minutes", 60)}, None
    if schedule_type == "daily":
        return {"run_time": data.get("run_time", "00:00")}, None
    if schedule_type == "weekly":
        return {
            "day_of_week": data.get("day_of_week", 0),
            "run_time": data.get("run_time", "00:00"),
        }, None
    if schedule_type == "cron":
        expression = data.get("cron_expression")
        if not expression:
            return None, "cron_expression is required for cron schedules"
        return {"cron_expression": expression}, None
    if schedule_type == "once":
        run_datetime = data.get("run_datetime")
        if not run_datetime:
            return None, "run_datetime is required for once schedules"
        return {"run_datetime": run_datetime}, None
    return None, f"Invalid type. Valid types: {', '.join(SCHEDULE_TYPES)}"


@bp.route("/api/scheduler/schedules", methods=["POST"])
@server.require_permission("server.command")
def create_schedule():
    """Create a new scheduled command"""
    data = request.get_json() or {}
    command = data.get("command")
    schedule_type = data.get("type", "interval")
    enabled = data.get("enabled", True)

    if not command:
        return jsonify({"error": "Command required"}), 400

    type_fields, error = _schedule_type_fields(schedule_type, data)
    if error:
        return jsonify({"error": error}), 400

    condition = data.get("condition")
    if condition is not None and not isinstance(condition, dict):
        return jsonify({"error": "condition must be an object"}), 400

    schedule = {
        "id": str(uuid.uuid4()),
        "command": command,
        "type": schedule_type,
        "enabled": enabled,
        "created": datetime.now(timezone.utc).isoformat(),
        "last_run": None,
        # The scheduler increments this; start it where the script does so
        # a record created here is indistinguishable from one it wrote.
        "run_count": 0,
    }
    schedule.update(type_fields)

    if condition:
        schedule["condition"] = condition

    with _schedule_lock():
        schedule_data = _load_schedules()
        schedule_data.setdefault("schedules", []).append(schedule)
        _save_schedules(schedule_data)

    username = server.get_username_from_request()
    server.log_audit_event(username, "scheduler.create", {"schedule_id": schedule["id"], "command": command})

    return jsonify({"success": True, "schedule": schedule}), 201


@bp.route("/api/scheduler/schedules/<schedule_id>/enable", methods=["PUT"])
@server.require_permission("server.command")
def enable_schedule(schedule_id):
    """Enable a scheduled command"""
    return _set_schedule_enabled(schedule_id, True)


@bp.route("/api/scheduler/schedules/<schedule_id>/disable", methods=["PUT"])
@server.require_permission("server.command")
def disable_schedule(schedule_id):
    """Disable a scheduled command"""
    return _set_schedule_enabled(schedule_id, False)


def _set_schedule_enabled(schedule_id, enabled):
    """Shared body of the enable and disable endpoints."""
    with _schedule_lock():
        schedule_data = _load_schedules()
        target = next((s for s in schedule_data.get("schedules", []) if s.get("id") == schedule_id), None)
        if target is None:
            return jsonify({"error": "Schedule not found"}), 404

        target["enabled"] = enabled
        _save_schedules(schedule_data)

    server.log_audit_event(
        server.get_username_from_request(),
        "scheduler.enable" if enabled else "scheduler.disable",
        {"schedule_id": schedule_id},
    )
    return (
        jsonify(
            {
                "success": True,
                "message": f"Schedule {'enabled' if enabled else 'disabled'}",
                "schedule": target,
            }
        ),
        200,
    )


@bp.route("/api/scheduler/schedules/<schedule_id>", methods=["PUT"])
@server.require_permission("server.command")
def update_schedule(schedule_id):
    """Update a scheduled command"""
    data = request.get_json() or {}

    if "condition" in data and data["condition"] is not None and not isinstance(data["condition"], dict):
        return jsonify({"error": "condition must be an object"}), 400

    with _schedule_lock():
        return _update_schedule_locked(schedule_id, data)


def _update_schedule_locked(schedule_id, data):
    """Body of the update endpoint, run while holding the schedule lock."""
    schedule_data = _load_schedules()

    schedule = next((s for s in schedule_data.get("schedules", []) if s.get("id") == schedule_id), None)
    if not schedule:
        return jsonify({"error": "Schedule not found"}), 404

    # A type change brings its own required fields with it, so validate the
    # result rather than letting a schedule end up as, say, a cron with no
    # expression — which the scheduler would skip forever without saying so.
    new_type = data.get("type", schedule.get("type"))
    if new_type not in SCHEDULE_TYPES:
        return jsonify({"error": f"Invalid type. Valid types: {', '.join(SCHEDULE_TYPES)}"}), 400

    merged = {**schedule, **{k: v for k, v in data.items() if k != "type"}}
    type_fields, error = _schedule_type_fields(new_type, merged)
    if error:
        return jsonify({"error": error}), 400

    if "command" in data:
        schedule["command"] = data["command"]
    if "enabled" in data:
        schedule["enabled"] = data["enabled"]
    if "condition" in data:
        if data["condition"]:
            schedule["condition"] = data["condition"]
        else:
            schedule.pop("condition", None)

    # Drop the old type's fields so a schedule switched from daily to
    # interval doesn't keep a stale run_time hanging off it.
    for stale in ("interval_minutes", "run_time", "day_of_week", "cron_expression", "run_datetime"):
        schedule.pop(stale, None)
    schedule["type"] = new_type
    schedule.update(type_fields)

    _save_schedules(schedule_data)

    server.log_audit_event(server.get_username_from_request(), "scheduler.update", {"schedule_id": schedule_id})

    return jsonify({"success": True, "schedule": schedule}), 200


@bp.route("/api/scheduler/schedules/<schedule_id>", methods=["DELETE"])
@server.require_permission("server.command")
def delete_schedule(schedule_id):
    """Delete a scheduled command"""
    with _schedule_lock():
        schedule_data = _load_schedules()
        schedules = schedule_data.get("schedules", [])

        remaining = [s for s in schedules if s.get("id") != schedule_id]
        # Reporting success for an id that was never there hides a typo in
        # the caller, and the old handler did exactly that.
        if len(remaining) == len(schedules):
            return jsonify({"error": "Schedule not found"}), 404

        schedule_data["schedules"] = remaining
        _save_schedules(schedule_data)

    username = server.get_username_from_request()
    server.log_audit_event(username, "scheduler.delete", {"schedule_id": schedule_id})

    return jsonify({"success": True, "message": "Schedule deleted"}), 200
