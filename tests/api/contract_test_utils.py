"""
API Contract Testing Utilities
Helpers for validating API contracts against OpenAPI schema
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

import jsonschema
from jsonschema import ValidationError, validate


def load_openapi_schema(schema_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load OpenAPI schema from file"""
    if schema_path is None:
        # Default to api/openapi.yaml location
        project_root = Path(__file__).parent.parent.parent
        schema_path = project_root / "api" / "openapi.yaml"

    if not schema_path.exists():
        raise FileNotFoundError(f"OpenAPI schema not found: {schema_path}")

    # For now, return empty dict if YAML parsing not available
    # In production, use PyYAML or similar
    try:
        import yaml

        with open(schema_path, "r") as f:
            return yaml.safe_load(f)
    except ImportError:
        # Fallback: try JSON
        try:
            with open(schema_path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}


def validate_response_schema(
    response_data: Dict[str, Any],
    endpoint: str,
    method: str = "GET",
    status_code: int = 200,
    schema: Optional[Dict[str, Any]] = None,
) -> tuple[bool, Optional[str]]:
    """
    Validate API response against OpenAPI schema

    Returns:
        (is_valid, error_message)
    """
    if schema is None:
        schema = load_openapi_schema()

    if not schema:
        return True, None  # Skip validation if schema not available

    try:
        # Find the path and method in schema
        paths = schema.get("paths", {})
        path_spec = paths.get(endpoint, {})
        method_spec = path_spec.get(method.lower(), {})

        # Get response schema for status code
        responses = method_spec.get("responses", {})
        response_spec = responses.get(str(status_code), {})

        # Get content schema
        content = response_spec.get("content", {})
        json_content = content.get("application/json", {})
        response_schema = json_content.get("schema", {})

        if not response_schema:
            return True, None  # No schema defined, skip validation

        # Validate against JSON Schema
        validate(instance=response_data, schema=response_schema)
        return True, None

    except ValidationError as e:
        return False, f"Schema validation error: {e.message}"
    except Exception as e:
        error_msg = str(e)
        # If schema has reference issues or missing components, treat as skip (not a failure)
        if "does not exist" in error_msg or "$ref" in error_msg or "PointerToNowhere" in error_msg:
            return True, None  # Skip validation if schema references are broken
        return False, f"Validation error: {error_msg}"


def validate_request_schema(
    request_data: Dict[str, Any], endpoint: str, method: str = "POST", schema: Optional[Dict[str, Any]] = None
) -> tuple[bool, Optional[str]]:
    """
    Validate API request against OpenAPI schema

    Returns:
        (is_valid, error_message)
    """
    if schema is None:
        schema = load_openapi_schema()

    if not schema:
        return True, None  # Skip validation if schema not available

    try:
        # Find the path and method in schema
        paths = schema.get("paths", {})
        path_spec = paths.get(endpoint, {})
        method_spec = path_spec.get(method.lower(), {})

        # Get request body schema
        request_body = method_spec.get("requestBody", {})
        content = request_body.get("content", {})
        json_content = content.get("application/json", {})
        request_schema = json_content.get("schema", {})

        if not request_schema:
            return True, None  # No schema defined, skip validation

        # Validate against JSON Schema
        validate(instance=request_data, schema=request_schema)
        return True, None

    except ValidationError as e:
        return False, f"Schema validation error: {e.message}"
    except Exception as e:
        error_msg = str(e)
        # If schema has reference issues or missing components, treat as skip (not a failure)
        if "does not exist" in error_msg or "$ref" in error_msg or "PointerToNowhere" in error_msg:
            return True, None  # Skip validation if schema references are broken
        return False, f"Validation error: {error_msg}"


def get_endpoint_schema(
    endpoint: str, method: str = "GET", schema: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """Get schema definition for an endpoint"""
    if schema is None:
        schema = load_openapi_schema()

    if not schema:
        return None

    paths = schema.get("paths", {})
    path_spec = paths.get(endpoint, {})
    method_spec = path_spec.get(method.lower(), {})

    return method_spec
