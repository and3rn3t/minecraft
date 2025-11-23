#!/usr/bin/env python3
"""
Command Scheduler - Manages scheduled server commands
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SCHEDULE_FILE = PROJECT_ROOT / "config" / "command-schedule.json"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"


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
    """Save scheduled commands to file"""
    SCHEDULE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SCHEDULE_FILE, "w") as f:
        json.dump(schedule_data, f, indent=2)
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
        return result.returncode == 0, result.stdout if result.returncode == 0 else result.stderr
    except subprocess.TimeoutExpired:
        return False, "Command execution timeout"
    except Exception as e:
        return False, str(e)


def check_and_run_schedules():
    """Check scheduled commands and run those that are due"""
    schedule_data = load_schedule()
    schedules = schedule_data.get("schedules", [])
    current_time = datetime.now(timezone.utc)

    for schedule in schedules:
        if not schedule.get("enabled", True):
            continue

        # Check if it's time to run
        if should_run_schedule(schedule, current_time):
            command = schedule.get("command")
            if command:
                success, output = execute_command(command)
                # Log execution
                log_execution(schedule.get("id"), command, success, output, current_time)
                # Update last_run
                schedule["last_run"] = current_time.isoformat()


def should_run_schedule(schedule, current_time):
    """Check if a schedule should run now"""
    schedule_type = schedule.get("type")  # "interval", "daily", "weekly", "cron"
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
                # Only run if it's the right time and we haven't run this week
                if current_time.hour == hour and current_time.minute == minute:
                    return (current_time - last_run_time).days >= 7
                return False
            else:
                return current_time.hour == hour and current_time.minute == minute

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


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "run":
        check_and_run_schedules()
    else:
        print("Usage: command-scheduler.py run")
        sys.exit(1)
