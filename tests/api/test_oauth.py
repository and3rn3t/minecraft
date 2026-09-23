#!/usr/bin/env python3
"""
Tests for OAuth API endpoints
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
    api_module.USERS = {
        "testuser": {
            "username": "testuser",
            "role": "admin",
            "email": "test@example.com",
            "oauth_providers": [],
            "enabled": True,
        }
    }

    return users_file


@pytest.fixture
def mock_auth_session(client, temp_users_file):
    """Create authenticated session for testing"""
    # Set session using session_transaction, then allow tests to make requests
    csrf_token = "test-csrf-token"
    with client.session_transaction() as session:
        session["username"] = "testuser"
        session["csrf_token"] = csrf_token
    # A session-authenticated mutating request must carry a matching
    # X-CSRF-Token header (see require_auth's CSRF check in api/server.py).
    # environ_base is merged into every request this client makes, so this
    # covers all of them without touching each call site individually.
    client.environ_base["HTTP_X_CSRF_TOKEN"] = csrf_token
    # Session persists across requests after the context exits
    yield client


@pytest.fixture
def temp_oauth_config(tmp_path, monkeypatch):
    """Create temporary OAuth config"""
    oauth_config_file = tmp_path / "config" / "oauth.conf"
    oauth_config_file.parent.mkdir(parents=True, exist_ok=True)

    import api.server as api_module

    monkeypatch.setattr(api_module, "OAUTH_CONFIG_FILE", oauth_config_file)
    monkeypatch.setattr(
        api_module,
        "OAUTH_CONFIG",
        {
            "google": {
                "client_id": "test-google-client-id",
                "client_secret": "test-google-secret",
                "redirect_uri": "http://localhost/oauth/callback",
            },
            "apple": {
                "client_id": "test-apple-client-id",
                "team_id": "test-team-id",
                "key_id": "test-key-id",
                "private_key": "",
                "redirect_uri": "http://localhost/oauth/callback",
            },
        },
    )

    return oauth_config_file


class TestOAuthURL:
    """Tests for GET /api/auth/oauth/<provider>/url endpoint"""

    def test_get_oauth_url_invalid_provider(self, client):
        """Get OAuth URL rejects invalid provider"""
        response = client.get("/api/auth/oauth/invalid/url")
        assert response.status_code == 400

    def test_get_oauth_url_missing_redirect_uri(self, client, temp_oauth_config):
        """Get OAuth URL requires redirect_uri"""
        response = client.get("/api/auth/oauth/google/url")
        assert response.status_code == 400

    def test_get_oauth_url_google_not_configured(self, client):
        """Get OAuth URL returns error if Google not configured"""
        import api.server as api_module

        api_module.OAUTH_CONFIG["google"]["client_id"] = ""

        response = client.get("/api/auth/oauth/google/url?redirect_uri=http://localhost/callback")
        assert response.status_code == 500

    def test_get_oauth_url_google_success(self, client, temp_oauth_config):
        """Get OAuth URL returns Google OAuth URL"""
        response = client.get("/api/auth/oauth/google/url?redirect_uri=http://localhost/callback")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "url" in data
        assert "accounts.google.com" in data["url"]
        assert "test-google-client-id" in data["url"]

    def test_get_oauth_url_apple_success(self, client, temp_oauth_config):
        """Get OAuth URL returns Apple OAuth URL"""
        response = client.get("/api/auth/oauth/apple/url?redirect_uri=http://localhost/callback")
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "url" in data
        assert "appleid.apple.com" in data["url"]


class TestOAuthLink:
    """Tests for POST /api/auth/oauth/<provider>/link endpoint"""

    def test_link_oauth_requires_auth(self, client):
        """Link OAuth account requires authentication"""
        response = client.post("/api/auth/oauth/google/link", json={"code": "test"})
        assert response.status_code == 401

    def test_link_oauth_invalid_provider(self, client, mock_auth_session):
        """Link OAuth account rejects invalid provider"""
        response = client.post(
            "/api/auth/oauth/invalid/link",
            json={"code": "test", "redirect_uri": "http://localhost/callback"},
        )
        assert response.status_code == 400

    def test_link_oauth_rejects_missing_state(self, client, mock_auth_session):
        """Account linking must verify `state` too, the same as login --
        otherwise an attacker's own OAuth response could be fed to a
        logged-in victim's browser and linked to the victim's account."""
        response = client.post(
            "/api/auth/oauth/google/link",
            json={"code": "test", "redirect_uri": "http://localhost/callback"},
        )
        assert response.status_code == 400
        assert "state" in response.get_json().get("error", "").lower()

    def test_link_oauth_rejects_wrong_state(self, client, mock_auth_session, oauth_state):
        response = client.post(
            "/api/auth/oauth/google/link",
            json={"code": "test", "redirect_uri": "http://localhost/callback", "state": "a-guessed-value"},
        )
        assert response.status_code == 400
        assert "state" in response.get_json().get("error", "").lower()

    def test_link_oauth_accepts_correct_state(self, client, mock_auth_session, oauth_state, temp_oauth_config):
        """With the right state, the request should get *past* the state
        check -- proven here by reaching (and failing at) the token
        exchange instead of being rejected for a bad state."""
        from unittest.mock import MagicMock, patch

        with patch("requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=400)
            response = client.post(
                "/api/auth/oauth/google/link",
                json={"code": "test", "redirect_uri": "http://localhost/callback", "state": oauth_state},
            )

        assert response.status_code == 400
        assert "state" not in response.get_json().get("error", "").lower()


class TestOAuthUnlink:
    """Tests for POST /api/auth/oauth/<provider>/unlink endpoint"""

    def test_unlink_oauth_requires_auth(self, client):
        """Unlink OAuth account requires authentication"""
        response = client.post("/api/auth/oauth/google/unlink")
        assert response.status_code == 401

    def test_unlink_oauth_invalid_provider(self, client, mock_auth_session):
        """Unlink OAuth account rejects invalid provider"""
        response = client.post("/api/auth/oauth/invalid/unlink")
        assert response.status_code == 400

    def test_unlink_oauth_prevents_last_method(self, client, temp_users_file, mock_auth_session, monkeypatch):
        """Unlink OAuth account prevents unlinking last auth method"""
        import api.server as api_module

        # User has only OAuth, no password
        api_module.USERS["testuser"] = {
            "username": "testuser",
            "oauth_providers": ["google:12345"],
            "role": "user",
            "enabled": True,
        }

        response = client.post("/api/auth/oauth/google/unlink")
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "last authentication method" in data.get("error", "").lower()


def _generate_rsa_keypair():
    """A fresh throwaway RSA keypair standing in for Apple's real signing key."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


@pytest.fixture
def rsa_keypair():
    """A single throwaway RSA keypair, generated once per test."""
    return _generate_rsa_keypair()


def _sign_rs256(private_pem, claims):
    import jwt as pyjwt

    return pyjwt.encode(claims, private_pem, algorithm="RS256")


def _fake_jwk_client(public_pem=None, raises=False):
    """A stand-in for jwt.PyJWKClient that serves a fixed public key (or
    always fails, simulating "no matching/reachable key") instead of making a
    real network call to appleid.apple.com."""

    class _FakeSigningKey:
        key = public_pem

    class _FakeJWKClient:
        def get_signing_key_from_jwt(self, token):
            if raises:
                raise Exception("no matching signing key")
            return _FakeSigningKey()

    return _FakeJWKClient()


class TestVerifyAppleIdToken:
    """Unit tests for verify_apple_id_token (api/server.py).

    Added after an audit found the previous implementation decoded Apple ID
    tokens with verify_signature=False, trusting the `sub` claim of any
    caller-supplied JWT outright -- a full authentication bypass, since
    anyone could POST a self-signed token naming an arbitrary user and be
    logged in as them.
    """

    def test_returns_none_when_apple_not_configured(self, monkeypatch):
        import api.server as api_module

        monkeypatch.setitem(api_module.OAUTH_CONFIG["apple"], "client_id", "")
        assert api_module.verify_apple_id_token("whatever") is None

    def test_rejects_token_signed_with_wrong_key(self, temp_oauth_config, monkeypatch):
        """The forged-login attack: a token signed by a key that isn't the
        one our (fake) Apple JWKS endpoint actually serves must be rejected,
        even though its claims look legitimate. Uses two distinct keypairs --
        one for the attacker's forged signature, one served as "Apple's" key
        -- so this fails closed unless the signatures genuinely mismatch."""
        import api.server as api_module

        attacker_private_pem, _ = _generate_rsa_keypair()
        _, real_public_pem = _generate_rsa_keypair()
        forged_token = _sign_rs256(
            attacker_private_pem,
            {"sub": "attacker-chosen-id", "aud": "test-apple-client-id", "iss": "https://appleid.apple.com"},
        )

        monkeypatch.setattr(api_module, "_get_apple_jwk_client", lambda: _fake_jwk_client(public_pem=real_public_pem))

        assert api_module.verify_apple_id_token(forged_token) is None

    def test_rejects_unreachable_or_unknown_key(self, temp_oauth_config, monkeypatch):
        import api.server as api_module

        monkeypatch.setattr(api_module, "_get_apple_jwk_client", lambda: _fake_jwk_client(raises=True))
        assert api_module.verify_apple_id_token("not-even-a-real-jwt") is None

    def test_accepts_correctly_signed_token(self, temp_oauth_config, rsa_keypair, monkeypatch):
        import api.server as api_module

        private_pem, public_pem = rsa_keypair
        token = _sign_rs256(
            private_pem,
            {"sub": "real-apple-user-id", "aud": "test-apple-client-id", "iss": "https://appleid.apple.com"},
        )
        monkeypatch.setattr(api_module, "_get_apple_jwk_client", lambda: _fake_jwk_client(public_pem=public_pem))

        decoded = api_module.verify_apple_id_token(token)
        assert decoded is not None
        assert decoded["sub"] == "real-apple-user-id"

    def test_rejects_wrong_audience(self, temp_oauth_config, rsa_keypair, monkeypatch):
        import api.server as api_module

        private_pem, public_pem = rsa_keypair
        token = _sign_rs256(
            private_pem,
            {"sub": "real-apple-user-id", "aud": "someone-elses-client-id", "iss": "https://appleid.apple.com"},
        )
        monkeypatch.setattr(api_module, "_get_apple_jwk_client", lambda: _fake_jwk_client(public_pem=public_pem))

        assert api_module.verify_apple_id_token(token) is None

    def test_rejects_expired_token(self, temp_oauth_config, rsa_keypair, monkeypatch):
        import time

        import api.server as api_module

        private_pem, public_pem = rsa_keypair
        token = _sign_rs256(
            private_pem,
            {
                "sub": "real-apple-user-id",
                "aud": "test-apple-client-id",
                "iss": "https://appleid.apple.com",
                "exp": int(time.time()) - 60,
            },
        )
        monkeypatch.setattr(api_module, "_get_apple_jwk_client", lambda: _fake_jwk_client(public_pem=public_pem))

        assert api_module.verify_apple_id_token(token) is None


@pytest.fixture
def oauth_state(client):
    """Seed the session with a known OAuth state, mirroring what
    GET /api/auth/oauth/<provider>/url does via _issue_oauth_state(), so
    tests that POST a callback can supply a state that verify_oauth_state()
    accepts. Without this every callback is rejected before it even reaches
    the ID-token/code checks -- see _verify_oauth_state in api/server.py."""
    token = "test-oauth-state-token"
    with client.session_transaction() as session:
        session["oauth_state"] = token
    return token


class TestAppleOAuthCallback:
    """Integration tests for POST /api/auth/oauth/apple/callback."""

    def test_callback_rejects_forged_token(self, client, temp_oauth_config, temp_users_file, oauth_state, monkeypatch):
        import api.server as api_module

        monkeypatch.setattr(api_module, "_get_apple_jwk_client", lambda: _fake_jwk_client(raises=True))

        response = client.post(
            "/api/auth/oauth/apple/callback", json={"id_token": "forged.token.value", "state": oauth_state}
        )
        assert response.status_code == 401

    def test_callback_rejects_missing_state(self, client, temp_oauth_config, temp_users_file):
        response = client.post("/api/auth/oauth/apple/callback", json={"id_token": "whatever"})
        assert response.status_code == 400

    def test_callback_rejects_wrong_state(self, client, temp_oauth_config, temp_users_file, oauth_state):
        response = client.post(
            "/api/auth/oauth/apple/callback", json={"id_token": "whatever", "state": "a-guessed-value"}
        )
        assert response.status_code == 400

    def test_callback_accepts_correctly_signed_token(
        self, client, temp_oauth_config, temp_users_file, oauth_state, rsa_keypair, monkeypatch
    ):
        import api.server as api_module

        private_pem, public_pem = rsa_keypair
        token = _sign_rs256(
            private_pem,
            {
                "sub": "real-apple-user-id",
                "email": "newapple@example.com",
                "aud": "test-apple-client-id",
                "iss": "https://appleid.apple.com",
            },
        )
        monkeypatch.setattr(api_module, "_get_apple_jwk_client", lambda: _fake_jwk_client(public_pem=public_pem))

        response = client.post("/api/auth/oauth/apple/callback", json={"id_token": token, "state": oauth_state})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        assert "apple:real-apple-user-id" in api_module.USERS[data["user"]["username"]]["oauth_providers"]


class TestAppleFormPostRelay:
    """Tests for POST /oauth/callback (api/server.py's
    apple_oauth_form_post_relay).

    Apple requires response_mode=form_post whenever the requested scope
    includes name/email, which get_oauth_url's Apple branch always does --
    so Apple POSTs the OAuth result to the redirect_uri instead of
    redirecting with it in the URL. The SPA's callback page only reads the
    URL's query string, so without this relay, every Apple sign-in would
    silently fail with the page unable to see anything Apple sent. This
    receives that POST and re-issues it as a redirect to the same path
    with the same fields as query params instead, matching what Google's
    flow already looks like to the frontend.

    config/nginx-minecraft.conf is what actually routes POST requests for
    this exact path here in production (GET goes to the SPA) -- not
    covered by these tests, which exercise the Flask route directly.
    """

    def test_relays_all_apple_fields_into_the_redirect_query_string(self, client):
        response = client.post(
            "/oauth/callback",
            data={
                "code": "auth-code-value",
                "state": "state-value",
                "id_token": "id-token-value",
                "user": '{"name":{"firstName":"Test"},"email":"test@example.com"}',
            },
        )
        assert response.status_code == 302
        location = response.headers["Location"]
        assert location.startswith("/oauth/callback?")
        assert "code=auth-code-value" in location
        assert "state=state-value" in location
        assert "id_token=id-token-value" in location
        # The JSON in `user` must survive being round-tripped through a
        # query string -- the frontend's OAuthCallback.jsx does
        # decodeURIComponent(...) then JSON.parse(...) on it.
        query = location.split("?", 1)[1]
        from urllib.parse import parse_qs

        parsed = parse_qs(query)
        assert json.loads(parsed["user"][0]) == {
            "name": {"firstName": "Test"},
            "email": "test@example.com",
        }

    def test_relays_only_the_fields_apple_actually_sent(self, client):
        """No `user` field on a returning user's sign-in (Apple only sends
        it once) -- the relay must not invent one."""
        response = client.post(
            "/oauth/callback",
            data={"code": "auth-code-value", "state": "state-value", "id_token": "id-token-value"},
        )
        assert response.status_code == 302
        assert "user=" not in response.headers["Location"]

    def test_relays_apple_error_response(self, client):
        """A user declining consent, or any other Apple-side error, also
        arrives via form_post -- must reach the SPA's error handling too."""
        response = client.post(
            "/oauth/callback",
            data={"error": "user_cancelled_authorize", "state": "state-value"},
        )
        assert response.status_code == 302
        location = response.headers["Location"]
        assert "error=user_cancelled_authorize" in location
        assert "state=state-value" in location

    def test_get_request_is_not_handled_by_this_route(self, client):
        """GET isn't registered for this route at all -- nginx is what
        sends GET requests for this same path to the SPA in production;
        this just confirms Flask itself doesn't also answer GET here."""
        response = client.get("/oauth/callback")
        assert response.status_code == 405
