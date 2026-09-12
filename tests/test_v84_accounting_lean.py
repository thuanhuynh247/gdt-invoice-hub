"""Unit & Route Integration Tests for Accounting Compliance Fast-Audit Studio (Law 149 & Decree 123)."""

from __future__ import annotations
import pytest

from invoices.service import get_accounting_compliance_summary


def test_get_accounting_compliance_summary_unit(app):
    """Verify single-pass accounting summary calculations."""
    with app.app_context():
        summary = get_accounting_compliance_summary("0109998887")
        assert "sales_revenue" in summary
        assert "sales_vat" in summary
        assert "purchase_expense" in summary
        assert "purchase_vat" in summary
        assert "deductible_input_vat" in summary
        assert "non_deductible_cash_vat" in summary
        assert "estimated_net_vat_payable" in summary
        assert "aging" in summary
        assert summary["estimated_net_vat_payable"] >= 0.0


def test_api_accounting_fast_summary_endpoint(client):
    """Verify /api/accounting/fast-summary endpoint integration in Flask app."""
    with client.session_transaction() as sess:
        sess["username"] = "admin"
        sess["role"] = "admin"
        sess["logged_in"] = True
        sess["taxpayer_mst"] = "0109998887"
        sess["active_taxpayer_mst"] = "0109998887"

    response = client.get("/api/accounting/fast-summary")
    assert response.status_code == 200
    data = response.get_json()

    assert data["status"] == "success"
    assert "query_latency_ms" in data
    assert "accounting_summary" in data
    assert data["query_latency_ms"] < 500.0
