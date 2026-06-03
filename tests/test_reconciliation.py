import pytest
from datetime import datetime, timedelta
import uuid

from invoices.models import Invoice, BankTransaction, AIAuditResult
from invoices.reconciliation_service import ReconciliationEngine

@pytest.fixture
def test_csv_content():
    return """Ngày giao dịch,Nội dung,Số tiền
2026-05-10,Thanh toan cong ty TNHH VNG cho hoa don 0001234,25000000
2026-05-11,CK tra tien dien thang 5,-500000
2026-05-12,Thanh toan tien nha cung cap Cong ty CP ABC,100000000
"""

def test_reconciliation_engine_process_csv(app, test_csv_content):
    with app.app_context():
        engine = ReconciliationEngine()
        txns = engine.process_csv(test_csv_content)
        
        assert len(txns) == 3
        
        # Verify DB insertion
        db_txns = BankTransaction.query.all()
        assert len(db_txns) == 3
        assert db_txns[0].amount == 25000000
        assert db_txns[1].amount == -500000
        assert db_txns[2].amount == 100000000

def test_reconciliation_engine_matching(app, test_csv_content):
    from extensions import db
    from invoices.models import TaxpayerProfile
    
    with app.app_context():
        tp = TaxpayerProfile(
            mst="0123456789", 
            company_name="Test", 
            gdt_username="admin",
            gdt_password_encrypted="encrypted",
            created_at=datetime.now().isoformat()
        )
        db.session.add(tp)
        db.session.flush()

        # Create an invoice that perfectly matches transaction 1 (amount = 25000000, keyword match)
        inv1 = Invoice(
            id=str(uuid.uuid4()),
            taxpayer_mst="0123456789",
            number="0001234",
            invoice_type="purchase",
            seller_name="Công ty TNHH VNG",
            total_amount=25000000,
            date="2026-05-09",
            imported_at=datetime.now().isoformat()
        )
        
        # Create an invoice that doesn't match any transaction but is over 20M (should be flagged)
        inv2 = Invoice(
            id=str(uuid.uuid4()),
            taxpayer_mst="0123456789",
            number="0009999",
            invoice_type="purchase",
            seller_name="Công ty TNHH FPT",
            total_amount=50000000,
            date="2026-05-01",
            imported_at=datetime.now().isoformat()
        )
        
        db.session.add(inv1)
        db.session.add(inv2)
        db.session.commit()
        
        # Run process
        engine = ReconciliationEngine()
        engine.process_csv(test_csv_content)
        
        results = engine.run_matching()
        
        assert results["transactions_processed"] == 3
        assert results["matches_found"] == 1
        assert results["invoices_flagged_risk"] == 1
        
        # Verify matched transaction
        txn_matched = BankTransaction.query.filter_by(matched_invoice_id=inv1.id).first()
        assert txn_matched is not None
        assert txn_matched.amount == 25000000
        assert txn_matched.confidence_score >= 0.5
        
        # Verify audit result for inv2
        warning = AIAuditResult.query.filter_by(invoice_id=inv2.id, warning_type="cash_payment_risk").first()
        assert warning is not None

def test_api_reconciliation_upload_unauthorized(client):
    response = client.post("/api/reconciliation/upload")
    assert response.status_code == 401

def test_api_reconciliation_results_unauthorized(client):
    response = client.get("/api/reconciliation/results")
    assert response.status_code == 401
