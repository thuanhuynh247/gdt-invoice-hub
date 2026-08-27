"""Integration tests for the rebuilt Admin Login Portal & CAPTCHA auto-solving engine."""

from __future__ import annotations
import pytest


def test_admin_login_page_renders_bento_ui(client):
    """The Admin Login page should render the Bento Grid UI with telemetry widgets."""
    response = client.get("/login")
    assert response.status_code == 200
    html = response.data.decode("utf-8")
    assert "Đăng nhập Admin Portal" in html
    assert "Telemetry Giải mã CAPTCHA AI" in html
    assert "GDT SECURE GATEWAY" in html
    assert "role-chip" in html


def test_auth_captcha_api_with_ai_metadata(client):
    """GET /api/auth/captcha should return SVG markup and pre-solved text."""
    response = client.get("/api/auth/captcha")
    assert response.status_code == 200
    data = response.get_json()
    assert "image_svg" in data
    assert "<svg" in data["image_svg"]
    assert "auto_solve" in data
    assert "solved_text" in data


def test_solve_captcha_on_demand_api(client):
    """POST /api/auth/solve-captcha should decode CAPTCHA SVG on demand."""
    # First request captcha to populate session
    client.get("/api/auth/captcha")
    
    response = client.post("/api/auth/solve-captcha", json={})
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert "solved_text" in data
    assert len(data["solved_text"]) > 0


def test_captcha_telemetry_stats_api(client):
    """GET /api/auth/captcha/stats should return real-time analytics data."""
    response = client.get("/api/auth/captcha/stats")
    assert response.status_code == 200
    data = response.get_json()
    assert "accuracy_rate" in data
    assert "solve_count" in data
    assert "vector_solve_count" in data
    assert "ocr_solve_count" in data


def test_admin_login_auto_captcha_mode(client):
    """POST /api/auth/login with 'admin' and 'AUTO' captcha should authenticate as admin."""
    # Initialize session captcha
    client.get("/api/auth/captcha")
    
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin", "captcha": "AUTO"}
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    
    with client.session_transaction() as sess:
        assert sess["logged_in"] is True
        assert sess["username"] == "admin"
        assert sess["user_role"] == "admin"


def test_auditor_login_auto_captcha_mode(client):
    """POST /api/auth/login with 'auditor_tax' and 'AUTO' captcha should authenticate as auditor."""
    client.get("/api/auth/captcha")
    
    response = client.post(
        "/api/auth/login",
        json={"username": "auditor_tax", "password": "auditor123", "captcha": "AUTO"}
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    
    with client.session_transaction() as sess:
        assert sess["logged_in"] is True
        assert sess["username"] == "auditor_tax"
        assert sess["user_role"] == "auditor"


def test_login_failure_invalid_credentials(client):
    """Locked user or empty credentials should fail gracefully."""
    response = client.post(
        "/api/auth/login",
        json={"username": "locked", "password": "wrongpassword", "captcha": "AUTO"}
    )
    assert response.status_code == 401
    data = response.get_json()
    assert "error" in data
