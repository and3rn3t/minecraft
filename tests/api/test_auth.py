#!/usr/bin/env python3
"""
Tests for user authentication API endpoints
"""

import json
from pathlib import Path as PathLib

import pytest

import api.server as api_module

PROJECT_ROOT = PathLib(__file__).parent.parent.parent

app = api_module.app


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

    monkeypatch.setattr(api_module, "USERS_FILE", users_file)
    monkeypatch.setattr(api_module, "USERS", {})

    return users_file


@pytest.fixture
def mock_bcrypt(monkeypatch):
    """Mock bcrypt for password hashing"""
    try:
        # Imported for the ImportError, which is how the fixture detects
        # whether bcrypt is available; the name itself is unused.
        import bcrypt  # noqa: F401

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

        monkeypatch.setattr("api.auth_crypto.hash_password", lambda p: f"hashed_{p}")
        monkeypatch.setattr("api.auth_crypto.verify_password", mock_checkpw)
        monkeypatch.setattr("api.auth_crypto.BCRYPT_AVAILABLE", True)
        return True
    except ImportError:
        return False


@pytest.fixture
def mock_jwt(monkeypatch):
    """Mock JWT for token generation"""
    try:
        # Same here: the import is the availability probe.
        import jwt as pyjwt  # noqa: F401

        def mock_generate_token(username):
            return f"token_{username}"

        def mock_verify_token(token):
            if token.startswith("token_"):
                return token.replace("token_", "")
            return None

        monkeypatch.setattr("api.auth_crypto.generate_token", mock_generate_token)
        monkeypatch.setattr("api.auth_crypto.verify_token", mock_verify_token)
        monkeypatch.setattr("api.auth_crypto.JWT_AVAILABLE", True)
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

        # Open registration, so this exercises duplicate detection rather than
        # the closed-registration gate.
        monkeypatch.setattr(api_module, "REGISTRATION_ENABLED", True)

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
        assert "newuser" in api_module.USERS

    def test_first_user_is_admin(self, client, temp_users_file, mock_bcrypt, mock_jwt):
        """The very first account bootstraps the server and is an admin"""
        if not mock_bcrypt:
            pytest.skip("bcrypt not available")

        assert api_module.USERS == {}

        response = client.post(
            "/api/auth/register",
            json={"username": "firstuser", "password": "password123"},
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get("user", {}).get("role") == "admin"
        assert api_module.USERS["firstuser"]["role"] == "admin"

    def test_later_users_are_not_admin(self, client, temp_users_file, mock_bcrypt, mock_jwt, monkeypatch):
        """Registering behind an existing account must not mint another admin"""
        if not mock_bcrypt:
            pytest.skip("bcrypt not available")

        monkeypatch.setattr(api_module, "REGISTRATION_ENABLED", True)
        api_module.USERS["firstuser"] = {
            "username": "firstuser",
            "password_hash": "hashed_password123",
            "role": "admin",
            "enabled": True,
        }

        response = client.post(
            "/api/auth/register",
            json={"username": "seconduser", "password": "password123"},
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get("user", {}).get("role") == "user"
        assert api_module.USERS["seconduser"]["role"] == "user"

    def test_registration_closed_once_a_user_exists(self, client, temp_users_file, mock_bcrypt, monkeypatch):
        """With REGISTRATION_ENABLED unset, only the bootstrap account may register"""
        if not mock_bcrypt:
            pytest.skip("bcrypt not available")

        monkeypatch.setattr(api_module, "REGISTRATION_ENABLED", False)
        api_module.USERS["firstuser"] = {
            "username": "firstuser",
            "password_hash": "hashed_password123",
            "role": "admin",
            "enabled": True,
        }

        response = client.post(
            "/api/auth/register",
            json={"username": "seconduser", "password": "password123"},
        )

        assert response.status_code == 403
        assert "seconduser" not in api_module.USERS


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

        monkeypatch.setattr("api.auth_crypto.verify_password", mock_verify_password)

        with client.session_transaction() as session:
            response = client.post("/api/auth/login", json={"username": "testuser", "password": "password123"})

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data.get("success") is True
            assert data.get("user", {}).get("username") == "testuser"
            assert "token" in data or session.get("username") == "testuser"


class TestLoginRateLimit:
    """Tests for rate limiting on POST /api/auth/login.

    Before this, nothing throttled login attempts at all -- a password could
    be brute-forced with no limit. login() is decorated
    @auth_rate_limit("5/minute;20/hour"); this exercises the per-minute
    limit. The autouse `_reset_rate_limiter` fixture in conftest.py clears
    the limiter's counters before every test, so this test's requests don't
    leak into (or get polluted by) any other test's.
    """

    def test_login_returns_429_after_limit_exceeded(self, client, temp_users_file, mock_bcrypt):
        if not mock_bcrypt:
            pytest.skip("bcrypt not available")

        # Wrong credentials on purpose -- the limiter counts the request
        # itself, regardless of whether the login succeeds.
        for _ in range(5):
            response = client.post("/api/auth/login", json={"username": "nope", "password": "nope"})
            assert response.status_code == 401

        response = client.post("/api/auth/login", json={"username": "nope", "password": "nope"})
        assert response.status_code == 429

    def test_login_succeeds_within_limit(self, client, temp_users_file, mock_bcrypt):
        if not mock_bcrypt:
            pytest.skip("bcrypt not available")

        for _ in range(4):
            response = client.post("/api/auth/login", json={"username": "nope", "password": "nope"})
            assert response.status_code == 401


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

        api_module.USERS["testuser"] = {
            "username": "testuser",
            "role": "user",
            "email": "test@example.com",
        }

        # Mock verify_token to return username
        def mock_verify_token(token):
            return "testuser" if token == "token_testuser" else None

        monkeypatch.setattr("api.auth_crypto.verify_token", mock_verify_token)

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
        _resolve_secret_key = api_module._resolve_secret_key

        assert _resolve_secret_key("from-env", "from-config") == "from-env"

    def test_config_file_used_when_environment_unset(self):
        _resolve_secret_key = api_module._resolve_secret_key

        assert _resolve_secret_key(None, "from-config") == "from-config"

    def test_values_are_stripped(self):
        _resolve_secret_key = api_module._resolve_secret_key

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
        _resolve_secret_key = api_module._resolve_secret_key

        # Real placeholders warn "known placeholder"; blank ones warn "ephemeral".
        with pytest.warns(UserWarning, match="placeholder|ephemeral"):
            resolved = _resolve_secret_key(placeholder, placeholder)

        assert resolved != placeholder.strip()
        assert len(resolved) == 64

    def test_falls_back_to_random_key_when_nothing_configured(self):
        _resolve_secret_key = api_module._resolve_secret_key

        with pytest.warns(UserWarning, match="ephemeral"):
            first = _resolve_secret_key(None, None)
            second = _resolve_secret_key(None, None)

        assert len(first) == 64
        assert first != second

    def test_module_key_is_not_a_known_placeholder(self):
        _REJECTED_SECRET_KEYS, SECRET_KEY = api_module._REJECTED_SECRET_KEYS, api_module.SECRET_KEY

        assert SECRET_KEY not in _REJECTED_SECRET_KEYS

    def test_flask_config_matches_signing_key(self):
        """generate_token/verify_token sign with the module-level SECRET_KEY,
        so Flask's session key must be the same value."""
        SECRET_KEY = api_module.SECRET_KEY

        assert app.config["SECRET_KEY"] == SECRET_KEY


class TestApiKeyHeaderOnly:
    """An API key is no longer accepted via ?api_key=... -- it leaks into
    nginx access logs, browser history, and any Referer header a follow-on
    request sends. Only the X-API-Key header works now."""

    def test_query_string_api_key_is_rejected(self, client, mock_api_keys):
        response = client.get(f"/api/auth/me?api_key={mock_api_keys}")
        assert response.status_code == 401

    def test_header_api_key_still_works(self, client, mock_api_keys):
        response = client.get("/api/auth/me", headers={"X-API-Key": mock_api_keys})
        assert response.status_code == 200


class TestSessionCookieHardening:
    """Tests that the session cookie issued at login carries the flags an
    auth cookie needs: HttpOnly (unreadable by client-side JS/XSS), Secure
    (never sent over plain HTTP), SameSite=Strict (never sent cross-site)."""

    def test_login_sets_hardened_session_cookie(self, client, temp_users_file, mock_bcrypt, mock_jwt, monkeypatch):
        if not mock_bcrypt:
            pytest.skip("bcrypt not available")

        api_module.USERS["testuser"] = {
            "username": "testuser",
            "password_hash": "hashed_password123",
            "role": "user",
            "enabled": True,
        }
        monkeypatch.setattr("api.auth_crypto.verify_password", lambda password, hashed: password == "password123")

        response = client.post("/api/auth/login", json={"username": "testuser", "password": "password123"})
        assert response.status_code == 200

        set_cookie_headers = response.headers.getlist("Set-Cookie")
        session_cookie = next((h for h in set_cookie_headers if h.startswith("session=")), None)
        assert session_cookie is not None, set_cookie_headers
        assert "HttpOnly" in session_cookie
        assert "Secure" in session_cookie
        assert "SameSite=Strict" in session_cookie


class TestCsrfProtection:
    """Tests for the CSRF check folded into require_auth's session branch
    (api/server.py). Only session-cookie-authenticated, state-changing
    requests are checked -- a browser attaches cookies to a cross-site
    request automatically, which is the CSRF vector; it never attaches a
    custom header or an Authorization/X-API-Key value on its own, so the
    Bearer-JWT and API-key auth paths don't need this."""

    def test_login_response_includes_csrf_token(self, client, temp_users_file, mock_bcrypt, mock_jwt, monkeypatch):
        if not mock_bcrypt:
            pytest.skip("bcrypt not available")

        api_module.USERS["testuser"] = {
            "username": "testuser",
            "password_hash": "hashed_password123",
            "role": "user",
            "enabled": True,
        }
        monkeypatch.setattr("api.auth_crypto.verify_password", lambda password, hashed: password == "password123")

        response = client.post("/api/auth/login", json={"username": "testuser", "password": "password123"})
        data = json.loads(response.data)
        assert data.get("csrf_token")

    def test_session_authenticated_mutation_without_token_is_rejected(self, client, temp_users_file):
        api_module.USERS["testuser"] = {"username": "testuser", "role": "admin", "enabled": True}
        with client.session_transaction() as session:
            session["username"] = "testuser"
            session["csrf_token"] = "the-real-token"

        # No X-CSRF-Token header at all -- e.g. a cross-site request, which
        # carries the cookie automatically but can't read or set this header.
        response = client.post("/api/users", json={"username": "new", "password": "password123", "role": "user"})
        assert response.status_code == 403

    def test_session_authenticated_mutation_with_wrong_token_is_rejected(self, client, temp_users_file):
        api_module.USERS["testuser"] = {"username": "testuser", "role": "admin", "enabled": True}
        with client.session_transaction() as session:
            session["username"] = "testuser"
            session["csrf_token"] = "the-real-token"

        response = client.post(
            "/api/users",
            json={"username": "new", "password": "password123", "role": "user"},
            headers={"X-CSRF-Token": "a-guessed-token"},
        )
        assert response.status_code == 403

    def test_session_authenticated_mutation_with_correct_token_succeeds(self, client, temp_users_file, mock_bcrypt):
        if not mock_bcrypt:
            pytest.skip("bcrypt not available")

        api_module.USERS["testuser"] = {"username": "testuser", "role": "admin", "enabled": True}
        with client.session_transaction() as session:
            session["username"] = "testuser"
            session["csrf_token"] = "the-real-token"

        response = client.post(
            "/api/users",
            json={"username": "new", "password": "password123", "role": "user"},
            headers={"X-CSRF-Token": "the-real-token"},
        )
        assert response.status_code == 201

    def test_session_authenticated_get_does_not_need_csrf_token(self, client, temp_users_file):
        """A read-only request carries no CSRF risk, so it isn't checked --
        this also has to hold so a client can fetch its own token in the
        first place (see get_csrf_token / GET /api/auth/csrf-token)."""
        api_module.USERS["testuser"] = {"username": "testuser", "role": "admin", "enabled": True}
        with client.session_transaction() as session:
            session["username"] = "testuser"
            session["csrf_token"] = "the-real-token"

        response = client.get("/api/auth/me")
        assert response.status_code == 200

    def test_csrf_token_endpoint_returns_the_session_token(self, client, temp_users_file):
        api_module.USERS["testuser"] = {"username": "testuser", "role": "admin", "enabled": True}
        with client.session_transaction() as session:
            session["username"] = "testuser"
            session["csrf_token"] = "the-real-token"

        response = client.get("/api/auth/csrf-token")
        assert response.status_code == 200
        assert json.loads(response.data)["csrf_token"] == "the-real-token"

    def test_bearer_token_auth_does_not_require_csrf_token(self, client, temp_users_file, mock_jwt):
        """A Bearer token is never attached by a browser automatically, so
        this path is not CSRF-exploitable and isn't checked."""
        if not mock_jwt:
            pytest.skip("jwt not available")

        api_module.USERS["testuser"] = {"username": "testuser", "role": "admin", "enabled": True}

        response = client.post(
            "/api/users",
            json={"username": "new", "password": "password123", "role": "user"},
            headers={"Authorization": "Bearer token_testuser"},
        )
        assert response.status_code != 403

    def test_bearer_token_wins_over_a_stray_session_cookie(self, client, temp_users_file, mock_jwt):
        """Regression test: the web panel is same-origin behind nginx, so
        the browser attaches the session cookie to *every* request --
        including ones the panel is authenticating with its Bearer token.
        require_auth must check the Bearer token before the session cookie,
        or every mutating panel action after login 403s on a missing CSRF
        header the panel never even knows to send."""
        if not mock_jwt:
            pytest.skip("jwt not available")

        api_module.USERS["testuser"] = {"username": "testuser", "role": "admin", "enabled": True}
        # A session cookie is present too (e.g. left over from the login
        # request that also minted the Bearer token) but carries no CSRF
        # token -- if the session branch won, this would 403.
        with client.session_transaction() as session:
            session["username"] = "testuser"

        response = client.post(
            "/api/users",
            json={"username": "new", "password": "password123", "role": "user"},
            headers={"Authorization": "Bearer token_testuser"},
        )
        assert response.status_code == 201


class TestAuthAuditLogging:
    """login/register/logout/2FA weren't audited at all before this --
    log_audit_event() (api/server.py) existed and was used elsewhere, but
    never called from any /api/auth/* route, despite
    docs/SECURITY_HARDENING.md claiming auth success/failure was tracked."""

    def test_login_success_is_audited(self, client, temp_users_file, mock_bcrypt, mock_jwt, monkeypatch, tmp_path):
        if not mock_bcrypt:
            pytest.skip("bcrypt not available")

        audit_log = tmp_path / "audit.log"
        monkeypatch.setattr(api_module, "AUDIT_LOG_FILE", audit_log)
        api_module.USERS["testuser"] = {
            "username": "testuser",
            "password_hash": "hashed_password123",
            "role": "user",
            "enabled": True,
        }
        monkeypatch.setattr("api.auth_crypto.verify_password", lambda password, hashed: password == "password123")

        response = client.post("/api/auth/login", json={"username": "testuser", "password": "password123"})
        assert response.status_code == 200

        written = audit_log.read_text()
        assert "login_success" in written
        assert "testuser" in written
        assert "password123" not in written

    def test_login_failure_is_audited(self, client, temp_users_file, mock_bcrypt, monkeypatch, tmp_path):
        if not mock_bcrypt:
            pytest.skip("bcrypt not available")

        audit_log = tmp_path / "audit.log"
        monkeypatch.setattr(api_module, "AUDIT_LOG_FILE", audit_log)

        response = client.post("/api/auth/login", json={"username": "nope", "password": "wrong"})
        assert response.status_code == 401

        written = audit_log.read_text()
        assert "login_failure" in written
        assert "wrong" not in written

    def test_logout_is_audited(self, client, temp_users_file, monkeypatch, tmp_path):
        audit_log = tmp_path / "audit.log"
        monkeypatch.setattr(api_module, "AUDIT_LOG_FILE", audit_log)
        with client.session_transaction() as session:
            session["username"] = "testuser"

        response = client.post("/api/auth/logout")
        assert response.status_code == 200

        written = audit_log.read_text()
        assert "logout" in written
        assert "testuser" in written

    def test_registration_is_audited_without_leaking_the_password(
        self, client, temp_users_file, mock_bcrypt, mock_jwt, monkeypatch, tmp_path
    ):
        if not mock_bcrypt:
            pytest.skip("bcrypt not available")

        audit_log = tmp_path / "audit.log"
        monkeypatch.setattr(api_module, "AUDIT_LOG_FILE", audit_log)

        response = client.post(
            "/api/auth/register", json={"username": "newuser", "password": "correcthorsebatterystaple"}
        )
        assert response.status_code == 200

        written = audit_log.read_text()
        assert "user_registered" in written
        assert "newuser" in written
        assert "correcthorsebatterystaple" not in written


class TestRevokedAccounts:
    """Disabling or deleting an account has to end the access it already has.

    Only password login used to check `enabled`, so a disabled or deleted
    user's session cookie and bearer token kept working until they expired.
    """

    @pytest.fixture
    def alice(self, temp_users_file):
        api_module.USERS["alice"] = {"username": "alice", "role": "admin", "enabled": True}
        return api_module.USERS["alice"]

    def _with_session(self, client):
        with client.session_transaction() as session:
            session["username"] = "alice"
            session["csrf_token"] = "csrf"

    def test_an_active_session_works(self, client, alice):
        self._with_session(client)
        response = client.get("/api/auth/me")
        assert response.status_code == 200

    def test_disabling_ends_the_session(self, client, alice):
        self._with_session(client)
        alice["enabled"] = False

        response = client.get("/api/auth/me")
        assert response.status_code == 401
        with client.session_transaction() as session:
            assert "username" not in session, "the dead session is cleared, not just refused"

    def test_deleting_ends_the_session(self, client, alice):
        self._with_session(client)
        del api_module.USERS["alice"]

        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_disabling_ends_the_bearer_token(self, client, alice, mock_jwt):
        headers = {"Authorization": "Bearer token_alice"}
        response = client.get("/api/auth/me", headers=headers)
        assert response.status_code == 200

        alice["enabled"] = False

        response = client.get("/api/auth/me", headers=headers)
        assert response.status_code == 401
