"""Tests for US-360, US-361, US-362, and US-363 (OCR Pipeline, Scaffolding, HSM Signing, and GDT Sandbox)."""

import io
import json
import base64
import pytest
from unittest.mock import patch
from invoices.v24_compliance_service import (
    scaffold_xml_from_ocr_data,
    generate_hsm_mock_certificate,
    sign_xml_invoice,
    transmit_to_gdt_sandbox
)
from invoices.vision_service import VisionOCRService

def test_ocr_pipeline_confidence_scores(app):
    """US-360: Verify that physical invoice OCR pipeline returns confidence level per field."""
    with app.app_context():
        service = VisionOCRService()
        result = service.extract_invoice_data(b"dummy_bytes", "invoice.png", "image/png")
        
        assert "confidence_scores" in result
        scores = result["confidence_scores"]
        assert isinstance(scores, dict)
        for field in ["number", "date", "seller_mst", "buyer_mst", "total_amount"]:
            assert field in scores
            assert 0.0 <= scores[field] <= 1.0


def test_xml_scaffold_from_ocr_data():
    """US-361: Generate conforming e-invoice XML bytes from OCR JSON fields."""
    ocr_data = {
        "template_code": "1",
        "symbol": "C26TBA",
        "number": "123",
        "date": "2026-06-05",
        "seller_name": "Cong Ty Van Phong Pham",
        "seller_mst": "0100112233",
        "buyer_name": "Cong Ty Phat Trien Phieu",
        "buyer_mst": "0108999999",
        "amount_before_tax": 5000000.0,
        "tax_amount": 400000.0,
        "total_amount": 5400000.0,
        "payment_method": "TM/CK"
    }
    
    xml_bytes = scaffold_xml_from_ocr_data(ocr_data)
    xml_str = xml_bytes.decode("utf-8")
    
    assert "<HDon>" in xml_str
    assert "<SHDon>00000123</SHDon>" in xml_str  # Padding check
    assert "<MST>0100112233</MST>" in xml_str
    assert "<TgTTTBSo>5400000.0</TgTTTBSo>" in xml_str


def test_hsm_cryptographic_signing():
    """US-362: Sign XML using X.509 mock certificates and calculate digests."""
    xml_draft = scaffold_xml_from_ocr_data({
        "seller_name": "VIETTEL-CA Provider",
        "seller_mst": "0102030405",
        "total_amount": 10000.0
    })
    
    cert_der, priv_key = generate_hsm_mock_certificate("VIETTEL-CA Provider", "0102030405")
    signed_xml = sign_xml_invoice(xml_draft, cert_der, priv_key)
    
    signed_str = signed_xml.decode("utf-8")
    assert "<Signature" in signed_str
    assert "<X509Certificate>" in signed_str
    assert "<SignatureValue>" in signed_str
    
    # Ensure it parses as a valid XML
    import lxml.etree
    root = lxml.etree.fromstring(signed_xml)
    assert len(root.xpath("//*[local-name()='Signature']")) == 1


def test_gdt_transmission_sandbox_success_and_failures():
    """US-363: Verify responses from mock GDT receiving gateway sandbox."""
    # 1. Success case (Correct signature)
    xml_draft = scaffold_xml_from_ocr_data({
        "seller_name": "Cong Ty ABC",
        "seller_mst": "0100112233",
        "date": "2026-06-05"
    })
    cert_der, priv_key = generate_hsm_mock_certificate("Cong Ty ABC", "0100112233")
    signed_xml = sign_xml_invoice(xml_draft, cert_der, priv_key)
    
    resp_success = transmit_to_gdt_sandbox(signed_xml)
    assert resp_success["status_code"] == "00"
    assert resp_success["gdt_code"].startswith("GDT-")
    
    # 2. Signature failure case (Tamped XML)
    tamped_xml_str = signed_xml.decode("utf-8").replace("Cong Ty ABC", "Cong Ty TAMPED")
    resp_tamper = transmit_to_gdt_sandbox(tamped_xml_str.encode("utf-8"))
    assert resp_tamper["status_code"] == "01"
    
    # 3. Format error case (Invalid XML tags structure)
    bad_xml = b"<HDon><BadTag>Error</BadTag></HDon>"
    resp_bad = transmit_to_gdt_sandbox(bad_xml)
    assert resp_bad["status_code"] == "02"


def test_api_routes_ocr_signing_sandbox(client, logged_in_client):
    """Test flask API compliance routes for OCR, Scaffolding, HSM Sign and GDT Transmit."""
    # 1. Scaffold API
    payload = {
        "seller_name": "Cong Ty Cung Cap",
        "seller_mst": "0100223344",
        "total_amount": 250000.0
    }
    resp = logged_in_client.post("/api/invoices/scaffold-xml", json={"ocr_data": payload})
    assert resp.status_code == 200
    res_json = resp.get_json()
    assert res_json["status"] == "success"
    xml_draft = res_json["xml"]
    assert "<HDon>" in xml_draft
    
    # 2. Sign HSM API
    resp_sign = logged_in_client.post("/api/invoices/sign-hsm", json={"xml": xml_draft})
    assert resp_sign.status_code == 200
    res_sign_json = resp_sign.get_json()
    assert res_sign_json["status"] == "success"
    signed_xml = res_sign_json["signed_xml"]
    assert "<Signature" in signed_xml
    
    # 3. GDT Gateway Transmit API
    resp_transmit = logged_in_client.post("/api/gdt-sandbox/transmit", json={"signed_xml": signed_xml})
    assert resp_transmit.status_code == 200
    res_transmit_json = resp_transmit.get_json()
    assert res_transmit_json["status_code"] == "00"
    assert "gdt_code" in res_transmit_json
