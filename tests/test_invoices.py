"""Invoice route tests."""

from __future__ import annotations


def test_invoice_page_redirects_when_not_logged_in(client):
    """Anonymous users should be redirected to login."""

    response = client.get("/invoices")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_fetch_invoices_requires_login(client):
    """API access must fail without a session."""

    response = client.get("/api/invoices?from=2026-05-01&to=2026-05-31")
    assert response.status_code == 401


def test_fetch_invoices_success(logged_in_client):
    """A valid date range should return mock invoices."""

    response = logged_in_client.get("/api/invoices?from=2026-05-01&to=2026-05-20")
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["total_count"] == 3
    assert len(payload["invoices"]) == 3


def test_fetch_cancelled_invoices_only(logged_in_client):
    """Cancelled route should only return cancelled rows."""

    response = logged_in_client.get("/api/cancelled-invoices?from=2026-05-01&to=2026-05-20")
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["total_count"] == 1
    assert payload["cancelled_invoices"][0]["is_cancelled"] is True


def test_fetch_invoices_invalid_date(logged_in_client):
    """Invalid date formats should return 400."""

    response = logged_in_client.get("/api/invoices?from=05-01-2026&to=2026-05-31")
    assert response.status_code == 400


def test_download_invoice_xml(logged_in_client):
    """Invoice XML should download with attachment headers."""

    response = logged_in_client.get("/api/invoices/INV-2026-0501/download")
    assert response.status_code == 200
    assert response.mimetype == "application/xml"
    assert "attachment;" in response.headers["Content-Disposition"]
