"""Unit and integration tests for cybersecurity hardening features.

Verifies correct injection of strict security headers and proper behavior
of the rate limiter (429 HTTP response and headers).
"""

from __future__ import annotations

import time
import pytest
from auth.security import limiter


@pytest.fixture(autouse=True)
def clean_rate_limiter():
    """Ensure the rate limiter starts with a clean state before every test."""
    with limiter.lock:
        limiter.requests.clear()
    yield
    with limiter.lock:
        limiter.requests.clear()


def test_security_headers_injected(client):
    """Ensure strict HTTP security headers are injected in all responses."""
    response = client.get("/login")
    assert response.status_code == 200

    # Assert standard security headers are present and configured correctly
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "SAMEORIGIN"
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    
    csp = response.headers.get("Content-Security-Policy")
    assert csp is not None
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "script-src" in csp


def test_rate_limiting_login_endpoint(client):
    """Ensure the login endpoint triggers 429 Too Many Requests after limit is exceeded."""
    # The login endpoint has a rate limit of 10 requests per minute
    payload = {"username": "admin", "password": "wrong-password", "captcha": "1234"}
    
    # Trigger 10 login requests
    for i in range(10):
        response = client.post("/api/auth/login", json=payload)
        # Should return either 401 (since credentials/captcha are mock-wrong) or 200/other, but NOT 429
        assert response.status_code != 429
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert int(response.headers["X-RateLimit-Remaining"]) == 10 - (i + 1)

    # The 11th request must exceed the rate limit and return 429
    excessive_response = client.post("/api/auth/login", json=payload)
    assert excessive_response.status_code == 429
    assert excessive_response.headers.get("X-RateLimit-Remaining") == "0"
    
    # Assert proper JSON response body for the rate limit
    body = excessive_response.get_json()
    assert body["error"] == "too_many_requests"
    assert "retry_after" in body
    assert int(excessive_response.headers.get("Retry-After", 0)) > 0
