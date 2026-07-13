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
        txns = engine.process_csv(test_csv_content, "0123456789")
        
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
        engine.process_csv(test_csv_content, "0123456789")
        
        results = engine.run_matching("0123456789")
        
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

def test_reconciliation_fuzzy_matching(app):
    from extensions import db
    from invoices.models import TaxpayerProfile
    
    with app.app_context():
        # Setup taxpayer
        tp = TaxpayerProfile(
            mst="0123456789", 
            company_name="Test Fuzzy", 
            gdt_username="admin",
            gdt_password_encrypted="encrypted",
            created_at=datetime.now().isoformat()
        )
        db.session.add(tp)
        db.session.flush()

        # Create invoice with slightly different name
        inv = Invoice(
            id=str(uuid.uuid4()),
            taxpayer_mst="0123456789",
            number="0002222",
            invoice_type="purchase",
            seller_name="CONG TY CO PHAN CONG NGHE FPT",
            total_amount=15000000,
            date="2026-05-10",
            imported_at=datetime.now().isoformat()
        )
        db.session.add(inv)
        
        # Transaction with fuzzy matching name & description
        txn = BankTransaction(
            id=str(uuid.uuid4()),
            taxpayer_mst="0123456789",
            bank_name="Vietcombank",
            transaction_date="2026-05-11",
            description="CK thanh toan hoa don 0002222 Cty FPT Tech",
            amount=15000000,
            status="unreconciled",
            imported_at=datetime.now().isoformat()
        )
        db.session.add(txn)
        db.session.commit()

        engine = ReconciliationEngine()
        results = engine.run_matching("0123456789")
        
        assert results["matches_found"] == 1
        
        # Verify matched
        updated_txn = BankTransaction.query.get(txn.id)
        assert updated_txn.matched_invoice_id == inv.id
        assert updated_txn.status == "matched"

def test_reconciliation_many_to_1(app):
    from extensions import db
    
    with app.app_context():
        # Clear previous
        Invoice.query.delete()
        BankTransaction.query.delete()
        db.session.commit()

        # Create one large invoice
        inv = Invoice(
            id=str(uuid.uuid4()),
            taxpayer_mst="0123456789",
            number="0003333",
            invoice_type="purchase",
            seller_name="Nha Cung Cap A",
            total_amount=30000000,
            date="2026-05-10",
            imported_at=datetime.now().isoformat()
        )
        db.session.add(inv)

        # Create two smaller transactions summing up to the invoice amount
        txn1 = BankTransaction(
            id=str(uuid.uuid4()),
            taxpayer_mst="0123456789",
            bank_name="Vietcombank",
            transaction_date="2026-05-11",
            description="Dat coc dot 1 hoa don 0003333",
            amount=10000000,
            status="unreconciled",
            imported_at=datetime.now().isoformat()
        )
        txn2 = BankTransaction(
            id=str(uuid.uuid4()),
            taxpayer_mst="0123456789",
            bank_name="Vietcombank",
            transaction_date="2026-05-12",
            description="Thanh toan dot 2 hoa don 0003333",
            amount=20000000,
            status="unreconciled",
            imported_at=datetime.now().isoformat()
        )
        db.session.add(txn1)
        db.session.add(txn2)
        db.session.commit()

        engine = ReconciliationEngine()
        results = engine.run_matching("0123456789")
        
        assert results["matches_found"] == 2
        
        # Both transactions should be matched to the same invoice
        t1 = BankTransaction.query.get(txn1.id)
        t2 = BankTransaction.query.get(txn2.id)
        assert t1.matched_invoice_id == inv.id
        assert t2.matched_invoice_id == inv.id
        assert t1.status == "matched"
        assert t2.status == "matched"

def test_reconciliation_1_to_many_split(app):
    from extensions import db
    
    with app.app_context():
        # Clear previous
        Invoice.query.delete()
        BankTransaction.query.delete()
        db.session.commit()

        # Create two invoices
        inv1 = Invoice(
            id=str(uuid.uuid4()),
            taxpayer_mst="0123456789",
            number="0004441",
            invoice_type="purchase",
            seller_name="Nha Cung Cap B",
            total_amount=12000000,
            date="2026-05-10",
            imported_at=datetime.now().isoformat()
        )
        inv2 = Invoice(
            id=str(uuid.uuid4()),
            taxpayer_mst="0123456789",
            number="0004442",
            invoice_type="purchase",
            seller_name="Nha Cung Cap B",
            total_amount=8000000,
            date="2026-05-10",
            imported_at=datetime.now().isoformat()
        )
        db.session.add(inv1)
        db.session.add(inv2)

        # Create one large transaction covering both invoices
        txn = BankTransaction(
            id=str(uuid.uuid4()),
            taxpayer_mst="0123456789",
            bank_name="Vietcombank",
            transaction_date="2026-05-12",
            description="Thanh toan gop hai hoa don 0004441 va 0004442",
            amount=20000000,
            status="unreconciled",
            imported_at=datetime.now().isoformat()
        )
        db.session.add(txn)
        db.session.commit()

        engine = ReconciliationEngine()
        results = engine.run_matching("0123456789")
        
        # Matches found should be 2 (one for inv1, one for inv2)
        assert results["matches_found"] == 2

        # The original transaction should be updated to match inv1 (amount = 12000000)
        t_orig = BankTransaction.query.get(txn.id)
        assert t_orig.matched_invoice_id == inv1.id
        assert t_orig.amount == 12000000
        assert t_orig.status == "matched"

        # There should be a new child transaction created for inv2 (amount = 8000000)
        t_child = BankTransaction.query.filter_by(
            matched_invoice_id=inv2.id
        ).first()
        assert t_child is not None
        assert t_child.amount == 8000000
        assert t_child.status == "matched"
        assert "(Tách đối chiếu)" in t_child.description

def test_reconciliation_vietnamese_accents(app):
    from extensions import db
    
    with app.app_context():
        Invoice.query.delete()
        BankTransaction.query.delete()
        db.session.commit()

        inv = Invoice(
            id=str(uuid.uuid4()),
            taxpayer_mst="0123456789",
            number="0005555",
            invoice_type="purchase",
            seller_name="CÔNG TY TNHH BÁCH HÓA XANH",
            total_amount=15000000,
            date="2026-05-10",
            imported_at=datetime.now().isoformat()
        )
        db.session.add(inv)
        
        txn = BankTransaction(
            id=str(uuid.uuid4()),
            taxpayer_mst="0123456789",
            bank_name="Vietcombank",
            transaction_date="2026-05-11",
            description="Thanh toan hoa don cho Cty Bach Hoa Xanh",
            amount=15000000,
            status="unreconciled",
            imported_at=datetime.now().isoformat()
        )
        db.session.add(txn)
        db.session.commit()

        engine = ReconciliationEngine()
        results = engine.run_matching("0123456789")
        
        assert results["matches_found"] == 1
        
        updated_txn = BankTransaction.query.get(txn.id)
        assert updated_txn.matched_invoice_id == inv.id
        assert updated_txn.status == "matched"

def test_reconciliation_1_to_many_date_proximity(app):
    from extensions import db
    
    with app.app_context():
        Invoice.query.delete()
        BankTransaction.query.delete()
        db.session.commit()

        inv1 = Invoice(
            id=str(uuid.uuid4()),
            taxpayer_mst="0123456789",
            number="0006661",
            invoice_type="purchase",
            seller_name="Nha Cung Cap C",
            total_amount=12000000,
            date="2026-01-10",
            imported_at=datetime.now().isoformat()
        )
        inv2 = Invoice(
            id=str(uuid.uuid4()),
            taxpayer_mst="0123456789",
            number="0006662",
            invoice_type="purchase",
            seller_name="Nha Cung Cap C",
            total_amount=8000000,
            date="2026-01-10",
            imported_at=datetime.now().isoformat()
        )
        db.session.add(inv1)
        db.session.add(inv2)

        txn = BankTransaction(
            id=str(uuid.uuid4()),
            taxpayer_mst="0123456789",
            bank_name="Vietcombank",
            transaction_date="2026-05-12",
            description="Thanh toan gop hai hoa don 0006661 va 0006662",
            amount=20000000,
            status="unreconciled",
            imported_at=datetime.now().isoformat()
        )
        db.session.add(txn)
        db.session.commit()

        engine = ReconciliationEngine()
        results = engine.run_matching("0123456789")
        
        assert results["matches_found"] == 0




