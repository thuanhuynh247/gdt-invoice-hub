"""Unit and integration tests for Foreign Contractor Tax (FCT/NTNN) Auditor and Mẫu 01/NTNN generator."""

from __future__ import annotations

from datetime import datetime
from extensions import db
from invoices.models import Invoice, LineItem


def _seed_fct_test_invoices(app):
    """Seed a rich mix of FCT-applicable and domestic invoices for calculation testing."""
    with app.app_context():
        LineItem.query.delete()
        Invoice.query.delete()
        db.session.commit()

        # 1. Foreign Contractor: Google Ads (MST starts with 900, Advertising category)
        inv_f1 = Invoice(
            id="FCT-001",
            filename="google_ads.xml",
            invoice_type="purchase",
            number="10001",
            date="2026-05-10",
            currency="VND",
            seller_mst="9001234567",
            seller_name="Google Asia Pacific Pte. Ltd.",
            buyer_mst="0109999999",
            buyer_name="CONG TY TIEN PHONG",
            amount_before_tax=10000000.0,
            tax_amount=0.0,
            total_amount=10000000.0,
            has_signature=True,
            imported_at=datetime.now().isoformat()
        )
        item_f1 = LineItem(
            invoice_id="FCT-001",
            item_name="Google Ads - Online advertising campaign",
            quantity=1,
            unit_price=10000000.0,
            amount_before_tax=10000000.0,
            tax_rate="0%",
            tax_amount=0.0
        )

        # 2. Foreign Contractor: Zoom SaaS (Name match, SaaS category - VAT Exempt)
        inv_f2 = Invoice(
            id="FCT-002",
            filename="zoom_saas.xml",
            invoice_type="purchase",
            number="10002",
            date="2026-05-15",
            currency="VND",
            seller_mst="9007654321",
            seller_name="Zoom Video Communications Inc",
            buyer_mst="0109999999",
            buyer_name="CONG TY TIEN PHONG",
            amount_before_tax=5000000.0,
            tax_amount=0.0,
            total_amount=5000000.0,
            has_signature=True,
            imported_at=datetime.now().isoformat()
        )
        item_f2 = LineItem(
            invoice_id="FCT-002",
            item_name="Zoom Pro Subscription License",
            quantity=10,
            unit_price=500000.0,
            amount_before_tax=5000000.0,
            tax_rate="0%",
            tax_amount=0.0
        )

        # 3. Foreign Contractor: AWS (Name match, Cloud/Hosting category - 5% VAT, 5% CIT)
        inv_f3 = Invoice(
            id="FCT-003",
            filename="aws_cloud.xml",
            invoice_type="purchase",
            number="10003",
            date="2026-05-20",
            currency="VND",
            seller_mst="",
            seller_name="Amazon Web Services (AWS)",
            buyer_mst="0109999999",
            buyer_name="CONG TY TIEN PHONG",
            amount_before_tax=20000000.0,
            tax_amount=0.0,
            total_amount=20000000.0,
            has_signature=True,
            imported_at=datetime.now().isoformat()
        )
        item_f3 = LineItem(
            invoice_id="FCT-003",
            item_name="AWS Cloud computing EC2 and S3 hosting services",
            quantity=1,
            unit_price=20000000.0,
            amount_before_tax=20000000.0,
            tax_rate="0%",
            tax_amount=0.0
        )

        # 4. Non-FCT: Regular domestic purchase invoice
        inv_dom = Invoice(
            id="DOMESTIC-001",
            filename="domestic.xml",
            invoice_type="purchase",
            number="0054",
            date="2026-05-25",
            currency="VND",
            seller_mst="0101112223",
            seller_name="CONG TY CUNG CAP TRONG NUOC",
            buyer_mst="0109999999",
            buyer_name="CONG TY TIEN PHONG",
            amount_before_tax=15000000.0,
            tax_amount=1500000.0,
            total_amount=16500000.0,
            has_signature=True,
            imported_at=datetime.now().isoformat()
        )

        db.session.add_all([inv_f1, item_f1, inv_f2, item_f2, inv_f3, item_f3, inv_dom])
        db.session.commit()


def test_fct_declaration_requires_login(client):
    """Ensure FCT declaration endpoint rejects anonymous users."""
    response = client.get("/api/reports/fct-declaration?period_type=monthly&period_value=05&year=2026")
    assert response.status_code in [302, 401]


def test_fct_declaration_calculation(app, logged_in_client):
    """Verify that foreign contractors are classified and calculated correctly under Circular 103 rules."""
    _seed_fct_test_invoices(app)

    response = logged_in_client.get("/api/reports/fct-declaration?period_type=monthly&period_value=05&year=2026")
    assert response.status_code == 200
    
    data = response.get_json()
    assert data["success"] is True
    assert data["year"] == "2026"
    assert data["period_value"] == "05"
    
    # 3 FCT invoices total: 10,000,000 (Google) + 5,000,000 (Zoom) + 20,000,000 (AWS) = 35,000,000
    assert data["total_revenue"] == 35000000.0
    
    # Google Ads (10M): 5% VAT = 500k, 5% CIT = 500k
    # Zoom SaaS (5M): 0% VAT = 0, 5% CIT = 250k
    # AWS Cloud (20M): 5% VAT = 1.0M, 5% CIT = 1.0M
    # Total VAT withheld = 500k + 0 + 1.0M = 1.5M
    # Total CIT withheld = 500k + 250k + 1.0M = 1.75M
    assert data["total_vat_withheld"] == 1500000.0
    assert data["total_cit_withheld"] == 1750000.0
    assert data["total_fct_payable"] == 3250000.0
    
    # Check individual rows
    invoices = data["fct_invoices"]
    assert len(invoices) == 3
    
    google_row = next(i for i in invoices if "Google" in i["seller_name"])
    assert google_row["vat_rate"] == 0.05
    assert google_row["cit_rate"] == 0.05
    assert google_row["vat_withheld"] == 500000.0
    assert google_row["cit_withheld"] == 500000.0
    
    zoom_row = next(i for i in invoices if "Zoom" in i["seller_name"])
    assert zoom_row["vat_rate"] == 0.00
    assert zoom_row["cit_rate"] == 0.05
    assert zoom_row["vat_withheld"] == 0.0
    assert zoom_row["cit_withheld"] == 250000.0


def test_fct_excel_export_requires_login(client):
    """Ensure FCT Excel export route rejects anonymous users."""
    response = client.get("/api/reports/fct-declaration/export-excel?period_type=monthly&period_value=05&year=2026")
    assert response.status_code in [302, 401]


def test_fct_excel_export_success(app, logged_in_client):
    """Verify that a valid Excel stream is returned by the FCT Excel exporter."""
    _seed_fct_test_invoices(app)

    response = logged_in_client.get("/api/reports/fct-declaration/export-excel?period_type=monthly&period_value=05&year=2026")
    assert response.status_code == 200
    assert response.mimetype == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert "ToKhai_01NTNN_2026_05.xlsx" in response.headers.get("Content-Disposition", "")
    
    # Check binary signature of xlsx zip file
    assert response.data.startswith(b"PK\x03\x04")
