"""Unit & Integration Tests for Advanced Accounting Upgrades & Lieflat HTML Report Generator (GDT-ACC-03)."""

from __future__ import annotations
import pytest


def test_api_accounting_tp_audit_endpoint(client):
    """Verify /api/accounting/tp-audit POST endpoint."""
    with client.session_transaction() as sess:
        sess["username"] = "admin"
        sess["role"] = "admin"
        sess["logged_in"] = True
        sess["taxpayer_mst"] = "0109998887"
        sess["active_taxpayer_mst"] = "0109998887"

    payload = {
        "taxpayer_mst": "0109998887",
        "consolidated_revenue": 60000000000.0,
        "ebitda": 12000000000.0,
        "net_interest_expense": 3000000000.0,
        "related_party_revenue": 20000000000.0
    }

    response = client.post("/api/accounting/tp-audit", json=payload)
    assert response.status_code == 200
    data = response.get_json()

    assert data["status"] == "success"
    assert "tp_audit" in data
    assert "is_interest_capped" in data["tp_audit"]


def test_api_accounting_report_html_endpoint(client):
    """Verify /api/accounting/report-html GET endpoint returning Lieflat HTML report."""
    with client.session_transaction() as sess:
        sess["username"] = "admin"
        sess["role"] = "admin"
        sess["logged_in"] = True
        sess["taxpayer_mst"] = "0109998887"
        sess["active_taxpayer_mst"] = "0109998887"

    response = client.get("/api/accounting/report-html")
    assert response.status_code == 200
    assert "text/html" in response.headers["Content-Type"]
    html_text = response.get_data(as_text=True)
    assert "LIEFLAT REPORT R04" in html_text
    assert "Báo Cáo Kiểm Toán Nhanh Thuế GTGT & TNDN" in html_text
