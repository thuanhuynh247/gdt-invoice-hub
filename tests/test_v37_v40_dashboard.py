"""Tests for the Executive Control Center dashboard and compliance dashboard (v37 and v40)."""

from __future__ import annotations

import pytest


def test_dashboard_requires_login(client):
    """Verify that anonymous users are redirected to login or blocked with 401 when visiting dashboard."""
    response = client.get("/dashboard")
    assert response.status_code == 302 or response.status_code == 401


def test_dashboard_success(logged_in_client):
    """Verify that an authenticated user can view the Executive Control Center dashboard."""
    response = logged_in_client.get("/dashboard")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Executive Control Center" in html
    assert "Taxpayer MST:" in html
    assert "glass-card" in html


def test_compliance_dashboard_requires_login(client):
    """Verify that anonymous users are blocked or redirected when visiting compliance dashboard."""
    response = client.get("/v40-compliance-dashboard")
    assert response.status_code == 302 or response.status_code == 401


def test_compliance_dashboard_success(logged_in_client):
    """Verify that an authenticated user can view the compliance dashboard."""
    response = logged_in_client.get("/v40-compliance-dashboard")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Bộ Công cụ Tuân thủ Thuế v40" in html
    assert "glass-card" in html
    assert "fct-tab" in html
