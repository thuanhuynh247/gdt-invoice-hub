"""
Tests for database schema migrations and model table compliance.
"""

from __future__ import annotations

import pytest
from extensions import db
from invoices.models import TaxRegulationChunk, AIChatSession, AIChatMessage


def test_database_migrations_exist(app):
    """Verify that model schemas migrate cleanly and columns match requirements."""
    with app.app_context():
        # Check TaxRegulationChunk columns
        res_chunk = db.session.execute(db.text("PRAGMA table_info(tax_regulation_chunk);")).fetchall()
        columns_chunk = {r[1]: r[2] for r in res_chunk}
        
        assert "id" in columns_chunk
        assert "document_source" in columns_chunk
        assert "page_number" in columns_chunk
        assert "effective_date" in columns_chunk
        assert "chunk_content" in columns_chunk
        assert "created_at" in columns_chunk

        # Check AIChatSession columns
        res_session = db.session.execute(db.text("PRAGMA table_info(ai_chat_session);")).fetchall()
        columns_session = {r[1]: r[2] for r in res_session}
        
        assert "id" in columns_session
        assert "title" in columns_session
        assert "created_at" in columns_session

        # Check AIChatMessage columns
        res_message = db.session.execute(db.text("PRAGMA table_info(ai_chat_message);")).fetchall()
        columns_message = {r[1]: r[2] for r in res_message}
        
        assert "id" in columns_message
        assert "session_id" in columns_message
        assert "role" in columns_message
        assert "content" in columns_message
        assert "created_at" in columns_message
