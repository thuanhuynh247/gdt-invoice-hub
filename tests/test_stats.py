"""Tests for the invoice statistics and details endpoints."""

from __future__ import annotations


def test_fetch_stats_requires_login(client):
    """Anonymous users should be blocked with 401 when fetching stats."""

    response = client.get("/api/invoices/stats?from=2026-05-01&to=2026-05-31")
    assert response.status_code == 401


def test_fetch_stats_success(logged_in_client):
    """Authenticated request with a valid date range should return accurate aggregations."""

    response = logged_in_client.get("/api/invoices/stats?from=2026-05-01&to=2026-05-20")
    assert response.status_code == 200

    payload = response.get_json()
    assert "total_spend" in payload
    assert "total_tax" in payload
    assert "active_count" in payload
    assert "cancelled_count" in payload
    assert "top_vendors" in payload
    assert "tax_breakdown" in payload

    # Mock data validation assertions
    assert payload["active_count"] == 2
    assert payload["cancelled_count"] == 1
    # Active spend: INV-2026-0501 (1,540,000) + INV-2026-0518 (972,000) = 2,512,000
    assert payload["total_spend"] == 2512000.0
    # Tax spend: 120,000 (10%) + 20,000 (10%) + 72,000 (8%) = 212,000
    assert payload["total_tax"] == 212000.0

    # Tax rate distributions assertions
    assert payload["tax_breakdown"]["10%"] == 140000.0
    assert payload["tax_breakdown"]["8%"] == 72000.0

    # Top Vendors assertions
    assert len(payload["top_vendors"]) > 0
    assert payload["top_vendors"][0]["name"] == "Cong ty A"


def test_fetch_stats_invalid_date(logged_in_client):
    """Requests with incorrectly formatted date ranges must return a 400 error."""

    response = logged_in_client.get("/api/invoices/stats?from=05-01-2026&to=2026-05-31")
    assert response.status_code == 400


def test_fetch_invoice_details_success(logged_in_client):
    """Authenticated request should retrieve line items for a valid invoice ID."""

    response = logged_in_client.get("/api/invoices/INV-2026-0501/details")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["invoice_id"] == "INV-2026-0501"
    assert len(payload["line_items"]) == 2
    assert payload["line_items"][0]["item_name"] == "Laptop Dell Vostro 3520"
    assert payload["line_items"][0]["tax_amount"] == 120000.0


def test_fetch_invoice_details_not_found(logged_in_client):
    """Requesting details for a non-existent invoice ID should yield a 404 error."""

    response = logged_in_client.get("/api/invoices/INV-UNKNOWN/details")
    assert response.status_code == 404
