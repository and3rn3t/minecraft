#!/usr/bin/env python3
"""Tests for the /api/datapacks endpoints (scripts/datapack-manager.sh)."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.server import app  # noqa: E402


@pytest.fixture
def client():
    """Create test client"""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_api_key():
    """Create mock API key"""
    return "test-api-key-datapacks-12345678901234567890"


class TestDatapacksAuth:
    """Every datapack route requires an API key."""

    def test_list_requires_auth(self, client):
        response = client.get("/api/datapacks")
        assert response.status_code == 401

    def test_install_requires_auth(self, client):
        response = client.post("/api/datapacks/install", data={"name": "family", "url": "https://example.com/x.zip"})
        assert response.status_code == 401

    def test_enable_requires_auth(self, client):
        response = client.put("/api/datapacks/family/enable")
        assert response.status_code == 401

    def test_disable_requires_auth(self, client):
        response = client.put("/api/datapacks/family/disable")
        assert response.status_code == 401

    def test_delete_requires_auth(self, client):
        response = client.delete("/api/datapacks/family")
        assert response.status_code == 401


class TestListDatapacks:
    @patch("api.server.run_script")
    def test_list_success(self, mock_run_script, client, mock_api_key):
        mock_run_script.return_value = (
            json.dumps([{"name": "family", "enabled": True, "world": "world"}]),
            "",
            0,
        )

        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True, "role": "admin"}}):
            response = client.get("/api/datapacks", headers={"X-API-Key": mock_api_key})

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["count"] == 1
        assert data["datapacks"][0]["name"] == "family"
        mock_run_script.assert_called_once_with("datapack-manager.sh", "list-json")

    @patch("api.server.run_script")
    def test_list_falls_back_to_empty_on_bad_output(self, mock_run_script, client, mock_api_key):
        mock_run_script.return_value = ("not json", "", 0)

        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True, "role": "admin"}}):
            response = client.get("/api/datapacks", headers={"X-API-Key": mock_api_key})

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data == {"datapacks": [], "count": 0}


class TestInstallDatapack:
    @patch("api.server.run_script")
    def test_install_from_url(self, mock_run_script, client, mock_api_key):
        mock_run_script.return_value = ("Installed datapack source: config/datapacks/family", "", 0)

        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True, "role": "admin"}}):
            response = client.post(
                "/api/datapacks/install",
                data={"name": "family", "url": "https://example.com/family.zip"},
                headers={"X-API-Key": mock_api_key},
            )

        assert response.status_code == 200
        args, kwargs = mock_run_script.call_args
        assert args[:3] == ("datapack-manager.sh", "install", "family")
        assert "--url" in args and "https://example.com/family.zip" in args
        assert "--yes" in args

    def test_install_requires_name(self, client, mock_api_key):
        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True, "role": "admin"}}):
            response = client.post(
                "/api/datapacks/install",
                data={"url": "https://example.com/family.zip"},
                headers={"X-API-Key": mock_api_key},
            )
        assert response.status_code == 400

    def test_install_requires_url_or_file(self, client, mock_api_key):
        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True, "role": "admin"}}):
            response = client.post(
                "/api/datapacks/install",
                data={"name": "family"},
                headers={"X-API-Key": mock_api_key},
            )
        assert response.status_code == 400

    @patch("api.server.run_script")
    def test_install_failure_returns_500(self, mock_run_script, client, mock_api_key):
        mock_run_script.return_value = ("", "Error: unknown option", 1)

        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True, "role": "admin"}}):
            response = client.post(
                "/api/datapacks/install",
                data={"name": "family", "url": "https://example.com/family.zip"},
                headers={"X-API-Key": mock_api_key},
            )

        assert response.status_code == 500
        assert "error" in json.loads(response.data)


class TestEnableDisableDeleteDatapack:
    @patch("api.server.run_script")
    def test_enable_success(self, mock_run_script, client, mock_api_key):
        mock_run_script.return_value = ("Enabled datapack: family (world: world)", "", 0)

        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True, "role": "admin"}}):
            response = client.put("/api/datapacks/family/enable", headers={"X-API-Key": mock_api_key})

        assert response.status_code == 200
        mock_run_script.assert_called_once_with("datapack-manager.sh", "enable", "family")

    @patch("api.server.run_script")
    def test_disable_success(self, mock_run_script, client, mock_api_key):
        mock_run_script.return_value = ("Disabled datapack: family (world: world)", "", 0)

        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True, "role": "admin"}}):
            response = client.put("/api/datapacks/family/disable", headers={"X-API-Key": mock_api_key})

        assert response.status_code == 200
        mock_run_script.assert_called_once_with("datapack-manager.sh", "disable", "family")

    @patch("api.server.run_script")
    def test_delete_success(self, mock_run_script, client, mock_api_key):
        mock_run_script.return_value = ("Deleted datapack: family", "", 0)

        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True, "role": "admin"}}):
            response = client.delete("/api/datapacks/family", headers={"X-API-Key": mock_api_key})

        assert response.status_code == 200
        mock_run_script.assert_called_once_with("datapack-manager.sh", "delete", "family", "--yes")

    @patch("api.server.run_script")
    def test_enable_failure_returns_500(self, mock_run_script, client, mock_api_key):
        mock_run_script.return_value = ("", "Error: no such datapack: ghost", 1)

        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True, "role": "admin"}}):
            response = client.put("/api/datapacks/ghost/enable", headers={"X-API-Key": mock_api_key})

        assert response.status_code == 500
        assert "error" in json.loads(response.data)


class TestDatapacksPermissions:
    """user role has datapacks.view but not datapacks.manage."""

    @patch("api.server.run_script")
    def test_user_role_can_list(self, mock_run_script, client, mock_api_key):
        mock_run_script.return_value = ("[]", "", 0)

        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True, "role": "user"}}):
            response = client.get("/api/datapacks", headers={"X-API-Key": mock_api_key})

        assert response.status_code == 200

    def test_user_role_cannot_enable(self, client, mock_api_key):
        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True, "role": "user"}}):
            response = client.put("/api/datapacks/family/enable", headers={"X-API-Key": mock_api_key})

        assert response.status_code == 403
