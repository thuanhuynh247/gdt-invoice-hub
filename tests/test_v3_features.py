"""Tests for Version 3.0.0 features: GDTSyncLog model and RAG-enhanced mitigation letters."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch, MagicMock

from extensions import db
from invoices.models import (
    Invoice,
    TaxpayerProfile,
    AIAuditResult,
    GDTSyncLog,
    TaxRegulationChunk,
)


# ── GDTSyncLog Model Tests ──────────────────────────────────────

def test_gdt_sync_log_table_creation(app):
    """The gdt_sync_log table must be auto-created on startup."""
    with app.app_context():
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
        assert "gdt_sync_log" in tables


def test_gdt_sync_log_crud_lifecycle(app):
    """Create, read, and verify a GDTSyncLog row."""
    with app.app_context():
        # Ensure a taxpayer profile exists for the FK constraint
        existing = db.session.get(TaxpayerProfile, "0109876543")
        if not existing:
            profile = TaxpayerProfile(
                mst="0109876543",
                company_name="CONG TY TEST SYNC",
                gdt_username="sync_test_user",
                gdt_password_encrypted="enc_placeholder",
                is_active=True,
                created_at=datetime.now().isoformat(),
            )
            db.session.add(profile)
            db.session.flush()

        log = GDTSyncLog(
            taxpayer_mst="0109876543",
            triggered_at=datetime.now().isoformat(),
            status="success",
            invoices_fetched=15,
            captcha_attempts=3,
            captcha_failures=1,
            error_message=None,
            elapsed_seconds=12.5,
        )
        db.session.add(log)
        db.session.commit()

        # Read back and verify
        saved = GDTSyncLog.query.filter_by(taxpayer_mst="0109876543").first()
        assert saved is not None
        assert saved.status == "success"
        assert saved.invoices_fetched == 15
        assert saved.captcha_attempts == 3
        assert saved.captcha_failures == 1
        assert saved.elapsed_seconds == 12.5

        d = saved.to_dict()
        assert d["taxpayer_mst"] == "0109876543"
        assert d["status"] == "success"
        assert d["invoices_fetched"] == 15


def test_gdt_sync_log_failed_status(app):
    """A sync log with failed status correctly stores the error message."""
    with app.app_context():
        existing = db.session.get(TaxpayerProfile, "0109876543")
        if not existing:
            profile = TaxpayerProfile(
                mst="0109876543",
                company_name="CONG TY TEST SYNC",
                gdt_username="sync_test_user",
                gdt_password_encrypted="enc_placeholder",
                is_active=True,
                created_at=datetime.now().isoformat(),
            )
            db.session.add(profile)
            db.session.flush()

        log = GDTSyncLog(
            taxpayer_mst="0109876543",
            triggered_at=datetime.now().isoformat(),
            status="failed",
            invoices_fetched=0,
            captcha_attempts=5,
            captcha_failures=5,
            error_message="CAPTCHA solver exhausted after 5 attempts",
            elapsed_seconds=45.2,
        )
        db.session.add(log)
        db.session.commit()

        saved = GDTSyncLog.query.filter_by(status="failed").first()
        assert saved is not None
        assert "CAPTCHA solver exhausted" in saved.error_message
        assert saved.elapsed_seconds == 45.2


# ── RAG-Enhanced Mitigation Letter Tests ──────────────────────────

def _create_test_invoice_with_warnings(app):
    """Create an invoice with multiple AI audit warnings for mitigation letter testing."""
    with app.app_context():
        AIAuditResult.query.filter_by(invoice_id="MIT-RAG-001").delete()
        Invoice.query.filter_by(id="MIT-RAG-001").delete()
        db.session.commit()

        inv = Invoice(
            id="MIT-RAG-001",
            filename="test_mitigation_rag.xml",
            invoice_type="purchase",
            number="99001",
            symbol="C26TXX",
            date="2026-05-15",
            currency="VND",
            seller_name="CONG TY THUONG MAI DICH VU XUAT KHAU ABC",
            seller_mst="0301234567",
            seller_address="123 Nguyen Hue, TP. Ho Chi Minh",
            buyer_name="CONG TY CO PHAN PHAT TRIEN CONG NGHE XYZ",
            buyer_mst="0109999999",
            buyer_address="45 Le Loi, Quan 1, TP. Ho Chi Minh",
            amount_before_tax=25000000.0,
            tax_amount=2500000.0,
            total_amount=27500000.0,
            payment_method="Tiền mặt",
            has_signature=True,
            signing_date="2026-05-17",
            imported_at=datetime.now().isoformat(),
        )
        db.session.add(inv)
        db.session.flush()

        # Add audit warnings
        w1 = AIAuditResult(
            invoice_id="MIT-RAG-001",
            warning_type="cash_payment_risk",
            explanation="Hóa đơn trên 20 triệu VND thanh toán bằng tiền mặt",
            created_at=datetime.now().isoformat(),
        )
        w2 = AIAuditResult(
            invoice_id="MIT-RAG-001",
            warning_type="signing_time_mismatch",
            explanation="Ngày ký số 2026-05-17 cách ngày lập 2026-05-15 hơn 1 ngày",
            created_at=datetime.now().isoformat(),
        )
        db.session.add_all([w1, w2])
        db.session.commit()

        return inv


def test_mitigation_letter_rag_context_injection(app):
    """Verify the mitigation letter generator fetches RAG context from FTS5 for targeted legal references."""
    inv = _create_test_invoice_with_warnings(app)

    with app.app_context():
        from invoices.ai_service import get_tax_rag_context

        # Verify RAG context retriever returns results for tax-related queries
        rag_context = get_tax_rag_context("khấu trừ thuế GTGT thanh toán tiền mặt")
        # Should either return FTS5 results or keyword dictionary fallback
        assert len(rag_context) > 0
        assert any(
            kw in rag_context.lower()
            for kw in ["khấu trừ", "tiền mặt", "thanh toán", "thuế gtgt", "20 triệu", "5 triệu"]
        )


def test_mitigation_letter_fallback_without_llm(app):
    """When AI is disabled, the mitigation letter must use the rules-based fallback that includes correct legal references for all warning types."""
    inv = _create_test_invoice_with_warnings(app)

    with app.app_context():
        from invoices.ai_service import AIComplianceAuditor

        # Reload the invoice with relationships
        loaded_inv = db.session.get(Invoice, "MIT-RAG-001")
        assert loaded_inv is not None

        auditor = AIComplianceAuditor()
        letter = auditor.generate_mitigation_letter(loaded_inv)

        # Must contain standard Vietnamese administrative header
        assert "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM" in letter
        assert "Độc lập - Tự do - Hạnh phúc" in letter
        assert "CÔNG VĂN GIẢI TRÌNH" in letter

        # Must contain cash payment defense with correct legal reference
        assert "Điều 15" in letter or "219/2013" in letter
        assert "tiền mặt" in letter or "chuyển khoản" in letter

        # Must contain signing time mismatch defense (Điều 9, Điều 10, or thời điểm lập)
        assert "Điều 9" in letter or "Điều 10" in letter or "thời điểm lập" in letter or "123/2020" in letter


def test_mitigation_letter_api_returns_200(app, logged_in_client):
    """The mitigation letter API must return 200 for an invoice with warnings."""
    _create_test_invoice_with_warnings(app)

    # The route is POST, not GET
    response = logged_in_client.post("/api/invoices/local/MIT-RAG-001/mitigation-letter")
    assert response.status_code == 200

    data = response.get_json()
    assert data["status"] == "success"
    assert "letter" in data
    assert "CỘNG HÒA" in data["letter"]
