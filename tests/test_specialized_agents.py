"""
Tests for Specialized Agent Routing and RAG retrieval for Corporate Tax Chatbot.
"""

from __future__ import annotations

import os
import pytest
from invoices.tax_advisor_service import get_specialized_agent
from invoices.ai_service import get_tax_rag_context, run_dynamic_pdf_ingestion, init_fts5_tables


@pytest.fixture(autouse=True)
def setup_specialized_data(app):
    with app.app_context():
        from unittest.mock import patch
        from invoices.ai_service import parse_and_chunk_pdf
        
        original_parse = parse_and_chunk_pdf
        
        def mock_parse(filename):
            import os
            base = os.path.basename(filename)
            if base in ["nghidinh132_2020.pdf", "nghidinh125_2020.pdf", "thongtu103_2014.pdf", "vanbanhopnhat61_2026_cit.pdf"]:
                return original_parse(filename)
            return []
            
        with patch("invoices.ai_service.parse_and_chunk_pdf", side_effect=mock_parse):
            init_fts5_tables()
            run_dynamic_pdf_ingestion(app)


def test_specialized_agent_routing():
    """Verify that specific queries route to the correct specialized tax agent."""
    # 1. Transfer Pricing Routing
    agent1, inst1 = get_specialized_agent("Doanh nghiệp tôi có phát sinh giao dịch liên kết theo nghị định 132/2020")
    assert "Transfer Pricing Auditor" in agent1
    assert "Nghị định 132/2020" in inst1

    # 2. Tax Penalties Routing
    agent2, inst2 = get_specialized_agent("Mức phạt chậm nộp hồ sơ khai thuế và tiền phạt chậm nộp tính thế nào")
    assert "Tax Penalties Specialist" in agent2
    assert "Nghị định 125/2020" in inst2

    # 3. Foreign Contractor Tax (FCT) Routing
    agent3, inst3 = get_specialized_agent("Thuế nhà thầu nước ngoài cho hoạt động dịch vụ phần mềm FCT là bao nhiêu")
    assert "FCT Consultant" in agent3
    assert "Thông tư 103/2014" in inst3


def test_specialized_rag_retrieval(app):
    """Verify FTS5 RAG queries match chunks from the newly ingested corporate tax PDFs."""
    with app.app_context():
        # Test Transfer Pricing RAG matching
        context_tp = get_tax_rag_context("giao dịch liên kết EBITDA 30%")
        assert "nghidinh132_2020.pdf" in context_tp
        assert "EBITDA" in context_tp

        # Test Tax Penalties RAG matching
        context_pen = get_tax_rag_context("phạt chậm nộp 0,03% mỗi ngày")
        assert "nghidinh125_2020.pdf" in context_pen
        assert "0,03%" in context_pen

        # Test FCT RAG matching
        context_fct = get_tax_rag_context("phương pháp trực tiếp thuế nhà thầu nước ngoài 103/2014")
        assert "thongtu103_2014.pdf" in context_fct
        assert "nhà thầu nước ngoài" in context_fct

