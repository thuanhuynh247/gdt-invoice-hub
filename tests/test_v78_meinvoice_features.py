"""Pytest verification suite for MISA meInvoice advanced features:
1. MISA AVA Multilingual Tax Translation Widget
2. Cryptographic Blockchain Ledger & Merkle Tree Integrity
3. POS/Ticket/Receipt invoice sub-types
"""

from __future__ import annotations

import json
import pytest
from flask import Flask
from extensions import db
from unittest.mock import patch, MagicMock
from invoices.models import Invoice, AuditBlock
from invoices.merkle_service import compute_invoice_hash, rebuild_and_write_merkle_roots, verify_ledger_integrity
from invoices.audit_ledger_service import add_audit_block, verify_ledger_integrity as verify_audit_ledger_integrity

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


# --- AXIS 1: MULTILINGUAL TRANSLATION WIDGET ---

@patch("invoices.tax_advisor_service.translate_text")
def test_api_tax_translate(mock_translate, mock_app):
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"

    mock_translate.return_value = "This is a translated tax advice."

    # Test translating to English
    payload = {
        "text": "Đây là lời khuyên thuế.",
        "target_lang": "en"
    }
    res = client.post("/api/tax/translate", json=payload)
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["translated"] == "This is a translated tax advice."
    mock_translate.assert_called_once_with("Đây là lời khuyên thuế.", "en")


# --- AXIS 3: BLOCKCHAIN & MERKLE INTEGRITY ---

def test_blockchain_verifications_and_tampering(mock_app):
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["active_taxpayer_mst"] = "0102030499"

    with mock_app.app_context():
        # Seed an invoice
        inv = Invoice(
            id="inv-secure-1",
            taxpayer_mst="0102030499",
            invoice_type="purchase",
            seller_mst="1234567890",
            seller_name="Nha Ban A",
            amount_before_tax=1000000.0,
            tax_amount=100000.0,
            total_amount=1100000.0,
            payment_method="Chuyển khoản",
            date="2026-06-26",
            signing_date="2026-06-26",
            imported_at="2026-06-26T00:00:00"
        )
        db.session.add(inv)
        db.session.commit()

        # Build Merkle Tree
        rebuild_and_write_merkle_roots("0102030499")
        
        # Log action to audit ledger
        add_audit_block("INITIAL_SYNC", "0102030499", {"invoice_id": "inv-secure-1"})

    # Verify blockchain endpoint
    res = client.post("/api/tax/blockchain-verify")
    assert res.status_code == 200
    data = json.loads(res.data)
    
    assert data["total_invoices"] == 1
    assert data["total_blocks"] >= 1
    assert data["invoice_ledger"]["valid"] is True
    assert data["audit_ledger"]["valid"] is True

    # Now simulate TAMPERING (editing invoice directly in DB without rebuilding Merkle Tree)
    with mock_app.app_context():
        tampered_inv = db.session.get(Invoice, "inv-secure-1")
        tampered_inv.total_amount = 9999999.0  # Illegal direct alteration
        db.session.commit()

    # Re-verify -> Should detect corruption!
    res_tampered = client.post("/api/tax/blockchain-verify")
    assert res_tampered.status_code == 200
    data_tampered = json.loads(res_tampered.data)
    
    assert data_tampered["invoice_ledger"]["valid"] is False
    assert "inv-secure-1" in data_tampered["invoice_ledger"]["tampered_ids"]

    # Run self-healing rebuild!
    res_rebuild = client.post("/api/tax/blockchain-rebuild")
    assert res_rebuild.status_code == 200
    data_rebuild = json.loads(res_rebuild.data)
    assert data_rebuild["status"] == "success"

    # Re-verify -> Should be secure again!
    res_healed = client.post("/api/tax/blockchain-verify")
    data_healed = json.loads(res_healed.data)
    assert data_healed["invoice_ledger"]["valid"] is True


# --- AXIS 5: INVOICE SUB-TYPES (POS / TICKET / RECEIPT) ---

def test_invoice_sub_types_creation(mock_app):
    with mock_app.app_context():
        # Create different sub-types
        inv_pos = Invoice(
            id="inv-pos-1",
            taxpayer_mst="0102030499",
            invoice_type="sales",
            invoice_sub_type="pos_receipt",  # POS Receipt
            total_amount=150000.0,
            date="2026-06-26",
            imported_at="2026-06-26T00:00:00"
        )
        inv_ticket = Invoice(
            id="inv-ticket-1",
            taxpayer_mst="0102030499",
            invoice_type="sales",
            invoice_sub_type="ticket",  # Electronic Ticket
            total_amount=50000.0,
            date="2026-06-26",
            imported_at="2026-06-26T00:00:00"
        )
        inv_standard = Invoice(
            id="inv-std-1",
            taxpayer_mst="0102030499",
            invoice_type="sales",
            total_amount=5000000.0,
            date="2026-06-26",
            imported_at="2026-06-26T00:00:00"
        )
        
        db.session.add_all([inv_pos, inv_ticket, inv_standard])
        db.session.commit()

        # Retrieve and verify
        p_inv = db.session.get(Invoice, "inv-pos-1")
        assert p_inv.invoice_sub_type == "pos_receipt"
        assert p_inv.to_dict()["invoice_sub_type"] == "pos_receipt"

        t_inv = db.session.get(Invoice, "inv-ticket-1")
        assert t_inv.invoice_sub_type == "ticket"
        assert t_inv.to_dict()["invoice_sub_type"] == "ticket"

        s_inv = db.session.get(Invoice, "inv-std-1")
        assert s_inv.invoice_sub_type == "standard" or s_inv.invoice_sub_type is None
        assert s_inv.to_dict()["invoice_sub_type"] == "standard"
