"""Parsing and validation tests."""

from __future__ import annotations

import pytest

from invoices.parser import DateValidationError, normalize_invoice, validate_date_range


def test_validate_date_range_accepts_valid_input():
    """A valid date range should parse without errors."""

    parsed_from, parsed_to = validate_date_range("2026-05-01", "2026-05-20")
    assert parsed_from.isoformat() == "2026-05-01"
    assert parsed_to.isoformat() == "2026-05-20"


def test_validate_date_range_rejects_future_date():
    """Future dates should be blocked by validation."""

    with pytest.raises(DateValidationError):
        validate_date_range("2099-01-01", "2099-01-02")


def test_normalize_invoice_maps_expected_fields():
    """Raw invoice payloads should be normalized consistently."""

    invoice = normalize_invoice(
        {
            "id": "INV-1",
            "date": "2026-05-01",
            "amount": 1000,
            "status": "valid",
            "issuer": "Cong ty A",
        }
    )
    assert invoice["id"] == "INV-1"
    assert invoice["is_cancelled"] is False


def test_parse_xml_nested_items():
    """Verify that we extract nested line item details from raw GDT XML bytes."""

    from invoices.parser import parse_xml_line_items

    xml_data = b"""<?xml version="1.0" encoding="utf-8"?>
    <HDon>
        <DLHDon>
            <NDHDon>
                <DSHHDVu>
                    <HHDVu>
                        <Ten>Laptop Dell Vostro</Ten>
                        <SLuong>1</SLuong>
                        <DGia>1200000</DGia>
                        <ThTien>1200000</ThTien>
                        <TSuat>10%</TSuat>
                        <TThue>120000</TThue>
                    </HHDVu>
                    <HHDVu>
                        <Ten>Mouse Logitech</Ten>
                        <SLuong>2</SLuong>
                        <DGia>100000</DGia>
                        <ThTien>200000</ThTien>
                        <TSuat>10%</TSuat>
                        <TThue>20000</TThue>
                    </HHDVu>
                </DSHHDVu>
            </NDHDon>
        </DLHDon>
    </HDon>
    """

    items = parse_xml_line_items(xml_data)
    assert len(items) == 2
    assert items[0]["item_name"] == "Laptop Dell Vostro"
    assert items[0]["quantity"] == 1.0
    assert items[0]["unit_price"] == 1200000.0
    assert items[0]["amount_before_tax"] == 1200000.0
    assert items[0]["tax_rate"] == "10%"
    assert items[0]["tax_amount"] == 120000.0

    assert items[1]["item_name"] == "Mouse Logitech"
    assert items[1]["quantity"] == 2.0

