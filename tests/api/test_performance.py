#!/usr/bin/env python3
"""
Performance Tests for API Endpoints
"""

import time

import pytest

from tests.api.performance_utils import (
    PerformanceTimer,
    benchmark_endpoint,
    measure_execution_time,
    print_performance_report,
    run_load_test,
)


@pytest.mark.performance
class TestAPIPerformance:
    """Performance tests for API endpoints"""

    def test_health_endpoint_performance(self, client):
        """Test health endpoint response time"""
        with PerformanceTimer("Health endpoint") as timer:
            response = client.get("/api/health")
            assert response.status_code == 200

        # Health endpoint should be very fast (< 50ms)
        assert timer.get_duration() < 0.05, "Health endpoint too slow"

    def test_health_endpoint_load(self, client):
        """Test health endpoint under load"""

        def make_request():
            response = client.get("/api/health")
            assert response.status_code == 200

        results = run_load_test(make_request, num_requests=100, num_threads=10)

        # Should handle 100 requests quickly
        assert results["success_count"] == 100
        assert results["avg_duration"] < 0.1  # Average < 100ms
        assert results["requests_per_second"] > 50  # At least 50 req/s

    def test_status_endpoint_performance(self, client, mock_api_keys):
        """Test status endpoint response time"""
        with PerformanceTimer("Status endpoint") as timer:
            response = client.get("/api/status", headers={"X-API-Key": mock_api_keys})
            assert response.status_code == 200

        # Status endpoint should be reasonably fast (< 200ms)
        assert timer.get_duration() < 0.2, "Status endpoint too slow"

    def test_backup_list_performance(self, client, mock_api_keys):
        """Test backup list endpoint performance"""
        with PerformanceTimer("Backup list endpoint") as timer:
            response = client.get("/api/backups", headers={"X-API-Key": mock_api_keys})
            assert response.status_code == 200

        # Backup list should be reasonably fast (< 500ms)
        assert timer.get_duration() < 0.5, "Backup list endpoint too slow"

    def test_measure_function_performance(self):
        """Test performance measurement utility"""

        def test_function():
            time.sleep(0.01)  # Simulate work

        duration = measure_execution_time(test_function)
        assert duration >= 0.01
        assert duration < 0.1  # Should be close to sleep time

    def test_benchmark_endpoint_utility(self, client, mock_api_keys):
        """Test benchmark utility function"""
        results = benchmark_endpoint(client, "GET", "/api/health", num_requests=50, num_threads=5)

        assert results["total_requests"] == 50
        assert results["success_count"] == 50
        assert results["requests_per_second"] > 0

        assert results["requests_per_second"] > 0
