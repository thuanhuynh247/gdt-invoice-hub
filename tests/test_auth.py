"""Auth route tests."""

from __future__ import annotations


def test_login_page_loads(client):
    """The login page should render with the username field."""

    response = client.get("/login")
    assert response.status_code == 200
    assert "Tên đăng nhập".encode("utf-8") in response.data


def test_auth_captcha_route_returns_svg(client):
    """Captcha endpoint should return SVG markup for the frontend."""

    response = client.get("/api/auth/captcha")
    payload = response.get_json()
    assert response.status_code == 200
    assert "<svg" in payload["image_svg"]


def test_login_requires_complete_payload(client):
    """The API should reject missing login fields."""

    response = client.post("/api/auth/login", json={"username": "demo", "password": "", "captcha": ""})
    assert response.status_code == 401
    assert response.get_json()["error"]


def test_login_success_sets_session(client):
    """Valid mock credentials should create a logged-in session."""

    response = client.post(
        "/api/auth/login",
        json={"username": "demo", "password": "secret", "captcha": "MOCK-1234"},
    )
    assert response.status_code == 200
    assert response.get_json()["status"] == "success"

    with client.session_transaction() as session:
        assert session["logged_in"] is True
        assert session["username"] == "demo"


def test_logout_clears_session(logged_in_client):
    """Logout should empty the session."""

    response = logged_in_client.post("/api/auth/logout")
    assert response.status_code == 200

    with logged_in_client.session_transaction() as session:
        assert "logged_in" not in session
