"""Pytest suite for V80 Compliance Hub (Circular 20/2026/TT-BTC & Decree 70/2025/NĐ-CP)."""

from __future__ import annotations

import os
import json
import pytest
import sqlite3
import tempfile
from flask import Flask
from extensions import db
from unittest.mock import patch, MagicMock

from invoices.v80_service import V80ComplianceService


@pytest.fixture
def temp_tenant_db(tmp_path):
    """Create an isolated test directory for tenant database files."""
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return str(data_dir)


@pytest.fixture
def mock_app(temp_tenant_db):
    """Mock Flask app with v80 routes registered."""
    app = Flask(__name__, template_folder="../templates")
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-v80"
    app.config["BASE_DATA_DIR"] = temp_tenant_db
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


def test_v80_compliant_authorized_card(temp_tenant_db):
    """Test fully compliant personal card payment above 5M threshold with doc and proof."""
    service = V80ComplianceService(base_data_dir=temp_tenant_db)
    mst = "0102030405"

    res = service.audit_authorized_expense(
        mst=mst,
        total_amount=15_000_000.0,
        vat_amount=1_500_000.0,
        invoice_number="INV-2026-001",
        invoice_date="2026-03-15",
        seller_mst="0100109106",
        seller_name="Viettel",
        payment_method="authorized_card",
        authorized_person="Nguyen Van A",
        has_authorization_doc=True,
        has_bank_proof=True,
        is_split_suspicious=False
    )

    assert res["risk_level"] == "SAFE"
    assert res["compliance_score"] == 100.0
    assert res["nondeductible_cit"] == 0.0
    assert res["noncreditable_vat"] == 0.0
    assert len(res["violations"]) == 0
    assert len(res["debate"]) == 3


def test_v80_cash_payment_violation(temp_tenant_db):
    """Test cash payment above 5M threshold is strictly disallowed under TT20 & ND70."""
    service = V80ComplianceService(base_data_dir=temp_tenant_db)
    mst = "0102030405"

    res = service.audit_authorized_expense(
        mst=mst,
        total_amount=8_000_000.0,
        vat_amount=800_000.0,
        invoice_number="INV-2026-002",
        payment_method="cash",
        has_authorization_doc=False,
        has_bank_proof=False
    )

    assert res["risk_level"] == "CRITICAL"
    assert res["nondeductible_cit"] == 8_000_000.0
    assert res["noncreditable_vat"] == 800_000.0
    assert res["compliance_score"] <= 50.0
    assert any("tiền mặt" in v.lower() for v in res["violations"])


def test_v80_missing_authorization_or_bank_proof(temp_tenant_db):
    """Test authorized card payment missing authorization doc or bank proof."""
    service = V80ComplianceService(base_data_dir=temp_tenant_db)
    mst = "0102030405"

    # Missing authorization doc
    res1 = service.audit_authorized_expense(
        mst=mst,
        total_amount=6_000_000.0,
        vat_amount=600_000.0,
        payment_method="authorized_card",
        has_authorization_doc=False,
        has_bank_proof=True
    )
    assert res1["nondeductible_cit"] == 6_000_000.0
    assert any("ủy quyền" in v.lower() for v in res1["violations"])

    # Missing bank proof
    res2 = service.audit_authorized_expense(
        mst=mst,
        total_amount=6_000_000.0,
        vat_amount=600_000.0,
        payment_method="authorized_card",
        has_authorization_doc=True,
        has_bank_proof=False
    )
    assert res2["nondeductible_cit"] == 6_000_000.0
    assert any("sao kê" in v.lower() or "ngân hàng" in v.lower() for v in res2["violations"])


def test_v80_negative_amount_error(temp_tenant_db):
    """Verify ValueError is raised on negative total amounts."""
    service = V80ComplianceService(base_data_dir=temp_tenant_db)
    mst = "0102030405"

    with pytest.raises(ValueError):
        service.audit_authorized_expense(mst=mst, total_amount=-5000)


def test_v80_history_and_deletion(temp_tenant_db):
    """Test audit log persistence, history retrieval, and log deletion."""
    service = V80ComplianceService(base_data_dir=temp_tenant_db)
    mst = "0102030405"

    # Insert 2 logs
    res1 = service.audit_authorized_expense(mst=mst, total_amount=10_000_000.0, invoice_number="INV-DEL-1")
    res2 = service.audit_authorized_expense(mst=mst, total_amount=20_000_000.0, invoice_number="INV-DEL-2")

    history = service.get_history(mst)
    assert len(history) >= 2
    first_id = history[0]["id"]

    # Delete first log
    deleted = service.delete_log(mst, first_id)
    assert deleted is True

    history_after = service.get_history(mst)
    assert not any(h["id"] == first_id for h in history_after)


def test_v80_batch_scan(temp_tenant_db):
    """Test batch scan across tenant invoices table."""
    service = V80ComplianceService(base_data_dir=temp_tenant_db)
    mst = "0102030405"

    # Setup dummy invoices in tenant DB
    conn = service.get_tenant_connection(mst)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT,
            invoice_date TEXT,
            seller_mst TEXT,
            seller_name TEXT,
            total_amount REAL,
            vat_amount REAL,
            payment_method TEXT
        )
    """)
    cur.execute("INSERT INTO invoices (invoice_number, invoice_date, total_amount, vat_amount, payment_method) VALUES ('INV-1', '2026-03-01', 10000000, 1000000, 'cash')")
    cur.execute("INSERT INTO invoices (invoice_number, invoice_date, total_amount, vat_amount, payment_method) VALUES ('INV-2', '2026-03-02', 15000000, 1500000, 'card')")
    cur.execute("INSERT INTO invoices (invoice_number, invoice_date, total_amount, vat_amount, payment_method) VALUES ('INV-3', '2026-03-03', 2000000, 200000, 'cash')")
    conn.commit()
    conn.close()

    scan_res = service.scan_tenant_invoices_for_circular20(mst)
    assert scan_res["total_scanned"] == 3
    assert scan_res["above_threshold_count"] == 2
    assert scan_res["critical_count"] == 1
    assert scan_res["warning_count"] == 1
    assert scan_res["total_nondeductible_cit"] == 10000000.0


def test_v80_api_routes(mock_app):
    """Test all V80 REST endpoints in Flask client."""
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["taxpayer_mst"] = "0102030405"

    # 1. Hub HTML page
    res_page = client.get("/v80-compliance-hub")
    assert res_page.status_code == 200
    assert b"Circular 20/2026/TT-BTC" in res_page.data

    # 2. Compliance Data GET
    res_data = client.get("/api/v80/compliance-data?mst=0102030405")
    assert res_data.status_code == 200
    data = json.loads(res_data.data)
    assert data["status"] == "success"
    assert "sample_card_compliant" in data
    assert "debate" in data

    # 3. Audit Expense POST
    payload = {
        "mst": "0102030405",
        "total_amount": 10000000,
        "vat_amount": 1000000,
        "payment_method": "authorized_card",
        "has_authorization_doc": True,
        "has_bank_proof": True
    }
    res_audit = client.post("/api/v80/audit-expense", json=payload)
    assert res_audit.status_code == 200
    audit_data = json.loads(res_audit.data)
    assert audit_data["results"]["risk_level"] == "SAFE"

    # 4. Batch Scan POST
    res_scan = client.post("/api/v80/batch-scan", json={"mst": "0102030405"})
    assert res_scan.status_code == 200
    scan_data = json.loads(res_scan.data)
    assert scan_data["status"] == "success"
