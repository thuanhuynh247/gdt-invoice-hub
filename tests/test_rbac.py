"""Unit tests for Role-Based Access Control (RBAC) (US-048)."""

from __future__ import annotations
import pytest
from flask import session

@pytest.fixture
def admin_client(client):
    """Seed an authenticated session with 'admin' role."""
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "admin"
        sess["user_role"] = "admin"
        sess["expires_at"] = "2099-05-20T00:00:00+00:00"
    return client

@pytest.fixture
def auditor_client(client):
    """Seed an authenticated session with 'auditor' role."""
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "my_auditor"
        sess["user_role"] = "auditor"
        sess["expires_at"] = "2099-05-20T00:00:00+00:00"
    return client

@pytest.fixture
def viewer_client(client):
    """Seed an authenticated session with 'viewer' role."""
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "my_viewer"
        sess["user_role"] = "viewer"
        sess["expires_at"] = "2099-05-20T00:00:00+00:00"
    return client


def test_admin_access_allowed(admin_client):
    """Verify that an Admin can access all endpoints including settings and profiles."""
    # Settings GET
    res = admin_client.get("/api/settings")
    assert res.status_code == 200

    # Settings POST
    res = admin_client.post("/api/settings", json={"smtp_port": 587, "schedule_weekday": 1})
    assert res.status_code == 200

    # Profiles GET
    res = admin_client.get("/api/profiles")
    assert res.status_code == 200


def test_auditor_access_restrictions(auditor_client):
    """Verify that Auditor is blocked from settings but allowed on profiles/exports."""
    # Settings GET -> Allowed
    res = auditor_client.get("/api/settings")
    assert res.status_code == 200

    # Settings POST -> Blocked
    res = auditor_client.post("/api/settings", json={})
    assert res.status_code == 403

    # Settings test email -> Blocked
    res = auditor_client.post("/api/settings/test-email", json={})
    assert res.status_code == 403

    # Profiles GET -> Allowed
    res = auditor_client.get("/api/profiles")
    assert res.status_code == 200


def test_viewer_access_restrictions(viewer_client):
    """Verify that Viewer is blocked from both settings and profiles/exports."""
    # Settings GET -> Blocked
    res = viewer_client.get("/api/settings")
    assert res.status_code == 403

    # Profiles GET -> Allowed
    res = viewer_client.get("/api/profiles")
    assert res.status_code == 200

    # Profile switch -> Allowed
    res = viewer_client.post("/api/profiles/switch", json={"mst": "all"})
    assert res.status_code == 200

    # Clear invoices -> Blocked
    res = viewer_client.delete("/api/invoices/local/clear")
    assert res.status_code == 403
