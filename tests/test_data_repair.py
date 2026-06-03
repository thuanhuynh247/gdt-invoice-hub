"""
Tests for XML Intelligent Data Repair (US-030).
Covers spell_money_vietnamese, expand_abbreviations, AIDataRepairer class, and route controls.
"""

from __future__ import annotations

import json
from unittest.mock import patch, MagicMock
import pytest

from extensions import db
from invoices.models import Invoice
from invoices.ai_service import spell_money_vietnamese, expand_abbreviations, AIDataRepairer


@pytest.fixture
def repair_sample_invoice(app):
    """Seed a sample invoice in the database for testing data repair."""
    with app.app_context():
        # Clear existing invoices
        Invoice.query.delete()
        db.session.commit()

        invoice = Invoice(
            id="INV-REPAIR-TEST",
            number="998877",
            date="2026-05-23",
            seller_name="CONG TY TNHH DT & TM AN PHAT MTV",
            seller_mst="0109988776",
            seller_address="123 Duong P. Gia Thuy, Q. Long Bien, HN",
            buyer_name="CP DIEN TU PHUONG DONG",
            buyer_mst="0301122334",
            buyer_address="456 P. Ben Nghe, Q.1, HCM",
            amount_before_tax=12300000.0,
            tax_amount=1230000.0,
            total_amount=13530000.0,
            amount_in_words="mười ba triệu năm trăm ba mươi nghìn đồng", # Incorrect or needs correction
            has_signature=True,
            signing_date="2026-05-23",
            payment_method="CK",
            imported_at="2026-05-23 10:00:00",
            import_status="imported"
        )
        db.session.add(invoice)
        db.session.commit()
        yield invoice


def test_spell_money_vietnamese():
    """Verify correct Vietnamese currency spelling with complex numbers."""
    assert spell_money_vietnamese(0) == "Không đồng"
    assert spell_money_vietnamese(105) == "Một trăm linh năm đồng chẵn"
    assert spell_money_vietnamese(115) == "Một trăm mười lăm đồng chẵn"
    assert spell_money_vietnamese(121) == "Một trăm hai mươi mốt đồng chẵn"
    assert spell_money_vietnamese(1500) == "Một nghìn năm trăm đồng chẵn"
    assert spell_money_vietnamese(1000000) == "Một triệu đồng chẵn"
    assert spell_money_vietnamese(13530000) == "Mười ba triệu năm trăm ba mươi nghìn đồng chẵn"
    assert spell_money_vietnamese(1002003005) == "Một tỷ không trăm linh hai triệu không trăm linh ba nghìn không trăm linh năm đồng chẵn"


def test_expand_abbreviations():
    """Verify expansion of standard Vietnamese corporate and location abbreviations."""
    raw_text = "CONG TY TNHH TM DV CP AN PHAT MTV TAI HN VA HCM. ADDR: P. GIA THUY, Q. LONG BIEN, HN"
    expected = "CONG TY Trách nhiệm Hữu hạn Thương mại Dịch vụ Cổ phần AN PHAT Một thành viên TAI Hà Nội VA Thành phố. Hồ Chí Minh. ADDR: Phường GIA THUY, Quận LONG BIEN, Hà Nội"
    assert expand_abbreviations(raw_text) == expected


@patch("invoices.ai_service.load_scheduler_settings")
@patch("invoices.ai_service.requests.post")
def test_ai_data_repairer_ollama_success(mock_post, mock_load_settings, repair_sample_invoice):
    """Verify AIDataRepairer standardizes metadata successfully using Ollama model response."""
    mock_load_settings.return_value = {
        "ai_enabled": True,
        "ai_provider": "ollama",
        "ai_model_name": "gemma-4",
        "ai_ollama_endpoint": "http://localhost:11434"
    }

    # Mock successful JSON response from local Ollama API
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {
            "content": json.dumps({
                "seller_name": "Công ty TNHH Đầu tư & Thương mại An Phát Một thành viên",
                "buyer_name": "Công ty Cổ phần Điện tử Phương Đông",
                "buyer_address": "456 Phường Bến Nghé, Quận 1, Thành phố Hồ Chí Minh",
                "amount_in_words": "Mười ba triệu năm trăm ba mươi nghìn đồng chẵn"
            })
        }
    }
    mock_post.return_value = mock_response

    repairer = AIDataRepairer()
    result = repairer.repair_metadata(repair_sample_invoice)

    assert result["seller_name"] == "Công ty TNHH Đầu tư & Thương mại An Phát Một thành viên"
    assert result["buyer_name"] == "Công ty Cổ phần Điện tử Phương Đông"
    assert result["buyer_address"] == "456 Phường Bến Nghé, Quận 1, Thành phố Hồ Chí Minh"
    assert result["amount_in_words"] == "Mười ba triệu năm trăm ba mươi nghìn đồng chẵn"

    # Verify that prompt content was generated correctly in the outgoing API payload
    called_args, called_kwargs = mock_post.call_args
    payload = called_kwargs["json"]
    user_content = payload["messages"][1]["content"]
    assert "CONG TY TNHH DT & TM AN PHAT MTV" in user_content
    assert "CP DIEN TU PHUONG DONG" in user_content


@patch("invoices.ai_service.load_scheduler_settings")
@patch("invoices.ai_service.requests.post")
def test_ai_data_repairer_fallback_on_error(mock_post, mock_load_settings, repair_sample_invoice):
    """Verify AIDataRepairer gracefully falls back to deterministic rule expansions if API fails."""
    mock_load_settings.return_value = {
        "ai_enabled": True,
        "ai_provider": "ollama",
        "ai_model_name": "gemma-4"
    }
    # Mock Ollama API exception
    mock_post.side_effect = Exception("Ollama endpoint offline")

    repairer = AIDataRepairer()
    result = repairer.repair_metadata(repair_sample_invoice)

    # Fallback must expand abbreviations via deterministic rules
    assert "Trách nhiệm Hữu hạn" in result["seller_name"]
    assert "Hồ Chí Minh" in result["buyer_address"]
    assert "Cổ phần" in result["buyer_name"]
    # Amount in words is standardized to spell money correctly
    assert result["amount_in_words"] == "Mười ba triệu năm trăm ba mươi nghìn đồng chẵn"


def test_route_repair_metadata_unauthorized(client):
    """Verify route blocks unauthorized access with 401."""
    response = client.post("/api/ai/repair-metadata", json={"invoice_id": "INV-REPAIR-TEST"})
    assert response.status_code == 302 or response.status_code == 401 # Redirects to login


@patch("invoices.ai_service.requests.post")
def test_route_repair_metadata_and_apply_flow(mock_post, logged_in_client, repair_sample_invoice):
    """Verify complete end-to-end flow from repair generation to applying and persistence."""
    # Mock Ollama local LLM output
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {
            "content": json.dumps({
                "seller_name": "Công ty TNHH Đầu tư & Thương mại An Phát Một thành viên",
                "buyer_name": "Công ty Cổ phần Điện tử Phương Đông",
                "buyer_address": "456 Phường Bến Nghé, Quận 1, Thành phố Hồ Chí Minh",
                "amount_in_words": "Mười ba triệu năm trăm ba mươi nghìn đồng chẵn"
            })
        }
    }
    mock_post.return_value = mock_response

    # 1. Ask for metadata repair suggestions
    res = logged_in_client.post("/api/ai/repair-metadata", json={
        "invoice_id": "INV-REPAIR-TEST"
    })
    assert res.status_code == 200
    data = res.get_json()

    assert "before" in data
    assert "after" in data
    assert "differences" in data
    assert "seller_name" in data["differences"]
    assert "buyer_name" in data["differences"]

    # 2. Apply modifications to database
    apply_res = logged_in_client.post("/api/ai/apply-repair", json={
        "invoice_id": "INV-REPAIR-TEST",
        "fields": ["seller_name", "buyer_name", "buyer_address"],
        "seller_name": "Công ty TNHH Đầu tư & Thương mại An Phát Một thành viên",
        "buyer_name": "Công ty Cổ phần Điện tử Phương Đông",
        "buyer_address": "456 Phường Bến Nghé, Quận 1, Thành phố Hồ Chí Minh"
    })
    assert apply_res.status_code == 200
    apply_data = apply_res.get_json()
    assert apply_data["success"] is True

    # 3. Check database to verify persistence
    with logged_in_client.application.app_context():
        updated_invoice = db.session.get(Invoice, "INV-REPAIR-TEST")
        assert updated_invoice.seller_name == "Công ty TNHH Đầu tư & Thương mại An Phát Một thành viên"
        assert updated_invoice.buyer_name == "Công ty Cổ phần Điện tử Phương Đông"
        # Since amount_in_words was NOT in selected fields list, it should remain untouched (raw string)
        assert updated_invoice.amount_in_words == "mười ba triệu năm trăm ba mươi nghìn đồng"
