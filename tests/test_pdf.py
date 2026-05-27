import pytest
from flask import session
from invoices.service import MOCK_INVOICES, build_invoice_lookup

def test_invoice_pdf_download_requires_login(client):
    """Verify that calling PDF download route without logging in returns 401."""
    response = client.get("/api/invoices/INV-2026-0501/pdf")
    assert response.status_code == 401

def test_invoice_pdf_download_success(logged_in_client, app):
    """Verify that PDF download route works and returns a valid PDF."""
    with app.test_request_context():
        with logged_in_client.session_transaction() as sess:
            sess["invoice_lookup"] = build_invoice_lookup(MOCK_INVOICES)

    response = logged_in_client.get("/api/invoices/INV-2026-0501/pdf")
    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert len(response.data) > 0

def test_invoice_pdf_download_not_found(logged_in_client):
    """Verify that calling PDF download route for a non-existing invoice returns 404."""
    response = logged_in_client.get("/api/invoices/INV-999999/pdf")
    assert response.status_code == 404

def test_reports_partners_pdf_requires_login(client):
    """Verify that calling partner directory PDF export without logging in returns 401."""
    response = client.get("/api/reports/partners/pdf?from=2026-05-01&to=2026-05-20")
    assert response.status_code == 401

def test_reports_partners_pdf_success(logged_in_client):
    """Verify that partner directory PDF export works and returns PDF."""
    response = logged_in_client.get("/api/reports/partners/pdf?from=2026-05-01&to=2026-05-20&direction=purchase")
    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert len(response.data) > 0

def test_reports_usage_pdf_requires_login(client):
    """Verify that calling BC26 PDF export without logging in returns 401."""
    response = client.get("/api/reports/usage/pdf?from=2026-05-01&to=2026-05-20")
    assert response.status_code == 401

def test_reports_usage_pdf_success(logged_in_client):
    """Verify that BC26 PDF export works and returns PDF."""
    response = logged_in_client.get("/api/reports/usage/pdf?from=2026-05-01&to=2026-05-20&direction=sold")
    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert len(response.data) > 0
