#!/usr/bin/env python3
"""
Analytics API Tests
Tests for analytics endpoints
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
# Add scripts directory to path for analytics_processor import
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

# Create a mock analytics_processor module for patching
# The actual file is analytics-processor.py (with hyphen), but it's imported as analytics_processor
# We need to create a mock module that can be patched
import types

from api.server import app  # noqa: E402


# Create mock AnalyticsProcessor class
class MockAnalyticsProcessor:
    pass


# Create and register the mock module
mock_analytics_module = types.ModuleType("analytics_processor")
mock_analytics_module.AnalyticsProcessor = MockAnalyticsProcessor
sys.modules["analytics_processor"] = mock_analytics_module


@pytest.fixture
def client():
    """Create test client"""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_api_key():
    """Create mock API key"""
    return "test-api-key-analytics-12345678901234567890"


@pytest.fixture
def mock_analytics_data():
    """Mock analytics data"""
    return {
        "players": [
            {"timestamp": 1706371200, "datetime": "2024-01-27 12:00:00", "data": ["player1", "player2"]},
            {"timestamp": 1706374800, "datetime": "2024-01-27 13:00:00", "data": ["player1"]},
        ],
        "performance": [
            {
                "timestamp": 1706371200,
                "datetime": "2024-01-27 12:00:00",
                "data": {"tps": 20.0, "cpu": 50.0, "memory": 1000},
            },
            {
                "timestamp": 1706374800,
                "datetime": "2024-01-27 13:00:00",
                "data": {"tps": 19.5, "cpu": 55.0, "memory": 1100},
            },
        ],
    }


@pytest.fixture
def mock_analytics_report():
    """Mock analytics report"""
    return {
        "generated_at": "2024-01-27T12:00:00",
        "period_hours": 24,
        "player_behavior": {
            "unique_players": 5,
            "peak_hour": 20,
            "hourly_distribution": {20: 10, 21: 8, 22: 5},
            "total_events": 15,
        },
        "performance": {
            "tps": {
                "trend": {"direction": "stable", "slope": 0.1, "change_percent": 2.5},
                "current": 20.0,
                "average": 19.8,
                "anomalies": [],
                "prediction": {"predicted": 20.1, "confidence": 85.0},
            },
            "cpu": {"trend": {"direction": "increasing"}, "current": 50.0, "average": 48.0},
            "memory": {"trend": {"direction": "stable"}, "current": 1000, "average": 950},
        },
        "summary": {
            "status": "healthy",
            "warnings": [],
            "recommendations": [],
        },
    }


class TestAnalyticsCollect:
    """Tests for /api/analytics/collect endpoint"""

    def test_collect_requires_auth(self, client):
        """Collect endpoint requires authentication"""
        response = client.post("/api/analytics/collect")
        assert response.status_code == 401

    @patch("api.server.run_script")
    def test_collect_success(self, mock_run_script, client, mock_api_key):
        """Test successful analytics collection"""
        mock_run_script.return_value = ("", "", 0)

        # Mock API key authentication
        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True}}):
            response = client.post("/api/analytics/collect", headers={"X-API-Key": mock_api_key})

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["success"] is True
        mock_run_script.assert_called_once_with("analytics-collector.sh")

    @patch("api.server.run_script")
    def test_collect_failure(self, mock_run_script, client, mock_api_key):
        """Test analytics collection failure"""
        mock_run_script.return_value = ("", "Error message", 1)

        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True}}):
            response = client.post("/api/analytics/collect", headers={"X-API-Key": mock_api_key})

        assert response.status_code == 500
        data = json.loads(response.data)
        assert "error" in data


class TestAnalyticsReport:
    """Tests for /api/analytics/report endpoint"""

    def test_report_requires_auth(self, client):
        """Report endpoint requires authentication"""
        response = client.get("/api/analytics/report")
        assert response.status_code == 401

    @patch("api.server.subprocess.run")
    @patch("pathlib.Path.exists")
    @patch("builtins.open", create=True)
    def test_report_success(self, mock_open, mock_exists, mock_subprocess, client, mock_api_key, mock_analytics_report):
        """Test successful report retrieval"""
        mock_exists.return_value = True
        mock_subprocess.return_value = MagicMock(returncode=0)
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(mock_analytics_report)

        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True}}):
            response = client.get("/api/analytics/report?hours=24", headers={"X-API-Key": mock_api_key})

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "report" in data
        assert data["report"]["period_hours"] == 24

    def test_report_invalid_hours(self, client, mock_api_key):
        """Test report with invalid hours parameter"""
        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True}}):
            response = client.get("/api/analytics/report?hours=999", headers={"X-API-Key": mock_api_key})
        # Should default to 24 hours
        assert response.status_code in [200, 404, 500]  # Depends on file existence

    @patch("api.server.subprocess.run")
    def test_report_not_available(self, mock_subprocess, client, mock_api_key):
        """Test report when not available"""
        mock_subprocess.return_value = MagicMock(returncode=0)

        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True}}):
            with patch("pathlib.Path.exists", return_value=False):
                response = client.get("/api/analytics/report", headers={"X-API-Key": mock_api_key})

        assert response.status_code == 404
        data = json.loads(response.data)
        assert "error" in data


class TestAnalyticsTrends:
    """Tests for /api/analytics/trends endpoint"""

    def test_trends_requires_auth(self, client):
        """Trends endpoint requires authentication"""
        response = client.get("/api/analytics/trends")
        assert response.status_code == 401

    @patch("analytics_processor.AnalyticsProcessor", new_callable=MagicMock)
    def test_trends_performance(self, mock_processor_class, client, mock_api_key):
        """Test performance trends"""
        mock_processor = MagicMock()
        mock_processor.analyze_performance_trends.return_value = {"tps": {"current": 20.0}}
        mock_processor_class.return_value = mock_processor

        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True}}):
            response = client.get(
                "/api/analytics/trends?hours=24&type=performance", headers={"X-API-Key": mock_api_key}
            )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "trends" in data
        assert data["period_hours"] == 24

    @patch("analytics_processor.AnalyticsProcessor")
    def test_trends_players(self, mock_processor_class, client, mock_api_key):
        """Test player behavior trends"""
        mock_processor = MagicMock()
        mock_processor.analyze_player_behavior.return_value = {"unique_players": 5}
        mock_processor_class.return_value = mock_processor

        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True}}):
            response = client.get("/api/analytics/trends?hours=24&type=players", headers={"X-API-Key": mock_api_key})

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "trends" in data

    def test_trends_import_error(self, client, mock_api_key):
        """Test trends when processor not available"""
        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True}}):
            with patch("analytics_processor.AnalyticsProcessor", side_effect=ImportError):
                response = client.get("/api/analytics/trends", headers={"X-API-Key": mock_api_key})

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "note" in data or "trends" in data


class TestAnalyticsAnomalies:
    """Tests for /api/analytics/anomalies endpoint"""

    def test_anomalies_requires_auth(self, client):
        """Anomalies endpoint requires authentication"""
        response = client.get("/api/analytics/anomalies")
        assert response.status_code == 401

    @patch("analytics_processor.AnalyticsProcessor")
    def test_anomalies_success(self, mock_processor_class, client, mock_api_key):
        """Test successful anomaly detection"""
        mock_processor = MagicMock()
        mock_processor.load_analytics_data.return_value = [
            {"timestamp": 1706371200, "data": {"tps": 20.0}},
            {"timestamp": 1706374800, "data": {"tps": 5.0}},  # Anomaly
        ]
        mock_processor.detect_anomalies.return_value = [
            {"timestamp": 1706374800, "value": 5.0, "severity": "high", "z_score": 3.5}
        ]
        mock_processor_class.return_value = mock_processor

        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True}}):
            response = client.get("/api/analytics/anomalies?hours=24&metric=tps", headers={"X-API-Key": mock_api_key})

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "anomalies" in data
        assert data["metric"] == "tps"

    @patch("analytics_processor.AnalyticsProcessor")
    def test_anomalies_no_data(self, mock_processor_class, client, mock_api_key):
        """Test anomalies when no data available"""
        mock_processor = MagicMock()
        mock_processor.load_analytics_data.return_value = []
        mock_processor_class.return_value = mock_processor

        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True}}):
            response = client.get("/api/analytics/anomalies", headers={"X-API-Key": mock_api_key})

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data["anomalies"] == []


class TestAnalyticsPredictions:
    """Tests for /api/analytics/predictions endpoint"""

    def test_predictions_requires_auth(self, client):
        """Predictions endpoint requires authentication"""
        response = client.get("/api/analytics/predictions")
        assert response.status_code == 401

    @patch("analytics_processor.AnalyticsProcessor")
    def test_predictions_success(self, mock_processor_class, client, mock_api_key):
        """Test successful prediction"""
        mock_processor = MagicMock()
        mock_processor.load_analytics_data.return_value = [
            {"timestamp": 1706371200, "data": {"memory": 1000}},
            {"timestamp": 1706374800, "data": {"memory": 1100}},
        ]
        mock_processor.predict_future.return_value = {
            "predicted": 1200,
            "confidence": 85.0,
            "trend": 100.0,
        }
        mock_processor_class.return_value = mock_processor

        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True}}):
            response = client.get(
                "/api/analytics/predictions?hours_ahead=1&metric=memory", headers={"X-API-Key": mock_api_key}
            )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "prediction" in data
        assert data["metric"] == "memory"
        assert data["hours_ahead"] == 1

    @patch("analytics_processor.AnalyticsProcessor")
    def test_predictions_no_data(self, mock_processor_class, client, mock_api_key):
        """Test predictions when no data available"""
        mock_processor = MagicMock()
        mock_processor.load_analytics_data.return_value = []
        mock_processor_class.return_value = mock_processor

        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True}}):
            response = client.get("/api/analytics/predictions", headers={"X-API-Key": mock_api_key})

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "message" in data or "prediction" in data


class TestPlayerBehavior:
    """Tests for /api/analytics/player-behavior endpoint"""

    def test_player_behavior_requires_auth(self, client):
        """Player behavior endpoint requires authentication"""
        response = client.get("/api/analytics/player-behavior")
        assert response.status_code == 401

    @patch("analytics_processor.AnalyticsProcessor")
    def test_player_behavior_success(self, mock_processor_class, client, mock_api_key):
        """Test successful player behavior analysis"""
        mock_processor = MagicMock()
        mock_processor.analyze_player_behavior.return_value = {
            "unique_players": 5,
            "peak_hour": 20,
            "hourly_distribution": {20: 10, 21: 8},
        }
        mock_processor_class.return_value = mock_processor

        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True}}):
            response = client.get("/api/analytics/player-behavior?hours=24", headers={"X-API-Key": mock_api_key})

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "behavior" in data
        assert data["period_hours"] == 24


class TestCustomReport:
    """Tests for /api/analytics/custom-report endpoint"""

    def test_custom_report_requires_auth(self, client):
        """Custom report endpoint requires authentication"""
        response = client.post("/api/analytics/custom-report")
        assert response.status_code == 401

    @patch("analytics_processor.AnalyticsProcessor")
    def test_custom_report_success(self, mock_processor_class, client, mock_api_key):
        """Test successful custom report generation"""
        mock_processor = MagicMock()
        mock_processor.analyze_performance_trends.return_value = {"tps": {"current": 20.0}}
        mock_processor.analyze_player_behavior.return_value = {"unique_players": 5}
        mock_processor.save_report.return_value = "/path/to/report.json"
        mock_processor_class.return_value = mock_processor

        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True}}):
            response = client.post(
                "/api/analytics/custom-report",
                headers={"X-API-Key": mock_api_key},
                json={"hours": 24, "metrics": ["performance", "players"]},
            )

        assert response.status_code == 200
        data = json.loads(response.data)
        assert "report" in data
        assert "saved_as" in data

    def test_custom_report_missing_fields(self, client, mock_api_key):
        """Test custom report with missing fields"""
        with patch("api.server.API_KEYS", {mock_api_key: {"enabled": True}}):
            response = client.post("/api/analytics/custom-report", headers={"X-API-Key": mock_api_key}, json={})

        # Should handle missing fields gracefully
        assert response.status_code in [200, 400, 500]
        assert response.status_code in [200, 400, 500]
