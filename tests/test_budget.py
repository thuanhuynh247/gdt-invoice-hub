"""
Unit tests for US-035: Budget Monitor & Spending Alerts.

Tests cover:
- GET /api/budget/config (load saved config)
- POST /api/budget/config (save config)
- GET /api/budget/actuals (spending aggregation by category)
- Auth protection on all endpoints
- Percentage calculation and status logic
- Empty state handling

Uses shared conftest fixtures: app, client, logged_in_client.
"""

from __future__ import annotations

import pytest
from extensions import db as _db
from invoices.models import Invoice, LineItem, SystemConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed_purchase_invoice(app, inv_id, month="2026-05"):
    """Seed a purchase invoice with 3 categorised line items."""
    with app.app_context():
        inv = Invoice(
            id=inv_id,
            invoice_type="purchase",
            date=f"{month}-15",
            seller_name="Nhà Cung Cấp Test",
            seller_mst="0123456789",
            amount_before_tax=10_000_000,
            tax_amount=1_000_000,
            total_amount=11_000_000,
            imported_at="2026-05-15T00:00:00",
            is_cancelled=False,
        )
        _db.session.add(inv)
        _db.session.flush()

        items = [
            LineItem(invoice_id=inv.id, item_name="Laptop Dell", unit="cái", quantity=1,
                     unit_price=5_000_000, amount_before_tax=5_000_000,
                     tax_rate="10%", tax_amount=500_000,
                     expense_category="Thiết bị công nghệ & Phần mềm"),
            LineItem(invoice_id=inv.id, item_name="Bút bi xanh", unit="hộp", quantity=10,
                     unit_price=200_000, amount_before_tax=2_000_000,
                     tax_rate="10%", tax_amount=200_000,
                     expense_category="Văn phòng phẩm & Thiết bị văn phòng"),
            LineItem(invoice_id=inv.id, item_name="Dịch vụ quảng cáo Google", unit="gói", quantity=1,
                     unit_price=3_000_000, amount_before_tax=3_000_000,
                     tax_rate="10%", tax_amount=300_000,
                     expense_category="Quảng cáo, Tiếp thị & Sự kiện"),
        ]
        for item in items:
            _db.session.add(item)
        _db.session.commit()


# ---------------------------------------------------------------------------
# Tests: Auth protection
# ---------------------------------------------------------------------------

def test_budget_config_get_requires_login(client):
    """GET /api/budget/config must reject unauthenticated requests with 401."""
    resp = client.get("/api/budget/config")
    assert resp.status_code == 401


def test_budget_config_post_requires_login(client):
    """POST /api/budget/config must reject unauthenticated requests with 401."""
    resp = client.post("/api/budget/config", json={"configs": []})
    assert resp.status_code == 401


def test_budget_actuals_requires_login(client):
    """GET /api/budget/actuals must reject unauthenticated requests with 401."""
    resp = client.get("/api/budget/actuals")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Tests: Config save & load
# ---------------------------------------------------------------------------

def test_budget_config_empty_by_default(logged_in_client):
    """GET /api/budget/config returns empty list when no config saved for month."""
    resp = logged_in_client.get("/api/budget/config?month=2099-01")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert isinstance(data["configs"], list)
    assert len(data["configs"]) == 0


def test_budget_config_save_and_load(logged_in_client):
    """POST saves config; GET retrieves it for the same month."""
    payload = {
        "month": "2026-06",
        "configs": [
            {"category": "Thiết bị công nghệ & Phần mềm", "limit_vnd": 10_000_000},
            {"category": "Văn phòng phẩm & Thiết bị văn phòng", "limit_vnd": 3_000_000},
        ]
    }
    resp = logged_in_client.post("/api/budget/config", json=payload)
    assert resp.status_code == 200
    assert resp.get_json()["success"] is True
    assert resp.get_json()["saved"] == 2

    # Load it back
    resp2 = logged_in_client.get("/api/budget/config?month=2026-06")
    assert resp2.status_code == 200
    data = resp2.get_json()
    assert data["success"] is True
    cats = {c["category"]: c["limit_vnd"] for c in data["configs"]}
    assert cats["Thiết bị công nghệ & Phần mềm"] == 10_000_000
    assert cats["Văn phòng phẩm & Thiết bị văn phòng"] == 3_000_000


# ---------------------------------------------------------------------------
# Tests: Actuals aggregation
# ---------------------------------------------------------------------------

def test_budget_actuals_empty_when_no_invoices(logged_in_client):
    """GET /api/budget/actuals returns empty actuals when no line items for month."""
    resp = logged_in_client.get("/api/budget/actuals?month=2099-01")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert isinstance(data["actuals"], list)


def test_budget_actuals_aggregates_correctly(logged_in_client, app):
    """Actuals sum line item amounts by expense_category for the target month."""
    _seed_purchase_invoice(app, inv_id="budget-agg-test-01", month="2026-07")

    resp = logged_in_client.get("/api/budget/actuals?month=2026-07")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True

    actuals_map = {a["category"]: a["actual_vnd"] for a in data["actuals"]}
    assert actuals_map.get("Thiết bị công nghệ & Phần mềm") == pytest.approx(5_000_000)
    assert actuals_map.get("Văn phòng phẩm & Thiết bị văn phòng") == pytest.approx(2_000_000)
    assert actuals_map.get("Quảng cáo, Tiếp thị & Sự kiện") == pytest.approx(3_000_000)


def test_budget_actuals_pct_and_status(logged_in_client, app):
    """Actuals endpoint computes pct_used and correct status for ok vs over_budget."""
    _seed_purchase_invoice(app, inv_id="budget-pct-test-01", month="2026-08")

    # Tech=10M limit (actual 5M=50% ok), Office=1M limit (actual 2M=200% over_budget)
    payload = {
        "month": "2026-08",
        "configs": [
            {"category": "Thiết bị công nghệ & Phần mềm", "limit_vnd": 10_000_000},
            {"category": "Văn phòng phẩm & Thiết bị văn phòng", "limit_vnd": 1_000_000},
        ]
    }
    logged_in_client.post("/api/budget/config", json=payload)

    resp = logged_in_client.get("/api/budget/actuals?month=2026-08")
    assert resp.status_code == 200
    data = resp.get_json()

    items = {a["category"]: a for a in data["actuals"]}

    tech = items.get("Thiết bị công nghệ & Phần mềm")
    assert tech is not None
    assert tech["pct_used"] == pytest.approx(50.0)
    assert tech["status"] == "ok"

    office = items.get("Văn phòng phẩm & Thiết bị văn phòng")
    assert office is not None
    assert office["pct_used"] == pytest.approx(200.0)
    assert office["status"] == "over_budget"


def test_budget_status_warning_threshold(logged_in_client, app):
    """Category at ~86% budget should have status='warning'."""
    _seed_purchase_invoice(app, inv_id="budget-warn-test-01", month="2026-09")

    # Marketing actual: 3M; limit = 3.5M → 85.7% → warning
    payload = {
        "month": "2026-09",
        "configs": [
            {"category": "Quảng cáo, Tiếp thị & Sự kiện", "limit_vnd": 3_500_000},
        ]
    }
    logged_in_client.post("/api/budget/config", json=payload)

    resp = logged_in_client.get("/api/budget/actuals?month=2026-09")
    data = resp.get_json()
    items = {a["category"]: a for a in data["actuals"]}
    mkt = items.get("Quảng cáo, Tiếp thị & Sự kiện")
    assert mkt is not None
    assert mkt["pct_used"] == pytest.approx(3_000_000 / 3_500_000 * 100, rel=0.01)
    assert mkt["status"] == "warning"


def test_budget_alert_level_aggregation(logged_in_client, app):
    """alert_level in response reflects worst status across all categories."""
    _seed_purchase_invoice(app, inv_id="budget-alert-test-01", month="2026-10")

    payload = {
        "month": "2026-10",
        "configs": [
            {"category": "Thiết bị công nghệ & Phần mềm", "limit_vnd": 10_000_000},  # 5M/10M = ok
            {"category": "Văn phòng phẩm & Thiết bị văn phòng", "limit_vnd": 500_000},  # 2M/0.5M = over_budget
        ]
    }
    logged_in_client.post("/api/budget/config", json=payload)

    resp = logged_in_client.get("/api/budget/actuals?month=2026-10")
    data = resp.get_json()
    assert data["alert_level"] == "over_budget"
