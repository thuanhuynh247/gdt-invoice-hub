"""
Unit tests for US-036: Invoice Aging & Receivable Tracker.

Tests cover:
- GET /api/aging/summary  — aging bucket aggregation
- PATCH /api/invoices/<id>/payment — due_date / paid_date update
- Auth protection on all endpoints
- Correct bucket classification (0-30, 31-60, 61-90, >90 days)
- Paid invoices excluded from aging report
- Cancelled invoices excluded from aging report
- age_days falls back to invoice.date when due_date is absent

Uses shared conftest fixtures: app, client, logged_in_client.
"""

from __future__ import annotations

import pytest
from datetime import date, timedelta

from extensions import db as _db
from invoices.models import Invoice


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _today_str() -> str:
    return date.today().isoformat()


def _days_ago(n: int) -> str:
    return (date.today() - timedelta(days=n)).isoformat()


def _make_sold_invoice(
    inv_id: str,
    invoice_date: str,
    amount: float = 5_000_000,
    buyer_name: str = "Khách hàng A",
    buyer_mst: str = "0900000001",
    due_date: str | None = None,
    paid_date: str | None = None,
    is_cancelled: bool = False,
):
    inv = Invoice(
        id=inv_id,
        invoice_type="sold",
        date=invoice_date,
        seller_name="Công ty Tôi",
        seller_mst="9999999999",
        buyer_name=buyer_name,
        buyer_mst=buyer_mst,
        amount_before_tax=amount,
        tax_amount=amount * 0.1,
        total_amount=amount * 1.1,
        imported_at="2026-01-01T00:00:00",
        is_cancelled=is_cancelled,
        due_date=due_date,
        paid_date=paid_date,
    )
    _db.session.add(inv)
    _db.session.commit()
    return inv


# ---------------------------------------------------------------------------
# Tests: Auth protection
# ---------------------------------------------------------------------------

def test_aging_summary_requires_login(client):
    """GET /api/aging/summary must reject unauthenticated requests."""
    resp = client.get("/api/aging/summary")
    assert resp.status_code == 401


def test_aging_payment_patch_requires_login(client):
    """PATCH /api/invoices/<id>/payment must reject unauthenticated requests."""
    resp = client.patch("/api/invoices/nonexistent/payment", json={"due_date": "2026-06-01"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Tests: Empty state
# ---------------------------------------------------------------------------

def test_aging_summary_empty_when_no_invoices(logged_in_client):
    """GET /api/aging/summary returns empty buckets when no sold invoices."""
    resp = logged_in_client.get("/api/aging/summary")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert "buckets" in data
    # All buckets exist but with zero totals
    bucket_labels = [b["label"] for b in data["buckets"]]
    assert "1–30 ngày" in bucket_labels
    assert ">90 ngày" in bucket_labels


# ---------------------------------------------------------------------------
# Tests: Bucket classification
# ---------------------------------------------------------------------------

def test_aging_bucket_0_to_30_days(logged_in_client, app):
    """Invoice 15 days overdue lands in 1–30 bucket."""
    with app.app_context():
        _make_sold_invoice(
            "aging-15d",
            invoice_date=_days_ago(15),
            due_date=_days_ago(15),
        )

    resp = logged_in_client.get("/api/aging/summary")
    data = resp.get_json()
    b = _bucket(data, "1–30 ngày")
    assert b["count"] >= 1
    assert b["total_amount"] >= 5_000_000


def test_aging_bucket_31_to_60_days(logged_in_client, app):
    """Invoice 45 days overdue lands in 31–60 bucket."""
    with app.app_context():
        _make_sold_invoice(
            "aging-45d",
            invoice_date=_days_ago(45),
            due_date=_days_ago(45),
        )

    resp = logged_in_client.get("/api/aging/summary")
    data = resp.get_json()
    b = _bucket(data, "31–60 ngày")
    assert b["count"] >= 1


def test_aging_bucket_61_to_90_days(logged_in_client, app):
    """Invoice 75 days overdue lands in 61–90 bucket."""
    with app.app_context():
        _make_sold_invoice(
            "aging-75d",
            invoice_date=_days_ago(75),
            due_date=_days_ago(75),
        )

    resp = logged_in_client.get("/api/aging/summary")
    data = resp.get_json()
    b = _bucket(data, "61–90 ngày")
    assert b["count"] >= 1


def test_aging_bucket_over_90_days(logged_in_client, app):
    """Invoice 120 days overdue lands in >90 bucket."""
    with app.app_context():
        _make_sold_invoice(
            "aging-120d",
            invoice_date=_days_ago(120),
            due_date=_days_ago(120),
        )

    resp = logged_in_client.get("/api/aging/summary")
    data = resp.get_json()
    b = _bucket(data, ">90 ngày")
    assert b["count"] >= 1


# ---------------------------------------------------------------------------
# Tests: Exclusion rules
# ---------------------------------------------------------------------------

def test_paid_invoices_excluded_from_aging(logged_in_client, app):
    """Invoices with paid_date set should NOT appear in aging summary."""
    with app.app_context():
        _make_sold_invoice(
            "aging-paid",
            invoice_date=_days_ago(60),
            due_date=_days_ago(60),
            paid_date=_days_ago(10),   # Already paid
        )

    resp = logged_in_client.get("/api/aging/summary?as_of=" + _today_str())
    data = resp.get_json()
    # Invoice "aging-paid" must not appear in any bucket
    for b in data["buckets"]:
        ids = [inv.get("id") for inv in b.get("invoices", [])]
        assert "aging-paid" not in ids


def test_cancelled_invoices_excluded_from_aging(logged_in_client, app):
    """Cancelled invoices should NOT appear in aging summary."""
    with app.app_context():
        _make_sold_invoice(
            "aging-cancelled",
            invoice_date=_days_ago(50),
            due_date=_days_ago(50),
            is_cancelled=True,
        )

    resp = logged_in_client.get("/api/aging/summary")
    data = resp.get_json()
    for b in data["buckets"]:
        ids = [inv.get("id") for inv in b.get("invoices", [])]
        assert "aging-cancelled" not in ids


def test_fallback_to_invoice_date_when_no_due_date(logged_in_client, app):
    """When due_date is absent, age is calculated from invoice.date."""
    with app.app_context():
        _make_sold_invoice(
            "aging-noduedate-100d",
            invoice_date=_days_ago(100),
            due_date=None,   # No due_date — fallback
        )

    resp = logged_in_client.get("/api/aging/summary")
    data = resp.get_json()
    b = _bucket(data, ">90 ngày")
    ids = [inv.get("id") for inv in b.get("invoices", [])]
    assert "aging-noduedate-100d" in ids


# ---------------------------------------------------------------------------
# Tests: PATCH /api/invoices/<id>/payment
# ---------------------------------------------------------------------------

def test_patch_payment_sets_due_date(logged_in_client, app):
    """PATCH /payment sets due_date on an invoice."""
    with app.app_context():
        _make_sold_invoice("aging-patch-due", invoice_date=_days_ago(5))

    resp = logged_in_client.patch(
        "/api/invoices/aging-patch-due/payment",
        json={"due_date": "2026-12-31"},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True

    # Confirm persisted
    with app.app_context():
        inv = _db.session.get(Invoice, "aging-patch-due")
        assert inv.due_date == "2026-12-31"


def test_patch_payment_sets_paid_date(logged_in_client, app):
    """PATCH /payment sets paid_date and invoice disappears from aging."""
    with app.app_context():
        _make_sold_invoice(
            "aging-patch-paid",
            invoice_date=_days_ago(40),
            due_date=_days_ago(40),
        )

    # Confirm it appears in aging before marking paid
    resp1 = logged_in_client.get("/api/aging/summary")
    all_ids_before = _all_invoice_ids(resp1.get_json())
    assert "aging-patch-paid" in all_ids_before

    # Mark as paid
    resp2 = logged_in_client.patch(
        "/api/invoices/aging-patch-paid/payment",
        json={"paid_date": _today_str()},
    )
    assert resp2.status_code == 200

    # Confirm it no longer appears
    resp3 = logged_in_client.get("/api/aging/summary")
    all_ids_after = _all_invoice_ids(resp3.get_json())
    assert "aging-patch-paid" not in all_ids_after


def test_patch_payment_404_on_missing_invoice(logged_in_client):
    """PATCH /payment returns 404 when invoice does not exist."""
    resp = logged_in_client.patch(
        "/api/invoices/nonexistent-xyz/payment",
        json={"due_date": "2026-06-01"},
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Assertion helpers
# ---------------------------------------------------------------------------

def _bucket(data: dict, label: str) -> dict:
    for b in data.get("buckets", []):
        if b["label"] == label:
            return b
    return {"count": 0, "total_amount": 0, "invoices": []}


def _all_invoice_ids(data: dict) -> list[str]:
    ids = []
    for b in data.get("buckets", []):
        ids.extend(inv.get("id") for inv in b.get("invoices", []))
    return ids
