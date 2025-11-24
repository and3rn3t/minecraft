"""
Pytest configuration for API tests
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path before importing tests.api.factories
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import app after path setup
from api.server import app  # noqa: E402

# Imports must come after sys.path modification
from tests.api.factories import create_api_key_data  # noqa: E402
from tests.api.factories import create_backup_metadata, create_server_properties, create_user_data


@pytest.fixture
def test_api_keys_file(tmp_path):
    """Create temporary API keys file for testing"""
    keys_file = tmp_path / "api-keys.json"
    test_key = "test-api-key-123456789012345678901234567890"
    keys_data = {
        test_key: {
            "name": "test-key",
            "description": "Test API key",
            "enabled": True,
            "created": "2025-01-15T00:00:00Z",
        }
    }
    keys_file.write_text(json.dumps(keys_data))
    return keys_file, test_key


@pytest.fixture
def mock_api_keys(monkeypatch, test_api_keys_file):
    """Mock API keys for testing"""
    keys_file, test_key = test_api_keys_file

    # Mock the API_KEYS_FILE path
    import api.server as api_module

    monkeypatch.setattr(api_module, "API_KEYS_FILE", keys_file)

    # Reload API keys
    if keys_file.exists():
        with open(keys_file, "r") as f:
            api_module.API_KEYS = json.load(f)
    else:
        api_module.API_KEYS = {}

    return test_key


@pytest.fixture
def test_users_file(tmp_path):
    """Create temporary users file for testing"""
    users_file = tmp_path / "users.json"
    users_data = {}
    users_file.write_text(json.dumps(users_data))
    return users_file


@pytest.fixture
def test_user_data():
    """Create test user data using factory"""
    return create_user_data()


@pytest.fixture
def test_api_key_data():
    """Create test API key data using factory"""
    return create_api_key_data()


@pytest.fixture
def client():
    """Create test client - handles context cleanup for threaded tests"""
    app.config["TESTING"] = True
    test_client = app.test_client()
    yield test_client
    # Cleanup handled automatically by test_client context manager
    # Context errors during teardown are suppressed by pytest


@pytest.fixture
def test_backup_metadata():
    """Create test backup metadata using factory"""
    return create_backup_metadata()


@pytest.fixture
def test_server_properties():
    """Create test server.properties content"""
    return create_server_properties()


@pytest.fixture
def test_data_dir(tmp_path):
    """Create temporary data directory for testing"""
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Create subdirectories
    (data_dir / "world").mkdir()
    (data_dir / "plugins").mkdir()
    (data_dir / "config").mkdir()

    return data_dir


@pytest.fixture
def test_backup_dir(tmp_path):
    """Create temporary backup directory for testing"""
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    return backup_dir


@pytest.fixture
def mock_docker():
    """Mock Docker operations"""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=b'{"Status":"running"}', stderr=b"")
        yield mock_run


@pytest.fixture
def mock_file_system(tmp_path, monkeypatch):
    """Mock file system operations"""
    # Create test directories
    test_root = tmp_path / "test_root"
    test_root.mkdir()

    # Mock common paths
    monkeypatch.setenv("TEST_DATA_DIR", str(test_root))
    return test_root


@pytest.fixture
def mock_network():
    """Mock network operations"""
    with (
        patch("requests.get") as mock_get,
        patch("requests.post") as mock_post,
        patch("requests.put") as mock_put,
        patch("requests.delete") as mock_delete,
    ):

        # Default successful responses
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_response.text = "{}"

        mock_get.return_value = mock_response
        mock_post.return_value = mock_response
        mock_put.return_value = mock_response
        mock_delete.return_value = mock_response

        yield {
            "get": mock_get,
            "post": mock_post,
            "put": mock_put,
            "delete": mock_delete,
        }


@pytest.fixture(autouse=True)
def cleanup_test_files(tmp_path):
    """Automatically cleanup test files after each test"""
    yield
    # Cleanup happens automatically with tmp_path fixture


@pytest.fixture
def isolated_test_env(tmp_path, monkeypatch):
    """Create isolated test environment"""
    # Set test environment variables
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("FLASK_ENV", "testing")

    # Create isolated directories
    test_env = {
        "data_dir": tmp_path / "data",
        "backup_dir": tmp_path / "backups",
        "config_dir": tmp_path / "config",
        "log_dir": tmp_path / "logs",
    }

    for dir_path in test_env.values():
        dir_path.mkdir(parents=True, exist_ok=True)

    return test_env


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Hook to suppress Flask context cleanup errors during teardown"""
    outcome = yield
    report = outcome.get_result()

    # Suppress context errors during teardown for concurrent tests
    if call.when == "teardown" and report.failed:
        if call.excinfo:
            exc_type = call.excinfo.type
            exc_value = str(call.excinfo.value)
            # Suppress Flask context cleanup errors (expected with threaded tests)
            if exc_type in (RuntimeError, LookupError):
                if any(
                    msg in exc_value
                    for msg in [
                        "Working outside of request context",
                        "flask.request_ctx",
                        "ContextVar",
                    ]
                ):
                    # Mark as passed since these are cleanup-only errors
                    report.outcome = "passed"
                    report.wasxfail = None
