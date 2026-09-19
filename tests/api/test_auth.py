#!/usr/bin/env python3
"""
Tests for user authentication API endpoints
"""

import json
import sys
from pathlib import Path as PathLib

import pytest

PROJECT_ROOT = PathLib(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.server import app


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
def mock_bcrypt(monkeypatch):
    """Mock bcrypt for password hashing"""
    try:
        import bcrypt

        def mock_checkpw(password, hashed):
            # Handle both bytes and strings
            if isinstance(password, bytes):
                password_str = password.decode()
            else:
                password_str = password
            if isinstance(hashed, bytes):
                hashed_str = hashed.decode()
            else:
                hashed_str = hashed
            return f"hashed_{password_str}" == hashed_str

        monkeypatch.setattr("api.server.hash_password", lambda p: f"hashed_{p}")
        monkeypatch.setattr("api.server.verify_password", mock_checkpw)
        monkeypatch.setattr("api.server.BCRYPT_AVAILABLE", True)
        return True
    except ImportError:
        return False


@pytest.fixture
def mock_jwt(monkeypatch):
    """Mock JWT for token generation"""
    try:
        import jwt as pyjwt

        def mock_generate_token(username):
            return f"token_{username}"

        def mock_verify_token(token):
            if token.startswith("token_"):
                return token.replace("token_", "")
            return None

        monkeypatch.setattr("api.server.generate_token", mock_generate_token)
        monkeypatch.setattr("api.server.verify_token", mock_verify_token)
        monkeypatch.setattr("api.server.JWT_AVAILABLE", True)
        return True
    except ImportError:
        return False


class TestUserRegistration:
    """Tests for POST /api/auth/register endpoint"""

    def test_register_requires_username_password(self, client):
        """Registration requires username and password"""
        response = client.post("/api/auth/register", json={})
        assert response.status_code == 400

    def test_register_validates_username_length(self, client, temp_users_file, mock_bcrypt):
        """Registration validates username length"""
        if not mock_bcrypt:
            pytest.skip("bcrypt not available")

        # Too short
        response = client.post("/api/auth/register", json={"username": "ab", "password": "password123"})
        assert response.status_code == 400

        # Too long
        response = client.post("/api/auth/register", json={"username": "a" * 33, "password": "password123"})
        assert response.status_code == 400

    def test_register_validates_password_length(self, client, temp_users_file, mock_bcrypt):
        """Registration validates password length"""
        if not mock_bcrypt:
            pytest.skip("bcrypt not available")

        response = client.post("/api/auth/register", json={"username": "testuser", "password": "short"})
        assert response.status_code == 400

    def test_register_prevents_duplicate_username(self, client, temp_users_file, mock_bcrypt, monkeypatch):
        """Registration prevents duplicate usernames"""
        if not mock_bcrypt:
            pytest.skip("bcrypt not available")

        import api.server as api_module

        # Create existing user
        api_module.USERS["testuser"] = {
            "username": "testuser",
            "password_hash": "hashed_password",
            "role": "user",
            "enabled": True,
        }

        response = client.post("/api/auth/register", json={"username": "testuser", "password": "password123"})
        assert response.status_code == 400

    def test_register_creates_user(self, client, temp_users_file, mock_bcrypt, mock_jwt):
        """Registration creates new user successfully"""
        if not mock_bcrypt:
            pytest.skip("bcrypt not available")

        response = client.post(
            "/api/auth/register",
            json={"username": "newuser", "password": "password123", "email": "test@example.com"},
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get("success") is True
        assert data.get("user", {}).get("username") == "newuser"

        # Verify user was created
        import api.server as api_module

        assert "newuser" in api_module.USERS


class TestUserLogin:
    """Tests for POST /api/auth/login endpoint"""

    def test_login_requires_username_password(self, client):
        """Login requires username and password"""
        response = client.post("/api/auth/login", json={})
        assert response.status_code == 400

    def test_login_rejects_invalid_username(self, client, temp_users_file, mock_bcrypt):
        """Login rejects non-existent username"""
        if not mock_bcrypt:
            pytest.skip("bcrypt not available")

        response = client.post("/api/auth/login", json={"username": "nonexistent", "password": "password123"})
        assert response.status_code == 401

    def test_login_rejects_invalid_password(self, client, temp_users_file, mock_bcrypt, monkeypatch):
        """Login rejects incorrect password"""
        if not mock_bcrypt:
            pytest.skip("bcrypt not available")

        import api.server as api_module

        api_module.USERS["testuser"] = {
            "username": "testuser",
            "password_hash": "hashed_wrongpassword",
            "role": "user",
            "enabled": True,
        }

        response = client.post("/api/auth/login", json={"username": "testuser", "password": "correctpassword"})
        assert response.status_code == 401

    def test_login_success(self, client, temp_users_file, mock_bcrypt, mock_jwt, monkeypatch):
        """Login succeeds with valid credentials"""
        if not mock_bcrypt:
            pytest.skip("bcrypt not available")

        import api.server as api_module

        # Create user with correct password hash
        api_module.USERS["testuser"] = {
            "username": "testuser",
            "password_hash": "hashed_password123",
            "role": "user",
            "enabled": True,
        }

        # Mock verify_password to return True for this password
        def mock_verify_password(password, hashed):
            return password == "password123" and hashed == "hashed_password123"

        monkeypatch.setattr("api.server.verify_password", mock_verify_password)

        with client.session_transaction() as session:
            response = client.post("/api/auth/login", json={"username": "testuser", "password": "password123"})

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data.get("success") is True
            assert data.get("user", {}).get("username") == "testuser"
            assert "token" in data or session.get("username") == "testuser"


class TestUserLogout:
    """Tests for POST /api/auth/logout endpoint"""

    def test_logout_clears_session(self, client, temp_users_file, mock_bcrypt, mock_jwt):
        """Logout clears user session"""
        if not mock_bcrypt:
            pytest.skip("bcrypt not available")

        with client.session_transaction() as session:
            session["username"] = "testuser"

            response = client.post("/api/auth/logout")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data.get("success") is True


class TestGetCurrentUser:
    """Tests for GET /api/auth/me endpoint"""

    def test_get_current_user_requires_auth(self, client):
        """Get current user requires authentication"""
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_get_current_user_with_session(self, client, temp_users_file, monkeypatch):
        """Get current user returns user info from session"""
        import api.server as api_module

        api_module.USERS["testuser"] = {
            "username": "testuser",
            "role": "admin",
            "email": "test@example.com",
            "created": "2025-01-15T00:00:00Z",
        }

        # Set session using session_transaction
        with client.session_transaction() as session:
            session["username"] = "testuser"

        # Make request after session is set (session persists across requests)
        response = client.get("/api/auth/me")

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get("username") == "testuser"
        assert data.get("role") == "admin"

    def test_get_current_user_with_token(self, client, temp_users_file, mock_jwt, monkeypatch):
        """Get current user returns user info from JWT token"""
        if not mock_jwt:
            pytest.skip("JWT not available")

        import api.server as api_module

        api_module.USERS["testuser"] = {
            "username": "testuser",
            "role": "user",
            "email": "test@example.com",
        }

        # Mock verify_token to return username
        def mock_verify_token(token):
            return "testuser" if token == "token_testuser" else None

        monkeypatch.setattr("api.server.verify_token", mock_verify_token)

        response = client.get("/api/auth/me", headers={"Authorization": "Bearer token_testuser"})

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get("username") == "testuser"


class TestSecretKeyResolution:
    """The signing key for sessions and JWTs must never fall back to a constant.

    A predictable key lets anyone mint a valid token for any user, so the
    resolver prefers the environment, then config/api.conf, and otherwise
    generates a random key rather than using a shipped placeholder.
    """

    def test_environment_wins_over_config_file(self):
        from api.server import _resolve_secret_key

        assert _resolve_secret_key("from-env", "from-config") == "from-env"

    def test_config_file_used_when_environment_unset(self):
        from api.server import _resolve_secret_key

        assert _resolve_secret_key(None, "from-config") == "from-config"

    def test_values_are_stripped(self):
        from api.server import _resolve_secret_key

        assert _resolve_secret_key("  spaced-key  ", None) == "spaced-key"

    @pytest.mark.parametrize(
        "placeholder",
        [
            "minecraft-server-api-secret-change-in-production",
            "changeme",
            "secret",
            "",
            "   ",
        ],
    )
    def test_placeholder_is_rejected_and_replaced(self, placeholder):
        from api.server import _resolve_secret_key

        resolved = _resolve_secret_key(placeholder, placeholder)

        assert resolved != placeholder.strip()
        assert len(resolved) == 64

    def test_falls_back_to_random_key_when_nothing_configured(self):
        from api.server import _resolve_secret_key

        first = _resolve_secret_key(None, None)
        second = _resolve_secret_key(None, None)

        assert len(first) == 64
        assert first != second

    def test_module_key_is_not_a_known_placeholder(self):
        import api.server as api_module

        assert api_module.SECRET_KEY not in api_module._REJECTED_SECRET_KEYS

    def test_flask_config_matches_signing_key(self):
        """generate_token/verify_token sign with the module-level SECRET_KEY,
        so Flask's session key must be the same value."""
        import api.server as api_module

        assert api_module.app.config["SECRET_KEY"] == api_module.SECRET_KEY
