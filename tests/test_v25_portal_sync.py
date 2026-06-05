"""Tests for US-370 and US-371 (GDT Portal Syncing and Dashboard API)."""

import pytest
from extensions import db
from invoices.models import Invoice, TaxpayerProfile
from invoices.v25_compliance_service import sync_gdt_verification_status, run_portal_sync_agent

def test_gdt_portal_sync_agent_success(app):
    """US-370: Sync pending invoices to check statuses and assign GDT codes."""
    with app.app_context():
        # Clear existing invoices to prevent conflicts
        db.session.query(Invoice).delete()
        db.session.commit()

        # Create a compliant invoice
        inv = Invoice(
            id="0100112233-C26TBA-00000001",
            number="00000001",
            symbol="C26TBA",
            template_code="1",
            date="2026-06-05",
            seller_mst="0100112233",
            seller_name="Seller A",
            buyer_mst="0108999999",
            buyer_name="Buyer B",
            amount_before_tax=100000.0,
            tax_amount=10000.0,
            total_amount=110000.0,
            payment_method="TM/CK",
            has_signature=True,
            invoice_status="pending",
            imported_at="2026-06-05T00:00:00"
        )
        db.session.add(inv)
        db.session.commit()

        # Execute status sync agent
        report = run_portal_sync_agent()

        assert report["status"] == "success"
        assert report["total_checked"] == 1
        assert report["status_counts"]["approved"] == 1

        # Check updated values in db
        db.session.expire_all()
        updated_inv = Invoice.query.get(inv.id)
        assert updated_inv.invoice_status == "approved"
        assert "GDT Approval Code: GDT-" in updated_inv.notes


def test_gdt_portal_sync_agent_rejected(app):
    """US-370: Invoices failing basic rules should be marked as rejected."""
    with app.app_context():
        db.session.query(Invoice).delete()
        db.session.commit()

        # Create an non-compliant invoice: cash payment over 20M & missing signature
        inv = Invoice(
            id="0100112233-C26TBA-00000002",
            number="00000002",
            symbol="C26TBA",
            template_code="1",
            date="2026-06-05",
            seller_mst="0100112233",
            seller_name="Seller A",
            buyer_mst="0108999999",
            buyer_name="Buyer B",
            amount_before_tax=30000000.0,
            tax_amount=3000000.0,
            total_amount=33000000.0,
            payment_method="TM", # CASH!
            has_signature=False, # MISSING SIGNATURE!
            invoice_status="pending",
            imported_at="2026-06-05T00:00:00"
        )
        db.session.add(inv)
        db.session.commit()

        report = run_portal_sync_agent()

        assert report["status"] == "success"
        assert report["total_checked"] == 1
        assert report["status_counts"]["rejected"] == 1

        db.session.expire_all()
        updated_inv = Invoice.query.get(inv.id)
        assert updated_inv.invoice_status == "rejected"
        assert "GDT Sync Refusal:" in updated_inv.notes
