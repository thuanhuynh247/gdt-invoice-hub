"""Tests for the cryptographic audit ledger service (US-090, US-091)."""

from __future__ import annotations

import pytest
from extensions import db
from invoices.models import AuditBlock
from invoices.audit_ledger_service import add_audit_block, verify_ledger_integrity, GENESIS_HASH


def test_ledger_block_creation_and_chaining(app):
    """Verify that multiple audit blocks are chained together correctly using SHA-256 hashes (US-090)."""
    with app.app_context():
        # Clear existing blocks
        AuditBlock.query.delete()
        db.session.commit()

        # Add Genesis / First Block
        payload1 = {"invoice_id": "INV-001", "total_amount": 1500000.0}
        block1 = add_audit_block(
            action_type="INVOICE_IMPORT",
            mst="0109998887",
            payload_dict=payload1
        )

        assert block1 is not None
        assert block1.block_id > 0
        assert block1.prev_block_hash == GENESIS_HASH
        assert len(block1.block_hash) == 64

        # Add Second Block
        payload2 = {"invoice_id": "INV-002", "total_amount": 2500000.0}
        block2 = add_audit_block(
            action_type="INVOICE_IMPORT",
            mst="0109998887",
            payload_dict=payload2
        )

        assert block2 is not None
        assert block2.prev_block_hash == block1.block_hash
        assert block2.block_hash != block1.block_hash

        # Verify integrity of the entire chain
        is_valid, corrupted_id, error_msg = verify_ledger_integrity()
        assert is_valid is True
        assert corrupted_id is None
        assert error_msg is None


def test_ledger_tampering_detection(app):
    """Verify that any database tampering triggers a validation failure (US-091)."""
    with app.app_context():
        # Clear and create two valid blocks
        AuditBlock.query.delete()
        db.session.commit()

        block1 = add_audit_block(
            action_type="INVOICE_IMPORT",
            mst="0109998887",
            payload_dict={"data": "Block 1"}
        )
        block2 = add_audit_block(
            action_type="SIGNATURE_VERIFY",
            mst="0109998887",
            payload_dict={"data": "Block 2"}
        )

        # Confirm initial integrity is perfectly valid
        is_valid, corrupted_id, error_msg = verify_ledger_integrity()
        assert is_valid is True

        # Simulate a direct DB database modification/tampering
        tampered_block = db.session.get(AuditBlock, block2.block_id)
        # Modify the payload hash directly without updating block_hash
        tampered_block.payload_hash = "tampered_hash_value_123"
        db.session.commit()

        # Integrity check MUST detect this tampering and return False
        is_valid, corrupted_id, error_msg = verify_ledger_integrity()
        assert is_valid is False
        assert corrupted_id == block2.block_id
        assert "Integrity corruption" in error_msg


def test_ledger_chain_break_detection(app):
    """Verify that a break in hash chaining (e.g. invalid prev_block_hash reference) is detected (US-091)."""
    with app.app_context():
        AuditBlock.query.delete()
        db.session.commit()

        block1 = add_audit_block(
            action_type="INVOICE_IMPORT",
            mst="0109998887",
            payload_dict={"data": "Block 1"}
        )
        block2 = add_audit_block(
            action_type="INVOICE_IMPORT",
            mst="0109998887",
            payload_dict={"data": "Block 2"}
        )

        # Break the chaining link manually
        tampered_block = db.session.get(AuditBlock, block2.block_id)
        tampered_block.prev_block_hash = "broken_link_value_999"
        db.session.commit()

        is_valid, corrupted_id, error_msg = verify_ledger_integrity()
        assert is_valid is False
        assert corrupted_id == block2.block_id
        assert "Chaining break" in error_msg
