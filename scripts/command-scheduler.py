#!/usr/bin/env python3
"""
Command Scheduler - Manages scheduled server commands
Enhanced with cron expressions, conditional execution, and event triggers
"""

import fcntl
import json
import os
import re
import subprocess
import sys
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

# Optional croniter for cron expressions
try:
    from croniter import croniter

    CRONITER_AVAILABLE = True
except ImportError:
    CRONITER_AVAILABLE = False
    croniter = None

PROJECT_ROOT = Path(__file__).parent.parent
SCHEDULE_FILE = PROJECT_ROOT / "config" / "command-schedule.json"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"


@contextmanager
def schedule_lock():
    """Hold an exclusive lock for the length of a read-modify-write.

    The API writes this file too. Without a lock, a timer pass that reads,
    runs commands and writes back can overwrite a schedule created through the
    API in between, and vice versa. The lock lives beside the file rather than
    on it, so it survives the atomic replace in save_schedule().
    """
    SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
    lock_path = SCHEDULE_FILE.with_name(SCHEDULE_FILE.name + ".lock")
    with open(lock_path, "w") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)


def load_schedule():
    """Load scheduled commands from file"""
    if SCHEDULE_FILE.exists():
        try:
            with open(SCHEDULE_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"schedules": []}
    return {"schedules": []}


def save_schedule(schedule_data):
    """Save scheduled commands to file, atomically.

    Truncating the file in place lets a concurrent reader see half a document;
    writing a sibling and renaming means a reader sees either the old file or
    the new one.
    """
    SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(SCHEDULE_FILE.parent), prefix=".schedule-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(schedule_data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, SCHEDULE_FILE)
    except BaseException:
        Path(tmp_path).unlink(missing_ok=True)
        raise
    return True


def execute_command(command):
    """Execute a server command via RCON"""
    try:
        rcon_script = SCRIPTS_DIR / "rcon-client.sh"
        if not rcon_script.exists():
            return False, "RCON client script not found"

        result = subprocess.run(
            [str(rcon_script), "command", command],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(PROJECT_ROOT),
        )
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr
    except subprocess.TimeoutExpired:
        return False, "Command execution timeout"
    except Exception as e:
        return False, str(e)


def check_and_run_schedules():
    """Check scheduled commands and run those that are due"""
    current_time = datetime.now(timezone.utc)

    # Read and write under one lock: the pass records last_run and run_count,
    # so without it an API write landing in between would be overwritten.
    with schedule_lock():
        schedule_data = load_schedule()
        schedules = schedule_data.get("schedules", [])

        for schedule in schedules:
            # One malformed record must not stop the rest. This loop used to
            # run bare, so a bad condition or an unparseable time took down the
            # whole pass — including the save below, losing the last_run of
            # commands that had already been executed.
            try:
                if not should_run_schedule(schedule, current_time):
                    continue

                command = schedule.get("command")
                if not command:
                    continue

                # Handle command templates with variables
                command = process_command_template(command, current_time)

                success, output = execute_command(command)
                # Log execution
                log_execution(schedule.get("id"), command, success, output, current_time)
                # Update last_run
                schedule["last_run"] = current_time.isoformat()
                schedule["run_count"] = schedule.get("run_count", 0) + 1

                # Handle one-time schedules
                if schedule.get("type") == "once":
                    schedule["enabled"] = False
            except Exception as exc:  # noqa: BLE001 - one bad schedule must not stop the others
                print(f"Schedule {schedule.get('id')} failed: {exc}", file=sys.stderr)

        # Save updated schedule data
        save_schedule(schedule_data)


def process_command_template(command, current_time):
    """Process command templates with variables"""
    # Replace {time} with current time
    command = command.replace("{time}", current_time.strftime("%H:%M"))
    command = command.replace("{date}", current_time.strftime("%Y-%m-%d"))

    # Replace {player_count} with actual player count
    player_count = get_player_count()
    command = command.replace("{player_count}", str(player_count))

    # Replace {datetime} with full datetime
    command = command.replace("{datetime}", current_time.isoformat())

    return command


def get_player_count():
    """Get current player count from server"""
    try:
        rcon_script = SCRIPTS_DIR / "rcon-client.sh"
        if not rcon_script.exists():
            return 0

        result = subprocess.run(
            [str(rcon_script), "command", "list"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(PROJECT_ROOT),
        )

        if result.returncode == 0 and result.stdout:
            # Parse "There are X of a max of Y players online"
            match = re.search(r"There are (\d+) of", result.stdout)
            if match:
                return int(match.group(1))
    except Exception:
        pass
    return 0


def check_condition(condition, current_time):
    """Check if a condition is met"""
    if not condition:
        return True

    # A hand-edited file can carry anything here. A string or a list used to
    # raise on .get() below, out through should_run_schedule() and into the
    # timer loop, which stopped every remaining schedule for that pass.
    if not isinstance(condition, dict):
        print(f"Ignoring malformed condition: {condition!r}", file=sys.stderr)
        return False

    condition_type = condition.get("type")

    if condition_type == "player_count":
        operator = condition.get("operator", ">")
        threshold = condition.get("value", 0)
        player_count = get_player_count()

        if operator == ">":
            return player_count > threshold
        elif operator == ">=":
            return player_count >= threshold
        elif operator == "<":
            return player_count < threshold
        elif operator == "<=":
            return player_count <= threshold
        elif operator == "==":
            return player_count == threshold

    elif condition_type == "time_range":
        # Check if current time is within range (e.g., peak hours)
        start_hour = condition.get("start_hour", 0)
        end_hour = condition.get("end_hour", 23)
        current_hour = current_time.hour
        return start_hour <= current_hour <= end_hour

    elif condition_type == "day_of_week":
        days = condition.get("days", [])  # List of weekday numbers
        return current_time.weekday() in days

    return True  # Default: condition met


def should_run_schedule(schedule, current_time):
    """Check if a schedule should run now"""
    # Check if enabled
    if not schedule.get("enabled", True):
        return False

    # Check condition first
    condition = schedule.get("condition")
    if condition and not check_condition(condition, current_time):
        return False

    schedule_type = schedule.get("type")  # "interval", "daily", "weekly", "cron", "once"
    last_run = schedule.get("last_run")

    if schedule_type == "interval":
        # Run every X minutes/hours
        interval_minutes = schedule.get("interval_minutes", 60)
        if last_run:
            last_run_time = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
            time_diff = (current_time - last_run_time).total_seconds() / 60
            return time_diff >= interval_minutes
        else:
            return True  # Never run, run now

    elif schedule_type == "daily":
        # Run at specific time daily
        run_time = schedule.get("run_time", "00:00")
        hour, minute = map(int, run_time.split(":"))
        current_hour = current_time.hour
        current_minute = current_time.minute

        if last_run:
            last_run_time = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
            # Only run if it's the right time and we haven't run today
            if current_hour == hour and current_minute == minute:
                return last_run_time.date() < current_time.date()
            return False
        else:
            return current_hour == hour and current_minute == minute

    elif schedule_type == "weekly":
        # Run on specific day at specific time
        day_of_week = schedule.get("day_of_week", 0)  # 0=Monday, 6=Sunday
        run_time = schedule.get("run_time", "00:00")
        hour, minute = map(int, run_time.split(":"))

        if current_time.weekday() == day_of_week:
            if last_run:
                last_run_time = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
                # Only run if right time and we haven't run this week
                if current_time.hour == hour and current_time.minute == minute:
                    return (current_time - last_run_time).days >= 7
                return False
            else:
                return current_time.hour == hour and current_time.minute == minute

    elif schedule_type == "cron":
        # Cron expression (requires croniter)
        if not CRONITER_AVAILABLE:
            return False

        cron_expr = schedule.get("cron_expression")
        if not cron_expr:
            return False

        try:
            # Work backwards from now to the slot that has most recently come
            # due. Asking croniter for the *next* slot after last_run meant a
            # cron that missed one tick could never catch up, and last_run_time
            # was never assigned in this branch at all, so the first run raised
            # UnboundLocalError into the except below and the schedule was
            # skipped silently from then on.
            previous_due = croniter(cron_expr, current_time).get_prev(datetime)

            if last_run:
                last_run_time = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
                return previous_due > last_run_time

            # Never run: only fire if that slot is the one we are standing in,
            # rather than replaying every slot since the schedule was created.
            return (current_time - previous_due).total_seconds() < 60
        except Exception:
            return False

    elif schedule_type == "once":
        # Run once at specific datetime
        run_datetime_str = schedule.get("run_datetime")
        if not run_datetime_str:
            return False

        try:
            run_datetime = datetime.fromisoformat(run_datetime_str.replace("Z", "+00:00"))
            if last_run:
                return False  # Already run
            # Run if current time is within 1 minute of scheduled time
            time_diff_seconds = abs((current_time - run_datetime).total_seconds())
            return time_diff_seconds < 60
        except Exception:
            return False

    return False


def log_execution(schedule_id, command, success, output, timestamp):
    """Log command execution"""
    log_file = PROJECT_ROOT / "config" / "command-schedule.log"
    log_entry = {
        "timestamp": timestamp.isoformat(),
        "schedule_id": schedule_id,
        "command": command,
        "success": success,
        "output": output[:500] if output else "",  # Limit output length
    }
    with open(log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")


def add_schedule(command, schedule_type, **kwargs):
    """Add a new scheduled command"""
    with schedule_lock():
        return _add_schedule_locked(command, schedule_type, **kwargs)


def _add_schedule_locked(command, schedule_type, **kwargs):
    schedule_data = load_schedule()
    schedules = schedule_data.get("schedules", [])

    schedule_id = str(uuid.uuid4())
    new_schedule = {
        "id": schedule_id,
        "command": command,
        "type": schedule_type,
        "enabled": kwargs.get("enabled", True),
        "created": datetime.now(timezone.utc).isoformat(),
        "run_count": 0,
    }

    # Add type-specific parameters
    if schedule_type == "interval":
        new_schedule["interval_minutes"] = kwargs.get("interval_minutes", 60)
    elif schedule_type == "daily":
        new_schedule["run_time"] = kwargs.get("run_time", "00:00")
    elif schedule_type == "weekly":
        new_schedule["day_of_week"] = kwargs.get("day_of_week", 0)
        new_schedule["run_time"] = kwargs.get("run_time", "00:00")
    elif schedule_type == "cron":
        new_schedule["cron_expression"] = kwargs.get("cron_expression")
    elif schedule_type == "once":
        new_schedule["run_datetime"] = kwargs.get("run_datetime")

    # Add condition if provided
    if "condition" in kwargs:
        new_schedule["condition"] = kwargs["condition"]

    schedules.append(new_schedule)
    schedule_data["schedules"] = schedules
    save_schedule(schedule_data)
    return schedule_id


def list_schedules():
    """List all scheduled commands"""
    schedule_data = load_schedule()
    schedules = schedule_data.get("schedules", [])
    return schedules


def remove_schedule(schedule_id):
    """Remove a scheduled command. Returns False if there was no such id."""
    with schedule_lock():
        schedule_data = load_schedule()
        schedules = schedule_data.get("schedules", [])
        remaining = [s for s in schedules if s.get("id") != schedule_id]

        # This used to return True either way, so the caller could not tell a
        # delete from a typo.
        if len(remaining) == len(schedules):
            return False

        schedule_data["schedules"] = remaining
        save_schedule(schedule_data)
        return True


def enable_schedule(schedule_id, enabled=True):
    """Enable or disable a scheduled command"""
    with schedule_lock():
        schedule_data = load_schedule()
        for schedule in schedule_data.get("schedules", []):
            if schedule.get("id") == schedule_id:
                schedule["enabled"] = enabled
                save_schedule(schedule_data)
                return True
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: command-scheduler.py {run|list|add|remove|enable|disable}")
        sys.exit(1)

    action = sys.argv[1]

    if action == "run":
        check_and_run_schedules()

    elif action == "list":
        schedules = list_schedules()
        print(json.dumps({"schedules": schedules}, indent=2))

    elif action == "add":
        if len(sys.argv) < 4:
            print("Usage: command-scheduler.py add <command> <type> [options]")
            sys.exit(1)
        command = sys.argv[2]
        schedule_type = sys.argv[3]
        # For CLI, you'd parse additional args, but this is simplified
        schedule_id = add_schedule(command, schedule_type)
        print(f"Schedule created: {schedule_id}")

    elif action == "remove":
        if len(sys.argv) < 3:
            print("Usage: command-scheduler.py remove <schedule_id>")
            sys.exit(1)
        schedule_id = sys.argv[2]
        if remove_schedule(schedule_id):
            print(f"Schedule removed: {schedule_id}")
        else:
            print(f"Schedule not found: {schedule_id}")
            sys.exit(1)

    elif action in ["enable", "disable"]:
        if len(sys.argv) < 3:
            action_usage = f"command-scheduler.py {action} <schedule_id>"
            print(f"Usage: {action_usage}")
            sys.exit(1)
        schedule_id = sys.argv[2]
        enabled = action == "enable"
        if enable_schedule(schedule_id, enabled):
            print(f"Schedule {action}d: {schedule_id}")
        else:
            print(f"Schedule not found: {schedule_id}")
            sys.exit(1)

    else:
        print(f"Unknown action: {action}")
        sys.exit(1)
