"""Unit tests for Cryptographic Ledger and Zero-Knowledge Proofs (US-332, US-333)."""

from __future__ import annotations

import pytest
from extensions import db
from invoices.models import Invoice
from invoices.merkle_service import (
    compute_invoice_hash,
    rebuild_and_write_merkle_roots,
    verify_ledger_integrity
)
from invoices.zkp_service import (
    generate_vat_compliance_proof,
    verify_vat_compliance_proof
)


def test_merkle_ledger_and_tamper_detection(app):
    """Test sequential Merkle ledger integrity and database modification warning."""
    with app.app_context():
        # Clear existing invoices
        Invoice.query.delete()
        db.session.commit()

        # Seed invoices
        inv1 = Invoice(
            id="inv1", taxpayer_mst="0101234567", seller_mst="111", buyer_mst="0101234567",
            number="001", total_amount=110000.0, amount_before_tax=100000.0, tax_amount=10000.0,
            date="2026-06-01", imported_at="2026-06-01T00:00:00Z"
        )
        inv2 = Invoice(
            id="inv2", taxpayer_mst="0101234567", seller_mst="222", buyer_mst="0101234567",
            number="002", total_amount=220000.0, amount_before_tax=200000.0, tax_amount=20000.0,
            date="2026-06-02", imported_at="2026-06-02T00:00:00Z"
        )
        db.session.add_all([inv1, inv2])
        db.session.commit()

        # Build Merkle roots
        root = rebuild_and_write_merkle_roots("0101234567")
        assert root is not None

        # Verify initial ledger is correct
        is_valid, tampered = verify_ledger_integrity("0101234567")
        assert is_valid is True
        assert len(tampered) == 0

        # Tamper with inv1 in DB (bypass app hooks by directly editing attributes)
        inv1.total_amount = 999999.0
        db.session.commit()

        # Verify tampered ledger is flagged
        is_valid_tampered, tampered_after = verify_ledger_integrity("0101234567")
        assert is_valid_tampered is False
        assert "inv1" in tampered_after


def test_zero_knowledge_proof_tax_compliance():
    """Test mathematically proving VAT rate compliance without revealing raw values."""
    # Scenario: Invoice has Net: 50,000, VAT: 5,000 (10% rate)
    net_amt = 50000.0
    vat_amt = 5000.0
    rate = 10

    proof_data = generate_vat_compliance_proof(net_amt, vat_amt, rate)
    assert "C_V" in proof_data
    assert "C_A" in proof_data
    assert proof_data["rate_percent"] == 10

    # Verify proof
    is_valid = verify_vat_compliance_proof(proof_data)
    assert is_valid is True

    # Tamper with rate to verify mismatch fails
    proof_data_tampered = proof_data.copy()
    proof_data_tampered["rate_percent"] = 8
    is_valid_tampered = verify_vat_compliance_proof(proof_data_tampered)
    assert is_valid_tampered is False
