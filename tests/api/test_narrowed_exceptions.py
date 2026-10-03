"""Handlers that used to catch every Exception now catch only what they expect.

The BLE001 lint rule (blind except) made each of these a decision. These tests pin
both halves of it: the failures the code is meant to absorb are still absorbed,
and an unexpected error (a bug) is no longer swallowed on its way out. The
scheduler's own comment records what a blanket except cost: an UnboundLocalError
was caught and every schedule was skipped silently from then on.
"""

import importlib.util
import json
import shutil
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import api.realtime as realtime  # noqa: E402
import api.server as api_module  # noqa: E402


@pytest.fixture(scope="module")
def scheduler():
    script = PROJECT_ROOT / "scripts" / "command-scheduler.py"
    assert script.is_file(), f"scheduler script not found: {script}"
    spec = importlib.util.spec_from_file_location("command_scheduler_narrowed", script)
    assert spec is not None and spec.loader is not None, f"cannot build an import spec for {script}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# -- save_users / save_api_keys -----------------------------------------------------


@pytest.mark.parametrize(
    "saver, file_attr, data_attr",
    [("save_users", "USERS_FILE", "USERS"), ("save_api_keys", "API_KEYS_FILE", "API_KEYS")],
)
class TestSavers:
    def test_a_successful_save_returns_true_and_writes_json(self, monkeypatch, tmp_path, saver, file_attr, data_attr):
        target = tmp_path / "data.json"
        monkeypatch.setattr(api_module, file_attr, target)
        monkeypatch.setattr(api_module, data_attr, {"alice": {"role": "admin"}})

        assert getattr(api_module, saver)() is True
        assert json.loads(target.read_text()) == {"alice": {"role": "admin"}}

    def test_an_unwritable_location_returns_false(self, monkeypatch, tmp_path, saver, file_attr, data_attr):
        blocker = tmp_path / "not-a-directory"
        blocker.write_text("a file where the directory should be")
        monkeypatch.setattr(api_module, file_attr, blocker / "data.json")
        monkeypatch.setattr(api_module, data_attr, {"alice": {}})

        assert getattr(api_module, saver)() is False

    def test_data_that_is_not_json_returns_false(self, monkeypatch, tmp_path, saver, file_attr, data_attr):
        monkeypatch.setattr(api_module, file_attr, tmp_path / "data.json")
        monkeypatch.setattr(api_module, data_attr, {"alice": object()})

        assert getattr(api_module, saver)() is False

    def test_an_unexpected_error_is_not_swallowed(self, monkeypatch, tmp_path, saver, file_attr, data_attr):
        monkeypatch.setattr(api_module, file_attr, tmp_path / "data.json")
        monkeypatch.setattr(api_module, data_attr, {"alice": {}})

        with patch("api.server.json.dump", side_effect=RuntimeError("a bug")):
            with pytest.raises(RuntimeError, match="a bug"):
                getattr(api_module, saver)()


# -- the file browser's backup and restore ------------------------------------------


@pytest.fixture
def root(monkeypatch, tmp_path):
    root = tmp_path.resolve()
    for name in ("data", "config", "backups", "scripts"):
        (root / name).mkdir()
    monkeypatch.setattr(api_module, "PROJECT_ROOT", root)
    monkeypatch.setattr(api_module, "ALLOWED_FILE_PATHS", [root / n for n in ("data", "config", "backups", "scripts")])
    return root


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setitem(api_module.API_KEYS, "narrow-admin", {"name": "a", "enabled": True, "role": "admin"})
    api_module.app.config["TESTING"] = True
    test_client = api_module.app.test_client()
    test_client.environ_base["HTTP_X_API_KEY"] = "narrow-admin"
    return test_client


class TestFileWriteBackup:
    # shutil's own errors (SameFileError among them) derive from OSError, so the
    # narrowed `except OSError` still covers every way a backup copy can fail
    @pytest.mark.parametrize(
        "error",
        [OSError("disk full"), shutil.Error("multi-file failure"), shutil.SameFileError("same file")],
        ids=["OSError", "shutil.Error", "shutil.SameFileError"],
    )
    def test_a_failed_backup_copy_does_not_stop_the_write(self, client, root, error):
        target = root / "data" / "notes.txt"
        target.write_text("old")

        with patch("api.blueprints.files.shutil.copy2", side_effect=error):
            response = client.post("/api/files/write", json={"path": "data/notes.txt", "content": "new"})

        assert response.status_code == 200
        assert target.read_text() == "new"
        assert response.get_json()["backup"] is None

    def test_a_failed_write_restores_the_original_and_reports_a_generic_error(self, client, root):
        target = root / "data" / "notes.txt"
        target.write_text("old")

        real_open = open

        def failing_open(path, mode="r", *args, **kwargs):
            if str(path) == str(target) and "w" in mode:
                raise OSError("read-only filesystem")
            return real_open(path, mode, *args, **kwargs)

        with patch("builtins.open", side_effect=failing_open):
            response = client.post("/api/files/write", json={"path": "data/notes.txt", "content": "new"})

        assert response.status_code == 500
        assert response.get_json() == {"error": "Internal server error"}
        assert target.read_text() == "old"


# -- command-scheduler.py -----------------------------------------------------------

def _now():
    from datetime import datetime, timezone

    return datetime(2027, 6, 1, 12, 0, tzinfo=timezone.utc)


class TestSchedulerDecisions:
    def test_an_invalid_cron_expression_is_not_due(self, scheduler):
        if not scheduler.CRONITER_AVAILABLE:
            pytest.skip("croniter not installed")
        schedule = {"type": "cron", "cron_expression": "not a cron expression"}

        assert scheduler.should_run_schedule(schedule, _now()) is False

    @pytest.mark.parametrize("run_datetime", ["not-a-date", "", 12345, ["2027-01-01"]])
    def test_a_once_schedule_with_an_unusable_datetime_is_not_due(self, scheduler, run_datetime):
        schedule = {"type": "once", "run_datetime": run_datetime}

        assert scheduler.should_run_schedule(schedule, _now()) is False

    def test_a_cron_schedule_with_an_unparseable_last_run_is_not_due(self, scheduler):
        if not scheduler.CRONITER_AVAILABLE:
            pytest.skip("croniter not installed")
        schedule = {"type": "cron", "cron_expression": "* * * * *", "last_run": "yesterday-ish"}

        assert scheduler.should_run_schedule(schedule, _now()) is False

    def test_a_bug_inside_the_cron_branch_is_not_swallowed(self, scheduler):
        """A blanket except here once turned an UnboundLocalError into 'never due'."""
        if not scheduler.CRONITER_AVAILABLE:
            pytest.skip("croniter not installed")
        schedule = {"type": "cron", "cron_expression": "* * * * *"}

        with patch.object(scheduler, "croniter", side_effect=RuntimeError("a bug")):
            with pytest.raises(RuntimeError, match="a bug"):
                scheduler.should_run_schedule(schedule, _now())


class TestSchedulerExecuteCommand:
    @pytest.fixture
    def with_rcon_script(self, scheduler, tmp_path, monkeypatch):
        (tmp_path / "rcon-client.sh").write_text("#!/bin/bash\n")
        monkeypatch.setattr(scheduler, "SCRIPTS_DIR", tmp_path)

    @pytest.mark.parametrize("error", [FileNotFoundError("no such file"), PermissionError("not executable")])
    def test_a_script_that_cannot_run_is_reported_not_raised(self, scheduler, with_rcon_script, error):
        with patch.object(scheduler.subprocess, "run", side_effect=error):
            ok, message = scheduler.execute_command("list")

        assert ok is False
        assert str(error) in message

    def test_a_timeout_is_reported(self, scheduler, with_rcon_script):
        import subprocess

        with patch.object(scheduler.subprocess, "run", side_effect=subprocess.TimeoutExpired("rcon", 30)):
            ok, message = scheduler.execute_command("list")

        assert (ok, message) == (False, "Command execution timeout")

    def test_an_unexpected_error_is_not_swallowed(self, scheduler, with_rcon_script):
        with patch.object(scheduler.subprocess, "run", side_effect=RuntimeError("a bug")):
            with pytest.raises(RuntimeError, match="a bug"):
                scheduler.execute_command("list")


# -- the log follower's cleanup -------------------------------------------------------


class TestStopLogReader:
    @pytest.fixture(autouse=True)
    def _restore_state(self):
        saved = dict(realtime._log_reader_state)
        yield
        realtime._log_reader_state.clear()
        realtime._log_reader_state.update(saved)

    def test_a_process_that_already_exited_is_fine(self):
        proc = MagicMock()
        proc.kill.side_effect = ProcessLookupError("already gone")
        realtime._log_reader_state["proc"] = proc

        realtime.stop_log_reader()

        assert realtime._log_reader_state["stop"] is True
        proc.kill.assert_called_once()

    def test_an_unexpected_error_from_kill_is_not_swallowed(self):
        proc = MagicMock()
        proc.kill.side_effect = RuntimeError("a bug")
        realtime._log_reader_state["proc"] = proc

        with pytest.raises(RuntimeError, match="a bug"):
            realtime.stop_log_reader()
