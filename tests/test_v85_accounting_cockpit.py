"""Unit & Integration Tests for Accounting Cockpit Studio (Law 149, Decree 123 & HTKK Export)."""

from __future__ import annotations
import pytest

from invoices.service import get_lean_accounting_cockpit


def test_get_lean_accounting_cockpit_unit(app):
    """Verify single-pass Accounting Cockpit calculation and disallowances."""
    with app.app_context():
        res = get_lean_accounting_cockpit("0109998887")
        assert "output_vat" in res
        assert "input_vat_total" in res
        assert "input_vat_deductible" in res
        assert "input_vat_disallowed_cash" in res
        assert "input_vat_disallowed_blacklisted" in res
        assert "net_vat_payable" in res
        assert "aging_receivables" in res
        assert "aging_payables" in res
        assert "htkk_ready" in res
        assert isinstance(res["htkk_ready"], bool)


def test_api_accounting_cockpit_endpoint(client):
    """Verify /api/accounting/cockpit GET endpoint."""
    with client.session_transaction() as sess:
        sess["username"] = "admin"
        sess["role"] = "admin"
        sess["logged_in"] = True
        sess["taxpayer_mst"] = "0109998887"
        sess["active_taxpayer_mst"] = "0109998887"

    response = client.get("/api/accounting/cockpit")
    assert response.status_code == 200
    data = response.get_json()

    assert data["status"] == "success"
    assert "query_latency_ms" in data
    assert "cockpit" in data
    assert data["query_latency_ms"] < 500.0
