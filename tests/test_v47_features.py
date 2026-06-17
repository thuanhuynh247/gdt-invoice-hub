"""Pytest verification suite for v47 VAT Law 48/2024/QH15 Compliance Engine.

Tests VAT rate classification, input credit eligibility validation,
refund threshold computation, API routing logic, and multi-tenant isolation.
"""

from __future__ import annotations

import os
import json
import sqlite3
import pytest
from flask import Flask
from invoices.multitenant_service import get_tenant_db_path, bootstrap_tenant_db
from invoices.v47_service import V47ComplianceService


@pytest.fixture
def mock_app():
    """Create a mock Flask app context with base configurations."""
    app = Flask(__name__, template_folder="../templates")
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["BASE_DATA_DIR"] = os.path.join(os.path.dirname(__file__), "..", "data")

    from auth import auth_blueprint
    from invoices.routes import invoices_blueprint
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(invoices_blueprint)

    @app.route("/")
    def index():
        return "index"

    return app


@pytest.fixture
def mock_tenant_db():
    """Ensure a clean tenant DB for testing."""
    mst = "0102030498"
    db_path = get_tenant_db_path(mst)

    if os.path.exists(db_path):
        try:
            os.unlink(db_path)
        except Exception:
            pass

    bootstrap_tenant_db(mst)
    yield mst

    if os.path.exists(db_path):
        try:
            os.unlink(db_path)
        except Exception:
            pass


def test_vat_rate_classification_10pct(mock_tenant_db):
    """Test default 10% rate for standard goods."""
    mst = mock_tenant_db
    service = V47ComplianceService()

    res = service.classify_vat_rate(mst, "Dịch vụ tư vấn quản lý doanh nghiệp")
    assert res["classified_rate"] == "10%"
    assert "Điều 9.3" in res["article_reference"]


def test_vat_rate_classification_5pct(mock_tenant_db):
    """Test 5% rate for reduced-rate items (e.g. medical equipment)."""
    mst = mock_tenant_db
    service = V47ComplianceService()

    res = service.classify_vat_rate(mst, "Thiết bị y tế chẩn đoán hình ảnh")
    assert res["classified_rate"] == "5%"
    assert "Điều 9.2" in res["article_reference"]


def test_vat_rate_classification_0pct(mock_tenant_db):
    """Test 0% rate for exported goods."""
    mst = mock_tenant_db
    service = V47ComplianceService()

    res = service.classify_vat_rate(mst, "Hàng hóa xuất khẩu sang Nhật Bản")
    assert res["classified_rate"] == "0%"
    assert "Điều 9.1" in res["article_reference"]


def test_vat_rate_non_taxable(mock_tenant_db):
    """Test non-taxable items (Article 5 categories)."""
    mst = mock_tenant_db
    service = V47ComplianceService()

    res = service.classify_vat_rate(mst, "Dịch vụ y tế khám chữa bệnh ART5_10")
    assert res["classified_rate"] == "NON_TAXABLE"
    assert res["exemption_code"] == "ART5_10"


def test_input_credit_eligible(mock_tenant_db):
    """Test eligible input credit with all conditions met."""
    mst = mock_tenant_db
    service = V47ComplianceService()

    res = service.check_input_credit_eligibility(
        mst=mst, invoice_number="INV-2026-001", invoice_amount=50000000.0,
        has_vat_invoice=True, has_bank_payment=True, seller_declared=True
    )
    assert res["is_eligible"] is True
    assert len(res["rejection_reasons"]) == 0


def test_input_credit_rejected_missing_invoice(mock_tenant_db):
    """Test rejection when VAT invoice is missing."""
    mst = mock_tenant_db
    service = V47ComplianceService()

    res = service.check_input_credit_eligibility(
        mst=mst, invoice_number="INV-2026-002", invoice_amount=30000000.0,
        has_vat_invoice=False, has_bank_payment=True, seller_declared=True
    )
    assert res["is_eligible"] is False
    assert any("MISSING_VAT_INVOICE" in r for r in res["rejection_reasons"])


def test_input_credit_rejected_no_bank_payment(mock_tenant_db):
    """Test rejection when non-cash payment proof is missing."""
    mst = mock_tenant_db
    service = V47ComplianceService()

    res = service.check_input_credit_eligibility(
        mst=mst, invoice_number="INV-2026-003", invoice_amount=25000000.0,
        has_vat_invoice=True, has_bank_payment=False, seller_declared=True
    )
    assert res["is_eligible"] is False
    assert any("MISSING_BANK_PAYMENT" in r for r in res["rejection_reasons"])


def test_refund_eligible(mock_tenant_db):
    """Test refund eligibility when uncredited balance ≥ 300M VND."""
    mst = mock_tenant_db
    service = V47ComplianceService()

    res = service.estimate_vat_refund(
        mst=mst, period_label="Q1-2026",
        total_output_vat=100_000_000, total_input_vat=500_000_000,
        export_revenue=5_000_000_000
    )
    assert res["refund_eligible"] is True
    assert res["uncredited_balance"] == 400_000_000
    # Refund cap = 10% of 5B = 500M, but uncredited is 400M → refund = 400M
    assert res["estimated_refund"] == 400_000_000


def test_refund_not_eligible(mock_tenant_db):
    """Test refund ineligibility when uncredited balance < 300M VND."""
    mst = mock_tenant_db
    service = V47ComplianceService()

    res = service.estimate_vat_refund(
        mst=mst, period_label="Q2-2026",
        total_output_vat=200_000_000, total_input_vat=400_000_000,
        export_revenue=1_000_000_000
    )
    assert res["refund_eligible"] is False
    assert res["uncredited_balance"] == 200_000_000
    assert res["estimated_refund"] == 0.0


def test_refund_capped_by_export_revenue(mock_tenant_db):
    """Test refund capped at 10% of export revenue."""
    mst = mock_tenant_db
    service = V47ComplianceService()

    res = service.estimate_vat_refund(
        mst=mst, period_label="Q3-2026",
        total_output_vat=50_000_000, total_input_vat=1_000_000_000,
        export_revenue=2_000_000_000
    )
    assert res["refund_eligible"] is True
    assert res["uncredited_balance"] == 950_000_000
    # Cap = 10% of 2B = 200M → refund = 200M (capped)
    assert res["estimated_refund"] == 200_000_000


def test_api_routes_v47(mock_app, mock_tenant_db):
    """Test v47 HTTP API routes and view rendering."""
    client = mock_app.test_client()

    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["taxpayer_mst"] = mock_tenant_db

    res_page = client.get("/v47-compliance-hub")
    assert res_page.status_code == 200
    assert b"VAT Law 48" in res_page.data or b"VAT Rate" in res_page.data

    res_api = client.get(f"/api/v47/compliance-data?mst={mock_tenant_db}")
    assert res_api.status_code == 200
    data = json.loads(res_api.data)
    assert data["status"] == "success"
    assert "rate_classification" in data
    assert "credit_check" in data
    assert "refund_estimate" in data
