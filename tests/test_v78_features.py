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
    # Should contain citations as a list
    assert isinstance(data["citations"], list)


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


# --- AXIS 5 & 3: TAX HEALTH SCORE & RECONCILIATION TESTS ---

def test_tax_health_score_calculation(mock_app):
    """Test tax health score service, Benford's Law penalty, cash payment risk, and bank reconciliation."""
    from invoices.models import TaxpayerProfile, Invoice, BankTransaction, Partner
    from invoices.tax_health_service import calculate_tax_health

    with mock_app.app_context():
        # 1. Create taxpayer profile
        tp = TaxpayerProfile(
            mst="0102030499",
            company_name="Cong ty Kiem Thu",
            gdt_username="testuser",
            gdt_password_encrypted="pass",
            is_active=True,
            created_at="2026-01-01T00:00:00"
        )
        db.session.add(tp)
        
        # 2. Seed some partners (one normal, one risky)
        partner_normal = Partner(
            mst="1234567890",
            name="Nha cung cap Binh Thuong",
            address="Hanoi, Vietnam",
            mst_status="Đang hoạt động"
        )
        partner_risky = Partner(
            mst="9999999999",
            name="Nha cung cap Rủi ro Cao",
            address="Haiphong, Vietnam",
            mst_status="Ngừng hoạt động"
        )
        db.session.add_all([partner_normal, partner_risky])

        # 3. Seed some purchase and sales invoices
        # Normal purchase
        inv1 = Invoice(
            id="inv-1",
            taxpayer_mst="0102030499",
            invoice_type="purchase",
            seller_mst="1234567890",
            seller_name="Nha cung cap Binh Thuong",
            amount_before_tax=10000000.0,
            tax_amount=1000000.0,
            total_amount=11000000.0,
            payment_method="Chuyển khoản",
            date="2026-06-01",
            signing_date="2026-06-01",
            imported_at="2026-06-26T00:00:00"
        )
        # Sales invoice
        inv2 = Invoice(
            id="inv-2",
            taxpayer_mst="0102030499",
            invoice_type="sales",
            buyer_mst="8888888888",
            buyer_name="Khach Hang A",
            amount_before_tax=30000000.0,
            tax_amount=3000000.0,
            total_amount=33000000.0,
            payment_method="Chuyển khoản",
            date="2026-06-02",
            signing_date="2026-06-02",
            imported_at="2026-06-26T00:00:00"
        )
        # Cash violation purchase invoice >= 20M (No bank matching or Cash method)
        inv3 = Invoice(
            id="inv-3",
            taxpayer_mst="0102030499",
            invoice_type="purchase",
            seller_mst="1234567890",
            seller_name="Nha cung cap Binh Thuong",
            amount_before_tax=25000000.0,
            tax_amount=2500000.0,
            total_amount=27500000.0,
            payment_method="Tiền mặt",  # VIOLATION!
            date="2026-06-03",
            signing_date="2026-06-03",
            imported_at="2026-06-26T00:00:00"
        )
        # Late signature invoice (> 5 days)
        inv4 = Invoice(
            id="inv-4",
            taxpayer_mst="0102030499",
            invoice_type="purchase",
            seller_mst="1234567890",
            seller_name="Nha cung cap Binh Thuong",
            amount_before_tax=5000000.0,
            tax_amount=500000.0,
            total_amount=5500000.0,
            payment_method="Chuyển khoản",
            date="2026-06-04",
            signing_date="2026-06-20",  # 16 days late!
            imported_at="2026-06-26T00:00:00"
        )
        db.session.add_all([inv1, inv2, inv3, inv4])

        # 4. Seed bank transactions for reconciliation matrix
        # Inflow matched
        tx_in = BankTransaction(
            id="tx-1",
            taxpayer_mst="0102030499",
            bank_name="Vietcombank",
            transaction_date="2026-06-02",
            description="Thanh toan hoa don inv-2",
            amount=33000000.0,
            status="matched",
            matched_invoice_id="inv-2",
            imported_at="2026-06-26T00:00:00"
        )
        # Outflow unmatched/unreconciled
        tx_out = BankTransaction(
            id="tx-2",
            taxpayer_mst="0102030499",
            bank_name="Vietcombank",
            transaction_date="2026-06-10",
            description="Rut tien mat chi tieu",
            amount=-5000000.0,
            status="unreconciled",
            imported_at="2026-06-26T00:00:00"
        )
        db.session.add_all([tx_in, tx_out])
        db.session.commit()

        # 5. Execute calculation
        res = calculate_tax_health("0102030499")
        
        # Check score, rating and metrics
        assert res["taxpayer_mst"] == "0102030499"
        assert "health_score" in res
        assert "compliance_rating" in res
        
        # Check non-cash payment risk count
        assert res["metrics"]["cash_payment_risk_count"] == 1
        # Check late signature count
        assert res["metrics"]["late_signature_count"] == 1
        
        # Check exposure projections
        # CIT exposure: 25,000,000 * 20% = 5,000,000
        # VAT exposure: 2,500,000
        assert res["tax_exposure"]["cit_non_deductible_exposure"] == 5000000.0
        assert res["tax_exposure"]["vat_non_deductible_exposure"] == 2500000.0
        assert res["tax_exposure"]["total_exposure"] == 7500000.0

        # Check bank reconciliation matrix
        assert res["reconciliation"]["total_bank_inflows"] == 33000000.0
        assert res["reconciliation"]["total_bank_outflows"] == 5000000.0
        assert len(res["reconciliation"]["unreconciled_transactions"]) == 1


def test_api_tax_health_score_endpoint(mock_app):
    """Test the HTTP endpoints for Tax Health Score."""
    client = mock_app.test_client()
    
    # 1. Page unauthorized
    res = client.get("/tax-health-score")
    assert res.status_code == 302  # Should redirect to login

    # 2. Page authorized
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["active_taxpayer_mst"] = "0102030499"

    res = client.get("/tax-health-score")
    assert res.status_code == 200
    assert b"Suckhoe" in res.data or b"Wise" in res.data or b"Health" in res.data or b"S\xe1\xbb\xa9c kh\xe1\xbb\x8fe" in res.data or b"S\xe1\xbb\xa9c Kh\xe1\xbb\x8fe" in res.data

    # 3. JSON API authorized (with mock database taxpayer)
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

    res_api = client.get("/api/tax/health-score")
    assert res_api.status_code == 200
    data = json.loads(res_api.data)
    assert data["taxpayer_mst"] == "0102030499"
    assert "health_score" in data
    assert "reconciliation" in data


def test_supplier_risk_audit_check(mock_app):
    """Test Axis 3: Supplier Risk Index triggers check alerts on high risk partner."""
    from invoices.models import Partner, Invoice
    from invoices.invoice_validator import validate_invoice

    with mock_app.app_context():
        # Register a blacklisted/closed partner in database
        risky_partner = Partner(
            mst="8888888888",
            name="Doanh Nghiep Ma A",
            address="Văn phòng ảo, Quận 1, TPHCM",
            mst_status="Ngừng hoạt động"  # Trigger condition
        )
        db.session.add(risky_partner)
        db.session.commit()

        # Create invoice from this partner
        inv = Invoice(
            id="inv-risky",
            taxpayer_mst="0102030499",
            invoice_type="purchase",
            seller_mst="8888888888",
            seller_name="Doanh Nghiep Ma A",
            amount_before_tax=10000000.0,
            tax_amount=1000000.0,
            total_amount=11000000.0,
            payment_method="Chuyển khoản",
            date="2026-06-05",
            signing_date="2026-06-05",
            imported_at="2026-06-26T00:00:00"
        )
        
        # Run invoice validator engine
        alerts = validate_invoice(inv)
        
        # We expect a critical supplier risk warning in the output
        supplier_alerts = [a for a in alerts if a["check"] == "Rủi ro NCC"]
        assert len(supplier_alerts) == 1
        assert supplier_alerts[0]["severity"] == "Nghiêm trọng"
        assert "NGỪNG HOẠT ĐỘNG" in supplier_alerts[0]["detail"]


def test_tax_chat_sessions_crud(mock_app):
    """Test full CRUD operations for AI Tax Advisor chat sessions and messages."""
    client = mock_app.test_client()

    # 1. Access without login -> 401
    res = client.get("/api/tax/chat/sessions")
    assert res.status_code == 401

    res = client.post("/api/tax/chat/sessions", json={"title": "Test Session"})
    assert res.status_code == 401

    # 2. Login
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"

    # 3. Create Session
    res = client.post("/api/tax/chat/sessions", json={"title": "Tư vấn GTGT 2026"})
    assert res.status_code == 201
    data = json.loads(res.data)
    assert "id" in data
    assert data["title"] == "Tư vấn GTGT 2026"
    session_id = data["id"]

    # 4. List Sessions
    res = client.get("/api/tax/chat/sessions")
    assert res.status_code == 200
    sessions_list = json.loads(res.data)
    assert len(sessions_list) >= 1
    assert any(s["id"] == session_id for s in sessions_list)

    # 5. Get Session details
    res = client.get(f"/api/tax/chat/sessions/{session_id}")
    assert res.status_code == 200
    session_detail = json.loads(res.data)
    assert session_detail["id"] == session_id
    assert session_detail["title"] == "Tư vấn GTGT 2026"
    assert len(session_detail["messages"]) == 0

    # 6. Rename Session
    res = client.put(f"/api/tax/chat/sessions/{session_id}", json={"title": "Tư vấn GTGT 2026 V2"})
    assert res.status_code == 200
    session_detail = json.loads(res.data)
    assert session_detail["title"] == "Tư vấn GTGT 2026 V2"

    # 7. Delete Session
    res = client.delete(f"/api/tax/chat/sessions/{session_id}")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["success"] is True

    # 8. Verify deletion
    res = client.get(f"/api/tax/chat/sessions/{session_id}")
    assert res.status_code == 404

