#!/usr/bin/env python3
"""
Tests for configuration file management API endpoints
"""

import json
import sys
from pathlib import Path as PathLib

import pytest

PROJECT_ROOT = PathLib(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import api.server as api_module  # noqa: E402


@pytest.fixture
def client():
    """Create test client"""
    api_module.app.config["TESTING"] = True
    with api_module.app.test_client() as client:
        yield client


@pytest.fixture
def mock_api_keys(monkeypatch):
    """Mock API keys for testing"""
    test_key = "test-api-key-123456789012345678901234567890"

    api_module.API_KEYS = {
        test_key: {"name": "test-key", "enabled": True, "created": "2025-01-15T00:00:00Z", "role": "admin"}
    }
    return test_key


@pytest.fixture
def temp_config_dir(tmp_path, monkeypatch):
    """Create temporary config directory"""
    config_dir = tmp_path / "config"
    data_dir = tmp_path / "data"
    config_dir.mkdir()
    data_dir.mkdir()

    monkeypatch.setattr(api_module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(api_module, "CONFIG_ALLOWED_PATHS", {"server.properties": data_dir / "server.properties"})

    return config_dir, data_dir


class TestConfigFilesList:
    """Tests for GET /api/config/files endpoint"""

    def test_list_config_files_requires_auth(self, client):
        """List config files endpoint requires API key"""
        response = client.get("/api/config/files")
        assert response.status_code == 401

    def test_list_config_files_success(self, client, mock_api_keys, temp_config_dir):
        """List config files returns file list"""
        config_dir, data_dir = temp_config_dir

        # Create a test file
        test_file = data_dir / "server.properties"
        test_file.write_text("# Test config\n")

        response = client.get("/api/config/files", headers={"X-API-Key": mock_api_keys})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "files" in data
        assert len(data["files"]) > 0


class TestConfigFileGet:
    """Tests for GET /api/config/files/<filename> endpoint"""

    def test_get_config_file_requires_auth(self, client):
        """Get config file endpoint requires API key"""
        response = client.get("/api/config/files/server.properties")
        assert response.status_code == 401

    def test_get_config_file_not_allowed(self, client, mock_api_keys):
        """Get config file rejects non-allowed files"""
        response = client.get("/api/config/files/../../../etc/passwd", headers={"X-API-Key": mock_api_keys})
        assert response.status_code == 403

    def test_get_config_file_not_found(self, client, mock_api_keys, temp_config_dir):
        """Get config file returns 404 for non-existent file"""
        response = client.get("/api/config/files/server.properties", headers={"X-API-Key": mock_api_keys})
        assert response.status_code == 404


class TestConfigFileSave:
    """Tests for POST /api/config/files/<filename> endpoint"""

    def test_save_config_file_requires_auth(self, client):
        """Save config file endpoint requires API key"""
        response = client.post("/api/config/files/server.properties", json={"content": "test"})
        assert response.status_code == 401

    def test_save_config_file_missing_content(self, client, mock_api_keys):
        """Save config file requires content field"""
        response = client.post(
            "/api/config/files/server.properties",
            headers={"X-API-Key": mock_api_keys},
            json={},
        )
        assert response.status_code == 400

    def test_save_config_file_invalid_properties(self, client, mock_api_keys, temp_config_dir):
        """Save config file validates properties format"""
        # Invalid properties format (missing =)
        invalid_content = "invalid-line-without-equals"
        response = client.post(
            "/api/config/files/server.properties",
            headers={"X-API-Key": mock_api_keys},
            json={"content": invalid_content},
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data

    def test_save_config_file_creates_backup(self, client, mock_api_keys, temp_config_dir, monkeypatch):
        """Save config file creates backup before saving"""
        config_dir, data_dir = temp_config_dir
        test_file = data_dir / "server.properties"
        test_file.write_text("# Original content\n")

        backup_dir = PathLib(temp_config_dir[0]) / "backups" / "config"
        backup_dir.mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr(api_module, "PROJECT_ROOT", PathLib(temp_config_dir[0]))

        valid_content = "# Valid config\nkey=value\n"
        response = client.post(
            "/api/config/files/server.properties",
            headers={"X-API-Key": mock_api_keys},
            json={"content": valid_content},
        )

        # Should succeed and create backup
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get("success") is True

        # Verify backup was created
        backup_files = list(backup_dir.glob("server.properties.*.backup"))
        assert len(backup_files) > 0

    def test_save_config_file_succeeds_without_a_prior_backup(
        self, client, mock_api_keys, temp_config_dir, monkeypatch
    ):
        """Saving a file that doesn't exist yet (no backup to make) still succeeds"""
        config_dir, data_dir = temp_config_dir
        test_file = data_dir / "server.properties"
        assert not test_file.exists()

        monkeypatch.setattr(api_module, "PROJECT_ROOT", PathLib(temp_config_dir[0]))

        valid_content = "# Valid config\nkey=value\n"
        response = client.post(
            "/api/config/files/server.properties",
            headers={"X-API-Key": mock_api_keys},
            json={"content": valid_content},
        )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get("success") is True
        assert data.get("backup") is None


class TestConfigFileValidate:
    """Tests for POST /api/config/files/<filename>/validate endpoint"""

    def test_validate_config_file_requires_auth(self, client):
        """Validate config file endpoint requires API key"""
        response = client.post("/api/config/files/server.properties/validate", json={"content": "test"})
        assert response.status_code == 401

    def test_validate_config_file_valid_properties(self, client, mock_api_keys):
        """Validate config file accepts valid properties format"""
        valid_content = "# Comment\nkey=value\nanother=value2\n"
        response = client.post(
            "/api/config/files/server.properties/validate",
            headers={"X-API-Key": mock_api_keys},
            json={"content": valid_content},
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get("valid") is True
        assert len(data.get("errors", [])) == 0

    def test_validate_config_file_invalid_properties(self, client, mock_api_keys):
        """Validate config file rejects invalid properties format"""
        invalid_content = "invalid-line-without-equals\n"
        response = client.post(
            "/api/config/files/server.properties/validate",
            headers={"X-API-Key": mock_api_keys},
            json={"content": invalid_content},
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data.get("valid") is False
        assert len(data.get("errors", [])) > 0


class TestInvalidYamlReporting:
    """A YAML syntax error is reported with its line and column.

    These go through api.config_redaction.describe_yaml_error. When that
    function moved out of server.py, nothing caught the callers losing it,
    because no test sent invalid YAML.
    """

    BAD_YAML = "services:\n  web:\n    image: nginx\n   ports: [80\n"

    @pytest.fixture
    def compose_file(self, tmp_path, monkeypatch):
        yaml = pytest.importorskip("yaml")
        compose = tmp_path / "docker-compose.yml"
        compose.write_text("services: {}\n")
        monkeypatch.setattr(api_module, "CONFIG_ALLOWED_PATHS", {"docker-compose.yml": compose})
        with pytest.raises(yaml.YAMLError):
            yaml.safe_load(self.BAD_YAML)  # the fixture's premise: this really is invalid
        return compose

    def test_describe_yaml_error_names_problem_line_and_column(self):
        yaml = pytest.importorskip("yaml")
        from api.config_redaction import describe_yaml_error

        with pytest.raises(yaml.YAMLError) as caught:
            yaml.safe_load(self.BAD_YAML)

        message = describe_yaml_error(caught.value)
        assert message.startswith("Invalid YAML: ")
        assert "line " in message and "column " in message

    def test_describe_yaml_error_without_a_position(self):
        from api.config_redaction import describe_yaml_error

        assert describe_yaml_error(Exception("anything")) == "Invalid YAML: could not be parsed"

    def test_save_rejects_invalid_yaml_with_a_location(self, client, mock_api_keys, compose_file):
        response = client.post(
            "/api/config/files/docker-compose.yml",
            headers={"X-API-Key": mock_api_keys},
            json={"content": self.BAD_YAML},
        )

        assert response.status_code == 400
        assert response.get_json()["error"].startswith("Invalid YAML: ")
        assert compose_file.read_text() == "services: {}\n"  # nothing was written

    def test_validate_reports_invalid_yaml_with_a_line(self, client, mock_api_keys, compose_file):
        response = client.post(
            "/api/config/files/docker-compose.yml/validate",
            headers={"X-API-Key": mock_api_keys},
            json={"content": self.BAD_YAML},
        )

        assert response.status_code == 200
        errors = response.get_json()["errors"]
        assert len(errors) == 1
        assert errors[0]["message"].startswith("Invalid YAML: ")
        assert errors[0]["line"] > 0
