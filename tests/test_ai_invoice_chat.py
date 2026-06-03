"""
Tests for US-211: Single-Invoice AI Chat (Contextual Invoice Chat Sessions).

Verifies:
- D2: Session creation with invoice_id association and auto-welcome message.
- D3: AIChatAgent injects invoice context into system prompt.
- Session lifecycle: create, list, resume, and delete invoice-linked sessions.
"""

from __future__ import annotations

import json
import uuid
import pytest
from unittest.mock import patch, MagicMock
from extensions import db
from invoices.models import Invoice, LineItem, AIChatSession, AIChatMessage


@pytest.fixture
def sample_invoice(app):
    """Create a sample invoice with line items for testing invoice-linked chat."""
    with app.app_context():
        inv = Invoice(
            id="CHAT-TEST-INV-001",
            filename="chat_test_inv.xml",
            invoice_type="purchase",
            number="0099001",
            symbol="1C26TSE",
            date="2026-05-20",
            currency="VND",
            seller_name="Công ty TNHH ABC Tech",
            seller_mst="0109998887",
            seller_address="123 Phạm Hùng, Cầu Giấy, Hà Nội",
            buyer_name="Doanh nghiệp của tôi",
            buyer_mst="0101234567",
            buyer_address="456 Nguyễn Trãi, Thanh Xuân, Hà Nội",
            amount_before_tax=5000000.0,
            tax_amount=500000.0,
            total_amount=5500000.0,
            payment_method="Chuyển khoản",
            imported_at="2026-05-21",
            taxpayer_mst="0101234567",
            t_score=85,
            t_rating="A",
            warnings_json=json.dumps(["Giá bán thấp hơn giá thị trường 15%."]),
        )
        item = LineItem(
            invoice_id="CHAT-TEST-INV-001",
            item_name="Bàn phím cơ Cherry MX",
            unit="Cái",
            quantity=10,
            unit_price=500000,
            amount_before_tax=5000000,
            tax_rate="10%",
            tax_amount=500000,
            expense_category="Thiết bị công nghệ & Phần mềm",
        )
        db.session.add(inv)
        db.session.add(item)
        db.session.commit()
        yield inv


def test_create_session_with_invoice_id(logged_in_client, app, sample_invoice):
    """D2: Creating a session with invoice_id links the session and auto-generates welcome message."""
    response = logged_in_client.post(
        "/api/ai/chat/sessions",
        json={"invoice_id": "CHAT-TEST-INV-001"},
    )
    assert response.status_code == 201
    data = response.get_json()

    # Session created with correct title
    assert data["invoice_id"] == "CHAT-TEST-INV-001"
    assert "0099001" in data["title"]  # title contains invoice number

    # Welcome message auto-generated
    assert len(data["messages"]) == 1
    welcome = data["messages"][0]
    assert welcome["role"] == "assistant"
    assert "Công ty TNHH ABC Tech" in welcome["content"]
    assert "0109998887" in welcome["content"]
    assert "0099001" in welcome["content"]
    assert "5,500,000" in welcome["content"]

    # Dual-compat: session key also present
    assert "session" in data
    assert data["session"]["invoice_id"] == "CHAT-TEST-INV-001"


def test_create_session_invoice_not_found(logged_in_client, app):
    """D2: Creating a session with non-existent invoice_id returns 404."""
    response = logged_in_client.post(
        "/api/ai/chat/sessions",
        json={"invoice_id": "DOES-NOT-EXIST"},
    )
    assert response.status_code == 404
    data = response.get_json()
    assert "error" in data


def test_invoice_session_appears_in_list(logged_in_client, app, sample_invoice):
    """Invoice-linked sessions appear in the session list with invoice_id populated."""
    # Create an invoice-linked session
    create_resp = logged_in_client.post(
        "/api/ai/chat/sessions",
        json={"invoice_id": "CHAT-TEST-INV-001"},
    )
    assert create_resp.status_code == 201
    session_id = create_resp.get_json()["id"]

    # Also create a general session for comparison
    logged_in_client.post(
        "/api/ai/chat/sessions",
        json={"title": "Phiên chung"},
    )

    # List sessions
    list_resp = logged_in_client.get("/api/ai/chat/sessions")
    assert list_resp.status_code == 200
    sessions = list_resp.get_json()

    invoice_sessions = [s for s in sessions if s.get("invoice_id") == "CHAT-TEST-INV-001"]
    general_sessions = [s for s in sessions if s.get("invoice_id") is None]

    assert len(invoice_sessions) == 1
    assert invoice_sessions[0]["id"] == session_id
    assert len(general_sessions) >= 1


def test_invoice_context_injection_in_ask(app, sample_invoice):
    """D3: AIChatAgent.ask() injects invoice context when session is linked."""
    from invoices.ai_service import AIChatAgent

    with app.app_context():
        # Create a linked session manually
        session_id = str(uuid.uuid4())
        session = AIChatSession(
            id=session_id,
            title="Tham vấn hóa đơn 0099001",
            invoice_id="CHAT-TEST-INV-001",
            created_at="2026-05-28 10:00:00",
        )
        db.session.add(session)
        db.session.commit()

        agent = AIChatAgent()

        # Mock requests.post to capture system prompts and return appropriate JSON responses
        captured_system_prompts = []

        def mock_post(url, json=None, **kwargs):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            
            # Extract messages and capture system prompt
            messages = json.get("messages", []) if json else []
            system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
            if system_msg:
                captured_system_prompts.append(system_msg)
                
            if json and json.get("format") == "json":
                # Intent classifier request
                mock_resp.json.return_value = {
                    "message": {
                        "content": '{"intent": "general_query"}'
                    }
                }
            else:
                # Final chat response
                mock_resp.json.return_value = {
                    "message": {
                        "content": "Hóa đơn này hoàn toàn hợp lệ."
                    }
                }
            return mock_resp

        with patch("requests.post", side_effect=mock_post):
            with patch("invoices.ai_service.load_scheduler_settings", return_value={"ai_enabled": True, "ai_provider": "ollama", "ai_model_name": "gemma-4"}):
                result = agent.ask(session_id, "Hóa đơn này có hợp lệ không?")

        # Verify invoice context was injected into the system prompt
        assert len(captured_system_prompts) >= 2
        answer_prompt = captured_system_prompts[-1]

        assert "CHAT-TEST-INV-001" in answer_prompt
        assert "Công ty TNHH ABC Tech" in answer_prompt
        assert "0109998887" in answer_prompt
        assert "Bàn phím cơ Cherry MX" in answer_prompt
        assert "5,000,000" in answer_prompt
        assert "Giá bán thấp hơn giá thị trường" in answer_prompt


def test_invoice_session_delete_cascade(logged_in_client, app, sample_invoice):
    """Deleting an invoice-linked session cascades to messages."""
    # Create session with invoice
    create_resp = logged_in_client.post(
        "/api/ai/chat/sessions",
        json={"invoice_id": "CHAT-TEST-INV-001"},
    )
    session_id = create_resp.get_json()["id"]

    # Send a message (mocked)
    with patch("invoices.ai_service.AIChatAgent.ask", return_value="Trả lời test"):
        logged_in_client.post(
            f"/api/ai/chat/sessions/{session_id}/message",
            json={"message": "Hóa đơn này có hợp lệ không?"},
        )

    # Delete session
    del_resp = logged_in_client.delete(f"/api/ai/chat/sessions/{session_id}")
    assert del_resp.status_code == 200

    # Verify cascade deletion
    with app.app_context():
        assert db.session.get(AIChatSession, session_id) is None
        assert AIChatMessage.query.filter_by(session_id=session_id).count() == 0


def test_invoice_session_welcome_includes_warnings(logged_in_client, app, sample_invoice):
    """Welcome message includes parsed warnings from invoice warnings_json."""
    response = logged_in_client.post(
        "/api/ai/chat/sessions",
        json={"invoice_id": "CHAT-TEST-INV-001"},
    )
    assert response.status_code == 201
    messages = response.get_json()["messages"]
    assert len(messages) == 1
    assert "Giá bán thấp hơn giá thị trường" in messages[0]["content"]


def test_invoice_session_welcome_cash_payment_warning(logged_in_client, app):
    """Welcome message warns about cash payment over 20M VND threshold."""
    with app.app_context():
        inv = Invoice(
            id="CHAT-CASH-INV",
            filename="cash_inv.xml",
            invoice_type="purchase",
            number="0099002",
            symbol="1C26ABC",
            date="2026-05-22",
            currency="VND",
            seller_name="NCC Tiền Mặt",
            seller_mst="9999888877",
            buyer_name="Doanh nghiệp của tôi",
            buyer_mst="0101234567",
            amount_before_tax=25000000.0,
            tax_amount=2500000.0,
            total_amount=27500000.0,
            payment_method="Tiền mặt",
            imported_at="2026-05-23",
            taxpayer_mst="0101234567",
            t_score=40,
            t_rating="C",
        )
        db.session.add(inv)
        db.session.commit()

    response = logged_in_client.post(
        "/api/ai/chat/sessions",
        json={"invoice_id": "CHAT-CASH-INV"},
    )
    assert response.status_code == 201
    welcome_content = response.get_json()["messages"][0]["content"]
    # Should contain cash payment compliance warning
    assert "Tiền mặt" in welcome_content or "tiền mặt" in welcome_content
    assert "20 triệu" in welcome_content or "khấu trừ" in welcome_content


def test_session_without_invoice_has_no_invoice_id(logged_in_client, app):
    """General sessions (no invoice_id) should return invoice_id as None."""
    response = logged_in_client.post(
        "/api/ai/chat/sessions",
        json={"title": "Cuộc hội thoại chung"},
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["invoice_id"] is None
    assert data["title"] == "Cuộc hội thoại chung"
    assert len(data["messages"]) == 0  # No auto-welcome for general sessions
