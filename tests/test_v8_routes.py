"""Tests for Version 8.0.0 Flask API routes (US-110 to US-115)."""

from __future__ import annotations

import base64
import json
from datetime import datetime
import pytest
from extensions import db
from invoices.models import TaxpayerProfile, Invoice

@pytest.fixture(autouse=True)
def disable_security_filters(app):
    with app.app_context():
        from invoices.scheduler import save_scheduler_settings
        save_scheduler_settings({
            "signature_filter_enabled": False,
            "blacklist_filter_enabled": False
        })


@pytest.fixture
def seeded_taxpayer_profile(app):
    """Seed a test taxpayer profile."""
    with app.app_context():
        # Clean any leftover profiles
        Invoice.query.delete()
        TaxpayerProfile.query.delete()
        db.session.commit()

        profile = TaxpayerProfile(
            mst="0102030405",
            company_name="Cong ty TNHH Thuong Mai Test",
            gdt_username="test_user",
            gdt_password_encrypted="encrypted_pw",
            is_active=True,
            created_at="2026-05-01T00:00:00"
        )
        db.session.add(profile)
        db.session.commit()
        return profile


def test_api_forecast_tax_raw_payload(logged_in_client):
    """POST /api/analytics/forecast should calculate tax forecast from user raw payload."""
    payload = {
        "historical_data": [
            {"period": "2026-01", "output_vat": 10_000_000, "input_vat": 8_000_000},
            {"period": "2026-02", "output_vat": 12_000_000, "input_vat": 9_000_000},
            {"period": "2026-03", "output_vat": 15_000_000, "input_vat": 11_000_000},
        ],
        "projected_period": "2026-04",
        "alpha": 0.7,
        "window_size": 3,
        "budget_limit": 5_000_000
    }
    response = logged_in_client.post("/api/analytics/forecast", json=payload)
    assert response.status_code == 200
    res_data = response.get_json()
    assert "forecast" in res_data
    forecast = res_data["forecast"]
    assert forecast["projected_period"] == "2026-04"
    assert forecast["projected_output_vat"] > 0.0
    assert forecast["projected_input_vat"] > 0.0
    assert forecast["projected_vat_payable"] == round(forecast["projected_output_vat"] - forecast["projected_input_vat"], 2)


def test_api_forecast_tax_from_db(logged_in_client, seeded_taxpayer_profile, app):
    """POST /api/analytics/forecast should query database invoices when no payload is provided."""
    # Seed session
    with logged_in_client.session_transaction() as sess:
        sess["active_taxpayer_mst"] = "0102030405"

    with app.app_context():
        # Add historical invoices to DB
        inv1 = Invoice(
            id="999-001",
            seller_mst="999999999",  # seller != us => purchase (input VAT)
            buyer_mst="0102030405",
            taxpayer_mst="0102030405",
            tax_amount=2_000_000.0,
            amount_before_tax=20_000_000.0,
            total_amount=22_000_000.0,
            date="2026-01-10",
            imported_at="2026-05-01T00:00:00",
            is_cancelled=False
        )
        inv2 = Invoice(
            id="0102030405-002",
            seller_mst="0102030405",  # seller == us => sale (output VAT)
            buyer_mst="888888888",
            taxpayer_mst="0102030405",
            tax_amount=5_000_000.0,
            amount_before_tax=50_000_000.0,
            total_amount=55_000_000.0,
            date="2026-01-15",
            imported_at="2026-05-01T00:00:00",
            is_cancelled=False
        )
        db.session.add_all([inv1, inv2])
        db.session.commit()

    payload = {
        "projected_period": "2026-02",
        "budget_limit": 10_000_000
    }
    response = logged_in_client.post("/api/analytics/forecast", json=payload)
    assert response.status_code == 200
    res_data = response.get_json()
    assert "forecast" in res_data
    forecast = res_data["forecast"]
    assert forecast["projected_period"] == "2026-02"
    assert forecast["historical_periods_used"] == ["2026-01"]
    assert forecast["projected_output_vat"] == 5_000_000.0
    assert forecast["projected_input_vat"] == 2_000_000.0
    assert forecast["projected_vat_payable"] == 3_000_000.0
    assert forecast["alert_triggered"] is False


def test_api_batch_parse_and_import(logged_in_client, seeded_taxpayer_profile):
    """POST /api/invoices/batch-parse should support base64 decompressed XML batches and persist them."""
    with logged_in_client.session_transaction() as sess:
        sess["active_taxpayer_mst"] = "0102030405"

    xml_str = """<?xml version="1.0" encoding="UTF-8"?>
    <HDon>
        <DLHDon>
            <SHDon>0099999</SHDon>
            <MSTNBan>0102030405</MSTNBan>
            <MSTNMua>0908070605</MSTNMua>
            <TgTCThue>1000000</TgTCThue>
            <TgTThue>100000</TgTThue>
            <TgTTTBSo>1100000</TgTTTBSo>
        </DLHDon>
    </HDon>
    """
    import zlib
    compressed_bytes = zlib.compress(xml_str.encode("utf-8"), level=9)
    b64_content = base64.b64encode(compressed_bytes).decode("utf-8")

    payload = {
        "invoices": [
            {"filename": "normal.xml", "content": xml_str, "compressed": False},
            {"filename": "compressed.xml", "content": b64_content, "compressed": True}
        ],
        "duplicate_strategy": "overwrite"
    }

    response = logged_in_client.post("/api/invoices/batch-parse", json=payload)
    assert response.status_code == 200
    res_data = response.get_json()
    assert res_data["total_processed"] == 2
    assert res_data["results"][0]["success"] is True
    assert res_data["results"][0]["invoice_number"] == "00099999"


def test_api_get_kpis_and_export(logged_in_client, seeded_taxpayer_profile, app):
    """GET /api/analytics/kpis and /export should return financial KPIs and downloadable CSV."""
    with logged_in_client.session_transaction() as sess:
        sess["active_taxpayer_mst"] = "0102030405"

    with app.app_context():
        inv1 = Invoice(
            id="0102030405-S1",
            seller_mst="0102030405",  # Sales
            buyer_mst="888888888",
            taxpayer_mst="0102030405",
            tax_amount=20_000_000.0,
            amount_before_tax=200_000_000.0,
            total_amount=220_000_000.0,
            date="2026-05-10",
            paid_date="2026-05-15",  # Clearance: 5 days
            imported_at="2026-05-01T00:00:00",
            is_cancelled=False
        )
        inv2 = Invoice(
            id="P999-0102030405",
            seller_mst="999999999",  # Purchase
            buyer_mst="0102030405",
            taxpayer_mst="0102030405",
            tax_amount=10_000_000.0,
            amount_before_tax=100_000_000.0,
            total_amount=110_000_000.0,
            date="2026-05-12",
            imported_at="2026-05-01T00:00:00",
            is_cancelled=False
        )
        db.session.add_all([inv1, inv2])
        db.session.commit()

    # 1. Check GET kpis
    response = logged_in_client.get("/api/analytics/kpis")
    assert response.status_code == 200
    res_data = response.get_json()
    assert res_data["taxpayer_mst"] == "0102030405"
    assert res_data["overall"]["gross_margin_percent"] == 50.0
    assert res_data["overall"]["tax_to_revenue_percent"] == 5.0
    assert res_data["overall"]["average_payment_period_days"] == 5.0

    # Check monthly trend breakdown
    assert "2026-05" in res_data["monthly_trends"]
    assert res_data["monthly_trends"]["2026-05"]["gross_margin_percent"] == 50.0

    # 2. Check GET kpi export CSV
    export_response = logged_in_client.get("/api/analytics/kpis/export")
    assert export_response.status_code == 200
    assert export_response.mimetype == "text/csv"
    assert "Content-Disposition" in export_response.headers
    assert "attachment; filename=" in export_response.headers["Content-Disposition"]
    
    csv_text = export_response.get_data(as_text=True)
    assert "Period" in csv_text
    assert "2026-05" in csv_text
    assert "50.00" in csv_text
