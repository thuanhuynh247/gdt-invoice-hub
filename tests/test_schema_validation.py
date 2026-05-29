"""Unit tests for GDT XML XSD Schema Validation (US-047)."""

from __future__ import annotations
import pytest
from invoices.schema_validator import validate_xml_schema
from invoices.service import import_xml_invoice
from invoices.models import Invoice
from extensions import db


VALID_XML_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<HDon>
  <DLHDon>
    <TTChung>
      <THDon>Hóa đơn giá trị gia tăng</THDon>
      <KHMSHDon>1</KHMSHDon>
      <KHHDon>C26TBA</KHHDon>
      <SHDon>12345678</SHDon>
      <NLap>2026-05-26</NLap>
    </TTChung>
    <NDHDon>
      <NBan>
        <Ten>Cong ty TNHH Thiet bi So A</Ten>
        <MST>0101234567</MST>
        <DChi>Ha Noi</DChi>
      </NBan>
      <NMua>
        <TenDonVi>Cong ty TNHH Giai Phap Cong Nghe</TenDonVi>
        <MST>0309876543</MST>
        <DChi>TP HCM</DChi>
      </NMua>
      <DSDVu>
        <HHDVu>
          <Ten>Laptop Dell Latitude 7420</Ten>
          <SLuong>1</SLuong>
          <DGia>20000000</DGia>
          <ThTien>20000000</ThTien>
          <TSuat>10%</TSuat>
          <TThue>2000000</TThue>
        </HHDVu>
      </DSDVu>
    </NDHDon>
  </DLHDon>
</HDon>
"""

INVALID_XML_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<HDon>
  <DLHDon>
    <TTChung>
      <THDon>Hóa đơn giá trị gia tăng</THDon>
      <!-- Missing KHHDon, SHDon, and NLap which are required by XSD -->
    </TTChung>
    <NDHDon>
      <NBan>
        <Ten>Cong ty TNHH Thiet bi So A</Ten>
        <MST>0101234567</MST>
        <DChi>Ha Noi</DChi>
      </NBan>
    </NDHDon>
  </DLHDon>
</HDon>
"""


def test_validate_xml_schema_valid():
    """Verify that a valid invoice XML passes XSD validation."""
    xml_bytes = VALID_XML_TEMPLATE.encode("utf-8")
    is_valid, err = validate_xml_schema(xml_bytes)
    assert is_valid is True
    assert err is None


def test_validate_xml_schema_invalid():
    """Verify that an invalid invoice XML fails XSD validation and returns an error."""
    xml_bytes = INVALID_XML_TEMPLATE.encode("utf-8")
    is_valid, err = validate_xml_schema(xml_bytes)
    assert is_valid is False
    assert err is not None
    assert "XSD Schema Validation Error" in err or "XML Syntax Error" in err


def test_import_xml_invoice_with_valid_xsd(app):
    """Verify that import_xml_invoice sets status 'imported' for a valid XSD invoice."""
    with app.app_context():
        # Clear existing
        Invoice.query.delete()
        db.session.commit()

        from invoices.scheduler import save_scheduler_settings
        save_scheduler_settings({
            "signature_filter_enabled": False,
            "blacklist_filter_enabled": False
        })

        xml_bytes = VALID_XML_TEMPLATE.encode("utf-8")
        res = import_xml_invoice(xml_bytes, "valid_invoice.xml")
        
        assert res["import_status"] == "imported"
        
        # Verify db record
        record = db.session.get(Invoice, res["id"])
        assert record is not None
        assert record.import_status == "imported"
        # XSD validation should not append structural error warnings
        assert not any("Cấu trúc XSD:" in w for w in record.warnings)


def test_import_xml_invoice_with_invalid_xsd(app):
    """Verify that import_xml_invoice sets status 'XSD_VALIDATION_FAILED' for an invalid XSD invoice."""
    with app.app_context():
        # Clear existing
        Invoice.query.delete()
        db.session.commit()

        from invoices.scheduler import save_scheduler_settings
        save_scheduler_settings({
            "signature_filter_enabled": False,
            "blacklist_filter_enabled": False
        })

        xml_bytes = INVALID_XML_TEMPLATE.encode("utf-8")
        # Set template code, symbol, number to make it parse-able by parser fallback
        # (Though we omitted it in XSD, parse_complete_xml uses fallbacks)
        res = import_xml_invoice(xml_bytes, "invalid_invoice.xml")
        
        assert res["import_status"] == "XSD_VALIDATION_FAILED"
        
        # Verify db record
        record = db.session.get(Invoice, res["id"])
        assert record is not None
        assert record.import_status == "XSD_VALIDATION_FAILED"
        # Check warnings
        assert any("Cấu trúc XSD:" in w for w in record.warnings)
