"""Tests for monthly supplier pivot table and excel exporter endpoints."""

from __future__ import annotations

from datetime import datetime
import io
import openpyxl
from extensions import db
from invoices.models import Invoice, LineItem, TaxpayerProfile


def _seed_test_invoices(app):
    """Seed purchase invoices and taxpayer profiles for supplier pivot tests."""
    with app.app_context():
        LineItem.query.delete()
        Invoice.query.delete()
        TaxpayerProfile.query.delete()
        db.session.commit()

        # Seed Taxpayer Profiles
        profile_active = TaxpayerProfile(
            mst="0109999999",
            company_name="CONG TY HOC TAP",
            gdt_username="username1",
            gdt_password_encrypted="encrypted1",
            is_active=True,
            created_at=datetime.now().isoformat()
        )
        profile_other = TaxpayerProfile(
            mst="0333333333",
            company_name="CONG TY KHAC",
            gdt_username="username2",
            gdt_password_encrypted="encrypted2",
            is_active=True,
            created_at=datetime.now().isoformat()
        )
        db.session.add_all([profile_active, profile_other])
        db.session.commit()

        # Invoice 1: Jan 2026, Seller A, purchase, active taxpayer
        inv1 = Invoice(
            id="MST_A-C26-0001",
            filename="pur_invoice_1.xml",
            invoice_type="purchase",
            template_code="1/001",
            symbol="C26",
            number="0001",
            date="2026-01-15",
            currency="VND",
            seller_mst="0101234567",
            seller_name="NHÀ CUNG CẤP A",
            buyer_mst="0109999999", # active taxpayer MST from logged_in_client context
            buyer_name="CONG TY HOC TAP",
            amount_before_tax=1000000.0,
            tax_amount=100000.0,
            total_amount=1100000.0,
            has_signature=True,
            imported_at=datetime.now().isoformat(),
            taxpayer_mst="0109999999"
        )

        # Invoice 2: Feb 2026, Seller A, purchase, active taxpayer
        inv2 = Invoice(
            id="MST_A-C26-0002",
            filename="pur_invoice_2.xml",
            invoice_type="purchase",
            template_code="1/001",
            symbol="C26",
            number="0002",
            date="2026-02-10",
            currency="VND",
            seller_mst="0101234567",
            seller_name="NHÀ CUNG CẤP A",
            buyer_mst="0109999999",
            buyer_name="CONG TY HOC TAP",
            amount_before_tax=2000000.0,
            tax_amount=200000.0,
            total_amount=2200000.0,
            has_signature=True,
            imported_at=datetime.now().isoformat(),
            taxpayer_mst="0109999999"
        )

        # Invoice 3: Feb 2026, Seller B, purchase, active taxpayer
        inv3 = Invoice(
            id="MST_B-C26-0003",
            filename="pur_invoice_3.xml",
            invoice_type="purchase",
            template_code="1/001",
            symbol="C26",
            number="0003",
            date="2026-02-28",
            currency="VND",
            seller_mst="0209876543",
            seller_name="NHÀ CUNG CẤP B",
            buyer_mst="0109999999",
            buyer_name="CONG TY HOC TAP",
            amount_before_tax=500000.0,
            tax_amount=50000.0,
            total_amount=550000.0,
            has_signature=True,
            imported_at=datetime.now().isoformat(),
            taxpayer_mst="0109999999"
        )

        # Invoice 4: Feb 2026, Seller A, sales (should NOT be included in purchase pivot)
        inv4 = Invoice(
            id="MST_A-C26-0004",
            filename="sales_invoice_4.xml",
            invoice_type="sales",
            template_code="1/001",
            symbol="C26",
            number="0004",
            date="2026-02-12",
            currency="VND",
            seller_mst="0109999999", # active taxpayer is seller
            seller_name="CONG TY HOC TAP",
            buyer_mst="0101234567",
            buyer_name="NHÀ CUNG CẤP A",
            amount_before_tax=900000.0,
            tax_amount=90000.0,
            total_amount=990000.0,
            has_signature=True,
            imported_at=datetime.now().isoformat(),
            taxpayer_mst="0109999999"
        )

        # Invoice 5: Feb 2026, Seller A, purchase, OTHER taxpayer (tenant isolation)
        inv5 = Invoice(
            id="MST_A-C26-0005",
            filename="pur_invoice_other.xml",
            invoice_type="purchase",
            template_code="1/001",
            symbol="C26",
            number="0005",
            date="2026-02-20",
            currency="VND",
            seller_mst="0101234567",
            seller_name="NHÀ CUNG CẤP A",
            buyer_mst="0333333333", # Different buyer MST
            buyer_name="CONG TY KHAC",
            amount_before_tax=800000.0,
            tax_amount=80000.0,
            total_amount=880000.0,
            has_signature=True,
            imported_at=datetime.now().isoformat(),
            taxpayer_mst="0333333333"
        )

        db.session.add_all([inv1, inv2, inv3, inv4, inv5])
        db.session.commit()


def test_supplier_pivot_requires_login(client):
    """Verify anonymous users are rejected with 401."""
    response = client.get("/api/invoices/supplier-pivot")
    assert response.status_code == 401

    response = client.get("/api/invoices/supplier-pivot/export")
    assert response.status_code == 401


def test_supplier_pivot_json_success(logged_in_client, app):
    """Verify JSON pivot engine filters and aggregates correctly under tenant isolation."""
    _seed_test_invoices(app)

    response = logged_in_client.get("/api/invoices/supplier-pivot?year=2026&value_type=total_amount&taxpayer_mst=0109999999")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["success"] is True
    assert payload["year"] == "2026"
    assert payload["value_type"] == "total_amount"
    
    # Months should be 01 to 12
    assert len(payload["months"]) == 12
    assert payload["months"][0] == "01"
    assert payload["months"][11] == "12"

    rows = payload["rows"]
    # We should have 2 sellers in the purchase list: NHÀ CUNG CẤP A and NHÀ CUNG CẤP B
    # Sorted by grand total descending, so NHÀ CUNG CẤP A (1.1M + 2.2M = 3.3M) is first, NHÀ CUNG CẤP B (550k) is second
    assert len(rows) == 2
    
    row_a = rows[0]
    assert row_a["seller_mst"] == "0101234567"
    assert row_a["seller_name"] == "NHÀ CUNG CẤP A"
    assert row_a["monthly_values"]["01"] == 1100000.0
    assert row_a["monthly_values"]["02"] == 2200000.0
    assert row_a["monthly_values"]["03"] == 0.0
    assert row_a["row_total"] == 3300000.0

    row_b = rows[1]
    assert row_b["seller_mst"] == "0209876543"
    assert row_b["seller_name"] == "NHÀ CUNG CẤP B"
    assert row_b["monthly_values"]["01"] == 0.0
    assert row_b["monthly_values"]["02"] == 550000.0
    assert row_b["row_total"] == 550000.0

    # Total row checks
    totals = payload["column_totals"]
    assert totals["01"] == 1100000.0
    assert totals["02"] == 2750000.0
    assert totals["03"] == 0.0
    assert payload["grand_total"] == 3850000.0


def test_supplier_pivot_json_invoice_count(logged_in_client, app):
    """Verify pivot counts aggregate correctly."""
    _seed_test_invoices(app)

    response = logged_in_client.get("/api/invoices/supplier-pivot?year=2026&value_type=invoice_count&taxpayer_mst=0109999999")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True

    rows = payload["rows"]
    # Seller A: 1 in Jan, 1 in Feb = 2 total
    assert rows[0]["seller_mst"] == "0101234567"
    assert rows[0]["monthly_values"]["01"] == 1
    assert rows[0]["monthly_values"]["02"] == 1
    assert rows[0]["row_total"] == 2

    # Seller B: 0 in Jan, 1 in Feb = 1 total
    assert rows[1]["seller_mst"] == "0209876543"
    assert rows[1]["monthly_values"]["01"] == 0
    assert rows[1]["monthly_values"]["02"] == 1
    assert rows[1]["row_total"] == 1

    assert payload["grand_total"] == 3


def test_supplier_pivot_export_xlsx(logged_in_client, app):
    """Verify Excel download route returns a valid formatted spreadsheet."""
    _seed_test_invoices(app)

    response = logged_in_client.get("/api/invoices/supplier-pivot/export?year=2026&value_type=total_amount&taxpayer_mst=0109999999")
    assert response.status_code == 200
    assert response.content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    
    # Read xlsx from bytes
    wb = openpyxl.load_workbook(io.BytesIO(response.data))
    sheet = wb.active
    
    # Title is in row 1
    assert "BẢNG TỔNG HỢP HOÁ ĐƠN ĐẦU VÀO THEO NHÀ CUNG CẤP" in sheet["A1"].value
    # Taxpayer MST should be in row 2
    assert "Mã số thuế Doanh nghiệp:" in sheet["A2"].value
    
    # Header is in row 4
    # Column A: MST, B: Tên, C..N: Tháng 01..12, O: Tổng cộng
    headers = [cell.value for cell in sheet[4]]
    assert "Mã số thuế" in headers
    assert "Tên nhà cung cấp" in headers
    assert "Tháng 01" in headers
    assert "Tổng cộng" in headers

    # Row 5: NHÀ CUNG CẤP A (total_amount = 3.3M)
    assert sheet["A5"].value == "0101234567"
    assert sheet["B5"].value == "NHÀ CUNG CẤP A"
    assert sheet["C5"].value == 1100000.0
    assert sheet["D5"].value == 2200000.0
    assert sheet["O5"].value == 3300000.0

    # Row 6: NHÀ CUNG CẤP B (total_amount = 550k)
    assert sheet["A6"].value == "0209876543"
    assert sheet["B6"].value == "NHÀ CUNG CẤP B"
    assert sheet["C6"].value == 0.0
    assert sheet["D6"].value == 550000.0
    assert sheet["O6"].value == 550000.0

    # Row 7: Grand Totals
    assert sheet["A7"].value == "TỔNG CỘNG"
    assert sheet["C7"].value == 1100000.0
    assert sheet["D7"].value == 2750000.0
    assert sheet["O7"].value == 3850000.0
