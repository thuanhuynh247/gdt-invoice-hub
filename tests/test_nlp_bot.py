"""
Tests for Conversational NLP & Text-to-SQL AI Chatbot.
Covers intent classification routing, Safe SQL parser verification, and successful execution + formatting.
"""

from __future__ import annotations

import json
from unittest.mock import patch, MagicMock
import pytest

from extensions import db
from invoices.models import Invoice, LineItem, AIChatSession, AIChatMessage
from invoices.ai_service import AIChatAgent
from invoices.scheduler import save_scheduler_settings


@pytest.fixture
def chat_setup(app):
    """Seed data and enable AI settings for testing."""
    with app.app_context():
        # Clear existing
        AIChatMessage.query.delete()
        AIChatSession.query.delete()
        LineItem.query.delete()
        Invoice.query.delete()
        db.session.commit()

        # Seed sample invoice
        inv = Invoice(
            id="123456789-AB-1",
            number="1",
            date="2026-05-25",
            seller_name="Cong ty TNHH Hoa Don Test",
            seller_mst="123456789",
            seller_address="Ha Noi",
            buyer_name="Khach Hang Mua Test",
            buyer_mst="987654321",
            buyer_address="TP HCM",
            amount_before_tax=10000000.0,
            tax_amount=1000000.0,
            total_amount=11000000.0,
            has_signature=True,
            signing_date="2026-05-25",
            payment_method="TM/CK",
            is_cancelled=False,
            imported_at="2026-05-25 10:00:00"
        )
        db.session.add(inv)

        item = LineItem(
            invoice_id="123456789-AB-1",
            item_name="Dich vu Cloud Server",
            quantity=1,
            unit_price=10000000.0,
            amount_before_tax=10000000.0,
            tax_rate="10%",
            tax_amount=1000000.0,
            expense_category="Thiết bị công nghệ & Phần mềm"
        )
        db.session.add(item)
        db.session.commit()

        # Enable AI
        save_scheduler_settings({
            "ai_enabled": True,
            "ai_provider": "ollama",
            "ai_model_name": "gemma-4",
            "ai_system_prompt": "Test Prompt"
        })

        session = AIChatSession(
            id="test-chat-session-999",
            title="Cuộc hội thoại mới",
            created_at="2026-05-25 10:00:00"
        )
        db.session.add(session)
        db.session.commit()

        yield session


def test_sql_safety_checker(app):
    """Test various SQL queries against the safe SQL parser checks."""
    agent = AIChatAgent()

    # Safe SELECTs
    assert agent._is_sql_safe("SELECT * FROM invoice") is True
    assert agent._is_sql_safe("  select id, total_amount from invoice where total_amount > 1000; ") is True
    assert agent._is_sql_safe("SELECT sum(amount_before_tax) FROM line_item JOIN invoice ON line_item.invoice_id = invoice.id") is True

    # Modified queries (inserts, drops, updates) - must be rejected
    assert agent._is_sql_safe("INSERT INTO invoice (number) VALUES ('123')") is False
    assert agent._is_sql_safe("UPDATE invoice SET is_cancelled = 1") is False
    assert agent._is_sql_safe("DROP TABLE line_item") is False
    assert agent._is_sql_safe("DELETE FROM invoice") is False
    assert agent._is_sql_safe("CREATE TABLE new_table (id TEXT)") is False

    # Chained statements / Semicolon in mid-string
    assert agent._is_sql_safe("SELECT * FROM invoice; DROP TABLE line_item;") is False
    assert agent._is_sql_safe("SELECT * FROM invoice; -- comment") is True  # trailing semicolon gets stripped, so it's safe

    # Forbidden tables (system_config, etc.)
    assert agent._is_sql_safe("SELECT * FROM system_config") is False
    assert agent._is_sql_safe("SELECT * FROM scheduler_log") is False
    assert agent._is_sql_safe("SELECT * FROM ai_chat_session") is False


@patch("invoices.ai_service.requests.post")
def test_intent_classification_routing_general(mock_post, app, chat_setup):
    """Test routing to general query when LLM returns 'general_query'."""
    agent = AIChatAgent()

    # Mock response for intent classification: general_query
    mock_resp_intent = MagicMock()
    mock_resp_intent.status_code = 200
    mock_resp_intent.json.return_value = {
        "message": {
            "content": '{"intent": "general_query"}'
        }
    }

    # Mock response for general RAG query fallback
    mock_resp_chat = MagicMock()
    mock_resp_chat.status_code = 200
    mock_resp_chat.json.return_value = {
        "message": {
            "content": "Đây là câu trả lời chung về VAT."
        }
    }

    # request.post will be called twice: first for intent, second for general chat fallback
    mock_post.side_effect = [mock_resp_intent, mock_resp_chat]

    with app.app_context():
        response = agent.ask(chat_setup.id, "Thuế VAT cho phần mềm là bao nhiêu?")
        assert response == "Đây là câu trả lời chung về VAT."


@patch("invoices.ai_service.requests.post")
def test_intent_classification_routing_sql_flow(mock_post, app, chat_setup):
    """Test full SQL flow when intent is sql_query and valid SQL is generated."""
    agent = AIChatAgent()

    # 1. Intent response (sql_query)
    mock_resp_intent = MagicMock()
    mock_resp_intent.status_code = 200
    mock_resp_intent.json.return_value = {
        "message": {
            "content": '{"intent": "sql_query"}'
        }
    }

    # 2. SQL generator response
    mock_resp_sql = MagicMock()
    mock_resp_sql.status_code = 200
    mock_resp_sql.json.return_value = {
        "message": {
            "content": '{"sql": "SELECT sum(total_amount) as total FROM invoice", "explanation": "Tính tổng tiền các hóa đơn"}'
        }
    }

    # 3. Final answer generator response
    mock_resp_answer = MagicMock()
    mock_resp_answer.status_code = 200
    mock_resp_answer.json.return_value = {
        "message": {
            "content": "Tổng doanh thu từ hóa đơn là 11.000.000 đ."
        }
    }

    mock_post.side_effect = [mock_resp_intent, mock_resp_sql, mock_resp_answer]

    with app.app_context():
        response = agent.ask(chat_setup.id, "Tính tổng doanh thu hóa đơn?")
        assert "Tổng doanh thu từ hóa đơn" in response


@patch("invoices.ai_service.requests.post")
def test_sql_unsafe_blocking(mock_post, app, chat_setup):
    """Test that unsafe generated SQL is blocked and an appropriate message is returned."""
    agent = AIChatAgent()

    # 1. Intent response (sql_query)
    mock_resp_intent = MagicMock()
    mock_resp_intent.status_code = 200
    mock_resp_intent.json.return_value = {
        "message": {
            "content": '{"intent": "sql_query"}'
        }
    }

    # 2. SQL generator response returning unsafe SQL (DROP TABLE)
    mock_resp_sql = MagicMock()
    mock_resp_sql.status_code = 200
    mock_resp_sql.json.return_value = {
        "message": {
            "content": '{"sql": "DROP TABLE invoice;", "explanation": "Xóa bảng hóa đơn"}'
        }
    }

    mock_post.side_effect = [mock_resp_intent, mock_resp_sql]

    with app.app_context():
        response = agent.ask(chat_setup.id, "Xóa toàn bộ hóa đơn đi?")
        assert "kiểm tra bảo mật" in response
        assert "DROP TABLE" in response


@patch("invoices.ai_service.requests.post")
def test_sql_execution_failure_fallback(mock_post, app, chat_setup):
    """Test fallback when SQL generated contains column/syntax error."""
    agent = AIChatAgent()

    # 1. Intent response (sql_query)
    mock_resp_intent = MagicMock()
    mock_resp_intent.status_code = 200
    mock_resp_intent.json.return_value = {
        "message": {
            "content": '{"intent": "sql_query"}'
        }
    }

    # 2. SQL generator response with invalid column name
    mock_resp_sql = MagicMock()
    mock_resp_sql.status_code = 200
    mock_resp_sql.json.return_value = {
        "message": {
            "content": '{"sql": "SELECT non_existent_column FROM invoice", "explanation": "Lấy cột không tồn tại"}'
        }
    }

    mock_post.side_effect = [mock_resp_intent, mock_resp_sql]

    with app.app_context():
        response = agent.ask(chat_setup.id, "Lấy cột lạ?")
        assert "Lỗi chi tiết" in response
        assert "non_existent_column" in response
