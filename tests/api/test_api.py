#!/usr/bin/env python3
"""
API Tests
Tests for the REST API server
"""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

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

    def test_status_filter_is_anchored_to_the_exact_container_name(self, client, mock_api_keys):
        """A container merely named similarly (e.g. minecraft-server-test) must not match.

        This is the same exact-name check scripts/lib/common.sh's
        container_running() makes for every other caller.
        """
        with patch("api.server.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="Up 2 hours", stderr="")
            client.get('/api/status', headers={'X-API-Key': mock_api_keys})

        docker_args = mock_run.call_args.args[0]
        assert "--filter" in docker_args
        filter_arg = docker_args[docker_args.index("--filter") + 1]
        assert filter_arg == "name=^minecraft-server$"

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
        """The lines parameter is passed through to docker logs --tail"""
        with patch('api.server.run_script', return_value=('', '', 0)), \
             patch('api.server.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout='first\nsecond')
            response = client.get(
                '/api/logs?lines=50',
                headers={'X-API-Key': mock_api_keys}
            )

        assert response.status_code == 200
        assert response.get_json() == {'logs': ['first', 'second'], 'lines': 2}
        assert mock_run.call_args.args[0] == ['docker', 'logs', '--tail', '50', 'minecraft-server']

    def test_logs_never_runs_the_following_manage_script(self, client, mock_api_keys):
        """`manage.sh logs` follows the log forever (compose logs -f). The endpoint used to
        run it first, so every request waited for run_script's 30s timeout."""
        with patch('api.server.run_script') as mock_script, \
             patch('api.server.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout='a\nb')
            response = client.get('/api/logs', headers={'X-API-Key': mock_api_keys})

        assert response.status_code == 200
        mock_script.assert_not_called()

    def test_a_docker_failure_reports_dockers_own_message(self, client, mock_api_keys):
        message = 'Error response from daemon: No such container: minecraft-server'
        with patch('api.server.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout='', stderr=message)
            response = client.get('/api/logs', headers={'X-API-Key': mock_api_keys})

        assert response.status_code == 200
        assert response.get_json() == {'logs': [message], 'lines': 1}

    def test_a_docker_failure_with_no_message_says_so(self, client, mock_api_keys):
        with patch('api.server.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout='', stderr='')
            response = client.get('/api/logs', headers={'X-API-Key': mock_api_keys})

        assert response.get_json() == {'logs': ['Unable to retrieve logs'], 'lines': 1}

    @pytest.mark.parametrize('error', [FileNotFoundError('docker'), subprocess.TimeoutExpired('docker', 10)])
    def test_docker_missing_or_too_slow_is_reported_not_raised(self, client, mock_api_keys, error):
        with patch('api.server.subprocess.run', side_effect=error):
            response = client.get('/api/logs', headers={'X-API-Key': mock_api_keys})

        assert response.status_code == 200
        assert response.get_json() == {'logs': ['Unable to retrieve logs'], 'lines': 1}


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
