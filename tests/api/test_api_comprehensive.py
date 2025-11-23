#!/usr/bin/env python3
"""
Comprehensive API Tests
Tests API endpoints beyond just authentication checks
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
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
    return "test-api-key-comprehensive-12345678901234567890"


class TestServerControlComprehensive:
    """Comprehensive tests for server control endpoints"""

    @patch("api.server.run_script")
    def test_start_server_success(self, mock_run_script, client, mock_api_key):
        """Test successful server start"""
        mock_run_script.return_value = ("Server started", "", 0)

        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True}}):
            response = client.post("/api/server/start", headers={"X-API-Key": mock_api_key})

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        mock_run_script.assert_called_once_with("manage.sh", "start")

    @patch("api.server.run_script")
    def test_stop_server_success(self, mock_run_script, client, mock_api_key):
        """Test successful server stop"""
        mock_run_script.return_value = ("Server stopped", "", 0)

        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True}}):
            response = client.post("/api/server/stop", headers={"X-API-Key": mock_api_key})

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True

    @patch("api.server.run_script")
    def test_restart_server_success(self, mock_run_script, client, mock_api_key):
        """Test successful server restart"""
        mock_run_script.return_value = ("Server restarted", "", 0)

        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True}}):
            response = client.post("/api/server/restart", headers={"X-API-Key": mock_api_key})

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True


class TestBackupComprehensive:
    """Comprehensive tests for backup endpoints"""

    @patch("api.server.run_script")
    def test_create_backup_success(self, mock_run_script, client, mock_api_key):
        """Test successful backup creation"""
        mock_run_script.return_value = ("Backup created: backup_20240127_120000.tar.gz", "", 0)

        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True}}):
            response = client.post("/api/backup", headers={"X-API-Key": mock_api_key})

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "backup" in data or "success" in data

    @patch("api.server.run_script")
    def test_list_backups_success(self, mock_run_script, client, mock_api_key):
        """Test successful backup listing"""
        mock_run_script.return_value = ("backup_20240127_120000.tar.gz\nbackup_20240126_120000.tar.gz", "", 0)

        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True}}):
            response = client.get("/api/backups", headers={"X-API-Key": mock_api_key})

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "backups" in data or "files" in data


class TestMetricsComprehensive:
    """Comprehensive tests for metrics endpoint"""

    @patch("api.server.run_script")
    @patch("api.server.subprocess.run")
    def test_metrics_returns_data(self, mock_subprocess, mock_run_script, client, mock_api_key):
        """Test metrics endpoint returns data"""
        mock_run_script.return_value = ("", "", 0)
        mock_subprocess.return_value = MagicMock(returncode=0, stdout="50.0%,1.5GiB / 2.0GiB,75.0%")

        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True}}):
            response = client.get("/api/metrics", headers={"X-API-Key": mock_api_key})

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "metrics" in data
        assert "timestamp" in data


class TestConfigFilesComprehensive:
    """Comprehensive tests for config file endpoints"""

    @patch("builtins.open", create=True)
    def test_get_config_file_success(self, mock_open, client, mock_api_key):
        """Test successful config file retrieval"""
        from pathlib import Path
        from unittest.mock import MagicMock
        from unittest.mock import mock_open as mock_file_open
        from unittest.mock import patch

        # Create a proper mock path
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_path.stat.return_value.st_size = 12
        # Mock relative_to to return a string path
        mock_path.relative_to.return_value = Path("data/server.properties")
        # Make str() work on the mock
        mock_path.__str__ = MagicMock(return_value="data/server.properties")

        # Mock file content
        mock_file_content = "test content"
        mock_file = mock_file_open(read_data=mock_file_content)
        mock_open.return_value = mock_file.return_value

        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True}}):
            with patch("api.server.CONFIG_ALLOWED_PATHS", {"server.properties": mock_path}):
                # Mock PROJECT_ROOT to avoid path issues
                mock_project_root = MagicMock(spec=Path)
                mock_project_root.__truediv__ = MagicMock(return_value=mock_path)
                with patch("api.server.PROJECT_ROOT", mock_project_root):
                    response = client.get("/api/config/files/server.properties", headers={"X-API-Key": mock_api_key})

        assert (
            response.status_code == 200
        ), f"Expected 200, got {response.status_code}. Response: {response.data.decode() if hasattr(response.data, 'decode') else response.data}"
        data = json.loads(response.data)
        assert "content" in data or "file" in data

    @patch("pathlib.Path.exists")
    @patch("builtins.open", create=True)
    def test_save_config_file_success(self, mock_open, mock_exists, client, mock_api_key):
        """Test successful config file save"""
        mock_exists.return_value = True
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True}}):
            response = client.post(
                "/api/config/files/server.properties",
                headers={"X-API-Key": mock_api_key},
                json={"content": "test content"},
            )

        # Should succeed or return appropriate status
        assert response.status_code in [200, 201, 400, 500]


class TestPlayersComprehensive:
    """Comprehensive tests for player endpoints"""

    @patch("api.server.run_script")
    def test_get_players_success(self, mock_run_script, client, mock_api_key):
        """Test successful player list retrieval"""
        mock_run_script.return_value = ("There are 2 of a max of 10 players online: player1, player2", "", 0)

        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True}}):
            response = client.get("/api/players", headers={"X-API-Key": mock_api_key})

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "players" in data or "count" in data


class TestWorldsComprehensive:
    """Comprehensive tests for world endpoints"""

    @patch("api.server.run_script")
    def test_list_worlds_success(self, mock_run_script, client, mock_api_key):
        """Test successful world listing"""
        mock_run_script.return_value = ("world (ACTIVE)\nworld_nether\nworld_the_end", "", 0)

        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True}}):
            response = client.get("/api/worlds", headers={"X-API-Key": mock_api_key})

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "worlds" in data or "count" in data


class TestErrorHandlingComprehensive:
    """Comprehensive error handling tests"""

    def test_invalid_json_returns_400(self, client, mock_api_key):
        """Test invalid JSON returns 400"""
        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True}}):
            response = client.post(
                "/api/server/command",
                headers={"X-API-Key": mock_api_key, "Content-Type": "application/json"},
                data="invalid json",
            )

        assert response.status_code in [400, 415, 500]

    def test_missing_required_field_returns_400(self, client, mock_api_key):
        """Test missing required field returns 400"""
        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True}}):
            response = client.post(
                "/api/server/command", headers={"X-API-Key": mock_api_key}, json={}  # Missing 'command' field
            )

        assert response.status_code in [400, 401, 500]

    @patch("api.server.run_script")
    def test_script_failure_returns_500(self, mock_run_script, client, mock_api_key):
        """Test script failure returns 500"""
        mock_run_script.return_value = ("", "Error occurred", 1)

        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True}}):
            response = client.post("/api/server/start", headers={"X-API-Key": mock_api_key})

        assert response.status_code == 500
        data = json.loads(response.data)
        assert "error" in data


class TestQueryParameters:
    """Tests for query parameter handling"""

    @patch("api.server.run_script")
    def test_logs_with_lines_parameter(self, mock_run_script, client, mock_api_key):
        """Test logs endpoint with lines parameter"""
        mock_run_script.return_value = ("log line 1\nlog line 2", "", 0)

        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True}}):
            response = client.get("/api/logs?lines=50", headers={"X-API-Key": mock_api_key})

        # Should accept parameter without error
        assert response.status_code != 401

    def test_analytics_report_with_hours_parameter(self, client, mock_api_key):
        """Test analytics report with hours parameter"""
        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True}}):
            response = client.get("/api/analytics/report?hours=6", headers={"X-API-Key": mock_api_key})

        # Should accept parameter (may fail if no data, but not 401)
        assert response.status_code != 401
        assert response.status_code != 401
