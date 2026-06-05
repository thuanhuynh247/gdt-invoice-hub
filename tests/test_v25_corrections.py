"""Tests for US-372 and US-373 (E-Invoice Correction/Replacement & Form 04/SS-HĐĐT)."""

import pytest
import lxml.etree
from extensions import db
from invoices.models import Invoice
from invoices.v25_compliance_service import generate_correction_or_replacement_xml, generate_form_04_ss_xml

def test_generate_correction_or_replacement_xml(app):
    """US-372: Verify generation of correction and replacement XML linking back to original invoices."""
    with app.app_context():
        orig_invoice = Invoice(
            id="0100112233-C26TBA-00000001",
            number="00000001",
            symbol="C26TBA",
            template_code="1",
            date="2026-06-05",
            seller_mst="0100112233",
            seller_name="Seller A",
            buyer_mst="0108999999",
            buyer_name="Buyer B",
            amount_before_tax=100000.0,
            tax_amount=10000.0,
            total_amount=110000.0,
            payment_method="TM/CK",
            has_signature=True,
            notes="GDT Approval Code: GDT-ABC123XYZ789"
        )
        
        # Scenario A: Replacement XML
        new_data = {
            "number": "00000002",
            "total_amount": 120000.0,
            "items": [
                {"item_name": "Sản phẩm thay thế", "quantity": 1.0, "unit_price": 120000.0, "amount_before_tax": 120000.0, "tax_rate": "10%", "tax_amount": 12000.0}
            ]
        }
        
        xml_bytes = generate_correction_or_replacement_xml(orig_invoice, new_data, "replacement")
        xml_str = xml_bytes.decode("utf-8")
        
        assert "Thay thế" in xml_str
        assert "<LHDon>1</LHDon>" in xml_str
        assert "<SHDonGoc>00000001</SHDonGoc>" in xml_str
        assert "<MaGoc>GDT-ABC123XYZ789</MaGoc>" in xml_str

        # Scenario B: Correction XML
        xml_bytes_corr = generate_correction_or_replacement_xml(orig_invoice, new_data, "correction")
        xml_str_corr = xml_bytes_corr.decode("utf-8")
        assert "Điều chỉnh" in xml_str_corr
        assert "<LHDon>2</LHDon>" in xml_str_corr


def test_generate_form_04_ss_xml():
    """US-373: Verify generation of Form 04/SS-HĐĐT reporting list of incorrect invoices to GDT."""
    bad_invoices = [
        {
            "original_number": "00000001",
            "original_symbol": "C26TBA",
            "original_template": "1",
            "original_date": "2026-06-05",
            "gdt_code": "GDT-ABC123XYZ789",
            "reason": "Sai đơn giá hàng hóa",
            "error_type": "2"
        }
    ]
    
    xml_bytes = generate_form_04_ss_xml("0108999999", "Company Name", bad_invoices)
    xml_str = xml_bytes.decode("utf-8")
    
    assert "Company Name" in xml_str
    assert "0108999999" in xml_str
    assert "<HDSSSot>" in xml_str
    assert "<LSSSot>2</LSSSot>" in xml_str
    assert "<LDo>Sai đơn giá hàng hóa</LDo>" in xml_str
