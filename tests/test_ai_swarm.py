"""Unit tests for the AI Swarm P2P Agent Mailroom (US-320)."""

from __future__ import annotations

import json
import pytest
from app import create_app
from extensions import db
from invoices.models import AgentMessage


@pytest.fixture
def app():
    """Create and configure a Flask application for testing."""
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "GDT_USE_MOCK": True,
        "WTF_CSRF_ENABLED": False,
    })

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


def test_agent_message_model(app):
    """Test standard AgentMessage database instantiation and serialization."""
    with app.app_context():
        msg = AgentMessage(
            sender_agent="AuditorAgent",
            receiver_agent="ForecasterAgent",
            subject="ForecastRequest",
            payload=json.dumps({"mst": "0101234567", "year": 2026}),
            status="pending",
            timestamp="2026-06-03T12:00:00Z"
        )
        db.session.add(msg)
        db.session.commit()

        retrieved = AgentMessage.query.first()
        assert retrieved is not None
        assert retrieved.sender_agent == "AuditorAgent"
        assert retrieved.receiver_agent == "ForecasterAgent"
        assert retrieved.status == "pending"

        d = retrieved.to_dict()
        assert d["sender_agent"] == "AuditorAgent"
        assert d["payload"]["mst"] == "0101234567"


def test_agent_mailroom_api(client, app):
    """Test send, inbox retrieval, and status updates via API endpoints."""
    # Send a message
    with client.session_transaction() as sess:
        sess["logged_in"] = True

    response = client.post("/api/agents/send", json={
        "sender_agent": "AuditorAgent",
        "receiver_agent": "ForecasterAgent",
        "subject": "RunForecast",
        "payload": {"mst": "0202020202"}
    })
    assert response.status_code == 201
    res_data = response.get_json()
    assert res_data["success"] is True
    msg_id = res_data["data"]["id"]

    # Check inbox of receiver
    response = client.get("/api/agents/inbox/ForecasterAgent?status=pending")
    assert response.status_code == 200
    inbox = response.get_json()
    assert len(inbox) == 1
    assert inbox[0]["sender_agent"] == "AuditorAgent"
    assert inbox[0]["payload"]["mst"] == "0202020202"

    # Update status to processed
    response = client.post(f"/api/agents/update-status/{msg_id}", json={
        "status": "processed"
    })
    assert response.status_code == 200
    assert response.get_json()["success"] is True

    # Retrieve inbox (pending) - should be empty now
    response = client.get("/api/agents/inbox/ForecasterAgent?status=pending")
    assert response.status_code == 200
    assert len(response.get_json()) == 0

    # Retrieve inbox (processed) - should contain the message
    response = client.get("/api/agents/inbox/ForecasterAgent?status=processed")
    assert response.status_code == 200
    assert len(response.get_json()) == 1


def test_joint_audit_coordinator(client, app):
    """Test the JointAuditCoordinator executing the swarm of agents."""
    with client.session_transaction() as sess:
        sess["logged_in"] = True

    response = client.post("/api/agents/audit-coordinator", json={
        "taxpayer_mst": "0101234567",
        "user_prompt": "Kiểm toán hồ sơ thuế đầu vào và dự báo doanh số năm 2026"
    })
    assert response.status_code == 200
    res_data = response.get_json()
    assert res_data["success"] is True
    assert "report_markdown" in res_data
    assert "swarm_confidence" in res_data
    assert "0101234567" in res_data["report_markdown"]
    assert "AuditorAgent" in res_data["report_markdown"]
    assert "ClassifierAgent" in res_data["report_markdown"]
    assert "ForecasterAgent" in res_data["report_markdown"]
