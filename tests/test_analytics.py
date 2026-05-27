"""Tests for Analytics Pro: Supplier Price Trends and VAT Forecast APIs."""

from __future__ import annotations

import pytest
from extensions import db as _db
from invoices.models import Invoice, LineItem


# ---------------------------------------------------------------------------
# Helpers — must run INSIDE the app context already active in conftest
# ---------------------------------------------------------------------------

def _make_purchase_invoice(inv_id, seller_name, seller_mst, date, tax_amount, amount):
    inv = Invoice(
        id=inv_id,
        invoice_type="purchase",
        seller_name=seller_name,
        seller_mst=seller_mst,
        date=date,
        amount_before_tax=amount,
        tax_amount=tax_amount,
        total_amount=amount + tax_amount,
        is_cancelled=False,
        imported_at="2026-05-23 00:00:00",
    )
    _db.session.add(inv)
    _db.session.commit()


def _make_sold_invoice(inv_id, date, tax_amount, amount):
    inv = Invoice(
        id=inv_id,
        invoice_type="sold",
        seller_name="Công ty tôi",
        seller_mst="9999999999",
        buyer_name="Khách hàng A",
        date=date,
        amount_before_tax=amount,
        tax_amount=tax_amount,
        total_amount=amount + tax_amount,
        is_cancelled=False,
        imported_at="2026-05-23 00:00:00",
    )
    _db.session.add(inv)
    _db.session.commit()


def _add_line_item(invoice_id, item_name, unit_price, qty=1):
    item = LineItem(
        invoice_id=invoice_id,
        item_name=item_name,
        quantity=qty,
        unit_price=unit_price,
        amount_before_tax=unit_price * qty,
        tax_rate="10%",
        tax_amount=unit_price * qty * 0.1,
    )
    _db.session.add(item)
    _db.session.commit()


# ---------------------------------------------------------------------------
# Top Items
# ---------------------------------------------------------------------------

def test_top_items_requires_login(client):
    resp = client.get("/api/analytics/top-items")
    assert resp.status_code == 401


def test_top_items_returns_list(client, app):
    _make_purchase_invoice("TOPITEM-01", "NCC A", "0100000001", "2026-03-01", 500000, 5000000)
    _make_purchase_invoice("TOPITEM-02", "NCC B", "0100000002", "2026-04-01", 500000, 5000000)
    _add_line_item("TOPITEM-01", "Giấy A4 Double A", 100000, 5)
    _add_line_item("TOPITEM-02", "Giấy A4 Double A", 110000, 3)
    _add_line_item("TOPITEM-02", "Mực In Canon", 250000, 2)

    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "testuser"

    resp = client.get("/api/analytics/top-items")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert len(data["items"]) >= 1


# ---------------------------------------------------------------------------
# Supplier Price Trends
# ---------------------------------------------------------------------------

def test_supplier_price_trends_requires_login(client):
    resp = client.get("/api/analytics/supplier-price-trends?item_name=Giấy")
    assert resp.status_code == 401


def test_supplier_price_trends_requires_item_name(client):
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "testuser"
    resp = client.get("/api/analytics/supplier-price-trends")
    assert resp.status_code == 400


def test_supplier_price_trends_empty_result(client, app):
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "testuser"
    resp = client.get("/api/analytics/supplier-price-trends?item_name=XYZDoesNotExist999")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data["series"] == []
    assert data["anomalies"] == []


def test_supplier_price_trends_two_sellers(client, app):
    _make_purchase_invoice("SPT-01", "NCC Rẻ", "0200000001", "2026-02-15", 100000, 1000000)
    _make_purchase_invoice("SPT-02", "NCC Đắt", "0200000002", "2026-02-20", 150000, 1500000)
    _make_purchase_invoice("SPT-03", "NCC Rẻ", "0200000001", "2026-03-10", 90000, 900000)
    _add_line_item("SPT-01", "Bút bi Thiên Long", 5000, 10)
    _add_line_item("SPT-02", "Bút bi Thiên Long", 7500, 10)
    _add_line_item("SPT-03", "Bút bi Thiên Long", 4500, 10)

    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "testuser"

    resp = client.get("/api/analytics/supplier-price-trends?item_name=Thiên+Long")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert len(data["months"]) >= 1
    assert len(data["series"]) >= 1
    if len(data["series"]) >= 2:
        assert data["series"][0]["avg_price"] <= data["series"][1]["avg_price"]


def test_supplier_price_trends_anomaly_detection(client, app):
    _make_purchase_invoice("ANO-01", "NCC Bình thường", "0300000001", "2026-01-10", 10000, 100000)
    _make_purchase_invoice("ANO-02", "NCC Bình thường", "0300000001", "2026-02-10", 10000, 100000)
    _make_purchase_invoice("ANO-03", "NCC Đắt bất thường", "0300000099", "2026-03-10", 15000, 150000)
    _add_line_item("ANO-01", "Mực in HP", 100000, 1)
    _add_line_item("ANO-02", "Mực in HP", 100000, 1)
    _add_line_item("ANO-03", "Mực in HP", 200000, 1)  # 100% above avg → anomaly

    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "testuser"

    resp = client.get("/api/analytics/supplier-price-trends?item_name=Mực+in+HP")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert len(data["anomalies"]) >= 1
    assert data["anomalies"][0]["pct_above"] > 20.0


# ---------------------------------------------------------------------------
# VAT Forecast
# ---------------------------------------------------------------------------

def test_vat_forecast_requires_login(client):
    resp = client.get("/api/analytics/vat-forecast")
    assert resp.status_code == 401


def test_vat_forecast_empty_db(client, app):
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "testuser"

    resp = client.get("/api/analytics/vat-forecast?year=2020")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True
    assert data["year"] == "2020"
    assert len(data["actual"]) == 12
    assert all(a["net_vat"] == 0 for a in data["actual"])
    assert data["forecast"] == []


def test_vat_forecast_monthly_aggregation(client, app):
    _make_sold_invoice("VAT-SOLD-01", "2026-01-15", 1000000, 10000000)
    _make_sold_invoice("VAT-SOLD-02", "2026-02-10", 1200000, 12000000)
    _make_sold_invoice("VAT-SOLD-03", "2026-03-05", 1500000, 15000000)
    _make_purchase_invoice("VAT-BUY-01", "NCC X", "0400000001", "2026-01-20", 400000, 4000000)
    _make_purchase_invoice("VAT-BUY-02", "NCC X", "0400000001", "2026-02-18", 500000, 5000000)
    _make_purchase_invoice("VAT-BUY-03", "NCC X", "0400000001", "2026-03-12", 600000, 6000000)

    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "testuser"

    resp = client.get("/api/analytics/vat-forecast?year=2026")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["success"] is True

    actual = {a["month"]: a for a in data["actual"]}
    assert actual["2026-01"]["output_vat"] == 1000000
    assert actual["2026-01"]["input_vat"] == 400000
    assert actual["2026-01"]["net_vat"] == 600000
    assert actual["2026-02"]["net_vat"] == 700000


def test_vat_forecast_generates_two_forecast_months(client, app):
    _make_sold_invoice("FC-SOLD-01", "2026-01-10", 500000, 5000000)
    _make_sold_invoice("FC-SOLD-02", "2026-02-10", 600000, 6000000)
    _make_sold_invoice("FC-SOLD-03", "2026-03-10", 700000, 7000000)

    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "testuser"

    resp = client.get("/api/analytics/vat-forecast?year=2026")
    data = resp.get_json()
    assert data["success"] is True
    assert len(data["forecast"]) == 2
    assert data["forecast"][0]["month"] > "2026-03"
    assert data["forecast"][1]["month"] > data["forecast"][0]["month"]


def test_vat_forecast_summary_totals(client, app):
    _make_sold_invoice("SUM-01", "2026-01-01", 1000000, 10000000)
    _make_sold_invoice("SUM-02", "2026-02-01", 2000000, 20000000)
    _make_purchase_invoice("SUM-BUY-01", "NCC S", "0500000001", "2026-01-05", 300000, 3000000)

    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "testuser"

    resp = client.get("/api/analytics/vat-forecast?year=2026")
    data = resp.get_json()
    assert data["success"] is True
    s = data["summary"]
    assert s["total_output_vat"] == 3000000
    assert s["total_input_vat"] == 300000
    assert s["total_net_vat"] == 2700000
    assert s["months_with_data"] >= 2
