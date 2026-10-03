"""
Deleting users, changing roles, disabling accounts, and reading the audit log.

The rule running through the first three: the server always keeps at least one
enabled admin. It used to count the target itself, so a *disabled* admin could
not be removed while exactly one other admin was active.
"""

import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import api.rbac as rbac  # noqa: E402
import api.server as api_module  # noqa: E402


@pytest.fixture
def users(tmp_path, monkeypatch):
    monkeypatch.setattr(api_module, "USERS_FILE", tmp_path / "users.json")
    monkeypatch.setattr(
        api_module,
        "USERS",
        {
            "boss": {"username": "boss", "role": "admin", "enabled": True},
            "alice": {"username": "alice", "role": "user", "enabled": True},
        },
    )
    return api_module.USERS


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setitem(api_module.API_KEYS, "users-admin", {"name": "a", "enabled": True, "role": "admin"})
    api_module.app.config["TESTING"] = True
    test_client = api_module.app.test_client()
    test_client.environ_base["HTTP_X_API_KEY"] = "users-admin"
    return test_client


def _saved(tmp_path_file):
    return json.loads(Path(tmp_path_file).read_text())


class TestDelete:
    def test_deletes_and_saves(self, client, users):
        response = client.delete("/api/users/alice")

        assert response.status_code == 200
        assert "alice" not in users
        assert "alice" not in _saved(api_module.USERS_FILE)

    def test_unknown_user_is_404(self, client, users):
        response = client.delete("/api/users/nobody")
        assert response.status_code == 404

    def test_the_last_enabled_admin_is_kept(self, client, users):
        response = client.delete("/api/users/boss")

        assert response.status_code == 400
        assert "boss" in users

    def test_a_disabled_admin_can_go_while_another_admin_is_active(self, client, users):
        users["old-admin"] = {"username": "old-admin", "role": "admin", "enabled": False}

        response = client.delete("/api/users/old-admin")
        assert response.status_code == 200

    def test_nobody_deletes_their_own_account(self, users):
        client = api_module.app.test_client()
        users["second"] = {"username": "second", "role": "admin", "enabled": True}
        with client.session_transaction() as session:
            session["username"] = "second"
            session["csrf_token"] = "csrf"

        response = client.delete("/api/users/second", headers={"X-CSRF-Token": "csrf"})

        assert response.status_code == 400
        assert "own account" in response.get_json()["error"]

    def test_a_failed_save_puts_the_user_back(self, client, users, monkeypatch):
        monkeypatch.setattr(api_module, "save_users", lambda: False)

        response = client.delete("/api/users/alice")
        assert response.status_code == 500
        assert users["alice"]["role"] == "user", "still there, as it still is on disk"


class TestRoleChange:
    def test_changes_the_role(self, client, users):
        response = client.put("/api/users/alice/role", json={"role": "operator"})

        assert response.status_code == 200
        assert users["alice"]["role"] == "operator"

    @pytest.mark.parametrize("body", [{}, {"role": "superuser"}])
    def test_needs_a_valid_role(self, client, users, body):
        response = client.put("/api/users/alice/role", json=body)
        assert response.status_code == 400
        assert users["alice"]["role"] == "user"

    def test_the_last_admin_cannot_be_demoted(self, client, users):
        response = client.put("/api/users/boss/role", json={"role": "user"})
        assert response.status_code == 400
        assert users["boss"]["role"] == "admin"

    def test_a_disabled_admin_can_be_demoted(self, client, users):
        users["old-admin"] = {"username": "old-admin", "role": "admin", "enabled": False}

        response = client.put("/api/users/old-admin/role", json={"role": "user"})
        assert response.status_code == 200

    def test_a_failed_save_keeps_the_old_role(self, client, users, monkeypatch):
        monkeypatch.setattr(api_module, "save_users", lambda: False)

        response = client.put("/api/users/alice/role", json={"role": "admin"})
        assert response.status_code == 500
        assert users["alice"]["role"] == "user", "not an admin in memory while still a user on disk"


class TestDisable:
    def test_the_last_admin_cannot_be_disabled(self, client, users):
        response = client.put("/api/users/boss/disable")
        assert response.status_code == 400
        assert users["boss"]["enabled"] is True

    def test_disabling_and_enabling_round_trip(self, client, users):
        response = client.put("/api/users/alice/disable")
        assert response.status_code == 200
        assert users["alice"]["enabled"] is False

        response = client.put("/api/users/alice/enable")
        assert response.status_code == 200
        assert users["alice"]["enabled"] is True

    def test_a_failed_save_leaves_the_account_enabled(self, client, users, monkeypatch):
        monkeypatch.setattr(api_module, "save_users", lambda: False)

        response = client.put("/api/users/alice/disable")
        assert response.status_code == 500
        assert users["alice"]["enabled"] is True

    def test_a_failed_save_leaves_the_account_disabled(self, client, users, monkeypatch):
        users["alice"]["enabled"] = False
        monkeypatch.setattr(api_module, "save_users", lambda: False)

        response = client.put("/api/users/alice/enable")
        assert response.status_code == 500
        assert users["alice"]["enabled"] is False, "not enabled in memory while still disabled on disk"


class TestAuditLog:
    @pytest.fixture
    def audit(self, tmp_path, monkeypatch):
        path = tmp_path / "audit.log"
        entries = [
            {"timestamp": "2026-09-01T10:00:00+00:00", "username": "alice", "action": "login_success"},
            {"timestamp": "2026-09-03T10:00:00+00:00", "username": "boss", "action": "server.start"},
            {"timestamp": "2026-09-02T10:00:00+00:00", "username": "alice", "action": "login_failure"},
        ]
        path.write_text("\n".join(json.dumps(e) for e in entries) + "\nnot json\n\n")
        monkeypatch.setattr(api_module, "AUDIT_LOG_FILE", path)
        return path

    @pytest.mark.parametrize("role", ["user", "operator"])
    def test_only_admins_can_read_it(self, audit, role, monkeypatch):
        """It held every account's IP addresses and failed sign-ins, and needed
        only logs.view, which the "user" role has."""
        monkeypatch.setitem(api_module.API_KEYS, f"audit-{role}", {"name": role, "enabled": True, "role": role})
        client = api_module.app.test_client()

        response = client.get("/api/audit/logs", headers={"X-API-Key": f"audit-{role}"})

        assert response.status_code == 403
        assert response.get_json()["required_permission"] == "audit.view"

    def test_no_role_but_admin_holds_audit_view(self):
        holders = [role for role, perms in rbac.ROLE_PERMISSIONS.items() if "audit.view" in perms]
        assert holders == ["admin"]

    def _get(self, client, query=""):
        return client.get(f"/api/audit/logs{query}").get_json()

    def test_newest_first_skipping_unreadable_lines(self, client, audit):
        data = self._get(client)

        assert [e["action"] for e in data["logs"]] == ["server.start", "login_failure", "login_success"]
        assert data["total"] == 3

    def test_filters_by_user_and_action(self, client, audit):
        assert [e["action"] for e in self._get(client, "?username=alice")["logs"]] == [
            "login_failure",
            "login_success",
        ]
        assert self._get(client, "?action=server.start")["total"] == 1

    def test_pages(self, client, audit):
        data = self._get(client, "?limit=1&offset=1")

        assert [e["action"] for e in data["logs"]] == ["login_failure"]
        assert data["total"] == 3

    @pytest.mark.parametrize(
        "query, expected_limit, expected_offset",
        [
            ("?limit=-1", 1, 0),
            ("?limit=0", 1, 0),
            ("?limit=999999", 1000, 0),
            ("?offset=-5", 100, 0),
        ],
    )
    def test_out_of_range_paging_is_clamped(self, client, audit, query, expected_limit, expected_offset):
        """A negative limit used to slice from the end of the list"""
        data = self._get(client, query)

        assert (data["limit"], data["offset"]) == (expected_limit, expected_offset)
        assert len(data["logs"]) == min(expected_limit, 3)

    def test_no_log_yet_is_an_empty_list(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(api_module, "AUDIT_LOG_FILE", tmp_path / "missing.log")
        assert self._get(client) == {"success": True, "logs": [], "total": 0, "limit": 100, "offset": 0}

    def test_actions_are_recorded(self, client, tmp_path, monkeypatch):
        path = tmp_path / "audit.log"
        monkeypatch.setattr(api_module, "AUDIT_LOG_FILE", path)

        with api_module.app.test_request_context(environ_base={"REMOTE_ADDR": "10.0.0.5"}):
            api_module.log_audit_event("alice", "backup.create", {"name": "nightly"})

        entry = json.loads(path.read_text())
        assert entry == {**entry, "username": "alice", "action": "backup.create", "ip_address": "10.0.0.5"}
        assert entry["details"] == {"name": "nightly"}
