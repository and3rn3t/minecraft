"""
Pytest configuration for API tests
"""

import pytest
import json
from pathlib import Path


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
            "created": "2025-01-15T00:00:00Z"
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
    monkeypatch.setattr(api_module, 'API_KEYS_FILE', keys_file)

    # Reload API keys
    if keys_file.exists():
        with open(keys_file, 'r') as f:
            api_module.API_KEYS = json.load(f)
    else:
        api_module.API_KEYS = {}

    return test_key

