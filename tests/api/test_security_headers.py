#!/usr/bin/env python3
"""
Tests for the security_headers() after-request hook (api/server.py).

Nothing exercised these before -- the header values (Content-Security-Policy
in particular) had never actually been asserted, so a change to the policy
string had no test catching an accidental regression.
"""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from api.server import app  # noqa: E402


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


class TestSecurityHeaders:
    def test_health_endpoint_carries_hardening_headers(self, client):
        response = client.get("/api/health")

        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert "max-age=31536000" in response.headers.get("Strict-Transport-Security", "")
        assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert "Server" not in response.headers

    def test_deprecated_xss_protection_header_is_not_sent(self, client):
        """X-XSS-Protection is deprecated and ignored by modern browsers;
        dropped rather than kept as dead weight."""
        response = client.get("/api/health")
        assert "X-XSS-Protection" not in response.headers

    def test_permissions_policy_denies_unused_browser_features(self, client):
        response = client.get("/api/health")
        policy = response.headers.get("Permissions-Policy", "")
        assert "geolocation=()" in policy
        assert "microphone=()" in policy
        assert "camera=()" in policy

    def test_csp_is_same_origin_only_with_no_inline_scripts(self, client):
        response = client.get("/api/health")
        csp = response.headers.get("Content-Security-Policy", "")

        assert "default-src 'self'" in csp
        assert "script-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        # Inline styles are needed (React's style={{...}} prop), inline
        # scripts are not -- script-src must not carry 'unsafe-inline'.
        assert "style-src 'self' 'unsafe-inline'" in csp
        script_src = next(part.strip() for part in csp.split(";") if part.strip().startswith("script-src"))
        assert "unsafe-inline" not in script_src
        assert "unsafe-eval" not in script_src

    def test_oauth_callback_relay_gets_none_of_these_headers_from_flask(self, client):
        """config/nginx-minecraft.conf's `location = /oauth/callback` adds
        this same header set unconditionally, covering both the GET (SPA)
        and POST (proxied to apple_oauth_form_post_relay) cases in one
        place. nginx's add_header appends rather than replaces an existing
        header of the same name on a proxied response, so if Flask also
        set these here, every one of them would be duplicated on this one
        route. Regression test for exactly that: confirmed live against a
        real nginx + a fake upstream replicating this hook's old
        (unconditional) behavior before this test/fix existed."""
        response = client.post("/oauth/callback", data={"code": "abc", "state": "xyz"})

        assert response.status_code == 302
        for header in (
            "X-Content-Type-Options",
            "X-Frame-Options",
            "Strict-Transport-Security",
            "Content-Security-Policy",
            "Referrer-Policy",
            "Permissions-Policy",
        ):
            assert header not in response.headers, f"{header} should be left to nginx for this route"
