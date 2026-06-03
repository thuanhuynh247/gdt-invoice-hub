"""Tests for High-Performance Batch XML Parser and Compressor (US-112, US-113)."""

from __future__ import annotations

from invoices.batch_parser import (
    compress_xml,
    decompress_xml,
    parse_single_xml,
    parse_batch_xml,
)


def test_compress_decompress_roundtrip():
    """Compressing and decompressing XML should produce the original string."""
    xml = "<invoice><id>INV-1</id></invoice>"
    compressed = compress_xml(xml)
    assert isinstance(compressed, bytes)
    assert len(compressed) > 0
    
    decompressed = decompress_xml(compressed)
    assert decompressed == xml


def test_compress_empty_returns_empty():
    """Empty string compression/decompression should return empty results."""
    assert compress_xml("") == b""
    assert decompress_xml(b"") == ""


def test_parse_single_invoice_xml():
    """Should extract invoice number and MSTs from valid invoice XML."""
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <HDon>
        <DLHDon>
            <SHDon>0004567</SHDon>
            <MSTNBan>0102030405</MSTNBan>
            <MSTNMua>0908070605</MSTNMua>
            <TgTCThue>1500000</TgTCThue>
            <TgTThue>150000</TgTThue>
            <TgTTTToan>1650000</TgTTTToan>
        </DLHDon>
    </HDon>
    """
    res = parse_single_xml("test_invoice.xml", xml)
    assert res.success is True
    assert res.data["invoice_number"] == "0004567"
    assert res.data["seller_mst"] == "0102030405"
    assert res.data["buyer_mst"] == "0908070605"
    assert res.data["amount_before_tax"] == 1_500_000.0
    assert res.data["tax_amount"] == 150_000.0
    assert res.data["total_amount"] == 1_650_000.0


def test_parse_malformed_xml():
    """Malformed XML should fail gracefully and report error."""
    res = parse_single_xml("malformed.xml", "<invalid-xml")
    assert res.success is False
    assert len(res.error_message) > 0


def test_parse_batch_xml_concurrently():
    """Concurrency pool should successfully parse multiple XML invoices in parallel."""
    xml1 = "<HDon><SHDon>1</SHDon></HDon>"
    xml2 = "<HDon><SHDon>2</SHDon></HDon>"
    xml3 = "<invalid"

    batch = [
        ("inv1.xml", xml1),
        ("inv2.xml", xml2),
        ("inv3.xml", xml3),
    ]

    results = parse_batch_xml(batch, max_workers=2)
    assert len(results) == 3
    
    assert results[0].success is True
    assert results[0].data["invoice_number"] == "1"
    
    assert results[1].success is True
    assert results[1].data["invoice_number"] == "2"

    assert results[2].success is False
