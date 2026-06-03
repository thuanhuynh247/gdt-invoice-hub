import pytest
from datetime import datetime, date, timedelta
import uuid
from extensions import db
from invoices.models import Invoice, TaxpayerProfile, BankTransaction

@pytest.fixture
def setup_taxpayer(app):
    with app.app_context():
        # Clear existing data to prevent integrity issues
        Invoice.query.delete()
        BankTransaction.query.delete()
        TaxpayerProfile.query.delete()
        db.session.commit()

        tp = TaxpayerProfile(
            mst="0109998887",
            company_name="Công Ty Toàn Cầu",
            gdt_username="toancau_gdt",
            gdt_password_encrypted="encrypted_pwd",
            created_at=datetime.now().isoformat()
        )
        db.session.add(tp)
        db.session.commit()
        return tp

def test_ar_ap_aging_buckets(app, logged_in_client, setup_taxpayer):
    with app.app_context():
        as_of = date.today()
        
        # 1. Outstanding Sales Invoice (Receivable) - 15 days overdue
        inv_ar_1 = Invoice(
            id=str(uuid.uuid4()),
            taxpayer_mst="0109998887",
            number="HD-1001",
            invoice_type="sold",
            buyer_name="Khách Hàng A",
            buyer_mst="0101010101",
            total_amount=150000000.0,
            amount_before_tax=136363636.0,
            date=(as_of - timedelta(days=20)).isoformat(),
            due_date=(as_of - timedelta(days=15)).isoformat(),
            is_cancelled=False,
            paid_date=None,
            imported_at=datetime.now().isoformat()
        )

        # 2. Outstanding Sales Invoice (Receivable) - Current (Not overdue)
        inv_ar_2 = Invoice(
            id=str(uuid.uuid4()),
            taxpayer_mst="0109998887",
            number="HD-1002",
            invoice_type="sold",
            buyer_name="Khách Hàng B",
            buyer_mst="0102020202",
            total_amount=300000000.0,
            amount_before_tax=272727272.0,
            date=as_of.isoformat(),
            due_date=(as_of + timedelta(days=10)).isoformat(),
            is_cancelled=False,
            paid_date=None,
            imported_at=datetime.now().isoformat()
        )

        # 3. Outstanding Purchase Invoice (Payable) - 45 days overdue
        inv_ap_1 = Invoice(
            id=str(uuid.uuid4()),
            taxpayer_mst="0109998887",
            number="HD-2001",
            invoice_type="bought",
            seller_name="Công Ty Điện Lực",
            seller_mst="0199999999",
            total_amount=80000000.0,
            amount_before_tax=72727272.0,
            date=(as_of - timedelta(days=50)).isoformat(),
            due_date=(as_of - timedelta(days=45)).isoformat(),
            is_cancelled=False,
            paid_date=None,
            imported_at=datetime.now().isoformat()
        )

        db.session.add_all([inv_ar_1, inv_ar_2, inv_ap_1])
        db.session.commit()

    # Simulate log in session or pass mst in request
    response = logged_in_client.get("/api/aging/summary?mst=0109998887")
    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    
    # Backwards compatibility check
    assert "buckets" in data
    assert len(data["buckets"]) == 4  # 1-30, 31-60, 61-90, >90

    # Receivables (AR) verification
    receivables = data["receivables"]
    assert receivables["total_amount"] == 450000000.0
    assert receivables["total_count"] == 2
    
    # Receivables buckets validation:
    # ar_buckets[0] is "Chưa quá hạn (Current)" -> HD-1002 (300,000,000)
    # ar_buckets[1] is "1-30 ngày" -> HD-1001 (150,000,000)
    ar_buckets = receivables["buckets"]
    assert ar_buckets
    assert ar_buckets[0]["total_amount"] == 300000000.0
    assert ar_buckets[1]["total_amount"] == 150000000.0

    # Payables (AP) verification
    payables = data["payables"]
    assert payables["total_amount"] == 80000000.0
    assert payables["total_count"] == 1
    
    # ap_buckets[2] is "31–60 ngày" -> HD-2001 (80,000,000)
    ap_buckets = payables["buckets"]
    assert ap_buckets
    assert ap_buckets[2]["total_amount"] == 80000000.0
    
    # Confirm AI categorization did OPEX and UTILITIES
    assert ap_buckets[2]["invoices"][0]["ai_category"] == "UTILITIES"

def test_cashflow_projection_forecast(app, logged_in_client, setup_taxpayer):
    with app.app_context():
        as_of = date.today()

        # Add a starting bank transaction
        tx = BankTransaction(
            id="TX-START-01",
            taxpayer_mst="0109998887",
            bank_name="Vietcombank",
            account_number="123456",
            transaction_date=as_of.isoformat(),
            reference_number="REF-001",
            description="Số dư ban đầu",
            amount=200000000.0,
            status="unreconciled",
            imported_at=datetime.now().isoformat()
        )
        db.session.add(tx)
        db.session.commit()

    response = logged_in_client.get("/api/cashflow/projection?mst=0109998887")
    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["base_balance"] == 200000000.0
    
    projections = data["projections"]
    assert len(projections) == 91
    # Starting projection balance matches base_balance
    assert projections[0]["balance_opt"] == 200000000.0
    assert projections[0]["balance_sim"] == 200000000.0

def test_what_if_late_payment_simulation(app, logged_in_client, setup_taxpayer):
    with app.app_context():
        as_of = date.today()

        # 10,000,000 VND receivable due in 5 days
        inv = Invoice(
            id=str(uuid.uuid4()),
            taxpayer_mst="0109998887",
            number="HD-DELAY",
            invoice_type="sold",
            buyer_name="Khách Hàng Trễ Hạn",
            buyer_mst="0108888888",
            total_amount=10000000.0,
            amount_before_tax=9090909.0,
            date=as_of.isoformat(),
            due_date=(as_of + timedelta(days=5)).isoformat(),
            is_cancelled=False,
            paid_date=None,
            imported_at=datetime.now().isoformat()
        )
        db.session.add(inv)
        db.session.commit()

    # Trigger with 10 days late simulation
    response = logged_in_client.get("/api/cashflow/projection?mst=0109998887&late_days=10&base_balance=100000000")
    data = response.get_json()

    assert response.status_code == 200
    assert data["success"] is True
    assert data["base_balance"] == 100000000.0

    projections = data["projections"]
    
    # In optimistic flow (no delays), cash should be collected at Day 5
    # In simulated flow (10 days delay), cash should be collected at Day 15
    
    # Day 5 verification
    day_5_proj = next(p for p in projections if p["date"] == (as_of + timedelta(days=5)).isoformat())
    assert day_5_proj["balance_opt"] == 110000000.0
    assert day_5_proj["balance_sim"] == 100000000.0

    # Day 15 verification
    day_15_proj = next(p for p in projections if p["date"] == (as_of + timedelta(days=15)).isoformat())
    assert day_15_proj["balance_opt"] == 110000000.0
    assert day_15_proj["balance_sim"] == 110000000.0
