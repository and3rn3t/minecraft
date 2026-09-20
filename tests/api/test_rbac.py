#!/usr/bin/env python3
"""
Tests for Role-Based Access Control (RBAC) functionality
"""

import json
import sys
from pathlib import Path as PathLib
from unittest.mock import MagicMock, patch

import pytest

PROJECT_ROOT = PathLib(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import api.server as api_module  # noqa: E402
from api.server import PERMISSIONS, ROLE_PERMISSIONS, app


@pytest.fixture
def client():
    """Create test client"""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def temp_users_file(tmp_path, monkeypatch):
    """Create temporary users file for testing"""
    users_file = tmp_path / "config" / "users.json"
    users_file.parent.mkdir(parents=True, exist_ok=True)

    import api.server as api_module

    monkeypatch.setattr(api_module, "USERS_FILE", users_file)
    api_module.USERS = {}

    return users_file


@pytest.fixture
def temp_api_keys_file(tmp_path, monkeypatch):
    """Create temporary API keys file for testing"""
    keys_file = tmp_path / "config" / "api-keys.json"
    keys_file.parent.mkdir(parents=True, exist_ok=True)

    import api.server as api_module

    monkeypatch.setattr(api_module, "API_KEYS_FILE", keys_file)
    api_module.API_KEYS = {}

    return keys_file


@pytest.fixture
def admin_user(temp_users_file, monkeypatch):
    """Create an admin user for testing"""
    import api.server as api_module

    api_module.USERS["admin"] = {
        "username": "admin",
        "password": "hashed_admin",
        "role": "admin",
        "email": "admin@example.com",
        "enabled": True,
        "created": "2025-01-15T00:00:00Z",
    }
    return "admin"


@pytest.fixture
def operator_user(temp_users_file, monkeypatch):
    """Create an operator user for testing"""
    import api.server as api_module

    api_module.USERS["operator"] = {
        "username": "operator",
        "password": "hashed_operator",
        "role": "operator",
        "email": "operator@example.com",
        "enabled": True,
        "created": "2025-01-15T00:00:00Z",
    }
    return "operator"


@pytest.fixture
def regular_user(temp_users_file, monkeypatch):
    """Create a regular user for testing"""
    import api.server as api_module

    api_module.USERS["user"] = {
        "username": "user",
        "password": "hashed_user",
        "role": "user",
        "email": "user@example.com",
        "enabled": True,
        "created": "2025-01-15T00:00:00Z",
    }
    return "user"


@pytest.fixture
def mock_bcrypt(monkeypatch):
    """Mock bcrypt for password hashing"""
    try:
        import bcrypt

        def mock_hashpw(password, salt):
            return f"hashed_{password.decode()}"

        def mock_checkpw(password, hashed):
            expected = f"hashed_{password.decode()}"
            return hashed == expected or hashed == expected.encode()

        monkeypatch.setattr(bcrypt, "hashpw", mock_hashpw)
        monkeypatch.setattr(bcrypt, "checkpw", mock_checkpw)
        return True
    except ImportError:
        return False


class TestPermissionSystem:
    """Tests for permission system"""

    def test_permissions_defined(self):
        """Test that permissions are properly defined"""
        assert isinstance(PERMISSIONS, dict)
        assert len(PERMISSIONS) > 0
        assert "server.view" in PERMISSIONS
        assert "server.control" in PERMISSIONS
        assert "users.manage" in PERMISSIONS

    def test_roles_defined(self):
        """Test that roles are properly defined"""
        assert isinstance(ROLE_PERMISSIONS, dict)
        assert "admin" in ROLE_PERMISSIONS
        assert "operator" in ROLE_PERMISSIONS
        assert "user" in ROLE_PERMISSIONS

    def test_admin_has_all_permissions(self):
        """Test that admin role has all permissions"""
        admin_perms = ROLE_PERMISSIONS["admin"]
        assert len(admin_perms) == len(PERMISSIONS)
        for perm in PERMISSIONS.keys():
            assert perm in admin_perms

    def test_operator_permissions(self):
        """Test that operator has appropriate permissions"""
        operator_perms = ROLE_PERMISSIONS["operator"]
        assert "server.view" in operator_perms
        assert "server.control" in operator_perms
        assert "backup.view" in operator_perms
        assert "backup.create" in operator_perms
        # Operator should not have user management
        assert "users.manage" not in operator_perms
        assert "api_keys.manage" not in operator_perms

    def test_user_permissions(self):
        """Test that regular user has limited permissions"""
        user_perms = ROLE_PERMISSIONS["user"]
        assert "server.view" in user_perms
        assert "backup.view" in user_perms
        # User should not have control permissions
        assert "server.control" not in user_perms
        assert "backup.create" not in user_perms
        assert "users.manage" not in user_perms


class TestPermissionEndpoints:
    """Tests for permission-related endpoints"""

    def test_get_permissions_requires_auth(self, client):
        """Get permissions endpoint requires authentication"""
        response = client.get("/api/permissions")
        assert response.status_code == 401

    def test_get_permissions_with_session(self, client, admin_user, temp_users_file):
        """Get permissions returns user permissions"""

        with client.session_transaction() as session:
            session["username"] = "admin"

        response = client.get("/api/permissions")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "permissions" in data
        assert "role" in data
        assert data["role"] == "admin"
        assert len(data["permissions"]) == len(PERMISSIONS)

    def test_get_permissions_for_operator(self, client, operator_user, temp_users_file):
        """Get permissions returns operator permissions"""

        with client.session_transaction() as session:
            session["username"] = "operator"

        response = client.get("/api/permissions")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["role"] == "operator"
        assert "server.view" in data["permissions"]
        assert "server.control" in data["permissions"]
        assert "users.manage" not in data["permissions"]

    def test_get_roles_requires_auth(self, client):
        """Get roles endpoint requires authentication"""
        response = client.get("/api/roles")
        assert response.status_code == 401

    def test_get_roles_with_session(self, client, admin_user, temp_users_file):
        """Get roles returns all roles and permissions"""

        with client.session_transaction() as session:
            session["username"] = "admin"

        response = client.get("/api/roles")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "roles" in data
        assert "admin" in data["roles"]
        assert "operator" in data["roles"]
        assert "user" in data["roles"]


class TestUserManagementPermissions:
    """Tests for user management endpoint permissions"""

    def test_list_users_requires_permission(self, client, regular_user, temp_users_file):
        """List users requires users.view permission"""

        with client.session_transaction() as session:
            session["username"] = "user"

        response = client.get("/api/users")
        # Regular user should not have users.view permission
        assert response.status_code == 403

    def test_list_users_with_permission(self, client, admin_user, temp_users_file):
        """List users works with users.view permission"""

        with client.session_transaction() as session:
            session["username"] = "admin"

        response = client.get("/api/users")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "users" in data

    def test_update_user_role_requires_permission(self, client, regular_user, temp_users_file):
        """Update user role requires users.manage permission"""

        with client.session_transaction() as session:
            session["username"] = "user"

        response = client.put(
            "/api/users/testuser/role",
            json={"role": "operator"},
        )
        assert response.status_code == 403

    def test_update_user_role_with_permission(self, client, admin_user, temp_users_file):
        """Update user role works with users.manage permission"""
        import api.server as api_module

        # Create a test user
        api_module.USERS["testuser"] = {
            "username": "testuser",
            "password": "hashed_test",
            "role": "user",
            "enabled": True,
            "created": "2025-01-15T00:00:00Z",
        }

        with client.session_transaction() as session:
            session["username"] = "admin"

        response = client.put(
            "/api/users/testuser/role",
            json={"role": "operator"},
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get("success") is True
        assert api_module.USERS["testuser"]["role"] == "operator"


class TestServerControlPermissions:
    """Tests for server control endpoint permissions"""

    def test_start_server_requires_permission(self, client, regular_user, temp_users_file):
        """Start server requires server.control permission"""

        with client.session_transaction() as session:
            session["username"] = "user"

        with patch("api.server.subprocess.run"):
            response = client.post("/api/server/start")
            # Regular user should not have server.control permission
            assert response.status_code == 403

    def test_start_server_with_permission(self, client, operator_user, temp_users_file):
        """Start server works with server.control permission"""

        with client.session_transaction() as session:
            session["username"] = "operator"

        with patch("api.server.subprocess.run") as mock_run:
            from unittest.mock import MagicMock

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = b""
            mock_result.stderr = b""
            mock_run.return_value = mock_result
            response = client.post("/api/server/start")
            # Operator should have server.control permission
            assert response.status_code in [200, 500]  # 500 if server already running

    def test_view_status_allowed_for_all(self, client, regular_user, temp_users_file):
        """View server status allowed for all authenticated users"""

        with client.session_transaction() as session:
            session["username"] = "user"

        with patch("api.server.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout=b"")
            response = client.get("/api/status")
            # Regular user should have server.view permission
            assert response.status_code == 200


class TestBackupPermissions:
    """Tests for backup endpoint permissions"""

    def test_create_backup_requires_permission(self, client, regular_user, temp_users_file):
        """Create backup requires backup.create permission"""

        with client.session_transaction() as session:
            session["username"] = "user"

        response = client.post("/api/backup")
        # Regular user should not have backup.create permission
        assert response.status_code == 403

    def test_create_backup_with_permission(self, client, operator_user, temp_users_file):
        """Create backup works with backup.create permission"""

        with client.session_transaction() as session:
            session["username"] = "operator"

        with patch("api.server.subprocess.run") as mock_run:
            from unittest.mock import MagicMock

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = b""
            mock_result.stderr = b""
            mock_run.return_value = mock_result
            response = client.post("/api/backup")
            # Operator should have backup.create permission
            assert response.status_code in [200, 500]

    def test_list_backups_allowed_for_all(self, client, regular_user, temp_users_file):
        """List backups allowed for all authenticated users"""

        with client.session_transaction() as session:
            session["username"] = "user"

        with patch("api.server.subprocess.run") as mock_run:
            from unittest.mock import MagicMock

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = b"[]"
            mock_result.stderr = b""
            mock_run.return_value = mock_result
            response = client.get("/api/backups")
            # Regular user should have backup.view permission
            assert response.status_code == 200


class TestAPIKeyPermissions:
    """Tests for API key management endpoint permissions"""

    def test_list_api_keys_requires_permission(self, client, regular_user, temp_users_file):
        """List API keys requires api_keys.view permission"""

        with client.session_transaction() as session:
            session["username"] = "user"

        response = client.get("/api/keys")
        # Regular user should not have api_keys.view permission
        assert response.status_code == 403

    def test_list_api_keys_with_permission(self, client, admin_user, temp_users_file, temp_api_keys_file):
        """List API keys works with api_keys.view permission"""
        import api.server as api_module

        # Create a test API key
        test_key = "test-api-key-123456789012345678901234567890"
        api_module.API_KEYS[test_key] = {
            "name": "test-key",
            "description": "Test key",
            "enabled": True,
            "created": "2025-01-15T00:00:00Z",
        }

        with client.session_transaction() as session:
            session["username"] = "admin"

        response = client.get("/api/keys")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "keys" in data

    def test_create_api_key_requires_permission(self, client, operator_user, temp_users_file):
        """Create API key requires api_keys.manage permission"""

        with client.session_transaction() as session:
            session["username"] = "operator"

        response = client.post(
            "/api/keys",
            json={"name": "test-key", "description": "Test"},
        )
        # Operator should not have api_keys.manage permission
        assert response.status_code == 403


class TestAPIKeyAccess:
    """API keys are scoped by their own role, like users are."""

    @staticmethod
    def _make_key(scope=None, key="test-api-key-123456789012345678901234567890"):
        entry = {
            "name": "test-key",
            "description": "Test key",
            "enabled": True,
            "created": "2025-01-15T00:00:00Z",
        }
        if scope:
            entry.update(scope)
        api_module.API_KEYS[key] = entry
        return key

    def test_admin_key_reaches_admin_endpoints(self, client, temp_api_keys_file):
        """A key created as an admin still has full access"""
        test_key = self._make_key({"role": "admin"})

        response = client.get("/api/users", headers={"X-API-Key": test_key})
        assert response.status_code == 200

        response = client.post(
            "/api/keys",
            headers={"X-API-Key": test_key},
            json={"name": "new-key", "description": "New key"},
        )
        assert response.status_code in [200, 201]

    def test_default_key_cannot_manage_users_or_keys(self, client, temp_api_keys_file):
        """A key with no role stated at creation is read-only, not an admin"""
        test_key = self._make_key({"role": "user"})

        users = client.get("/api/users", headers={"X-API-Key": test_key})
        assert users.status_code == 403

        escalate = client.post(
            "/api/keys",
            headers={"X-API-Key": test_key},
            json={"name": "escalate", "description": "should not work"},
        )
        assert escalate.status_code == 403

        # It keeps the read access its role grants.
        status = client.get("/api/status", headers={"X-API-Key": test_key})
        assert status.status_code == 200

    def test_operator_key_controls_server_but_not_users(self, client, temp_api_keys_file):
        """The middle rung behaves like an operator user does"""
        test_key = self._make_key({"role": "operator"})

        users = client.get("/api/users", headers={"X-API-Key": test_key})
        assert users.status_code == 403

        with patch("api.server.subprocess.run") as mock_run:
            from unittest.mock import MagicMock

            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = b""
            mock_result.stderr = b""
            mock_run.return_value = mock_result
            response = client.post("/api/server/start", headers={"X-API-Key": test_key})
            assert response.status_code in [200, 500]

    def test_explicit_permission_list_overrides_role(self, client, temp_api_keys_file):
        """A key can be narrowed to single permissions, for a Shortcut or a widget"""
        test_key = self._make_key({"role": "admin", "permissions": ["server.view"]})

        status = client.get("/api/status", headers={"X-API-Key": test_key})
        assert status.status_code == 200
        users = client.get("/api/users", headers={"X-API-Key": test_key})
        assert users.status_code == 403

    def test_unknown_permission_names_are_ignored(self, client, temp_api_keys_file):
        """A typo in the config file must not widen a key"""
        test_key = self._make_key({"permissions": ["server.view", "not.a.permission"]})

        assert api_module.get_api_key_permissions(api_module.API_KEYS[test_key]) == ["server.view"]

    def test_pre_scoping_keys_are_migrated_to_admin(self):
        """Keys written before scoping keep working, but say so explicitly"""
        keys = {"legacy": {"name": "legacy", "enabled": True}}
        with pytest.warns(UserWarning, match="no role"):
            api_module._migrate_api_key_roles(keys)

        assert keys["legacy"]["role"] == "admin"

    def test_migration_leaves_scoped_keys_alone(self):
        """A key that already states its scope is not touched"""
        keys = {"scoped": {"name": "scoped", "enabled": True, "role": "user"}}
        api_module._migrate_api_key_roles(keys)

        assert keys["scoped"]["role"] == "user"


class TestPermissionsAreDefined:
    """A permission that is enforced but never declared is invisible: no role
    lists it, and a scoped API key cannot be granted it."""

    def test_every_enforced_permission_is_declared(self):
        """Guards the defect where 14 endpoints required an undeclared
        server.manage, which no admin-scoped API key could ever hold."""
        import re

        source = (PathLib(__file__).parent.parent.parent / "api" / "server.py").read_text()
        enforced = set(re.findall(r'require_permission\("([^"]+)"\)', source))

        undeclared = sorted(p for p in enforced if p not in PERMISSIONS)
        assert undeclared == [], f"enforced but not in PERMISSIONS: {undeclared}"

    def test_admin_role_covers_every_permission(self):
        """The admin role is defined as all of them; keep it that way"""
        assert set(ROLE_PERMISSIONS["admin"]) == set(PERMISSIONS)


class TestAdminApiKeyParity:
    """An admin-scoped key should reach what an admin user reaches"""

    def test_admin_key_matches_admin_user(self, client, temp_api_keys_file):
        """Regression: an admin key was refused the server.manage endpoints
        that an admin user could reach, because the permission was undeclared
        and the key path had no admin short-circuit."""
        test_key = "admin-parity-key"
        api_module.API_KEYS[test_key] = {"name": "dash", "enabled": True, "role": "admin"}

        response = client.get("/api/announcements", headers={"X-API-Key": test_key})
        assert response.status_code != 403

    def test_operator_key_still_refused_server_manage(self, client, temp_api_keys_file):
        """The parity is for admins only; it must not widen the other roles"""
        test_key = "operator-parity-key"
        api_module.API_KEYS[test_key] = {"name": "op", "enabled": True, "role": "operator"}

        response = client.get("/api/announcements", headers={"X-API-Key": test_key})
        assert response.status_code == 403

    def test_an_explicit_allowlist_beats_the_admin_role(self, client, temp_api_keys_file):
        """A key narrowed to named permissions is held to them, whatever its role"""
        test_key = "narrowed-admin-key"
        api_module.API_KEYS[test_key] = {
            "name": "shortcut",
            "enabled": True,
            "role": "admin",
            "permissions": ["server.view"],
        }

        refused = client.get("/api/announcements", headers={"X-API-Key": test_key})
        assert refused.status_code == 403

        allowed = client.get("/api/status", headers={"X-API-Key": test_key})
        assert allowed.status_code == 200


class TestCreateUser:
    """POST /api/users — how accounts are added once registration closes"""

    @staticmethod
    def _mock_hashing(monkeypatch):
        monkeypatch.setattr(api_module, "BCRYPT_AVAILABLE", True)
        monkeypatch.setattr(api_module, "hash_password", lambda p: f"hashed_{p}")

    def test_admin_can_create_a_user(self, client, admin_user, temp_users_file, monkeypatch):
        """The happy path: an admin adds an account with the default role"""
        self._mock_hashing(monkeypatch)
        with client.session_transaction() as session:
            session["username"] = "admin"

        response = client.post("/api/users", json={"username": "silas", "password": "a-long-password"})

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["user"] == {"username": "silas", "role": "user"}
        assert api_module.USERS["silas"]["role"] == "user"
        assert api_module.USERS["silas"]["password_hash"] == "hashed_a-long-password"

    def test_admin_can_choose_the_role(self, client, admin_user, temp_users_file, monkeypatch):
        """An explicit role is honoured when it is a real one"""
        self._mock_hashing(monkeypatch)
        with client.session_transaction() as session:
            session["username"] = "admin"

        response = client.post(
            "/api/users",
            json={"username": "jonah", "password": "a-long-password", "role": "operator"},
        )

        assert response.status_code == 201
        assert api_module.USERS["jonah"]["role"] == "operator"

    def test_operator_cannot_create_a_user(self, client, operator_user, temp_users_file):
        """Creating accounts needs users.manage, which an operator lacks"""
        with client.session_transaction() as session:
            session["username"] = "operator"

        response = client.post("/api/users", json={"username": "sneaky", "password": "a-long-password"})

        assert response.status_code == 403
        assert "sneaky" not in api_module.USERS

    def test_regular_user_cannot_create_a_user(self, client, regular_user, temp_users_file):
        """Nor may an ordinary account, which is the escalation that matters"""
        with client.session_transaction() as session:
            session["username"] = "user"

        response = client.post(
            "/api/users",
            json={"username": "sneaky", "password": "a-long-password", "role": "admin"},
        )

        assert response.status_code == 403

    def test_unauthenticated_request_is_refused(self, client, temp_users_file):
        """No session, no account creation"""
        response = client.post("/api/users", json={"username": "anon", "password": "a-long-password"})

        assert response.status_code in (401, 403)

    def test_invalid_role_is_rejected(self, client, admin_user, temp_users_file, monkeypatch):
        """An unrecognised role is a bad request, not a silent default"""
        self._mock_hashing(monkeypatch)
        with client.session_transaction() as session:
            session["username"] = "admin"

        response = client.post(
            "/api/users",
            json={"username": "silas", "password": "a-long-password", "role": "superuser"},
        )

        assert response.status_code == 400
        assert "silas" not in api_module.USERS

    def test_duplicate_username_is_rejected(self, client, admin_user, temp_users_file, monkeypatch):
        """An existing account must not be overwritten"""
        self._mock_hashing(monkeypatch)
        with client.session_transaction() as session:
            session["username"] = "admin"

        response = client.post("/api/users", json={"username": "admin", "password": "a-long-password"})

        assert response.status_code == 400
        assert api_module.USERS["admin"]["role"] == "admin"

    def test_short_password_is_rejected(self, client, admin_user, temp_users_file, monkeypatch):
        """The same password rule registration applies"""
        self._mock_hashing(monkeypatch)
        with client.session_transaction() as session:
            session["username"] = "admin"

        response = client.post("/api/users", json={"username": "silas", "password": "short"})

        assert response.status_code == 400
        assert "silas" not in api_module.USERS

    def test_username_length_is_validated(self, client, admin_user, temp_users_file, monkeypatch):
        """Same 3-32 character bound as registration"""
        self._mock_hashing(monkeypatch)
        with client.session_transaction() as session:
            session["username"] = "admin"

        too_short = client.post("/api/users", json={"username": "ab", "password": "a-long-password"})
        assert too_short.status_code == 400

        too_long = client.post("/api/users", json={"username": "a" * 33, "password": "a-long-password"})
        assert too_long.status_code == 400

    def test_a_failed_save_does_not_leave_the_user_behind(
        self, client, admin_user, temp_users_file, monkeypatch
    ):
        """A user that could not be persisted must not linger in memory,
        where it would work until the next restart and then vanish."""
        self._mock_hashing(monkeypatch)
        monkeypatch.setattr(api_module, "save_users", lambda: False)
        with client.session_transaction() as session:
            session["username"] = "admin"

        response = client.post("/api/users", json={"username": "silas", "password": "a-long-password"})

        assert response.status_code == 500
        assert "silas" not in api_module.USERS


class TestAPIKeyScopeManagement:
    """Tests for creating and re-scoping keys through the API"""

    def test_created_keys_default_to_least_privilege(self, client, admin_user, temp_users_file, temp_api_keys_file):
        """Creating a key without saying what it is for must not mint an admin"""
        with client.session_transaction() as session:
            session["username"] = "admin"

        response = client.post("/api/keys", json={"name": "shortcut"})
        assert response.status_code == 201
        data = json.loads(response.data)
        assert data["role"] == "user"
        assert "users.manage" not in data["permissions"]

    def test_create_rejects_an_invalid_role(self, client, admin_user, temp_users_file, temp_api_keys_file):
        """An unrecognised role is a bad request, not a silent default"""
        with client.session_transaction() as session:
            session["username"] = "admin"

        response = client.post("/api/keys", json={"name": "bad", "role": "superuser"})
        assert response.status_code == 400

    def test_create_rejects_unknown_permissions(self, client, admin_user, temp_users_file, temp_api_keys_file):
        """A misspelled permission is rejected rather than dropped quietly"""
        with client.session_transaction() as session:
            session["username"] = "admin"

        response = client.post("/api/keys", json={"name": "bad", "permissions": ["server.viwe"]})
        assert response.status_code == 400

    def test_a_key_can_be_narrowed_after_the_fact(self, client, admin_user, temp_users_file, temp_api_keys_file):
        """Migrated admin keys have to be narrowable, or the migration is a dead end"""
        test_key = "test-api-key-123456789012345678901234567890"
        api_module.API_KEYS[test_key] = {"name": "legacy", "enabled": True, "role": "admin"}

        with client.session_transaction() as session:
            session["username"] = "admin"

        response = client.put(f"/api/keys/{test_key}", json={"role": "user"})
        assert response.status_code == 200
        assert api_module.API_KEYS[test_key]["role"] == "user"

        # And the narrowed key is refused where it used to be allowed.
        refused = client.get("/api/users", headers={"X-API-Key": test_key})
        assert refused.status_code == 403

    def test_the_id_from_the_listing_resolves(self, client, admin_user, temp_users_file, temp_api_keys_file):
        """GET /api/keys shows a first-8...last-4 preview, and that is what the
        web UI sends back, so every endpoint taking a key id has to accept it."""
        full_key = "mc_abcdef1234567890abcdef1234567890abcdef12"
        api_module.API_KEYS[full_key] = {"name": "dashboard", "enabled": True, "role": "admin"}

        with client.session_transaction() as session:
            session["username"] = "admin"

        listed_id = json.loads(client.get("/api/keys").data)["keys"][0]["id"]
        assert "..." in listed_id

        rescoped = client.put(f"/api/keys/{listed_id}", json={"role": "user"})
        assert rescoped.status_code == 200
        assert api_module.API_KEYS[full_key]["role"] == "user"

        disabled = client.put(f"/api/keys/{listed_id}/disable")
        assert disabled.status_code == 200
        assert api_module.API_KEYS[full_key]["enabled"] is False

        deleted = client.delete(f"/api/keys/{listed_id}")
        assert deleted.status_code == 200
        assert full_key not in api_module.API_KEYS

    def test_an_ambiguous_id_resolves_to_nothing(self, client, admin_user, temp_users_file, temp_api_keys_file):
        """A prefix shared by two keys must not act on whichever came first"""
        api_module.API_KEYS["mc_shared_prefix_aaaa"] = {"name": "one", "enabled": True, "role": "user"}
        api_module.API_KEYS["mc_shared_prefix_bbbb"] = {"name": "two", "enabled": True, "role": "user"}

        with client.session_transaction() as session:
            session["username"] = "admin"

        response = client.delete("/api/keys/mc_shared_prefix")
        assert response.status_code == 404
        assert len(api_module.API_KEYS) == 2

    def test_rescope_rolls_back_a_failed_save(self, client, admin_user, temp_users_file, temp_api_keys_file, monkeypatch):
        """A scope that could not be written must not stay live in this process"""
        test_key = "test-api-key-123456789012345678901234567890"  # gitleaks:allow
        api_module.API_KEYS[test_key] = {"name": "legacy", "enabled": True, "role": "admin"}
        monkeypatch.setattr(api_module, "save_api_keys", lambda: False)

        with client.session_transaction() as session:
            session["username"] = "admin"

        response = client.put(f"/api/keys/{test_key}", json={"role": "user"})

        assert response.status_code == 500
        assert api_module.API_KEYS[test_key]["role"] == "admin"

    def test_rescope_requires_a_scope(self, client, admin_user, temp_users_file, temp_api_keys_file):
        """An empty body is a bad request"""
        test_key = "test-api-key-123456789012345678901234567890"
        api_module.API_KEYS[test_key] = {"name": "legacy", "enabled": True, "role": "admin"}

        with client.session_transaction() as session:
            session["username"] = "admin"

        response = client.put(f"/api/keys/{test_key}", json={})
        assert response.status_code == 400


class TestUserEnableDisable:
    """Tests for user enable/disable functionality"""

    def test_enable_user_requires_permission(self, client, regular_user, temp_users_file):
        """Enable user requires users.manage permission"""
        import api.server as api_module

        api_module.USERS["testuser"] = {
            "username": "testuser",
            "password": "hashed_test",
            "role": "user",
            "enabled": False,
            "created": "2025-01-15T00:00:00Z",
        }

        with client.session_transaction() as session:
            session["username"] = "user"

        response = client.put("/api/users/testuser/enable")
        assert response.status_code == 403

    def test_enable_user_with_permission(self, client, admin_user, temp_users_file):
        """Enable user works with users.manage permission"""
        import api.server as api_module

        api_module.USERS["testuser"] = {
            "username": "testuser",
            "password": "hashed_test",
            "role": "user",
            "enabled": False,
            "created": "2025-01-15T00:00:00Z",
        }

        with client.session_transaction() as session:
            session["username"] = "admin"

        response = client.put("/api/users/testuser/enable")
        assert response.status_code == 200
        assert api_module.USERS["testuser"]["enabled"] is True

    def test_disable_user_with_permission(self, client, admin_user, temp_users_file):
        """Disable user works with users.manage permission"""
        import api.server as api_module

        api_module.USERS["testuser"] = {
            "username": "testuser",
            "password": "hashed_test",
            "role": "user",
            "enabled": True,
            "created": "2025-01-15T00:00:00Z",
        }

        with client.session_transaction() as session:
            session["username"] = "admin"

        response = client.put("/api/users/testuser/disable")
        assert response.status_code == 200
        assert api_module.USERS["testuser"]["enabled"] is False

    def test_cannot_disable_last_admin(self, client, admin_user, temp_users_file):
        """Cannot disable the last admin user"""
        import api.server as api_module

        # Count admins
        admin_count = sum(1 for u in api_module.USERS.values() if u.get("role") == "admin" and u.get("enabled"))

        with client.session_transaction() as session:
            session["username"] = "admin"

        # Try to disable the only admin
        if admin_count == 1:
            response = client.put("/api/users/admin/disable")
            assert response.status_code == 400
            data = json.loads(response.data)
            assert "error" in data
            assert "last admin" in data["error"].lower()


class TestConfigFilePermissions:
    """Tests for config file endpoint permissions"""

    def test_view_config_requires_permission(self, client, regular_user, temp_users_file):
        """View config requires config.view permission"""

        with client.session_transaction() as session:
            session["username"] = "user"

        # Regular user should have config.view permission
        with patch("api.server.subprocess.run") as mock_run:
            from unittest.mock import MagicMock

            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = b"[]"
            mock_result.stderr = b""
            mock_run.return_value = mock_result
            response = client.get("/api/config/files")
            assert response.status_code == 200

    def test_edit_config_requires_permission(self, client, regular_user, temp_users_file):
        """Edit config requires config.edit permission"""

        with client.session_transaction() as session:
            session["username"] = "user"

        # Regular user should not have config.edit permission
        response = client.post(
            "/api/config/files/server.properties",
            json={"content": "test=value"},
        )
        assert response.status_code == 403

    def test_edit_config_with_permission(self, client, operator_user, temp_users_file):
        """Edit config works with config.edit permission"""

        with client.session_transaction() as session:
            session["username"] = "operator"

        # Operator should not have config.edit permission either
        response = client.post(
            "/api/config/files/server.properties",
            json={"content": "test=value"},
        )
        assert response.status_code == 403

    def test_edit_config_admin(self, client, admin_user, temp_users_file):
        """Edit config works for admin"""

        with client.session_transaction() as session:
            session["username"] = "admin"

        # Admin should have config.edit permission
        # This will fail if file doesn't exist, but permission check should pass
        with patch("api.server.Path.exists", return_value=True):
            with patch("api.server.Path.write_text"):
                with patch("api.server.subprocess.run") as mock_run:
                    from unittest.mock import MagicMock

                    mock_result = MagicMock()
                    mock_result.returncode = 0
                    mock_result.stdout = b""
                    mock_result.stderr = b""
                    mock_run.return_value = mock_result
                    response = client.post(
                        "/api/config/files/server.properties",
                        json={"content": "test=value"},
                    )
                    # Should pass permission check (may fail on validation or file operations)
                    assert response.status_code in [200, 400, 404, 500]
