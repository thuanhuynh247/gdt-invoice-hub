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
