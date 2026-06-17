"""Tests for Version 27.0.0 compliance, tax risk radar, and treasury sandbox (US-390 to US-395)."""

from __future__ import annotations

import json
from datetime import datetime
import pytest

from invoices.v27_service import (
    parse_delivery_note_xml,
    reconcile_delivery_to_invoice,
    export_delivery_reconciliation_csv,
    calculate_pre_audit_risk,
    generate_svg_radar_chart,
    parse_econtract_metadata,
    reconcile_contract_milestones,
    simulate_treasury_forecast
)


def test_pxk_xml_parsing_and_validation():
    """US-390: Test parsing of electronic delivery note (PXK) xml with signature check."""
    valid_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <HDon>
        <DLHDon>
            <TTChung>
                <SoPXK>PXK-2026-001</SoPXK>
                <NgayXuat>2026-06-01</NgayXuat>
                <KhoXuat>Kho Hà Nội</KhoXuat>
                <KhoNhap>Kho Sài Gòn</KhoNhap>
                <NguoiVanChuyen>Nguyễn Văn A</NguoiVanChuyen>
                <PhuongTienVanChuyen>Xe tải</PhuongTienVanChuyen>
                <ContractRef>HĐ-099/BTC</ContractRef>
            </TTChung>
            <NDHDon>
                <GoodsItem>
                    <MaHang>SKU-1001</MaHang>
                    <TenHang>Bộ Vi Xử Lý Intel Core i9</TenHang>
                    <DonViTinh>Cái</DonViTinh>
                    <SoLuong>15</SoLuong>
                </GoodsItem>
                <GoodsItem>
                    <MaHang>SKU-1002</MaHang>
                    <TenHang>RAM Corsair Vengeance 64GB</TenHang>
                    <DonViTinh>Bộ</DonViTinh>
                    <SoLuong>30</SoLuong>
                </GoodsItem>
            </NDHDon>
        </DLHDon>
        <Signature>
            <SignedInfo>
                <Reference URI="GDT-Decree123-Sign" />
            </SignedInfo>
            <SignatureValue>MOCK_SIGNATURE</SignatureValue>
        </Signature>
    </HDon>"""

    parsed = parse_delivery_note_xml(valid_xml)
    assert parsed["status"] == "valid"
    assert parsed["so_pxk"] == "PXK-2026-001"
    assert parsed["ngay_xuat"] == "2026-06-01"
    assert len(parsed["goods"]) == 2
    assert parsed["goods"][0]["sku"] == "SKU-1001"
    assert parsed["goods"][0]["quantity"] == 15.0

    # Test unsigned XML
    unsigned_xml = valid_xml.replace("<Signature>", "<!--").replace("</Signature>", "-->").replace("<SignatureValue>", "").replace("</SignatureValue>", "").replace("Signature", "Sig")
    parsed_unsigned = parse_delivery_note_xml(unsigned_xml)
    assert parsed_unsigned["status"] == "unsigned"
    assert not parsed_unsigned["has_signature"]


def test_pxk_to_invoice_reconciliation():
    """US-391: Test matching delivery items against invoice lines and exporting CSV."""
    delivery_notes = [
        {
            "so_pxk": "PXK-2026-001",
            "ngay_xuat": "2026-06-01",
            "goods": [
                {"sku": "SKU-1001", "name": "Intel Core i9", "quantity": 15.0},
                {"sku": "SKU-1002", "name": "RAM Corsair", "quantity": 30.0}
            ]
        },
        {
            "so_pxk": "PXK-2026-002",
            "ngay_xuat": "2026-06-02",
            "goods": [
                {"sku": "SKU-1003", "name": "SSD Samsung", "quantity": 50.0}
            ]
        }
    ]

    invoices = [
        {
            "invoice_no": "INV-001",
            "reference_no": "PXK-2026-001",
            "invoice_date": "2026-06-02",
            "line_items": [
                {"sku": "SKU-1001", "name": "Intel Core i9", "quantity": 15.0},
                {"sku": "SKU-1002", "name": "RAM Corsair", "quantity": 28.0}  # Lệch 2
            ]
        }
    ]

    report = reconcile_delivery_to_invoice(delivery_notes, invoices)
    assert report["status"] == "flagged"
    assert len(report["matched_records"]) == 1
    assert len(report["unmatched_deliveries"]) == 1
    assert report["matched_records"][0]["status"] == "discrepancy"
    assert len(report["matched_records"][0]["discrepancies"]) == 1
    assert report["matched_records"][0]["discrepancies"][0]["sku"] == "SKU-1002"
    assert report["matched_records"][0]["discrepancies"][0]["variance"] == -2.0

    csv_data = export_delivery_reconciliation_csv(report)
    assert "BÁO CÁO ĐỐI CHIẾU PHIẾU XUẤT KHO VÀ HÓA ĐƠN THƯƠNG MẠI" in csv_data
    assert "PXK-2026-001" in csv_data
    assert "SKU-1002" in csv_data
    assert "PXK-2026-002" in csv_data


def test_pre_audit_corporate_tax_risk_radar():
    """US-392 & US-393: Test pre-audit scoring, risk radar plotting and suggestions."""
    profile = {"mst": "0109999999", "company_name": "Công ty Ánh Sáng"}
    
    invoices = [
        {"invoice_id": "INV-001", "seller_mst": "0109999999", "direction": "in", "amount": 25000000.0, "payment_method": "CASH", "status": "ACTIVE", "delivery_date": "2026-06-01", "invoice_date": "2026-06-15"}, # Timing latency (>10 days) & cash violation (>=20M)
        {"invoice_id": "INV-002", "seller_mst": "0202020202", "direction": "in", "amount": 10000000.0, "payment_method": "BANK", "status": "CANCELLED"}, # Cancellation & Blacklist supplier
    ]

    related_party = {
        "ebitda": 2000000000.0,
        "net_interest": 900000000.0 # Ratio = 45% (>30% limit)
    }

    report = calculate_pre_audit_risk(profile, invoices, related_party)
    assert report["status"] in ["warning", "critical"]
    assert report["scores"]["related_party"] == 100.0
    assert report["scores"]["blacklist"] == 100.0
    assert report["scores"]["latency"] == 100.0
    assert report["scores"]["cash_limit"] > 0
    assert report["scores"]["cancellation"] == 100.0
    assert report["risk_index"] > 50.0
    assert len(report["advisory_notes"]) > 0

    # Test SVG generator
    svg = generate_svg_radar_chart(report["scores"])
    assert "<svg" in svg
    assert "Giao dịch liên kết" in svg
    assert "polygon" in svg


def test_econtract_parsing_and_reconciliation():
    """US-394: Test structured e-contract milestones tracker."""
    contract_json = """{
        "contract_no": "CTR-2026-888",
        "effective_date": "2026-06-01",
        "contract_value": 500000000.0,
        "supplier_name": "Công ty A",
        "customer_name": "Công ty B",
        "milestones": [
            {"due_date": "2026-06-10", "percentage": 40.0, "description": "Đợt 1"},
            {"due_date": "2026-07-10", "percentage": 60.0, "description": "Đợt 2"}
        ]
    }"""

    parsed = parse_econtract_metadata(contract_json)
    assert parsed["contract_no"] == "CTR-2026-888"
    assert parsed["contract_value"] == 500000000.0
    assert len(parsed["milestones"]) == 2
    assert parsed["milestones"][0]["value"] == 200000000.0

    # Reconcile milestones
    invoices = [
        {"contract_ref": "CTR-2026-888", "amount": 200000000.0}
    ]
    payments = [
        {"contract_ref": "CTR-2026-888", "amount": 150000000.0}
    ]

    report = reconcile_contract_milestones(parsed, invoices, payments)
    assert report["status"] == "flagged"
    assert report["total_invoiced"] == 200000000.0
    assert report["total_paid"] == 150000000.0
    assert report["reconciled_milestones"][0]["allocated_paid"] == 150000000.0
    assert report["reconciled_milestones"][0]["status"] == "partially_paid"


def test_treasury_forecast_sandbox_simulation():
    """US-395: Test daily cash flow projections and CIT/VAT sandbox estimation."""
    milestones = [
        {"due_date": "2026-06-10", "milestone_value": 200000000.0}
    ]
    invoices = [
        {"direction": "in", "invoice_date": "2026-06-01", "amount": 50000000.0, "status": "ACTIVE"} # Net 30 -> outflow 2026-07-01
    ]

    forecast = simulate_treasury_forecast(
        milestones=milestones,
        invoices=invoices,
        starting_cash=100000000.0,
        delay_days=10, # Collection moves from 2026-06-10 to 2026-06-20
        cit_discount=0.20 # 20% discount on corporate tax
    )

    assert forecast["starting_cash"] == 100000000.0
    assert forecast["ending_cash"] == 250000000.0
    assert forecast["total_projected_inflow"] == 200000000.0
    assert forecast["total_projected_outflow"] == 50000000.0
    assert forecast["projected_vat_obligation"] > 0
    assert forecast["projected_cit_obligation"] > 0
    assert len(forecast["timeline"]) == 61


def test_v27_endpoints(logged_in_client):
    """Test flask routing, payload parsing, and responses for Version 27 compliance panel."""
    # 1. Page render
    resp = logged_in_client.get("/v27-compliance")
    assert resp.status_code == 200

    # 2. PXK Parse API
    xml_data = """<?xml version="1.0" encoding="UTF-8"?>
    <HDon>
        <DLHDon>
            <TTChung>
                <SoPXK>PXK-27-TEST</SoPXK>
            </TTChung>
            <NDHDon>
                <GoodsItem>
                    <MaHang>SKU-99</MaHang>
                    <SoLuong>10</SoLuong>
                </GoodsItem>
            </NDHDon>
        </DLHDon>
    </HDon>"""
    resp = logged_in_client.post("/api/compliance/pxk-parse", json={"xml_content": xml_data})
    assert resp.status_code == 200
    parsed = resp.get_json()
    assert parsed["so_pxk"] == "PXK-27-TEST"

    # 3. PXK Reconcile
    body = {
        "delivery_notes": [parsed],
        "invoices": [
            {
                "reference_no": "PXK-27-TEST",
                "invoice_no": "INV-27-TEST",
                "line_items": [{"sku": "SKU-99", "quantity": 10}]
            }
        ]
    }
    resp = logged_in_client.post("/api/compliance/pxk-reconcile", json=body)
    assert resp.status_code == 200
    report = resp.get_json()
    assert report["status"] == "compliant"

    # 4. PXK Export CSV
    resp = logged_in_client.post("/api/compliance/pxk-export-csv", json=body)
    assert resp.status_code == 200
    assert resp.mimetype == "text/csv"
    assert b"PXK-27-TEST" in resp.data

    # 5. Pre-Audit Tax Risk
    risk_body = {
        "invoices": [{"amount": 25000000.0, "payment_method": "CASH"}],
        "related_party_context": {"ebitda": 1000000.0, "net_interest": 500000.0}
    }
    resp = logged_in_client.post("/api/compliance/pre-audit-risk", json=risk_body)
    assert resp.status_code == 200
    report = resp.get_json()
    assert report["risk_index"] > 0

    # 6. SVG Radar
    svg_body = {"scores": report["scores"]}
    resp = logged_in_client.post("/api/compliance/risk-radar-svg", json=svg_body)
    assert resp.status_code == 200
    svg_data = resp.get_json()
    assert "<svg" in svg_data["svg_markup"]

    # 7. E-Contract Parse
    contract_json = """{
        "contract_no": "CTR-27",
        "effective_date": "2026-06-01",
        "contract_value": 1000000.0,
        "milestones": [{"due_date": "2026-05-10", "percentage": 100.0}]
    }"""
    resp = logged_in_client.post("/api/compliance/econtract-parse", json={"json_content": contract_json})
    assert resp.status_code == 200
    contract_data = resp.get_json()
    assert contract_data["contract_no"] == "CTR-27"

    # 8. E-Contract Reconcile
    recon_body = {
        "contract": contract_data,
        "invoices": [],
        "payments": []
    }
    resp = logged_in_client.post("/api/compliance/econtract-reconcile", json=recon_body)
    assert resp.status_code == 200
    recon_data = resp.get_json()
    assert recon_data["status"] == "flagged"

    # 9. Treasury Forecast
    forecast_body = {
        "milestones": contract_data["milestones"],
        "invoices": [],
        "starting_cash": 500000.0,
        "delay_days": 10,
        "cit_discount": 0.10
    }
    resp = logged_in_client.post("/api/compliance/treasury-forecast", json=forecast_body)
    assert resp.status_code == 200
    forecast_data = resp.get_json()
    assert len(forecast_data["timeline"]) == 61
