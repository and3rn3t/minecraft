#!/usr/bin/env python3
"""
Tests for OAuth API endpoints
"""

import json
import sys
import tempfile
from pathlib import Path
from pathlib import Path as PathLib
from unittest.mock import MagicMock, patch

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
    with client.session_transaction() as session:
        session["username"] = "testuser"
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
