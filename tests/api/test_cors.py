#!/usr/bin/env python3
"""
Tests for CORS configuration (api/server.py)

api/server.py's ALLOWED_ORIGINS defaults to "*" (every origin) and is used
with supports_credentials=True, which lets any site make authenticated
requests against this API once it's reachable beyond a trusted local
network. The actual origin allowlist is fixed at process start (flask-cors
is configured once, at import time, from the ALLOWED_ORIGINS environment
variable), so it isn't something a test can flip per-case against the live
`app` object. What *is* directly testable is the startup safeguard: a loud
warning any time the wildcard default is still in effect.
"""

import sys
import warnings
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.server import _warn_if_cors_wildcard_with_credentials  # noqa: E402


class TestCorsWildcardWarning:
    """Tests for _warn_if_cors_wildcard_with_credentials (api/server.py)"""

    def test_warns_on_wildcard_origin(self):
        with pytest.warns(UserWarning, match="ALLOWED_ORIGINS"):
            _warn_if_cors_wildcard_with_credentials(["*"])

    def test_no_warning_for_explicit_origin(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            _warn_if_cors_wildcard_with_credentials(["https://minecraft.example.com"])

    def test_no_warning_for_multiple_explicit_origins(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            _warn_if_cors_wildcard_with_credentials(["https://a.example.com", "https://b.example.com"])
