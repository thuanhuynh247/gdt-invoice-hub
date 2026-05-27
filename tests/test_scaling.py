"""
Scaling, Performance, and Multi-tenant Isolation tests.
Verifies SQLite WAL Mode concurrent read/write performance and MST data separation/isolation.
"""

from __future__ import annotations

import threading
import time
import pytest
from extensions import db
from invoices.models import Invoice, LineItem


def test_sqlite_wal_concurrency(app):
    """Verify that concurrent read and write operations do not lock the SQLite database under WAL mode."""
    num_threads = 5
    barrier = threading.Barrier(num_threads * 2)
    exceptions = []

    def reader_target():
        # Wait for all threads to align
        barrier.wait()
        try:
            with app.app_context():
                for _ in range(50):
                    # Perform reads
                    invoices = Invoice.query.all()
                    _ = [inv.id for inv in invoices]
                    time.sleep(0.01)
        except Exception as e:
            exceptions.append(f"Reader error: {e}")

    def writer_target(thread_id: int):
        barrier.wait()
        try:
            with app.app_context():
                for i in range(10):
                    # Perform inserts/updates
                    inv_id = f"CONCURRENT-INV-{thread_id}-{i}"
                    inv = Invoice(
                        id=inv_id,
                        number=f"C-{thread_id}-{i}",
                        date="2026-05-25",
                        seller_name=f"Concurrent Seller {thread_id}",
                        seller_mst=f"MST-{thread_id}",
                        total_amount=100.0,
                        imported_at="2026-05-25 12:00:00"
                    )
                    db.session.add(inv)
                    db.session.commit()
                    
                    # Read back and delete
                    refetched = db.session.get(Invoice, inv_id)
                    if refetched:
                        db.session.delete(refetched)
                        db.session.commit()
                        
                    time.sleep(0.01)
        except Exception as e:
            exceptions.append(f"Writer error: {e}")

    threads = []
    # Create 5 readers and 5 writers
    for i in range(num_threads):
        threads.append(threading.Thread(target=reader_target))
        threads.append(threading.Thread(target=writer_target, args=(i,)))

    for t in threads:
        t.start()

    for t in threads:
        t.join()

    # Assert no exceptions occurred during concurrent read/write (database is locked checks)
    assert len(exceptions) == 0, f"Concurrency exceptions encountered: {exceptions}"


def test_multi_tenant_mst_isolation(app):
    """Verify data isolation and separation across different seller and buyer MSTs."""
    with app.app_context():
        # Clear existing
        Invoice.query.delete()
        db.session.commit()

        # Seed two different sellers (multi-tenant simulation)
        inv1 = Invoice(
            id="MST-SELLER-A-001",
            number="101",
            date="2026-05-25",
            seller_name="Công ty Cổ phần A",
            seller_mst="111111111",
            buyer_name="Công ty Mua Chung",
            buyer_mst="999999999",
            total_amount=5000000.0,
            imported_at="2026-05-25 10:00:00"
        )
        inv2 = Invoice(
            id="MST-SELLER-B-001",
            number="102",
            date="2026-05-25",
            seller_name="Công ty Cổ phần B",
            seller_mst="222222222",
            buyer_name="Công ty Mua Chung",
            buyer_mst="999999999",
            total_amount=10000000.0,
            imported_at="2026-05-25 10:00:00"
        )
        db.session.add_all([inv1, inv2])
        db.session.commit()

        # Query filtered by Seller MST A
        invoices_a = Invoice.query.filter_by(seller_mst="111111111").all()
        assert len(invoices_a) == 1
        assert invoices_a[0].id == "MST-SELLER-A-001"

        # Query filtered by Seller MST B
        invoices_b = Invoice.query.filter_by(seller_mst="222222222").all()
        assert len(invoices_b) == 1
        assert invoices_b[0].id == "MST-SELLER-B-001"

        # Query filtered by Seller MST C (non-existent tenant)
        invoices_c = Invoice.query.filter_by(seller_mst="333333333").all()
        assert len(invoices_c) == 0

        # Clean up
        Invoice.query.delete()
        db.session.commit()
