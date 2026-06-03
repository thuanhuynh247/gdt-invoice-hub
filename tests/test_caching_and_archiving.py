"""Unit and Integration Tests for Caching and Archiving (US-124, US-125)."""

from __future__ import annotations

import os
import zipfile
import pytest
from datetime import date, datetime
from extensions import db
from invoices.models import Invoice, LineItem, TaxpayerProfile
from invoices.stats_cache import get_cached_stats, set_cached_stats, invalidate_stats_cache
from invoices.archiver import InvoiceArchiver

class TestHybridCachingLayer:
    """US-124: Hybrid Stats Caching and Invalidation Layer."""

    def test_cache_hit_and_miss(self):
        """Verify that cache correctly stores, retrieves, and invalidates KPI statistics."""
        mst = "0102030405"
        from_d = "2026-05-01"
        to_d = "2026-05-31"
        direction = "purchase"
        
        # Ensure fresh start
        invalidate_stats_cache(mst)
        
        # Miss first
        assert get_cached_stats(mst, from_d, to_d, direction) is None
        
        # Store
        sample_stats = {
            "total_spend": 500000000.0,
            "total_tax": 40000000.0,
            "active_count": 5,
            "cancelled_count": 0
        }
        set_cached_stats(mst, from_d, to_d, direction, sample_stats)
        
        # Hit next
        hit = get_cached_stats(mst, from_d, to_d, direction)
        assert hit is not None
        assert hit["total_spend"] == 500000000.0
        assert hit["active_count"] == 5
        
        # Invalidate for this MST specifically
        invalidate_stats_cache(mst)
        assert get_cached_stats(mst, from_d, to_d, direction) is None

    def test_cache_invalidation_on_invoice_save(self, app):
        """Assert that saving or modifying an invoice invalidates the stats cache."""
        with app.app_context():
            mst = "0102030405"
            from_d = "2026-05-01"
            to_d = "2026-05-31"
            direction = "purchase"
            
            sample_stats = {"total_spend": 100.0}
            set_cached_stats(mst, from_d, to_d, direction, sample_stats)
            
            # Verify cached
            assert get_cached_stats(mst, from_d, to_d, direction) is not None
            
            # Save invoice to invoke invalidation trigger
            from invoices.service import _save_local_invoices
            sample_invoice = {
                "id": "99999999-XYZ-123",
                "date": "2026-05-15",
                "amount": 50000.0,
                "status": "valid",
                "issuer": "Cong ty Test",
                "seller_mst": mst,
                "buyer_mst": "buyer-mst-123",
                "items": []
            }
            _save_local_invoices([sample_invoice])
            
            # Verify cache has been invalidated!
            assert get_cached_stats(mst, from_d, to_d, direction) is None


class TestZeroDowntimeArchiver:
    """US-125: Automated historical partition & zero-downtime zlib archiver."""

    def test_archive_process_and_query_merge(self, app):
        """Validate historical archiving and transparent merged search operations."""
        with app.app_context():
            # Setup taxpayer profile in session/db to prevent foreign key errors
            profile = TaxpayerProfile.query.filter_by(mst="0101234567").first()
            if not profile:
                profile = TaxpayerProfile(
                    mst="0101234567",
                    company_name="MISA Test",
                    gdt_username="misa_test",
                    gdt_password_encrypted="dummy",
                    is_active=True,
                    created_at="2026-05-28"
                )
                db.session.add(profile)
                db.session.commit()

            # Ensure clean database & clean archive first
            Invoice.query.filter(Invoice.id.like("ARCHIVE-%")).delete()
            db.session.commit()
            
            archive_path = "data/archives/cold_invoices.zip"
            if os.path.exists(archive_path):
                try:
                    os.remove(archive_path)
                except Exception:
                    pass

            # 1. Create one active invoice (recent date: 2026)
            active_inv = Invoice(
                id="ARCHIVE-ACTIVE-1",
                date="2026-05-10",
                amount_before_tax=1000000.0,
                tax_amount=100000.0,
                total_amount=1100000.0,
                imported_at="2026-05-28",
                taxpayer_mst="0101234567",
                buyer_mst="0101234567"
            )
            db.session.add(active_inv)
            
            # 2. Create one historical invoice (older than 5 years: e.g. 2020)
            historical_inv = Invoice(
                id="ARCHIVE-COLD-1",
                date="2020-03-15",
                amount_before_tax=5000000.0,
                tax_amount=500000.0,
                total_amount=5500000.0,
                imported_at="2026-05-28",
                taxpayer_mst="0101234567",
                buyer_mst="0101234567"
            )
            db.session.add(historical_inv)
            
            # Create a line item for historical invoice
            hist_item = LineItem(
                invoice_id="ARCHIVE-COLD-1",
                item_name="Laptop cu",
                quantity=1.0,
                unit_price=5000000.0,
                amount_before_tax=5000000.0,
                tax_rate="10%",
                tax_amount=500000.0
            )
            db.session.add(hist_item)
            db.session.commit()

            # Verify both are in database
            assert Invoice.query.filter_by(id="ARCHIVE-ACTIVE-1").first() is not None
            assert Invoice.query.filter_by(id="ARCHIVE-COLD-1").first() is not None

            # Run archiving with reference date in 2026 (5 years cutoff -> 2021 cutoff)
            archived_count = InvoiceArchiver.archive_old_invoices(
                retention_years=5,
                reference_date=date(2026, 5, 29)
            )
            
            # Verify only 1 invoice (the 2020 one) is archived
            assert archived_count == 1
            
            # Verify historical invoice is deleted from live SQLite
            assert Invoice.query.filter_by(id="ARCHIVE-COLD-1").first() is None
            
            # Verify active invoice remains in live SQLite
            assert Invoice.query.filter_by(id="ARCHIVE-ACTIVE-1").first() is not None
            
            # Verify zip archive exists and contains invoices.json
            assert os.path.exists(archive_path)
            with zipfile.ZipFile(archive_path, "r") as zf:
                assert "invoices.json" in zf.namelist()
                
            # Perform merged query across active and cold archived datasets
            merged_results = InvoiceArchiver.search_merged_invoices(
                date_from=date(2020, 1, 1),
                date_to=date(2026, 12, 31),
                taxpayer_mst="0101234567"
            )
            
            # Both the active invoice and historical archived invoice should return!
            assert len(merged_results) >= 2
            ids = [inv["id"] for inv in merged_results]
            assert "ARCHIVE-ACTIVE-1" in ids
            assert "ARCHIVE-COLD-1" in ids
            
            # Verify historical line items are preserved in the merged return
            cold_record = next(inv for inv in merged_results if inv["id"] == "ARCHIVE-COLD-1")
            assert len(cold_record["items"]) == 1
            assert cold_record["items"][0]["item_name"] == "Laptop cu"

            # Clean up
            Invoice.query.filter(Invoice.id.like("ARCHIVE-%")).delete()
            db.session.commit()
            if os.path.exists(archive_path):
                try:
                    os.remove(archive_path)
                except Exception:
                    pass
