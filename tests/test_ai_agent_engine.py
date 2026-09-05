"""Unit tests for AI Agent Swarm Audit & Chat REST endpoints (AI Agent In-Depth)."""

import json
import pytest


def test_ai_swarm_audit_endpoint_success(client):
    """Verify /api/ai/swarm-audit triggers JointAuditCoordinator and returns markdown audit report."""
    response = client.post(
        "/api/ai/swarm-audit",
        data=json.dumps({
            "taxpayer_mst": "0312345678",
            "user_prompt": "Kiểm tra rủi ro tuân thủ thuế và giao dịch liên kết"
        }),
        content_type="application/json"
    )
    
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["taxpayer_mst"] == "0312345678"
    assert "swarm_confidence" in data
    assert "report_markdown" in data
    assert "SWARM AUDIT REPORT" in data["report_markdown"]
    assert "AuditorAgent" in data["report_markdown"]


def test_ai_agent_chat_endpoint_success(client):
    """Verify /api/ai/agent-chat processes query using TaxAdvisoryAgent ReAct loop."""
    response = client.post(
        "/api/ai/agent-chat",
        data=json.dumps({
            "query": "Quy định định khoản thuế GTGT theo Thông tư 99/2025/TT-BTC?"
        }),
        content_type="application/json"
    )
    
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "response" in data
    assert data["harness_status"] == "completed"
    assert data["exit_condition"] == "final_answer_reached"


def test_ai_agent_chat_empty_query(client):
    """Verify /api/ai/agent-chat returns 400 when query is missing."""
    response = client.post(
        "/api/ai/agent-chat",
        data=json.dumps({"query": ""}),
        content_type="application/json"
    )
    
    assert response.status_code == 400
    data = response.get_json()
    assert "error" in data
