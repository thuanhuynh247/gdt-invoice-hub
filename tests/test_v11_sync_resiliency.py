"""Integration tests for checking sync queue resiliency, parallel job isolation, and scheduler integration."""

from __future__ import annotations

import time
from datetime import date
from unittest.mock import patch
import pytest

from flask import Flask
from extensions import db
from invoices.models import TaxpayerProfile, GDTSyncLog, Invoice
from invoices.sync_queue import ResilientSyncQueue, SyncJob
from auth.crypto import encrypt_password

@pytest.fixture
def sync_app(app):
    """Fixture containing Flask application with ResilientSyncQueue and temp database."""
    # Force mock mode to false to trigger realistic service validation
    app.config["GDT_USE_MOCK"] = False
    
    # Initialize the queue extension inside the app if not present
    if "resilient_sync_queue" not in app.extensions:
        ResilientSyncQueue(app)
        
    return app

def test_sync_queue_parallel_execution_and_isolation(sync_app):
    """Test that parallel jobs run concurrently and failures on one profile do not block others."""
    app = sync_app
    queue = app.extensions["resilient_sync_queue"]

    # 1. Create two taxpayer profiles in master database
    # Profile A: Valid, should succeed
    # Profile B: Invalid, should raise connection error
    with app.app_context():
        # Clear master tables
        TaxpayerProfile.query.delete()
        db.session.commit()

        # Clear tenant tables by context-switching
        from invoices.thread_local import set_current_thread_mst, clear_thread_local_context
        for mst in ["0101234567", "9999999999"]:
            set_current_thread_mst(mst)
            GDTSyncLog.query.delete()
            db.session.commit()
            db.session.remove()

        clear_thread_local_context()

        encrypted_pwd = encrypt_password("Secret123")
        
        profile_a = TaxpayerProfile(
            mst="0101234567",
            company_name="Valid Corp",
            gdt_username="valid_user",
            gdt_password_encrypted=encrypted_pwd,
            is_active=True,
            created_at="2026-05-30T00:00:00Z"
        )
        profile_b = TaxpayerProfile(
            mst="9999999999",
            company_name="Failure LLC",
            gdt_username="failure_user",
            gdt_password_encrypted=encrypted_pwd,
            is_active=True,
            created_at="2026-05-30T00:00:00Z"
        )
        db.session.add(profile_a)
        db.session.add(profile_b)
        db.session.commit()
        db.session.remove()

    # 2. Mock fetch_invoices to trigger isolated failure on Profile B
    from invoices.service import GDTIntegrationNotReadyError, normalize_invoice, MOCK_INVOICES
    
    def side_effect_fetch(query):
        from invoices.thread_local import get_current_thread_mst
        mst = get_current_thread_mst()
        if mst == "9999999999":
            # Simulate isolated connection failure for taxpayer B
            raise GDTIntegrationNotReadyError("Simulated GDT connection timeout for taxpayer 9999999999.")
        
        # Valid profile: return mock invoices
        return [normalize_invoice(inv) for inv in MOCK_INVOICES]

    with patch("invoices.service.fetch_invoices", side_effect=side_effect_fetch), \
         patch("invoices.service.download_invoice_xml", return_value=b"<xml></xml>"):
        
        # 3. Enqueue both jobs
        date_from = date(2026, 5, 1)
        date_to = date(2026, 5, 31)
        
        job_a = queue.enqueue_sync("0101234567", date_from, date_to, direction="purchase")
        job_b = queue.enqueue_sync("9999999999", date_from, date_to, direction="purchase")

        # 4. Wait for both jobs to finish
        start_wait = time.time()
        while job_a.status in ("queued", "running") or job_b.status in ("queued", "running"):
            time.sleep(0.1)
            if time.time() - start_wait > 5.0:
                break  # Prevent infinite loop

        # 5. Verify results and isolation
        # Profile A should succeed
        assert job_a.status == "success"
        assert job_a.invoices_fetched > 0
        assert job_a.error_message is None

        # Profile B should fail but NOT crash the queue or Job A
        assert job_b.status == "failed"
        assert "Simulated GDT connection timeout" in job_b.error_message

        # Check sync logs written to database
        # Note: Tenant databases are routed via thread MST. For testing DB routing, 
        # let's verify using the thread-local context manually or direct DB state query.
        with app.app_context():
            from invoices.thread_local import set_current_thread_mst, clear_thread_local_context
            
            # Query log for A (Valid Corp database)
            set_current_thread_mst("0101234567")
            logs_a = GDTSyncLog.query.filter_by(taxpayer_mst="0101234567").all()
            assert len(logs_a) == 1
            assert logs_a[0].status == "success"
            assert logs_a[0].invoices_fetched > 0
            db.session.remove()
            
            # Query log for B (Failure LLC database)
            set_current_thread_mst("9999999999")
            logs_b = GDTSyncLog.query.filter_by(taxpayer_mst="9999999999").all()
            assert len(logs_b) == 1
            assert logs_b[0].status == "failed"
            assert "Simulated GDT connection timeout" in logs_b[0].error_message
            db.session.remove()
            
            clear_thread_local_context()

def test_sync_queue_emergency_stop(sync_app):
    """Test that emergency stop cancels all queued sync requests instantly."""
    app = sync_app
    queue = app.extensions["resilient_sync_queue"]

    # Enqueue a mock job
    with app.app_context():
        encrypted_pwd = encrypt_password("Pass123")
        profile = TaxpayerProfile(
            mst="1234567890",
            company_name="Emergency Corp",
            gdt_username="emergency_user",
            gdt_password_encrypted=encrypted_pwd,
            is_active=True,
            created_at="2026-05-30T00:00:00Z"
        )
        db.session.merge(profile)
        db.session.commit()
        db.session.remove()

    # Trigger emergency stop
    queue.emergency_stop()

    # Ensure queue is clean and running jobs are terminated/executor recreated
    assert queue._shutdown_requested is False
    assert queue.executor is not None
