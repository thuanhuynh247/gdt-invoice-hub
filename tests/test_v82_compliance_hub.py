"""Unit tests for V82 Compliance Hub: Tax Settlement & CIT/VAT Deductibility Engine."""

import pytest
import os
import shutil
import tempfile
from invoices.v82_service import V82ComplianceService


@pytest.fixture
def temp_service():
    temp_dir = tempfile.mkdtemp()
    service = V82ComplianceService(base_data_dir=temp_dir)
    yield service, temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_valid_invoice_audit(temp_service):
    service, _ = temp_service
    tenant_mst = "0101234567"

    res = service.audit_invoice_deductibility(
        tenant_mst=tenant_mst,
        vendor_name="CÔNG TY TNHH PHÁT TRIỂN CÔNG NGHỆ ABC",
        vendor_mst="0109876543",
        invoice_number="INV-2026-001",
        invoice_date="2026-08-25",
        total_amount=55_000_000.0,
        vat_amount=5_000_000.0,
        payment_method="BANK_TRANSFER",
        has_non_cash_proof=True,
        is_valid_xml=True,
        is_blacklisted=False,
    )

    assert res["risk_level"] == "SAFE"
    assert res["compliance_score"] == 100.0
    assert res["cit_deductible_amount"] == 50_000_000.0
    assert res["cit_non_deductible_amount"] == 0.0
    assert res["vat_creditable_amount"] == 5_000_000.0
    assert len(res["violations"]) == 0
    assert "đủ điều kiện" in res["audit_notes"].lower()


def test_cash_payment_over_20m_violation(temp_service):
    service, _ = temp_service
    tenant_mst = "0101234567"

    res = service.audit_invoice_deductibility(
        tenant_mst=tenant_mst,
        vendor_name="CÔNG TY TNHH DỊCH VỤ THƯƠNG MẠI XYZ",
        vendor_mst="0108888888",
        invoice_number="INV-2026-002",
        invoice_date="2026-08-26",
        total_amount=33_000_000.0,
        vat_amount=3_000_000.0,
        payment_method="CASH",
        has_non_cash_proof=False,
        is_valid_xml=True,
        is_blacklisted=False,
    )

    assert res["risk_level"] in ("WARNING", "CRITICAL")
    assert res["cit_deductible_amount"] == 0.0
    assert res["cit_non_deductible_amount"] == 30_000_000.0
    assert res["vat_creditable_amount"] == 0.0
    assert any("thanh toán bằng tiền mặt" in v for v in res["violations"])


def test_blacklisted_vendor_violation(temp_service):
    service, _ = temp_service
    tenant_mst = "0101234567"

    res = service.audit_invoice_deductibility(
        tenant_mst=tenant_mst,
        vendor_name="CÔNG TY MA LỜI DỤNG THUẾ",
        vendor_mst="0109999999",
        invoice_number="INV-2026-003",
        invoice_date="2026-08-27",
        total_amount=100_000_000.0,
        vat_amount=10_000_000.0,
        payment_method="BANK_TRANSFER",
        has_non_cash_proof=True,
        is_valid_xml=True,
        is_blacklisted=True,
    )

    assert res["risk_level"] == "CRITICAL"
    assert res["cit_deductible_amount"] == 0.0
    assert res["cit_non_deductible_amount"] == 90_000_000.0
    assert res["vat_creditable_amount"] == 0.0
    assert any("doanh nghiệp bỏ địa điểm kinh doanh" in v for v in res["violations"])


def test_summary_analytics_and_history(temp_service):
    service, _ = temp_service
    tenant_mst = "0101234567"

    # Audit 2 invoices
    service.audit_invoice_deductibility(
        tenant_mst=tenant_mst,
        vendor_name="NCC A",
        vendor_mst="0101111111",
        invoice_number="001",
        invoice_date="2026-08-01",
        total_amount=11_000_000.0,
        vat_amount=1_000_000.0,
        payment_method="BANK_TRANSFER",
        has_non_cash_proof=True,
    )
    service.audit_invoice_deductibility(
        tenant_mst=tenant_mst,
        vendor_name="NCC B",
        vendor_mst="0102222222",
        invoice_number="002",
        invoice_date="2026-08-02",
        total_amount=22_000_000.0,
        vat_amount=2_000_000.0,
        payment_method="CASH",
        has_non_cash_proof=False,
    )

    analytics = service.get_summary_analytics(tenant_mst)
    assert analytics["total_invoices"] == 2
    assert analytics["grand_total_amount"] == 33_000_000.0
    assert analytics["total_deductible"] == 10_000_000.0

    history = service.get_history(tenant_mst)
    assert len(history) == 2

    # Delete 1 log
    deleted = service.delete_log(tenant_mst, history[0]["id"])
    assert deleted is True

    history_after = service.get_history(tenant_mst)
    assert len(history_after) == 1


# --- Flask Route Integration Tests ---

@pytest.fixture
def mock_app(temp_service):
    _, temp_dir = temp_service
    from flask import Flask
    from extensions import db

    app = Flask(__name__, template_folder="../templates")
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-v82"
    app.config["BASE_DATA_DIR"] = temp_dir
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    from auth import auth_blueprint
    from invoices.routes import invoices_blueprint
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(invoices_blueprint)

    @app.route("/")
    def index():
        return "Index Page"

    with app.app_context():
        db.create_all()
        yield app


def test_v82_hub_requires_login(mock_app):
    """Anonymous access to /v82-compliance-hub redirects to login."""
    client = mock_app.test_client()
    response = client.get("/v82-compliance-hub")
    assert response.status_code in (302, 401)


def test_v82_hub_render(mock_app):
    """Authenticated access to /v82-compliance-hub returns 200 and renders Bento grid layout."""
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["taxpayer_mst"] = "0101234567"

    response = client.get("/v82-compliance-hub")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "V82" in html or "Quyết Toán Thuế" in html


def test_v82_audit_invoice_route(mock_app):
    """POST /api/v82/audit-invoice performs audit and returns status='success'."""
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["taxpayer_mst"] = "0101234567"

    payload = {
        "vendor_name": "CÔNG TY TNHH PHÁT TRIỂN CÔNG NGHỆ ABC",
        "vendor_mst": "0109876543",
        "invoice_number": "INV-2026-999",
        "invoice_date": "2026-08-27",
        "total_amount": 55000000.0,
        "vat_amount": 5000000.0,
        "payment_method": "BANK_TRANSFER",
        "has_non_cash_proof": True,
        "is_valid_xml": True,
        "is_blacklisted": False
    }
    response = client.post("/api/v82/audit-invoice", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert "results" in data
    assert data["results"]["risk_level"] == "SAFE"


def test_v82_compliance_data_route(mock_app):
    """GET /api/v82/compliance-data returns summary analytics and history."""
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["taxpayer_mst"] = "0101234567"

    response = client.get("/api/v82/compliance-data")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert "analytics" in data
    assert "history" in data


def test_v82_delete_log_route(mock_app):
    """DELETE /api/v82/delete-log deletes an existing log entry."""
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["taxpayer_mst"] = "0101234567"

    # Audit an invoice first
    client.post("/api/v82/audit-invoice", json={
        "vendor_name": "NCC TEST DELETE",
        "vendor_mst": "0101111111",
        "invoice_number": "INV-DEL-1",
        "invoice_date": "2026-08-27",
        "total_amount": 10000000.0,
        "vat_amount": 1000000.0
    })

    # Fetch history
    res_data = client.get("/api/v82/compliance-data").get_json()
    history = res_data.get("history", [])
    assert len(history) > 0
    log_id = history[0]["id"]

    # Delete log via POST or DELETE with JSON
    del_resp = client.post("/api/v82/delete-log", json={"log_id": log_id})
    assert del_resp.status_code == 200
    del_data = del_resp.get_json()
    assert del_data["status"] == "success"


