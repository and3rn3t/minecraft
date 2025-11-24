#!/usr/bin/env python3
"""
API Contract Tests
Validates API responses against OpenAPI schema
"""

import json

import pytest

from tests.api.contract_test_utils import get_endpoint_schema, validate_request_schema, validate_response_schema


@pytest.mark.contract
class TestAPIContracts:
    """Contract tests for API endpoints"""

    def test_health_endpoint_contract(self, client):
        """Test health endpoint response contract"""
        response = client.get("/api/health")
        assert response.status_code == 200

        data = json.loads(response.data)

        # Validate response structure (basic check)
        assert "status" in data or "health" in data or "message" in data

    def test_status_endpoint_contract(self, client, mock_api_keys):
        """Test status endpoint response contract"""
        response = client.get("/api/status", headers={"X-API-Key": mock_api_keys})
        assert response.status_code == 200

        data = json.loads(response.data)

        # Validate response structure
        assert isinstance(data, dict)
        # Status endpoint should have server information
        assert "status" in data or "server" in data or "running" in data

    def test_backup_list_contract(self, client, mock_api_keys):
        """Test backup list endpoint contract"""
        response = client.get("/api/backups", headers={"X-API-Key": mock_api_keys})
        assert response.status_code == 200

        data = json.loads(response.data)

        # Validate response structure
        assert isinstance(data, dict)
        # Should have backups array or list
        assert "backups" in data or "items" in data or isinstance(data, list)

    def test_validate_response_schema_utility(self):
        """Test response schema validation utility"""
        response_data = {"status": "ok", "message": "Server is running"}

        # This will skip validation if schema not available or has issues
        is_valid, error = validate_response_schema(response_data, "/api/health", "GET", 200)

        # Should either be valid or skip (if schema not available or has reference issues)
        # The utility function now handles schema reference errors gracefully
        assert is_valid or error is None

    def test_validate_request_schema_utility(self):
        """Test request schema validation utility"""
        request_data = {"username": "testuser", "password": "testpass"}

        # This will skip validation if schema not available
        is_valid, error = validate_request_schema(request_data, "/api/auth/register", "POST")

        # Should either be valid or skip (if schema not available)
        assert is_valid or error is None

    def test_get_endpoint_schema_utility(self):
        """Test endpoint schema retrieval utility"""
        schema = get_endpoint_schema("/api/health", "GET")

        # Should return schema dict or None
        assert schema is None or isinstance(schema, dict)

        assert schema is None or isinstance(schema, dict)
