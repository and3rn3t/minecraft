#!/usr/bin/env python3
"""
Tests for backup management API endpoints (restore/delete)
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
def mock_api_keys(monkeypatch):
    """Mock API keys for testing"""
    test_key = "test-api-key-123456789012345678901234567890"
    import api.server as api_module

    api_module.API_KEYS = {test_key: {"name": "test-key", "enabled": True, "created": "2025-01-15T00:00:00Z"}}
    return test_key


@pytest.fixture
def temp_backup_environment(tmp_path, monkeypatch):
    """Create temporary backup environment"""
    backups_dir = tmp_path / "backups"
    data_dir = tmp_path / "data"
    backups_dir.mkdir()
    data_dir.mkdir()

    import api.server as api_module

    monkeypatch.setattr(api_module, "PROJECT_ROOT", tmp_path)

    # Create a test backup file
    backup_file = backups_dir / "minecraft_backup_20250115_120000.tar.gz"
    backup_file.write_bytes(b"fake tar.gz content")

    return backups_dir, data_dir, backup_file


class TestBackupRestore:
    """Tests for POST /api/backups/<filename>/restore endpoint"""

    def test_restore_backup_requires_auth(self, client):
        """Restore backup endpoint requires API key"""
        response = client.post("/api/backups/test_backup.tar.gz/restore")
        assert response.status_code == 401

    def test_restore_backup_not_found(self, client, mock_api_keys, temp_backup_environment):
        """Restore backup returns 404 for non-existent backup"""
        backups_dir, data_dir, backup_file = temp_backup_environment

        response = client.post(
            "/api/backups/nonexistent_backup.tar.gz/restore",
            headers={"X-API-Key": mock_api_keys},
        )
        assert response.status_code == 404

    def test_restore_backup_invalid_filename(self, client, mock_api_keys):
        """Restore backup rejects invalid backup filenames"""
        response = client.post(
            "/api/backups/../../../etc/passwd/restore",
            headers={"X-API-Key": mock_api_keys},
        )
        assert response.status_code == 400

    @patch("api.server.run_script")
    def test_restore_backup_stops_server(self, mock_run_script, client, mock_api_keys, temp_backup_environment):
        """Restore backup stops server before restore"""
        backups_dir, data_dir, backup_file = temp_backup_environment
        mock_run_script.return_value = (None, None, 0)

        # Mock tarfile extraction
        with patch("tarfile.open") as mock_tarfile:
            mock_tar = MagicMock()
            mock_tarfile.return_value.__enter__.return_value = mock_tar

            response = client.post(
                f"/api/backups/{backup_file.name}/restore",
                headers={"X-API-Key": mock_api_keys},
            )

            # Should attempt to stop server
            assert mock_run_script.called
            call_args = mock_run_script.call_args
            assert call_args[0][0] == "manage.sh"
            assert call_args[0][1] == "stop"


class TestBackupDelete:
    """Tests for DELETE /api/backups/<filename> endpoint"""

    def test_delete_backup_requires_auth(self, client):
        """Delete backup endpoint requires API key"""
        response = client.delete("/api/backups/test_backup.tar.gz")
        assert response.status_code == 401

    def test_delete_backup_not_found(self, client, mock_api_keys):
        """Delete backup returns 404 for non-existent backup"""
        response = client.delete(
            "/api/backups/nonexistent_backup.tar.gz",
            headers={"X-API-Key": mock_api_keys},
        )
        assert response.status_code == 404

    def test_delete_backup_invalid_filename(self, client, mock_api_keys):
        """Delete backup rejects invalid backup filenames"""
        response = client.delete(
            "/api/backups/../../../etc/passwd",
            headers={"X-API-Key": mock_api_keys},
        )
        assert response.status_code == 400

    def test_delete_backup_success(self, client, mock_api_keys, temp_backup_environment, monkeypatch):
        """Delete backup successfully removes backup file"""
        backups_dir, data_dir, backup_file = temp_backup_environment

        import api.server as api_module

        monkeypatch.setattr(api_module, "PROJECT_ROOT", Path(temp_backup_environment[0].parent))

        assert backup_file.exists()

        response = client.delete(
            f"/api/backups/{backup_file.name}",
            headers={"X-API-Key": mock_api_keys},
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get("success") is True

        # Verify backup file was deleted
        assert not backup_file.exists()
