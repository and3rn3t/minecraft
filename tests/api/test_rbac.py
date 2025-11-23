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
        import api.server as api_module

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
        import api.server as api_module

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
        import api.server as api_module

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
        import api.server as api_module

        with client.session_transaction() as session:
            session["username"] = "user"

        response = client.get("/api/users")
        # Regular user should not have users.view permission
        assert response.status_code == 403

    def test_list_users_with_permission(self, client, admin_user, temp_users_file):
        """List users works with users.view permission"""
        import api.server as api_module

        with client.session_transaction() as session:
            session["username"] = "admin"

        response = client.get("/api/users")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "users" in data

    def test_update_user_role_requires_permission(self, client, regular_user, temp_users_file):
        """Update user role requires users.manage permission"""
        import api.server as api_module

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
        import api.server as api_module

        with client.session_transaction() as session:
            session["username"] = "user"

        with patch("api.server.subprocess.run") as mock_run:
            response = client.post("/api/server/start")
            # Regular user should not have server.control permission
            assert response.status_code == 403

    def test_start_server_with_permission(self, client, operator_user, temp_users_file):
        """Start server works with server.control permission"""
        import api.server as api_module

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
        import api.server as api_module

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
        import api.server as api_module

        with client.session_transaction() as session:
            session["username"] = "user"

        response = client.post("/api/backup")
        # Regular user should not have backup.create permission
        assert response.status_code == 403

    def test_create_backup_with_permission(self, client, operator_user, temp_users_file):
        """Create backup works with backup.create permission"""
        import api.server as api_module

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
        import api.server as api_module

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
        import api.server as api_module

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
        import api.server as api_module

        with client.session_transaction() as session:
            session["username"] = "operator"

        response = client.post(
            "/api/keys",
            json={"name": "test-key", "description": "Test"},
        )
        # Operator should not have api_keys.manage permission
        assert response.status_code == 403


class TestAPIKeyAccess:
    """Tests for API key access (should have admin permissions)"""

    def test_api_key_has_admin_permissions(self, client, temp_api_keys_file):
        """API keys should have admin-level permissions"""
        import api.server as api_module

        test_key = "test-api-key-123456789012345678901234567890"
        api_module.API_KEYS[test_key] = {
            "name": "test-key",
            "description": "Test key",
            "enabled": True,
            "created": "2025-01-15T00:00:00Z",
        }

        # API key should be able to access user management
        response = client.get("/api/users", headers={"X-API-Key": test_key})
        assert response.status_code == 200

        # API key should be able to create API keys
        response = client.post(
            "/api/keys",
            headers={"X-API-Key": test_key},
            json={"name": "new-key", "description": "New key"},
        )
        assert response.status_code in [200, 201]  # 201 CREATED is also valid

        # API key should be able to control server
        with patch("api.server.subprocess.run") as mock_run:
            from unittest.mock import MagicMock

            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = b""
            mock_result.stderr = b""
            mock_run.return_value = mock_result
            response = client.post("/api/server/start", headers={"X-API-Key": test_key})
            assert response.status_code in [200, 500]


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
        import api.server as api_module

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
        import api.server as api_module

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
        import api.server as api_module

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
        import api.server as api_module

        with client.session_transaction() as session:
            session["username"] = "admin"

        # Admin should have config.edit permission
        # This will fail if file doesn't exist, but permission check should pass
        with patch("api.server.Path.exists", return_value=True):
            with patch("api.server.Path.write_text") as mock_write:
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
