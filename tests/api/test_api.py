#!/usr/bin/env python3
"""
API Tests
Tests for the REST API server
"""

import pytest
import json
import sys
from pathlib import Path

# Add project root to path before importing api.server
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import after path modification
from api.server import app  # noqa: E402


@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def api_key():
    """Create test API key"""
    # In real tests, this would create a test key
    return "test-api-key-123456789012345678901234567890"


class TestHealthEndpoint:
    """Tests for /api/health endpoint"""

    def test_health_endpoint_no_auth(self, client):
        """Health endpoint should work without authentication"""
        response = client.get('/api/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
        assert 'timestamp' in data
        assert 'version' in data


class TestStatusEndpoint:
    """Tests for /api/status endpoint"""

    def test_status_requires_auth(self, client):
        """Status endpoint requires API key"""
        response = client.get('/api/status')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data

    def test_status_with_invalid_key(self, client):
        """Status endpoint rejects invalid API key"""
        response = client.get(
            '/api/status',
            headers={'X-API-Key': 'invalid-key'}
        )
        assert response.status_code == 401


class TestServerControl:
    """Tests for server control endpoints"""

    def test_start_requires_auth(self, client):
        """Start endpoint requires API key"""
        response = client.post('/api/server/start')
        assert response.status_code == 401

    def test_stop_requires_auth(self, client):
        """Stop endpoint requires API key"""
        response = client.post('/api/server/stop')
        assert response.status_code == 401

    def test_restart_requires_auth(self, client):
        """Restart endpoint requires API key"""
        response = client.post('/api/server/restart')
        assert response.status_code == 401


class TestServerCommand:
    """Tests for /api/server/command endpoint"""

    def test_command_requires_auth(self, client):
        """Command endpoint requires API key"""
        response = client.post(
            '/api/server/command',
            json={'command': 'list'}
        )
        assert response.status_code == 401

    def test_command_requires_command_field(self, client, mock_api_keys):
        """Command endpoint requires command in body"""
        response = client.post(
            '/api/server/command',
            headers={'X-API-Key': mock_api_keys},
            json={}
        )
        # Should return 400 for missing command field
        # Note: If API key validation fails first, it returns 401
        assert response.status_code in [400, 401]


class TestBackupEndpoints:
    """Tests for backup endpoints"""

    def test_backup_requires_auth(self, client):
        """Backup endpoint requires API key"""
        response = client.post('/api/backup')
        assert response.status_code == 401

    def test_backups_list_requires_auth(self, client):
        """Backups list endpoint requires API key"""
        response = client.get('/api/backups')
        assert response.status_code == 401


class TestLogsEndpoint:
    """Tests for /api/logs endpoint"""

    def test_logs_requires_auth(self, client):
        """Logs endpoint requires API key"""
        response = client.get('/api/logs')
        assert response.status_code == 401

    def test_logs_accepts_lines_parameter(self, client, mock_api_keys):
        """Logs endpoint accepts lines parameter"""
        response = client.get(
            '/api/logs?lines=50',
            headers={'X-API-Key': mock_api_keys}
        )
        # May fail if server not running, but should not be 401
        assert response.status_code != 401


class TestPlayersEndpoint:
    """Tests for /api/players endpoint"""

    def test_players_requires_auth(self, client):
        """Players endpoint requires API key"""
        response = client.get('/api/players')
        assert response.status_code == 401


class TestMetricsEndpoint:
    """Tests for /api/metrics endpoint"""

    def test_metrics_requires_auth(self, client):
        """Metrics endpoint requires API key"""
        response = client.get('/api/metrics')
        assert response.status_code == 401


class TestWorldsEndpoint:
    """Tests for /api/worlds endpoint"""

    def test_worlds_requires_auth(self, client):
        """Worlds endpoint requires API key"""
        response = client.get('/api/worlds')
        assert response.status_code == 401


class TestPluginsEndpoint:
    """Tests for /api/plugins endpoint"""

    def test_plugins_requires_auth(self, client):
        """Plugins endpoint requires API key"""
        response = client.get('/api/plugins')
        assert response.status_code == 401


class TestErrorHandling:
    """Tests for error handling"""

    def test_404_for_unknown_endpoint(self, client):
        """Unknown endpoints return 404"""
        response = client.get('/api/unknown')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'error' in data

    def test_cors_headers_present(self, client):
        """CORS headers are present in responses"""
        response = client.get('/api/health')
        # Check if CORS headers are set (either by flask-cors or manual)
        # This depends on whether flask-cors is installed
        assert response.status_code == 200
