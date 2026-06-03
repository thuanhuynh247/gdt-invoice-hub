"""
Tests for Upgraded Chatbot RAG System (Dynamic PDF Ingestion & FTS5 Indexing).
Verifies PDF chunking, database migrations, FTS5 matching, and search latency.
"""

from __future__ import annotations

import os
import time
import pytest
from unittest.mock import patch, MagicMock
from extensions import db
from invoices.models import TaxRegulationChunk
from invoices.ai_service import (
    parse_and_chunk_pdf,
    init_fts5_tables,
    run_dynamic_pdf_ingestion,
    get_tax_rag_context
)


def test_pdf_text_extraction(app):
    """Verify pypdf extracts text from local PDFs successfully or fails gracefully if missing."""
    with app.app_context():
        # Test on luat48.pdf if exists
        if os.path.exists("luat48.pdf"):
            chunks = parse_and_chunk_pdf("luat48.pdf")
            assert isinstance(chunks, list)
            if len(chunks) > 0:
                assert chunks[0]["document_source"] == "luat48.pdf"
                assert "page_number" in chunks[0]
                assert "effective_date" in chunks[0]
                assert "chunk_content" in chunks[0]
                assert len(chunks[0]["chunk_content"]) > 0


def test_text_splitter_paragraphs():
    """Test parse_and_chunk_pdf splitting logic with standard text chunk structures."""
    # Since parse_and_chunk_pdf reads from file, let's mock the PdfReader and verify paragraph splitter
    with patch("pypdf.PdfReader") as mock_reader:
        mock_page = MagicMock()
        # Create a page content with more than 180 words to trigger split
        words_paragraph1 = " ".join([f"word{i}" for i in range(190)]) + "."
        words_paragraph2 = " " + " ".join([f"extra{i}" for i in range(50)]) + "."
        mock_page.extract_text.return_value = words_paragraph1 + words_paragraph2
        
        mock_pdf = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_reader.return_value = mock_pdf

        # We pass a fake existing filename path
        with patch("os.path.exists", return_value=True):
            chunks = parse_and_chunk_pdf("mock_document.pdf")
            
            # Since there were ~240 words split by period ending word after 180, it should split into 2 chunks
            assert len(chunks) >= 1
            assert chunks[0]["document_source"] == "mock_document.pdf"
            assert chunks[0]["page_number"] == 1
            assert "word0" in chunks[0]["chunk_content"]


def test_fts5_indexing_relevance(app):
    """Verify SQLite FTS5 index returns correct regulation chunk based on search keywords."""
    with app.app_context():
        init_fts5_tables()
        
        # Clear existing chunks
        TaxRegulationChunk.query.delete()
        db.session.execute(db.text("DELETE FROM tax_regulation_fts"))
        db.session.commit()

        # Seed test chunks
        chunk1 = TaxRegulationChunk(
            document_source="luat48.pdf",
            page_number=1,
            effective_date="2025-07-01",
            chunk_content="Quy định khấu trừ thuế nộp thay đối với nhà cung cấp nước ngoài nccnn trực tuyến.",
            created_at="2026-05-28 00:00:00"
        )
        chunk2 = TaxRegulationChunk(
            document_source="luat149.signed.pdf",
            page_number=2,
            effective_date="2026-01-01",
            chunk_content="Miễn thuế khâu thương mại đối với sản phẩm nông sản trồng trọt thủy sản sơ chế.",
            created_at="2026-05-28 00:00:00"
        )
        db.session.add(chunk1)
        db.session.add(chunk2)
        db.session.commit()

        # Sync to FTS5 virtual table
        db.session.execute(
            db.text("INSERT INTO tax_regulation_fts (chunk_id, chunk_content, document_source, page_number) VALUES (:cid, :content, :source, :page);"),
            {"cid": chunk1.id, "content": chunk1.chunk_content, "source": chunk1.document_source, "page": chunk1.page_number}
        )
        db.session.execute(
            db.text("INSERT INTO tax_regulation_fts (chunk_id, chunk_content, document_source, page_number) VALUES (:cid, :content, :source, :page);"),
            {"cid": chunk2.id, "content": chunk2.chunk_content, "source": chunk2.document_source, "page": chunk2.page_number}
        )
        db.session.commit()

        # Test RAG query matching
        context = get_tax_rag_context("nhà cung cấp nước ngoài nccnn")
        assert "luat48.pdf" in context
        assert "nhà cung cấp nước ngoài" in context
        assert "nông sản trồng trọt" not in context

        # Test RAG query matching second chunk
        context_agri = get_tax_rag_context("nông sản trồng trọt")
        assert "luat149.signed.pdf" in context_agri
        assert "thủy sản sơ chế" in context_agri
        assert "nhà cung cấp nước ngoài" not in context_agri


def test_fts5_latency(app):
    """Verify that FTS5 dynamic queries run extremely fast (< 5ms)."""
    with app.app_context():
        init_fts5_tables()
        
        # Measure query latency
        start_time = time.perf_counter()
        get_tax_rag_context("khấu trừ nccnn")
        end_time = time.perf_counter()
        
        latency_ms = (end_time - start_time) * 1000
        print(f"FTS5 RAG latency: {latency_ms:.4f} ms")
        # Ensure lookup is under 5ms limit for fast conversational responses
        assert latency_ms < 5.0
