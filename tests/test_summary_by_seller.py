"""Tests for monthly/quarterly input invoice summary by seller endpoint."""

from __future__ import annotations

from datetime import datetime
from extensions import db
from invoices.models import Invoice, LineItem


def _seed_test_invoices(app):
    """Seed test invoices across different months and quarters."""
    with app.app_context():
        # Clean existing invoices
        LineItem.query.delete()
        Invoice.query.delete()
        db.session.commit()

        # Invoice 1: May 2026 (Q2), Seller A
        inv1 = Invoice(
            id="MST_A-C26-0001",
            filename="gdt_invoice_1.xml",
            invoice_type="purchase",
            template_code="1/001",
            symbol="C26",
            number="0001",
            date="2026-05-10",
            currency="VND",
            seller_mst="0101234567",
            seller_name="CONG TY A",
            buyer_mst="0109999999",
            buyer_name="CONG TY HOC TAP",
            amount_before_tax=100000.0,
            tax_amount=10000.0,
            total_amount=110000.0,
            has_signature=True,
            imported_at=datetime.now().isoformat()
        )

        # Invoice 2: May 2026 (Q2), Seller A (aggregates with inv1)
        inv2 = Invoice(
            id="MST_A-C26-0002",
            filename="gdt_invoice_2.xml",
            invoice_type="purchase",
            template_code="1/001",
            symbol="C26",
            number="0002",
            date="2026-05-15",
            currency="VND",
            seller_mst="0101234567",
            seller_name="CONG TY A",
            buyer_mst="0109999999",
            buyer_name="CONG TY HOC TAP",
            amount_before_tax=200000.0,
            tax_amount=20000.0,
            total_amount=220000.0,
            has_signature=True,
            imported_at=datetime.now().isoformat()
        )

        # Invoice 3: April 2026 (Q2), Seller B
        inv3 = Invoice(
            id="MST_B-C26-0003",
            filename="gdt_invoice_3.xml",
            invoice_type="purchase",
            template_code="1/001",
            symbol="C26",
            number="0003",
            date="2026-04-20",
            currency="VND",
            seller_mst="0209876543",
            seller_name="CONG TY B",
            buyer_mst="0109999999",
            buyer_name="CONG TY HOC TAP",
            amount_before_tax=500000.0,
            tax_amount=50000.0,
            total_amount=550000.0,
            has_signature=True,
            imported_at=datetime.now().isoformat()
        )

        # Invoice 4: January 2026 (Q1), Seller A
        inv4 = Invoice(
            id="MST_A-C26-0004",
            filename="gdt_invoice_4.xml",
            invoice_type="purchase",
            template_code="1/001",
            symbol="C26",
            number="0004",
            date="2026-01-10",
            currency="VND",
            seller_mst="0101234567",
            seller_name="CONG TY A",
            buyer_mst="0109999999",
            buyer_name="CONG TY HOC TAP",
            amount_before_tax=400000.0,
            tax_amount=40000.0,
            total_amount=440000.0,
            has_signature=True,
            imported_at=datetime.now().isoformat()
        )

        db.session.add_all([inv1, inv2, inv3, inv4])
        db.session.commit()


def test_summary_by_seller_requires_login(client):
    """Anonymous users should be blocked with 401."""
    response = client.get("/api/invoices/summary-by-seller")
    assert response.status_code == 401


def test_summary_by_seller_monthly_success(logged_in_client, app):
    """Verify monthly aggregation works correctly with seed data."""
    _seed_test_invoices(app)

    response = logged_in_client.get("/api/invoices/summary-by-seller?period_type=monthly&year=2026")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["success"] is True
    assert payload["period_type"] == "monthly"
    assert payload["year"] == "2026"

    data = payload["data"]
    # We should have 3 periods: Tháng 05 / 2026, Tháng 04 / 2026, Tháng 01 / 2026
    assert len(data) == 3

    # Check Sorting (descending by period name)
    assert data[0]["period"] == "Tháng 05 / 2026"
    assert data[1]["period"] == "Tháng 04 / 2026"
    assert data[2]["period"] == "Tháng 01 / 2026"

    # Check details of "Tháng 05 / 2026" (CONG TY A)
    m5 = data[0]
    assert len(m5["sellers"]) == 1
    assert m5["sellers"][0]["seller_mst"] == "0101234567"
    assert m5["sellers"][0]["seller_name"] == "CONG TY A"
    assert m5["sellers"][0]["invoice_count"] == 2
    assert m5["sellers"][0]["total_before_tax"] == 300000.0
    assert m5["sellers"][0]["total_tax"] == 30000.0
    assert m5["sellers"][0]["total_amount"] == 330000.0

    assert m5["total_before_tax"] == 300000.0
    assert m5["total_tax"] == 30000.0
    assert m5["total_amount"] == 330000.0

    # Check details of "Tháng 04 / 2026" (CONG TY B)
    m4 = data[1]
    assert len(m4["sellers"]) == 1
    assert m4["sellers"][0]["seller_mst"] == "0209876543"
    assert m4["sellers"][0]["total_amount"] == 550000.0

    # Check details of "Tháng 01 / 2026" (CONG TY A)
    m1 = data[2]
    assert len(m1["sellers"]) == 1
    assert m1["sellers"][0]["seller_mst"] == "0101234567"
    assert m1["sellers"][0]["total_amount"] == 440000.0


def test_summary_by_seller_quarterly_success(logged_in_client, app):
    """Verify quarterly aggregation works correctly with seed data."""
    _seed_test_invoices(app)

    response = logged_in_client.get("/api/invoices/summary-by-seller?period_type=quarterly&year=2026")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["success"] is True
    assert payload["period_type"] == "quarterly"

    data = payload["data"]
    # We should have 2 quarters: Quý 2 / 2026 (April & May), Quý 1 / 2026 (January)
    assert len(data) == 2

    # Sorting check
    assert data[0]["period"] == "Quý 2 / 2026"
    assert data[1]["period"] == "Quý 1 / 2026"

    # In Quý 2 / 2026, we have CONG TY B (total 550k) and CONG TY A (total 330k)
    # Sorted descending by seller spend, so CONG TY B must be first
    q2 = data[0]
    assert len(q2["sellers"]) == 2
    assert q2["sellers"][0]["seller_name"] == "CONG TY B"
    assert q2["sellers"][0]["total_amount"] == 550000.0
    assert q2["sellers"][1]["seller_name"] == "CONG TY A"
    assert q2["sellers"][1]["total_amount"] == 330000.0

    # Period totals
    assert q2["total_amount"] == 880000.0
    assert q2["total_before_tax"] == 800000.0
    assert q2["total_tax"] == 80000.0


def test_summary_by_seller_empty_db(logged_in_client, app):
    """Verify response when database contains no invoices."""
    with app.app_context():
        LineItem.query.delete()
        Invoice.query.delete()
        db.session.commit()

    response = logged_in_client.get("/api/invoices/summary-by-seller?period_type=monthly")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert len(payload["data"]) == 0
