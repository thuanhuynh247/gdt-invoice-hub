import pytest
from unittest.mock import patch
import invoices.routes
from extensions import db
from invoices.models import Invoice, AIAuditResult

def create_mock_invoice():
    """Helper to insert a mock local invoice for testing."""
    inv = Invoice(
        id="test-mitigation-invoice-1",
        number="HD-MITIGATE",
        date="2026-05-25",
        seller_name="High Risk Seller Joint Stock Company",
        seller_mst="0101234599", # high-risk MST
        buyer_name="My Company LLC",
        buyer_mst="0504030201",
        total_amount=25000000, # cash limit check warning >= 20M
        payment_method="Tiền mặt",
        has_signature=True,
        t_score=40,
        t_rating="F",
        imported_at="2026-05-25 00:00:00"
    )
    db.session.add(inv)
    
    warning1 = AIAuditResult(
        invoice_id=inv.id,
        warning_type="cash_payment_risk",
        explanation="Thanh toán bằng tiền mặt cho giao dịch từ 20 triệu đồng trở lên không được khấu trừ thuế GTGT.",
        created_at="2026-05-25 10:00:00"
    )
    warning2 = AIAuditResult(
        invoice_id=inv.id,
        warning_type="suspicious_transaction",
        explanation="Nhà cung cấp thuộc danh sách doanh nghiệp rủi ro cao về thuế.",
        created_at="2026-05-25 10:00:00"
    )
    db.session.add_all([warning1, warning2])
    db.session.commit()
    return inv

def cleanup_mock_invoice():
    """Helper to remove the mock local invoice after test execution."""
    inv = db.session.get(Invoice, "test-mitigation-invoice-1")
    if inv:
        db.session.delete(inv)
    AIAuditResult.query.filter_by(invoice_id="test-mitigation-invoice-1").delete()
    db.session.commit()

def test_generate_mitigation_letter_requires_login(client):
    """Accessing the mitigation letter generation endpoint must fail without a session."""
    response = client.post("/api/invoices/local/test-mitigation-invoice-1/mitigation-letter")
    assert response.status_code == 401

@patch("invoices.ai_service.load_scheduler_settings")
def test_generate_mitigation_letter_success(mock_load_settings, logged_in_client, app):
    """Generating a mitigation letter for an existing high-risk invoice should return the letter."""
    mock_load_settings.return_value = {"ai_enabled": False}
    with app.app_context():
        create_mock_invoice()
    
    try:
        response = logged_in_client.post("/api/invoices/local/test-mitigation-invoice-1/mitigation-letter")
        assert response.status_code == 200
        payload = response.get_json()
        assert payload["status"] == "success"
        assert "letter" in payload
        assert "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM" in payload["letter"]
        assert "CÔNG VĂN GIẢI TRÌNH" in payload["letter"]
        assert "0101234599" in payload["letter"]
    finally:
        with app.app_context():
            cleanup_mock_invoice()

def test_generate_mitigation_letter_non_existent(logged_in_client):
    """Generating a mitigation letter for a non-existent invoice should return 404."""
    response = logged_in_client.post("/api/invoices/local/non-existent-invoice-id/mitigation-letter")
    assert response.status_code == 404

def test_export_mitigation_letter_doc(logged_in_client, app):
    """Exporting a mitigation letter to DOC format should return a download response."""
    with app.app_context():
        create_mock_invoice()
    
    try:
        export_payload = {
            "letter": "Test mitigation letter content with legal explanations.",
            "format": "doc"
        }
        response = logged_in_client.post(
            "/api/invoices/local/test-mitigation-invoice-1/mitigation-letter/export",
            json=export_payload
        )
        assert response.status_code == 200
        content_type = response.headers["Content-Type"]
        assert any(t in content_type for t in ["application/vnd.ms-word", "application/msword", "application/octet-stream"])
        assert "attachment; filename=" in response.headers["Content-Disposition"]
        assert b"Test mitigation letter" in response.data
    finally:
        with app.app_context():
            cleanup_mock_invoice()

def test_export_mitigation_letter_pdf(logged_in_client, app):
    """Exporting a mitigation letter to PDF format should return a PDF download response."""
    with app.app_context():
        create_mock_invoice()
    
    try:
        export_payload = {
            "letter": "Test mitigation letter content in PDF.",
            "format": "pdf"
        }
        response = logged_in_client.post(
            "/api/invoices/local/test-mitigation-invoice-1/mitigation-letter/export",
            json=export_payload
        )
        assert response.status_code == 200
        assert "application/pdf" in response.headers["Content-Type"]
        assert "attachment; filename=" in response.headers["Content-Disposition"]
        # PDF files should start with the standard %PDF signature bytes
        assert response.data.startswith(b"%PDF")
    finally:
        with app.app_context():
            cleanup_mock_invoice()
