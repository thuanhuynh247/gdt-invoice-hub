"""
Tests for AI Compliance Auditor feature.
Covers settings, AI Compliance Auditor service, provider API calls, database persistence, and routes.
"""

from __future__ import annotations

import json
from unittest.mock import patch, MagicMock
import pytest

from extensions import db
from invoices.models import Invoice, LineItem, AIAuditResult
from invoices.ai_service import AIComplianceAuditor
from invoices.scheduler import save_scheduler_settings, load_scheduler_settings


@pytest.fixture
def sample_invoice(app):
    """Seed a sample invoice and items in the database for testing."""
    with app.app_context():
        # Clear existing
        AIAuditResult.query.delete()
        LineItem.query.delete()
        Invoice.query.delete()
        print("FIXTURE DEBUG session instance id:", id(db.session()))
        db.session.commit()

        invoice = Invoice(
            id="INV-AI-TEST-001",
            number="12345",
            date="2026-05-23",
            seller_name="Cong ty TNHH Thiet bi So A",
            seller_mst="0101234567",
            seller_address="Ha Noi",
            buyer_name="Cong ty TNHH Giai Phap Cong Nghe",
            buyer_mst="0309876543",
            buyer_address="TP HCM",
            amount_before_tax=20000000.0,
            tax_amount=2000000.0,
            total_amount=22000000.0,
            has_signature=True,
            signing_date="2026-05-23",
            payment_method="TM/CK",
            imported_at="2026-05-23 10:00:00",
            import_status="imported"
        )
        db.session.add(invoice)

        item1 = LineItem(
            invoice_id="INV-AI-TEST-001",
            item_name="Laptop Dell Latitude 7420",
            quantity=1,
            unit_price=20000000.0,
            amount_before_tax=20000000.0,
            tax_rate="10%",
            tax_amount=2000000.0
        )
        db.session.add(item1)
        db.session.commit()

        # Add item2 with same name to test historical price averaging
        invoice2 = Invoice(
            id="INV-AI-TEST-002",
            number="12346",
            date="2026-05-22",
            seller_name="Cong ty TNHH Thiet bi So A",
            seller_mst="0101234567",
            seller_address="Ha Noi",
            buyer_name="Cong ty TNHH Giai Phap Cong Nghe",
            buyer_mst="0309876543",
            buyer_address="TP HCM",
            amount_before_tax=18000000.0,
            tax_amount=1800000.0,
            total_amount=19800000.0,
            has_signature=True,
            signing_date="2026-05-22",
            payment_method="TM/CK",
            imported_at="2026-05-22 10:00:00",
            import_status="imported"
        )
        db.session.add(invoice2)


        item2 = LineItem(
            invoice_id="INV-AI-TEST-002",
            item_name="Laptop Dell Latitude 7420",
            quantity=1,
            unit_price=18000000.0,
            amount_before_tax=18000000.0,
            tax_rate="10%",
            tax_amount=1800000.0
        )
        db.session.add(item2)
        db.session.commit()

        yield invoice


def test_ai_settings_saving_and_loading(app):
    """Test saving and loading AI auditing configuration fields, including API Key ciphering."""
    with app.app_context():
        ai_settings = {
            "ai_enabled": True,
            "ai_provider": "gemini",
            "ai_model_name": "gemini-1.5-pro",
            "ai_ollama_endpoint": "http://ollama-test-host:11434",
            "ai_api_key": "my-secret-gemini-key",
            "ai_system_prompt": "Custom Compliance Agent Instruction"
        }
        
        save_scheduler_settings(ai_settings)
        loaded = load_scheduler_settings()

        assert loaded["ai_enabled"] is True
        assert loaded["ai_provider"] == "gemini"
        assert loaded["ai_model_name"] == "gemini-1.5-pro"
        assert loaded["ai_ollama_endpoint"] == "http://ollama-test-host:11434"
        # The key should be masked for client view but load_scheduler_settings decrypts if queried programmatically/internally, 
        # or wait - in routes the API masks it. Let's make sure it is saved.
        assert loaded["ai_system_prompt"] == "Custom Compliance Agent Instruction"
        assert loaded["ai_api_key"] != ""  # Should have been encrypted/saved


def test_historical_average_price_calculation(app, sample_invoice):
    """Test that historical unit prices are averaged correctly across line items with matching name."""
    with app.app_context():
        auditor = AIComplianceAuditor()
        avg_price = auditor.get_historical_average_price("Laptop Dell Latitude 7420")
        # Item 1 has 20M, Item 2 has 18M -> average = 19M
        assert avg_price == 19000000.0


@patch("requests.post")
def test_audit_invoice_disabled_does_nothing(mock_post, app, sample_invoice):
    """When AI Auditing is disabled, audit_invoice should immediately return empty and not query any APIs."""
    with app.app_context():
        # Setup settings with AI disabled
        save_scheduler_settings({"ai_enabled": False})
        
        auditor = AIComplianceAuditor()
        db_inv = db.session.get(Invoice, sample_invoice.id)
        results = auditor.audit_invoice(db_inv)
        
        assert len(results) == 0
        mock_post.assert_not_called()


@patch("requests.post")
def test_audit_invoice_ollama_success(mock_post, app, sample_invoice):
    """Test successful Ollama audit workflow producing a warning."""
    with app.app_context():
        save_scheduler_settings({
            "ai_enabled": True,
            "ai_provider": "ollama",
            "ai_ollama_endpoint": "http://localhost:11434",
            "ai_model_name": "gemma-4",
            "ai_system_prompt": "Audit Prompt"
        })

        # Mock Ollama JSON response format
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "message": {
                "content": json.dumps({
                    "anomalies": [
                        {
                            "warning_type": "price_anomaly",
                            "item_name": "Laptop Dell Latitude 7420",
                            "explanation": "Đơn giá 20M cao hơn mức giá trung bình lịch sử (18M) khoảng 11%."
                        }
                    ]
                })
            }
        }
        mock_post.return_value = mock_resp

        auditor = AIComplianceAuditor()
        db_inv = db.session.get(Invoice, sample_invoice.id)
        results = auditor.audit_invoice(db_inv)

        assert len(results) == 1
        assert results[0].warning_type == "price_anomaly"
        assert "Laptop Dell Latitude 7420" in results[0].explanation
        assert db_inv.ai_audited is True

        # Verify endpoint called
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "http://localhost:11434/api/chat"
        payload = kwargs["json"]
        assert payload["model"] == "gemma-4"
        assert payload["format"] == "json"


@patch("requests.post")
def test_audit_invoice_gemini_success(mock_post, app, sample_invoice):
    """Test successful Google Gemini audit workflow with 0 warnings."""
    with app.app_context():
        save_scheduler_settings({
            "ai_enabled": True,
            "ai_provider": "gemini",
            "ai_api_key": "fake-gemini-key",
            "ai_model_name": "gemini-1.5-flash"
        })

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": json.dumps({"anomalies": []})}
                        ]
                    }
                }
            ]
        }
        mock_post.return_value = mock_resp

        auditor = AIComplianceAuditor()
        db_inv = db.session.get(Invoice, sample_invoice.id)
        results = auditor.audit_invoice(db_inv)

        assert len(results) == 0
        assert db_inv.ai_audited is True

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert "generativelanguage.googleapis.com" in args[0]
        assert "fake-gemini-key" in args[0]


def test_api_manual_ai_audit(logged_in_client, app, sample_invoice):
    """Test the manual POST API route to trigger AI Auditing on a local invoice."""
    with app.app_context():
        save_scheduler_settings({
            "ai_enabled": True,
            "ai_provider": "ollama",
            "ai_ollama_endpoint": "http://localhost:11434",
            "ai_model_name": "gemma-4"
        })

    # Mock auditor.audit_invoice to avoid network calls
    with patch.object(AIComplianceAuditor, "audit_invoice") as mock_audit:
        # Create a mock result
        mock_audit.return_value = [
            AIAuditResult(
                invoice_id=sample_invoice.id,
                warning_type="personal_purchase",
                explanation="Nuoc uong Lavie tieu dung ca nhan.",
                created_at="2026-05-23 10:00:00"
            )
        ]

        # Trigger manual audit API
        url = f"/api/invoices/local/{sample_invoice.id}/ai-audit"
        response = logged_in_client.post(url)
        assert response.status_code == 200
        payload = response.get_json()
        assert "ai_warnings" in payload
        assert len(payload["ai_warnings"]) == 1
        
        # Verify call was received by service
        mock_audit.assert_called_once()


def test_invoice_details_returns_ai_warnings_and_status(logged_in_client, app, sample_invoice):
    """Test that the invoice details API returns both ai_warnings and the ai_audited status flag."""
    # We use the active application context from the fixture (do not push a nested one)
    sample_invoice.ai_audited = True
    
    # Add warning
    warning = AIAuditResult(
        invoice_id=sample_invoice.id,
        warning_type="personal_purchase",
        explanation="Warning test explanation",
        created_at="2026-05-23 10:00:00"
    )
    db.session.add(warning)
    db.session.commit()


    # Get details
    response = logged_in_client.get(f"/api/invoices/{sample_invoice.id}/details")
    assert response.status_code == 200
    payload = response.get_json()
    print("PAYLOAD IN TEST:", payload)

    assert "ai_warnings" in payload
    assert len(payload["ai_warnings"]) == 1
    assert payload["ai_warnings"][0]["warning_type"] == "personal_purchase"
    assert payload["ai_warnings"][0]["explanation"] == "Warning test explanation"
    assert payload["ai_audited"] is True


def test_api_chat_sessions_flow(logged_in_client, app):
    """Test the complete AI Chatbot session and messaging REST workflow."""
    from invoices.models import AIChatSession, AIChatMessage

    # 1. Create a session
    payload = {"title": "Cuộc hội thoại mới"}
    response = logged_in_client.post("/api/ai/chat/sessions", json=payload)
    assert response.status_code == 201
    created_session = response.get_json()
    assert "id" in created_session
    assert created_session["title"] == "Cuộc hội thoại mới"
    assert "messages" in created_session
    assert len(created_session["messages"]) == 0

    session_id = created_session["id"]

    # 2. Get list of sessions
    response = logged_in_client.get("/api/ai/chat/sessions")
    assert response.status_code == 200
    sessions_list = response.get_json()
    assert any(s["id"] == session_id for s in sessions_list)

    # 3. Send message with mocked AIChatAgent
    with patch("invoices.ai_service.AIChatAgent.ask") as mock_ask:
        mock_ask.return_value = "Tổng số tiền hóa đơn đã mua là 22.000.000 đ."

        msg_payload = {"message": "Thống kê tổng tiền hóa đơn đã mua?"}
        response = logged_in_client.post(
            f"/api/ai/chat/sessions/{session_id}/message",
            json=msg_payload
        )
        assert response.status_code == 200
        chat_resp = response.get_json()
        assert "user_message" in chat_resp
        assert "assistant_message" in chat_resp
        assert "session_title" in chat_resp
        assert chat_resp["user_message"]["role"] == "user"
        assert chat_resp["user_message"]["content"] == "Thống kê tổng tiền hóa đơn đã mua?"
        assert chat_resp["assistant_message"]["role"] == "assistant"
        assert chat_resp["assistant_message"]["content"] == "Tổng số tiền hóa đơn đã mua là 22.000.000 đ."

        # Verify title was auto-updated since original was default
        assert chat_resp["session_title"] == "Thống kê tổng tiền hóa đơn đã ..."

        mock_ask.assert_called_once_with(session_id, "Thống kê tổng tiền hóa đơn đã mua?")

    # 4. Delete session
    response = logged_in_client.delete(f"/api/ai/chat/sessions/{session_id}")
    assert response.status_code == 200
    del_resp = response.get_json()
    assert del_resp["success"] is True

    # 5. Verify deleted from DB
    with app.app_context():
        deleted_sess = db.session.get(AIChatSession, session_id)
        assert deleted_sess is None
        # Cascade deleted check
        deleted_msgs = AIChatMessage.query.filter_by(session_id=session_id).all()
        assert len(deleted_msgs) == 0


def test_ai_auditor_programmatic_verification(app, sample_invoice):
    """Test that programmatic verification filters out price anomalies below 5% deviation and cash limits below threshold."""
    from invoices.models import LineItem
    from invoices.ai_service import AIComplianceAuditor

    with app.app_context():
        # Save settings
        save_scheduler_settings({
            "ai_enabled": True,
            "ai_provider": "ollama",
            "ai_ollama_endpoint": "http://localhost:11434",
            "ai_model_name": "gemma-4"
        })

        # Clear existing LineItems to be completely clean
        LineItem.query.delete()
        db.session.commit()

        # Add item1 with unit_price 20M
        item1 = LineItem(
            invoice_id=sample_invoice.id,
            item_name="Unique Laptop For Testing Average Price 123",
            quantity=1,
            unit_price=20000000.0,
            amount_before_tax=20000000.0,
            tax_rate="10%",
            tax_amount=2000000.0
        )
        db.session.add(item1)

        # Add a second item to establish historical price
        item2 = LineItem(
            invoice_id="INV-AI-TEST-002",
            item_name="Unique Laptop For Testing Average Price 123",
            quantity=1,
            unit_price=19600000.0,  # Average will be (20M + 19.6M)/2 = 19.8M
            amount_before_tax=19600000.0,
            tax_rate="10%",
            tax_amount=1960000.0
        )
        db.session.add(item2)
        db.session.commit()

        # Verify historical average price
        auditor = AIComplianceAuditor()
        avg = auditor.get_historical_average_price("Unique Laptop For Testing Average Price 123")
        assert avg == 19800000.0

        # Now test that a deviation of 20M vs 19.8M (approx 1.01%) is less than 5%,
        # so a price anomaly warning returned by AI should be ignored programmatically.
        with patch("invoices.ai_service.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            # Mock LLM returning a price anomaly warning and a cash warning (for invoice under threshold)
            mock_resp.json.return_value = {
                "message": {
                    "content": json.dumps({
                        "anomalies": [
                            {
                                "warning_type": "price_anomaly",
                                "item_name": "Unique Laptop For Testing Average Price 123",
                                "explanation": "Đơn giá biến động nhẹ so với trung bình."
                            },
                            {
                                "warning_type": "personal_purchase",
                                "item_name": "",
                                "explanation": "Cảnh báo thanh toán bằng tiền mặt theo Thông tư 219/2013/TT-BTC."
                            }
                        ]
                    })
                }
            }
            mock_post.return_value = mock_resp

            # We change sample_invoice total_amount to 1M (under 20M cash limit)
            db_inv = db.session.get(Invoice, sample_invoice.id)
            db_inv.total_amount = 1000000.0
            db.session.commit()

            results = auditor.audit_invoice(db_inv)
            # Both anomalies should be filtered out by programmatic verification
            assert len(results) == 0


def test_ai_chat_agent_rag_retrieval(app):
    """Test that AIChatAgent uses local RAG database search when intent is general_query."""
    import uuid
    from datetime import datetime
    from invoices.ai_service import get_tax_rag_context, AIChatAgent
    from invoices.models import AIChatSession

    with app.app_context():
        # Save settings
        save_scheduler_settings({
            "ai_enabled": True,
            "ai_provider": "ollama",
            "ai_ollama_endpoint": "http://localhost:11434",
            "ai_model_name": "gemma-4"
        })

        # Test RAG retrieval helper directly
        context_c15 = get_tax_rag_context("Điều kiện khấu trừ thuế GTGT là gì?")
        assert "Điều 15" in context_c15
        assert "không dùng tiền mặt" in context_c15

        context_car = get_tax_rag_context("ô tô dưới 9 chỗ có nguyên giá vượt 1,6 tỷ")
        assert "1,6 tỷ" in context_car or "1.6 tỷ" in context_car

        # Test AIChatAgent ask calls LLM with retrieved context
        agent = AIChatAgent()
        
        # Create dummy session
        from datetime import timezone
        session = AIChatSession(
            id=str(uuid.uuid4()),
            title="Hỏi luật thuế",
            created_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        )
        db.session.add(session)
        db.session.commit()

        with patch("invoices.ai_service.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.side_effect = [
                {"message": {"content": "{\"intent\": \"general_query\"}"}},  # Intent classification call
                {"message": {"content": "Quy định khấu trừ thuế GTGT đầu vào yêu cầu hóa đơn hợp lệ..."}} # Main prompt call
            ]
            mock_post.return_value = mock_resp

            ans = agent.ask(session.id, "Điều kiện khấu trừ thuế GTGT?")
            assert "Quy định khấu trừ" in ans

            # Verify that get_tax_rag_context was integrated into the prompt sent to LLM
            assert mock_post.call_count == 2
            args, kwargs = mock_post.call_args
            prompt_sent = kwargs["json"]["messages"][0]["content"]
            assert "Điều 15" in prompt_sent
            assert "không dùng tiền mặt" in prompt_sent


def test_ai_auditor_gemma4_extended_warnings(app, sample_invoice):
    """Test that AIComplianceAuditor processes and stores all 6 warning types correctly using gemma-4 configuration."""
    with app.app_context():
        # Setup settings with gemma-4 and enabled
        save_scheduler_settings({
            "ai_enabled": True,
            "ai_provider": "ollama",
            "ai_ollama_endpoint": "http://localhost:11434",
            "ai_model_name": "gemma-4"
        })

        # Mock requests.post to return a JSON containing all 6 warning types
        with patch("invoices.ai_service.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "message": {
                    "content": json.dumps({
                        "anomalies": [
                            {
                                "warning_type": "personal_purchase",
                                "item_name": "Điện thoại iPhone 15 Pro",
                                "explanation": "Chi tiêu thiết bị cá nhân cao cấp không hợp lệ khấu trừ thuế."
                            },
                            {
                                "warning_type": "price_anomaly",
                                "item_name": "Laptop Dell Latitude 7420",
                                "explanation": "Đơn giá biến động 35% so với lịch sử (19M)."
                            },
                            {
                                "warning_type": "invoice_timing",
                                "item_name": "",
                                "explanation": "Hóa đơn lập ngày 2026-05-22 nhưng ký ngày 2026-05-24 (trễ 2 ngày)."
                            },
                            {
                                "warning_type": "cash_payment_risk",
                                "item_name": "",
                                "explanation": "Hóa đơn trị giá 22 triệu đồng thanh toán bằng tiền mặt TM sai Điều 15 Thông tư 219/2013."
                            },
                            {
                                "warning_type": "tax_rate_mismatch",
                                "item_name": "Dịch vụ Phần mềm Quản lý",
                                "explanation": "Áp dụng sai thuế suất 8% cho phần mềm CNTT theo Nghị định 72/2024/NĐ-CP."
                            },
                            {
                                "warning_type": "suspicious_transaction",
                                "item_name": "",
                                "explanation": "Nhà cung cấp thuộc danh sách doanh nghiệp rủi ro cao của Tổng cục Thuế."
                            }
                        ]
                    })
                }
            }
            mock_post.return_value = mock_resp

            auditor = AIComplianceAuditor()
            db_inv = db.session.get(Invoice, sample_invoice.id)
            results = auditor.audit_invoice(db_inv)

            # Ensure all 6 anomalies were saved and processed properly
            # Note: total_amount of sample_invoice is 22M, which is >= 20M, so the cash_payment_risk is not filtered out!
            # And Laptop Dell Latitude 7420 deviation: 20M vs average 19M is 5.26%, which is >= 5%, so price_anomaly is not filtered out either!
            assert len(results) == 6
            types = [r.warning_type for r in results]
            assert "personal_purchase" in types
            assert "price_anomaly" in types
            assert "invoice_timing" in types
            assert "cash_payment_risk" in types
            assert "tax_rate_mismatch" in types
            assert "suspicious_transaction" in types

            # Check that correct default model gemma-4 is queried
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            assert kwargs["json"]["model"] == "gemma-4"




