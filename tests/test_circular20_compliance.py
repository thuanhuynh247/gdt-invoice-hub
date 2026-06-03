"""Tests for Circular 20/2026/TT-BTC compliance logic."""

from __future__ import annotations

import os
import pytest
from unittest.mock import patch, MagicMock
from extensions import db
from invoices.models import TaxRegulationChunk
from invoices.ai_service import parse_and_chunk_pdf, get_tax_rag_context
from invoices.ai_tax_advisor import TaxAdvisoryAgent, create_tax_regulation_index


def test_circular_20_effective_date_mapping():
    """Verify that parse_and_chunk_pdf correctly maps 20-btc.pdf to effective date 2026-03-12."""
    with patch("pypdf.PdfReader") as mock_reader:
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Điều 13. Chi phí mua hàng ủy quyền qua cá nhân từ 5 triệu đồng trở lên phải có chứng từ thanh toán không dùng tiền mặt."
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_reader.return_value = mock_pdf

        with patch("os.path.exists", return_value=True):
            chunks = parse_and_chunk_pdf("20-btc.pdf")
            assert len(chunks) > 0
            assert chunks[0]["effective_date"] == "2026-03-12"
            assert chunks[0]["document_source"] == "20-btc.pdf"


def test_chatbot_rag_fallback_contains_circular_20():
    """Verify that get_tax_rag_context returns Circular 20 details when queried about employee authorized payments."""
    # When FTS5 is not available or query matches, it falls back to TAX_REGULATIONS
    # Let's test the fallback keyword lookup for Circular 20 keywords
    context = get_tax_rag_context("thẻ cá nhân ủy quyền thanh toán 5 triệu thông tư 20")
    assert "20/2026/TT-BTC" in context or "20/2026" in context
    assert "ủy quyền" in context.lower()
    assert "5 triệu" in context or "5 trieu" in context


def test_tax_advisory_agent_circular_20_risk_detection():
    """Verify that the offline TaxAdvisoryAgent flags employee-authorized payments >= 5M without non-cash proof."""
    agent = TaxAdvisoryAgent()
    
    sample_invoices = [
        # Invoice 1: Employee authorized purchase >= 5M VND, NO non-cash proof (RISK)
        {
            "id": "INV-EMP-RISK-001",
            "seller_name": "Công ty Cung Cấp",
            "seller_mst": "0102030405",
            "total_amount": 6_500_000,
            "payment_method": "Thẻ cá nhân ủy quyền",
            "t_score": 90,
            "has_signature": True,
            "date": "2026-05-01",
            "has_non_cash_proof": False,
        },
        # Invoice 2: Employee authorized purchase >= 5M VND, HAS non-cash proof (CLEAN)
        {
            "id": "INV-EMP-CLEAN-002",
            "seller_name": "Công ty Cung Cấp 2",
            "seller_mst": "0102030406",
            "total_amount": 8_000_000,
            "payment_method": "Cá nhân thanh toán",
            "t_score": 92,
            "has_signature": True,
            "date": "2026-05-02",
            "has_non_cash_proof": True,
        },
        # Invoice 3: Employee authorized purchase < 5M VND, NO non-cash proof (CLEAN under limit)
        {
            "id": "INV-EMP-SMALL-003",
            "seller_name": "Cửa hàng Nhỏ",
            "seller_mst": "0102030407",
            "total_amount": 4_200_000,
            "payment_method": "Nhân viên thanh toán",
            "t_score": 85,
            "has_signature": True,
            "date": "2026-05-03",
            "has_non_cash_proof": False,
        }
    ]
    
    findings = agent.scan_invoices(sample_invoices)
    
    # Verify INV-EMP-RISK-001 is flagged with CIT_CIRCULAR_20_RISK
    emp_risk_findings = [
        f for f in findings if f["invoice_id"] == "INV-EMP-RISK-001"
    ]
    assert len(emp_risk_findings) == 1
    risks = emp_risk_findings[0]["risks"]
    assert any(r["type"] == "CIT_CIRCULAR_20_RISK" for r in risks)
    
    risk_item = next(r for r in risks if r["type"] == "CIT_CIRCULAR_20_RISK")
    assert risk_item["severity"] == "HIGH"
    assert "Thông tư 20/2026/TT-BTC" in risk_item["message"]
    # Check that legal references are present and point to Circular 20
    assert any("Thông tư 20" in ref for ref in risk_item["legal_refs"])
    
    # Verify CLEAN invoices are not flagged with CIT_CIRCULAR_20_RISK
    clean_ids = [f["invoice_id"] for f in findings if any(r["type"] == "CIT_CIRCULAR_20_RISK" for r in f["risks"])]
    assert "INV-EMP-CLEAN-002" not in clean_ids
    assert "INV-EMP-SMALL-003" not in clean_ids
