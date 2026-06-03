"""Tests for Captcha Analytics and Sync Health Monitoring API (US-143)."""

from __future__ import annotations
import pytest
from flask import current_app
from auth.captcha_solver import captcha_analytics


class MockLock:
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class MockJob:
    def __init__(self, status="running"):
        self.status = status


class MockQueue:
    def __init__(self, jobs=None):
        self._lock = MockLock()
        self.jobs = jobs or {}


def test_captcha_analytics_recording():
    """Verify that CaptchaAnalytics accumulates metrics correctly and thread-safely."""
    # Reset stats
    captcha_analytics.total_latency = 0.0
    captcha_analytics.solve_count = 0
    captcha_analytics.success_count = 0
    captcha_analytics.fail_count = 0

    # Record some solves
    captcha_analytics.record_solve(0.5)
    captcha_analytics.record_solve(1.5)
    
    # Record success and fail
    captcha_analytics.record_success()
    captcha_analytics.record_success()
    captcha_analytics.record_fail()

    stats = captcha_analytics.get_stats()
    assert stats["solve_count"] == 2
    assert stats["success_count"] == 2
    assert stats["fail_count"] == 1
    assert stats["average_latency_seconds"] == 1.0
    
    # Accuracy rate: 2 successes out of 3 total records (success + fail = 3) => 2 / 3 = 66.67%
    assert pytest.approx(stats["accuracy_rate"], 0.01) == 66.67


def test_sync_health_api_access_rbac(client):
    """Verify RBAC access permissions on GET /api/sync/health."""
    # 1. Anonymous user should get 401
    response = client.get("/api/sync/health")
    assert response.status_code == 401

    # 2. Logged-in non-admin (e.g., standard viewer) should get 403
    with client.session_transaction() as session:
        session["user_role"] = "viewer"
        session["username"] = "john_doe"
        session["logged_in"] = True

    response = client.get("/api/sync/health")
    assert response.status_code == 403


def test_sync_health_api_payload_for_admin(app, client):
    """Verify GET /api/sync/health returns detailed health payload for admin."""
    # Login as admin
    with client.session_transaction() as session:
        session["user_role"] = "admin"
        session["username"] = "admin_user"
        session["logged_in"] = True

    # Mock captcha stats
    captcha_analytics.solve_count = 10
    captcha_analytics.success_count = 8
    captcha_analytics.fail_count = 2
    captcha_analytics.total_latency = 5.0

    # Mock resilient_sync_queue in flask app extension dictionary
    mock_queue = MockQueue(jobs={"job1": MockJob(status="running")})
    
    # Put the mock queue in app extension dictionary
    app.extensions["resilient_sync_queue"] = mock_queue

    try:
        response = client.get("/api/sync/health")
        assert response.status_code == 200
        
        data = response.get_json()
        assert data["crawler_status"] == "running"
        assert data["solver"]["success_count"] == 8
        assert data["solver"]["fail_count"] == 2
        assert data["solver"]["solve_count"] == 10
        assert pytest.approx(data["solver"]["accuracy_rate"], 0.01) == 80.0
        assert pytest.approx(data["solver"]["average_latency_seconds"], 0.01) == 0.5
    finally:
        # Clean up mock queue from app extensions
        if "resilient_sync_queue" in app.extensions:
            del app.extensions["resilient_sync_queue"]
