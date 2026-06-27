"""
Tests for Corporate Income Tax (CIT) 2025/2026 RAG Integration.
Verifies FTS5 and keyword lookup logic for the newly registered vanbanhopnhat61_2026_cit.pdf.
"""

from __future__ import annotations

import pytest
from invoices.ai_service import get_tax_rag_context, run_dynamic_pdf_ingestion, init_fts5_tables


@pytest.fixture(autouse=True)
def setup_cit_data(app):
    with app.app_context():
        from unittest.mock import patch
        from invoices.ai_service import parse_and_chunk_pdf
        
        original_parse = parse_and_chunk_pdf
        
        def mock_parse(filename):
            import os
            base = os.path.basename(filename)
            if base in ["vanbanhopnhat61_2026_cit.pdf", "20-btc.pdf"]:
                return original_parse(filename)
            return []
            
        with patch("invoices.ai_service.parse_and_chunk_pdf", side_effect=mock_parse):
            init_fts5_tables()
            run_dynamic_pdf_ingestion(app)


def test_cit_rag_tax_rates_15(app):
    """Verify that querying for CIT rate under 3 billion VND matches the new CIT regulation."""
    with app.app_context():
        # Match using FTS5 or fallback keywords
        context = get_tax_rag_context("doanh thu dưới 3 tỷ đóng thuế suất bao nhiêu?")
        assert context is not None
        assert "15%" in context
        assert "vanbanhopnhat61_2026_cit.pdf" in context or "Văn bản hợp nhất số 61" in context


def test_cit_rag_tax_rates_17(app):
    """Verify that querying for CIT rate between 3 and 50 billion VND matches the new CIT regulation."""
    with app.app_context():
        context = get_tax_rag_context("doanh thu từ 3 tỷ đến 50 tỷ thuế suất")
        assert context is not None
        assert "17%" in context
        assert "vanbanhopnhat61_2026_cit.pdf" in context or "Văn bản hợp nhất số 61" in context


def test_cit_rag_net_zero_green(app):
    """Verify that green transition and Net Zero reduction query routes to CIT regulations."""
    with app.app_context():
        context = get_tax_rag_context("chi phí giảm phát thải khí nhà kính net zero có được trừ không?")
        assert context is not None
        assert "Net Zero" in context or "giảm phát thải" in context
        assert any(x in context for x in ["vanbanhopnhat61_2026_cit.pdf", "Văn bản hợp nhất số 61", "20-btc.pdf"])


def test_cit_rag_digital_transformation(app):
    """Verify that digital transformation and IT training query routes to CIT regulations."""
    with app.app_context():
        context = get_tax_rag_context("chi phí chuyển đổi số và đào tạo nghề nghiệp cho nhân viên")
        assert context is not None
        assert "chuyển đổi số" in context or "đào tạo" in context
        assert any(x in context for x in ["vanbanhopnhat61_2026_cit.pdf", "Văn bản hợp nhất số 61", "20-btc.pdf"])

