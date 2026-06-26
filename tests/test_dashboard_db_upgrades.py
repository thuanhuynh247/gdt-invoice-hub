import pytest
import sqlite3
from sqlalchemy import text
from extensions import db
from invoices.models import Invoice, BankTransaction, LineItem
from auth.crypto import encrypt_password
from datetime import datetime, timezone
import uuid

def test_sqlite_wal_mode_and_indexes(app):
    """Test that SQLite WAL mode is enabled and indexes are created successfully."""
    from invoices.thread_local import set_current_thread_mst, clear_thread_local_context
    with app.app_context():
        set_current_thread_mst("0102030499")
        try:
            # Get active connection
            connection = db.session.connection()
            dbapi_conn = connection.connection.dbapi_connection
            
            # Verify WAL mode
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode")
            journal_mode = cursor.fetchone()[0]
            assert journal_mode.lower() == "wal"
            
            # Check index existence in the schema
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = [row[0] for row in cursor.fetchall()]
            
            assert "idx_invoice_lookup" in indexes
            assert "idx_line_item_invoice" in indexes
            assert "idx_bank_trans_lookup" in indexes
            cursor.close()
        finally:
            clear_thread_local_context()

def test_api_invoice_trends(logged_in_client, app):
    """Test that the trends API /api/invoices/trends returns the correct aggregated sales and purchases."""
    mst = "0102030499"
    with logged_in_client.session_transaction() as sess:
        sess["active_taxpayer_mst"] = mst
        sess["tax_code"] = mst

    from invoices.thread_local import set_current_thread_mst, clear_thread_local_context
    with app.app_context():
        set_current_thread_mst(mst)
        try:
            # Clean up
            Invoice.query.filter_by(taxpayer_mst=mst).delete()
            db.session.commit()

            # Add mock invoices (sale and purchase)
            inv_sale = Invoice(
                id=str(uuid.uuid4()),
                taxpayer_mst=mst,
                number="101",
                invoice_type="sold",
                seller_mst=mst,
                total_amount=10000000.0,
                date="2026-05-15",
                is_cancelled=False,
                imported_at=datetime.now(timezone.utc).isoformat()
            )
            inv_purchase = Invoice(
                id=str(uuid.uuid4()),
                taxpayer_mst=mst,
                number="201",
                invoice_type="purchase",
                buyer_mst=mst,
                total_amount=5000000.0,
                date="2026-05-20",
                is_cancelled=False,
                imported_at=datetime.now(timezone.utc).isoformat()
            )
            db.session.add(inv_sale)
            db.session.add(inv_purchase)
            db.session.commit()
        finally:
            clear_thread_local_context()

    resp = logged_in_client.get("/api/invoices/trends")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    
    trends = data["data"]
    assert len(trends) > 0
    # Month should be 2026-05
    may_trend = [t for t in trends if t["month"] == "2026-05"]
    assert len(may_trend) == 1
    assert may_trend[0]["sales"] == 10000000.0
    assert may_trend[0]["purchases"] == 5000000.0

def test_api_reconcile_auto_endpoint(logged_in_client, app):
    """Test automated matching via post endpoint /api/invoices/reconcile/auto."""
    mst = "0102030499"
    with logged_in_client.session_transaction() as sess:
        sess["active_taxpayer_mst"] = mst
        sess["tax_code"] = mst

    from invoices.thread_local import set_current_thread_mst, clear_thread_local_context
    with app.app_context():
        set_current_thread_mst(mst)
        try:
            # Clear data
            BankTransaction.query.filter_by(taxpayer_mst=mst).delete()
            Invoice.query.filter_by(taxpayer_mst=mst).delete()
            db.session.commit()

            # Insert transaction
            txn = BankTransaction(
                id="TXN-999",
                taxpayer_mst=mst,
                bank_name="Vietcombank",
                transaction_date="2026-05-10",
                description="CK thanh toan cho HĐ 888",
                amount=30000000.0,
                status="unreconciled",
                imported_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            # Insert invoice
            inv = Invoice(
                id="INV-888",
                taxpayer_mst=mst,
                number="888",
                invoice_type="purchase",
                seller_mst="0999888777",
                total_amount=30000000.0,
                date="2026-05-09",
                imported_at=datetime.now(timezone.utc).isoformat()
            )
            db.session.add(txn)
            db.session.add(inv)
            db.session.commit()
        finally:
            clear_thread_local_context()

    resp = logged_in_client.post("/api/invoices/reconcile/auto")
    assert resp.status_code == 200
    res_data = resp.get_json()
    assert res_data["status"] == "success"
    assert res_data["results"]["matches_found"] == 1

    with app.app_context():
        set_current_thread_mst(mst)
        try:
            updated_txn = BankTransaction.query.get("TXN-999")
            assert updated_txn.status == "matched"
            assert updated_txn.matched_invoice_id == "INV-888"
        finally:
            clear_thread_local_context()

def test_api_reconcile_manual_endpoint(logged_in_client, app):
    """Test manual matching via post endpoint /api/invoices/reconcile/manual."""
    mst = "0102030499"
    with logged_in_client.session_transaction() as sess:
        sess["active_taxpayer_mst"] = mst
        sess["tax_code"] = mst

    from invoices.thread_local import set_current_thread_mst, clear_thread_local_context
    with app.app_context():
        set_current_thread_mst(mst)
        try:
            # Clear data
            BankTransaction.query.filter_by(taxpayer_mst=mst).delete()
            Invoice.query.filter_by(taxpayer_mst=mst).delete()
            db.session.commit()

            # Insert transaction
            txn = BankTransaction(
                id="TXN-777",
                taxpayer_mst=mst,
                bank_name="Vietcombank",
                transaction_date="2026-05-12",
                description="CK thanh toan thu cong",
                amount=15000000.0,
                status="unreconciled",
                imported_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            # Insert invoice
            inv = Invoice(
                id="INV-555",
                taxpayer_mst=mst,
                number="555",
                invoice_type="purchase",
                seller_mst="0999888777",
                total_amount=15000000.0,
                date="2026-05-01",
                imported_at=datetime.now(timezone.utc).isoformat()
            )
            db.session.add(txn)
            db.session.add(inv)
            db.session.commit()
        finally:
            clear_thread_local_context()

    resp = logged_in_client.post(
        "/api/invoices/reconcile/manual",
        json={"transaction_id": "TXN-777", "invoice_id": "INV-555"}
    )
    assert resp.status_code == 200
    res_data = resp.get_json()
    assert res_data["status"] == "success"

    with app.app_context():
        set_current_thread_mst(mst)
        try:
            updated_txn = BankTransaction.query.get("TXN-777")
            assert updated_txn.status == "matched"
            assert updated_txn.matched_invoice_id == "INV-555"
        finally:
            clear_thread_local_context()
