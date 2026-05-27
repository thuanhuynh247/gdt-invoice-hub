"""
Tests for Upgraded Chatbot RAG System with 2025/2026 VAT Regulations.
Verifies keyword-based RAG routing for Law 48/2024/QH15 and Law 149/2025/QH15.
"""

from __future__ import annotations

import pytest
from invoices.ai_service import get_tax_rag_context


def test_rag_default_fallback(app):
    """Verify that if no keywords match, the default RAG context is returned."""
    with app.app_context():
        context = get_tax_rag_context("hỏi đáp linh tinh")
        assert context is not None
        # Default fallback should contain the new Law 48 (index 0) and General Deduction rules (index 2)
        assert "Luật Thuế GTGT số 48/2024/QH15" in context
        assert "Điều kiện khấu trừ thuế GTGT đầu vào" in context


def test_rag_law_48_matching(app):
    """Verify that querying about Law 48, foreign digital providers, or 5M threshold routes correctly."""
    with app.app_context():
        # Match via "luật 48"
        context = get_tax_rag_context("Quy định trong luật 48 như thế nào?")
        assert "Luật Thuế GTGT số 48/2024/QH15" in context
        assert "nhà cung cấp nước ngoài" in context

        # Match via foreign provider
        context_nccnn = get_tax_rag_context("mua dịch vụ của Google Meta khấu trừ thuế thế nào")
        assert "Luật Thuế GTGT số 48/2024/QH15" in context_nccnn
        assert "Google, Meta, AWS" in context_nccnn


def test_rag_law_149_matching(app):
    """Verify that querying about Law 149, 500 million threshold, or raw agriculture products routes correctly."""
    with app.app_context():
        # Match via "luật 149"
        context = get_tax_rag_context("Các điểm mới của luật 149")
        assert "Luật sửa đổi bổ sung Luật Thuế GTGT số 149/2025/QH15" in context
        assert "500 triệu" in context

        # Match via 500 million threshold
        context_500m = get_tax_rag_context("Hộ kinh doanh doanh thu 500tr có đóng thuế không?")
        assert "Luật sửa đổi bổ sung Luật Thuế GTGT số 149/2025/QH15" in context_500m
        assert "500 triệu đồng/năm" in context_500m

        # Match via agriculture products
        context_agri = get_tax_rag_context("Mua bán nông sản thô ở khâu thương mại có được miễn thuế?")
        assert "Luật sửa đổi bổ sung Luật Thuế GTGT số 149/2025/QH15" in context_agri
        assert "sản phẩm trồng trọt" in context_agri
