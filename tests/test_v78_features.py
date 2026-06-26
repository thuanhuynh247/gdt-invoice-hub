"""Pytest verification suite for V78 compliance validation (Benford's Law) and AI Tax Advisor.
"""

from __future__ import annotations

import json
import pytest
from flask import Flask
from extensions import db
from unittest.mock import patch, MagicMock

@pytest.fixture
def mock_app():
    app = Flask(__name__, template_folder="../templates")
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    db.init_app(app)
    
    from auth import auth_blueprint
    from invoices.routes import invoices_blueprint
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(invoices_blueprint)

    @app.route("/")
    def index():
        return "index"

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


# --- V78 INVOICE COMPLIANCE & BENFORD TESTS ---

def test_v78_invoice_validation_page_unauthorized(mock_app):
    client = mock_app.test_client()
    res = client.get("/v78-invoice-validation")
    # Should redirect or deny if not logged in
    assert res.status_code in [302, 401, 403]


def test_v78_invoice_validation_page_authorized(mock_app):
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"

    res = client.get("/v78-invoice-validation")
    assert res.status_code == 200
    assert b"Ki\xe1\xbb\x83m to\xc3\xa1n v78" in res.data or b"Benford" in res.data


@patch("invoices.invoice_validator.validate_all_invoices")
def test_api_v78_validate(mock_validate, mock_app):
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["active_taxpayer_mst"] = "0102030499"

    mock_validate.return_value = {
        "status": "success",
        "benford_actual": {"1": 30.1, "2": 17.6},
        "benford_expected": {"1": 30.1, "2": 17.6},
        "anomaly_detected": False
    }

    res = client.get("/api/v78/validate")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["status"] == "success"
    assert "benford_actual" in data
    assert data["benford_actual"]["1"] == 30.1



# --- AI TAX ADVISOR & RAG TESTS ---

def test_tax_advisor_page_authorized(mock_app):
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"

    res = client.get("/tax-advisor")
    assert res.status_code == 200
    assert b"PixelRAG" in res.data


def test_api_tax_settings(mock_app):
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"

    # 1. Get Settings
    res_get = client.get("/api/tax/settings")
    assert res_get.status_code == 200
    data_get = json.loads(res_get.data)
    assert "ai_provider" in data_get

    # 2. Save Settings
    payload = {
        "ai_provider": "openai",
        "ai_model_name": "gpt-4o-mini",
        "ai_api_key": "test-key-123",
        "ai_ollama_endpoint": ""
    }
    res_post = client.post("/api/tax/settings", json=payload)
    assert res_post.status_code == 200
    data_post = json.loads(res_post.data)
    assert data_post["success"] is True

    # 3. Verify saved settings
    res_verify = client.get("/api/tax/settings")
    data_verify = json.loads(res_verify.data)
    assert data_verify["ai_provider"] == "openai"
    assert data_verify["ai_model_name"] == "gpt-4o-mini"


@patch("requests.post")
def test_api_tax_chat_fallback_and_rag(mock_post, mock_app):
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"

    # Set up mock response for LLM API (Ollama/OpenAI/Gemini)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Theo quy định thuế GTGT..."}}],
        "response": "Theo quy định thuế GTGT..."
    }
    mock_post.return_value = mock_response

    # Save settings as local Ollama first
    client.post("/api/tax/settings", json={
        "ai_provider": "ollama",
        "ai_model_name": "gemma-4",
        "ai_api_key": "",
        "ai_ollama_endpoint": "http://localhost:11434"
    })

    # Call chat
    res = client.post("/api/tax/chat", json={"message": "Khấu trừ thuế GTGT đầu vào"})
    assert res.status_code == 200
    data = json.loads(res.data)
    assert "response" in data
    assert "citations" in data
    # Should contain at least some citations related to GTGT / Law 149 / Law 48
    assert len(data["citations"]) > 0


# --- VBA & EXCEL INTEGRATION GATEWAY TESTS ---

def test_vba_gateway_auth_failed(mock_app):
    client = mock_app.test_client()
    # Missing token -> 401
    res = client.get("/api/v1/vba/status")
    assert res.status_code == 401
    
    # Wrong token -> 401
    res = client.get("/api/v1/vba/status?vba_token=wrong")
    assert res.status_code == 401


def test_vba_gateway_status_and_taxpayers(mock_app):
    client = mock_app.test_client()
    
    # Standard seed profile
    from invoices.models import TaxpayerProfile
    with mock_app.app_context():
        tp = TaxpayerProfile(
            mst="0102030499",
            company_name="Cong ty Kiem Thu",
            gdt_username="testuser",
            gdt_password_encrypted="pass",
            is_active=True,
            created_at="2026-01-01T00:00:00"
        )
        db.session.add(tp)
        db.session.commit()

    # Query with default token
    res = client.get("/api/v1/vba/status?vba_token=vba-secret-token-123")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["status"] == "healthy"
    assert data["total_taxpayers"] == 1

    # Query taxpayers list
    res_tp = client.get("/api/v1/vba/taxpayers?vba_token=vba-secret-token-123")
    assert res_tp.status_code == 200
    tps = json.loads(res_tp.data)
    assert len(tps) == 1
    assert tps[0]["mst"] == "0102030499"
    assert tps[0]["company_name"] == "Cong ty Kiem Thu"


@patch("auth.captcha_solver.solve_captcha_from_svg")
def test_vba_gateway_solve_captcha(mock_solve, mock_app):
    client = mock_app.test_client()
    mock_solve.return_value = "XYZ12"

    payload = {
        "svg_content": "<svg><text>XYZ12</text></svg>",
        "captcha_key": "some-session-key"
    }
    res = client.post("/api/v1/vba/solve-captcha?vba_token=vba-secret-token-123", json=payload)
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["success"] is True
    assert data["solution"] == "XYZ12"


def test_vba_gateway_sync_invoices(mock_app):
    client = mock_app.test_client()
    
    # Standard seed profile
    from invoices.models import TaxpayerProfile
    with mock_app.app_context():
        tp = TaxpayerProfile(
            mst="0102030499",
            company_name="Cong ty Kiem Thu",
            gdt_username="testuser",
            gdt_password_encrypted="pass",
            is_active=True,
            created_at="2026-01-01T00:00:00"
        )
        db.session.add(tp)
        db.session.commit()

    payload = {
        "taxpayer_mst": "0102030499",
        "invoices": [
            {
                "seller_mst": "0123456789",
                "symbol": "1C26TAA",
                "number": "0000123",
                "date": "2026-06-25",
                "seller_name": "Nha Ban Si A",
                "buyer_name": "Cong ty Kiem Thu",
                "buyer_mst": "0102030499",
                "amount_before_tax": 1000000.0,
                "tax_amount": 80000.0,
                "total_amount": 1080000.0,
                "has_signature": True,
                "signing_date": "2026-06-25",
                "invoice_status": "Đã cấp mã",
                "items": [
                    {
                        "item_name": "Dịch vụ phần mềm",
                        "quantity": 1.0,
                        "unit_price": 1000000.0,
                        "amount_before_tax": 1000000.0,
                        "tax_rate": "8%",
                        "tax_amount": 80000.0,
                        "amount_after_tax": 1080000.0
                    }
                ]
            }
        ]
    }

    res = client.post("/api/v1/vba/sync-invoices?vba_token=vba-secret-token-123", json=payload)
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["success"] is True
    assert data["summary"]["created"] == 1
    assert data["summary"]["failed"] == 0

    # Verify that it is in database and compliance validation was run
    from invoices.models import Invoice, LineItem
    with mock_app.app_context():
        inv = db.session.get(Invoice, "0123456789-1c26taa-0000123")
        assert inv is not None
        assert inv.total_amount == 1080000.0
        assert inv.taxpayer_mst == "0102030499"
        
        # Check line item is synced
        items = LineItem.query.filter_by(invoice_id=inv.id).all()
        assert len(items) == 1
        assert items[0].item_name == "Dịch vụ phần mềm"
        assert items[0].tax_rate == "8%"

        # Check compliance auditing warnings are computed (warnings_json is a JSON string of list of alerts)
        # Note: Since the mock DB lacks other invoices, semantic duplicate checks and other database-wide checks pass.
        # But single invoice check ran and generated no error because math matches (1000000 + 80000 == 1080000).
        assert inv.warnings_json is not None
        warnings = json.loads(inv.warnings_json)
        assert isinstance(warnings, list)

