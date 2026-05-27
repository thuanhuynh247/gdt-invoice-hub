"""Tests for secure credentials storage and automatic session refreshing."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from auth.crypto import decrypt_password, encrypt_password
from invoices.service import InvoiceQuery, fetch_invoices


def test_cryptography_reversible(app):
    """Test that passwords can be encrypted and decrypted back to original."""
    with app.app_context():
        original = "TaxpayerPass123"
        ciphertext = encrypt_password(original)
        assert ciphertext != original
        assert len(ciphertext) > 20

        decrypted = decrypt_password(ciphertext)
        assert decrypted == original


def test_cryptography_handles_empty(app):
    """Test that cryptography helpers handle empty strings gracefully."""
    with app.app_context():
        assert encrypt_password("") == ""
        assert decrypt_password("") == ""


def test_login_stores_encrypted_password(app, client):
    """Test that POST /api/auth/login stores the encrypted password in session."""
    # Set config directly on app fixture
    app.config["GDT_USE_MOCK"] = True
    app.config["AUTO_SOLVE_CAPTCHA"] = True
    app.config["SECRET_KEY"] = "change-this-secret-key"

    response = client.post(
        "/api/auth/login",
        json={"username": "0101234567", "password": "MySecretPassword", "captcha": "AUTO"},
    )
    assert response.status_code == 200
    with client.session_transaction() as sess:
        assert sess.get("logged_in") is True
        assert sess.get("username") == "0101234567"
        enc_pass = sess.get("encrypted_password")
        assert enc_pass is not None
        assert enc_pass != "MySecretPassword"

        # Decrypt it to verify
        with app.app_context():
            decrypted = decrypt_password(enc_pass)
        assert decrypted == "MySecretPassword"


@patch("requests.post")
@patch("requests.get")
@patch("auth.captcha.fetch_captcha_payload")
@patch("auth.captcha.pop_prefetched_captcha")
def test_auto_refresh_triggered_on_401(
    mock_pop_captcha, mock_fetch_captcha, mock_get, mock_post, app, client
):
    """Test that a 401 GDT response triggers auto-refresh and successfully retries."""

    # Mock pop_prefetched_captcha to return None so we fall back to fetch_captcha_payload
    mock_pop_captcha.return_value = None

    # Mock captcha fetch return value
    mock_fetch_captcha.return_value = {
        "key": "mock-key",
        "content": "<svg><text>MOCK</text></svg>",
        "cookies": {},
    }

    # Setup mock responses for invoices endpoint
    mock_response_401 = MagicMock()
    mock_response_401.status_code = 401

    mock_response_200 = MagicMock()
    mock_response_200.status_code = 200
    mock_response_200.json.return_value = {
        "datas": [
            {
                "id": "INV-MOCK-1",
                "tdlap": "2026-05-01",
                "tthai": "valid",
                "nbten": "Test Seller",
                "tgtcthue": 100000,
            }
        ]
    }

    # Mock profile GET call
    mock_profile_response = MagicMock()
    mock_profile_response.status_code = 200
    mock_profile_response.json.return_value = {
        "fullName": "Test Taxpayer LLC",
        "groupId": "0101234567",
    }

    # Unified get mock side effect
    invoice_calls = []
    def get_side_effect(url, *args, **kwargs):
        if "invoices" in url:
            if not invoice_calls:
                invoice_calls.append(True)
                return mock_response_401
            return mock_response_200
        elif "profile" in url:
            return mock_profile_response
        return MagicMock(status_code=404)

    mock_get.side_effect = get_side_effect

    # Mock authentication POST call for the refresh logic
    mock_auth_response = MagicMock()
    mock_auth_response.status_code = 200
    mock_auth_response.json.return_value = {"token": "refreshed-jwt-token-999"}
    mock_post.return_value = mock_auth_response

    # Setup conftest client with session state
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "0101234567"
        with app.app_context():
            sess["encrypted_password"] = encrypt_password("MySecretPassword")
        sess["jwt"] = "expired-jwt-token"
        sess["expires_at"] = "2026-05-21T00:00:00+00:00"

    with app.test_request_context():
        # Bind the variables from the session to current_app context config manually
        app.config["GDT_USE_MOCK"] = False
        app.config["GDT_BASE_URL"] = "https://hoadondientu.gdt.gov.vn"
        app.config["CURRENT_JWT"] = "expired-jwt-token"
        app.config["CURRENT_USERNAME"] = "0101234567"
        app.config["CURRENT_ENCRYPTED_PASSWORD"] = sess["encrypted_password"]
        app.config["GDT_TIMEOUT_SECONDS"] = 10

        query = InvoiceQuery(date_from=date(2026, 5, 1), date_to=date(2026, 5, 1))
        invoices = fetch_invoices(query)

        # Verify request retried and returned successfully
        assert len(invoices) == 1
        assert invoices[0]["id"] == "INV-MOCK-1"
        assert invoices[0]["issuer"] == "Test Seller"
        assert app.config["CURRENT_JWT"] == "refreshed-jwt-token-999"
