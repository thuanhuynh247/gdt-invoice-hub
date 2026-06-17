"""
Tests for Version 32.0.0 VAT Refund Exporter Wizard & Swarm AI compiler.
"""

from __future__ import annotations

import json
from datetime import datetime
from extensions import db
from invoices.models import Invoice, LineItem, TaxpayerProfile, BankTransaction
from tests.test_vat_refund import _seed_refund_test_data

def test_v32_compliance_page_route(logged_in_client):
    """Verify GET /v32-compliance page route loads successfully."""
    response = logged_in_client.get("/v32-compliance")
    assert response.status_code == 200
    assert b"Wise Exporter VAT Refund Wizard" in response.data
    assert b"Version 32.0.0" in response.data

def test_api_agents_swarm_v32_chat_route(logged_in_client, app):
    """Verify POST /api/agents/swarm-v32-chat endpoint returns structured multi-agent timeline and defense briefing."""
    _seed_refund_test_data(app)

    # Call swarm endpoint
    response = logged_in_client.post(
        "/api/agents/swarm-v32-chat",
        json={
            "taxpayer_mst": "0109998887",
            "taxpayer_name": "CONG TY CO PHAN CONG NGHE TOAN CAU",
            "eligible_invoice_ids": ["PUR-VAL-01"],
            "customs_declarations": [
                {
                    "declaration_number": "HQ-2026-001",
                    "product_description": "Phan mem xuat khau",
                    "quantity": 1,
                    "customs_value_vnd": 200000000.0
                }
            ]
        }
    )
    
    assert response.status_code == 200
    payload = response.get_json()
    
    assert payload["status"] == "success"
    assert "chat_steps" in payload
    assert len(payload["chat_steps"]) > 0
    
    # Assert specific agents are present in the discussion
    agents = [step["agent"] for step in payload["chat_steps"]]
    assert "RefundCoordinator" in agents
    assert "RefundAuditor" in agents
    assert "CustomsLiaison" in agents
    assert "TaxCounsel" in agents

    # Assert report contains sections
    report = payload["report_markdown"]
    assert "BÁO CÁO PHÂN TÍCH RỦI RO & PHÒNG VỆ HỒ SƠ HOÀN THUẾ GTGT" in report
    assert "KHUYM" in report or "Hệ thống meInvoice" in report
    assert "0109998887" in report
