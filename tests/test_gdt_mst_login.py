"""Integration and unit tests for GDT MST login, CAPTCHA payload extraction, profile syncing, and taxpayer roles."""

import os
import json
import pytest
from flask import session


@pytest.fixture
def mst_client():
    """Build a test client configured for GDT MST authentication tests."""
    os.environ["GDT_USE_MOCK"] = "true"
    os.environ["AUTO_SOLVE_CAPTCHA"] = "true"
    from app import create_app
    from extensions import db

    app = create_app()
    app.config["TESTING"] = True
    app.config["GDT_USE_MOCK"] = True
    app.config["AUTO_SOLVE_CAPTCHA"] = True
    app.config["WTF_CSRF_ENABLED"] = False

    with app.app_context():
        db.create_all()
        with app.test_client() as client:
            yield client


def test_mst_login_successful_mock(mst_client):
    """Test login with a valid 10-digit tax identification number (MST)."""
    response = mst_client.post(
        "/api/auth/login",
        json={
            "username": "0316459946",
            "password": "GdtPassword123@",
            "captcha": "AUTO",
        },
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert data["tax_code"] == "0316459946" or data["tax_code"] is None

    # Check session variables
    with mst_client.session_transaction() as sess:
        assert sess.get("logged_in") is True
        assert sess.get("username") == "0316459946"
        assert sess.get("user_role") == "taxpayer"


def test_mst_13digit_login(mst_client):
    """Test login with a 13-digit branch MST (e.g. 0316459946-001)."""
    response = mst_client.post(
        "/api/auth/login",
        json={
            "username": "0316459946-001",
            "password": "BranchPassword123@",
            "captcha": "AUTO",
        },
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"

    with mst_client.session_transaction() as sess:
        assert sess.get("user_role") == "taxpayer"


def test_mst_login_with_custom_captcha_key_payload(mst_client):
    """Test login when client passes captcha_key explicitly in the JSON payload."""
    response = mst_client.post(
        "/api/auth/login",
        json={
            "username": "0101234567",
            "password": "TaxPassword456!",
            "captcha": "ABCD",
            "key": "custom-captcha-key-12345",
        },
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"


def test_mst_profile_auto_sync_to_db(mst_client):
    """Verify that logging in with an MST automatically creates/updates TaxpayerProfile in SQLite."""
    response = mst_client.post(
        "/api/auth/login",
        json={
            "username": "0316459946",
            "password": "SecurePassword999#",
            "captcha": "AUTO",
        },
    )
    assert response.status_code == 200

    from invoices.models import TaxpayerProfile
    profile = TaxpayerProfile.query.filter_by(mst="0316459946").first()
    assert profile is not None
    assert profile.gdt_username == "0316459946"
    assert profile.encrypted_password is not None
