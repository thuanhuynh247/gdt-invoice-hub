"""Tests for Intelligent Document Processing (IDP) Pipeline (US-102, US-103)."""

from __future__ import annotations

import pytest
from invoices.ocr_pipeline import (
    extract_text_from_content,
    parse_invoice_from_text,
    parse_vietnamese_number,
    add_to_review_queue,
    get_review_queue,
    clear_review_queue,
)


def test_parse_vietnamese_number():
    """Vietnamese number formats should be parsed to floats correctly."""
    assert parse_vietnamese_number("1.500.000") == 1500000.0
    assert parse_vietnamese_number("2.350.000,50") == 2350000.5
    assert parse_vietnamese_number("150000") == 150000.0
    assert parse_vietnamese_number("1,5") == 1.5
    assert parse_vietnamese_number("invalid") == 0.0
    assert parse_vietnamese_number("") == 0.0


class TestOCRTextExtraction:
    """US-102: OCR Text Extraction Pipeline for Scanned Invoices."""

    def test_extract_text_normalization(self):
        """Raw text should be normalized (newlines and whitespace)."""
        raw = "Công ty ABC\r\n\tMã số thuế:  0109998887"
        res = extract_text_from_content(raw)
        assert "Công ty ABC\n Mã số thuế: 0109998887" in res.raw_text

    def test_confidence_scoring(self):
        """Presence of invoice markers should increase confidence."""
        good_text = "Hóa đơn điện tử Mã số thuế 0109998887 Cộng tiền hàng"
        bad_text = "Just a random document with no invoice keywords"
        
        good_res = extract_text_from_content(good_text)
        bad_res = extract_text_from_content(bad_text)
        
        assert good_res.confidence > bad_res.confidence
        assert good_res.confidence >= 0.6


class TestStructuredInvoiceParser:
    """US-103: Structured Invoice Parser from OCR Text."""

    def _sample_ocr_text(self):
        return """
        CÔNG TY CỔ PHẦN CÔNG NGHỆ BẦU TRỜI
        Mã số thuế: 0109998887
        Địa chỉ: 123 Đường Bầu Trời, Hà Nội
        
        HÓA ĐƠN ĐIỆN TỬ
        Số: 0001234
        Ký hiệu: 1C23TNN
        Ngày 15/05/2026
        
        Tên đơn vị: CÔNG TY TNHH NGƯỜI MUA
        Mã số thuế: 0112223334
        Địa chỉ: 456 Đường Mặt Đất, TP.HCM
        Hình thức thanh toán: Chuyển khoản
        
        Cộng tiền hàng: 10.000.000
        Thuế suất: 10%
        Tiền thuế GTGT: 1.000.000
        Tổng cộng: 11.000.000
        """

    def test_parse_structured_fields(self):
        """Regex patterns should extract all fields correctly."""
        text = self._sample_ocr_text()
        parsed = parse_invoice_from_text(text)
        
        assert parsed.seller_mst == "0109998887"
        assert parsed.buyer_mst == "0112223334"
        assert parsed.invoice_number == "0001234"
        assert parsed.invoice_symbol == "1C23TNN"
        assert parsed.invoice_date == "15/05/2026"
        assert parsed.amount_before_tax == 10_000_000.0
        assert parsed.tax_amount == 1_000_000.0
        assert parsed.total_amount == 11_000_000.0
        assert parsed.tax_rate == "10%"
        assert parsed.payment_method == "Chuyển khoản"
        assert parsed.confidence > 0.8
        assert len(parsed.warnings) == 0

    def test_missing_fields_generate_warnings(self):
        """Missing mandatory fields should lower confidence and generate warnings."""
        text = "Hóa đơn điện tử thiếu thông tin"
        parsed = parse_invoice_from_text(text)
        
        assert parsed.confidence < 0.5
        assert len(parsed.warnings) > 0
        assert any("MST người bán" in w for w in parsed.warnings)
        assert any("số hóa đơn" in w for w in parsed.warnings)


class TestReviewQueue:
    """Manual review queue management for low-confidence IDP results."""

    def setup_method(self):
        clear_review_queue()

    def test_add_to_review_queue(self):
        """Parsed results should be added to the queue."""
        parsed = parse_invoice_from_text("Bad OCR")
        add_to_review_queue(parsed, "scan1.pdf")
        
        queue = get_review_queue()
        assert len(queue) == 1
        assert queue[0]["filename"] == "scan1.pdf"
        assert "parsed_fields" in queue[0]

    def test_clear_review_queue(self):
        """Clearing the queue should remove all items."""
        parsed = parse_invoice_from_text("Bad OCR")
        add_to_review_queue(parsed)
        assert len(get_review_queue()) == 1
        clear_review_queue()
        assert len(get_review_queue()) == 0
