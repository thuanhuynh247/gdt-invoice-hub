"""Tests for Agent Harness endpoints."""

from __future__ import annotations
import json
import pytest
import sqlite3


@pytest.fixture(autouse=True)
def clean_harness_db():
    """Clear test data from harness.db before each test to ensure test isolation."""
    conn = None
    try:
        conn = sqlite3.connect("harness.db", timeout=10.0)
        cur = conn.cursor()
        # Check if tables exist first
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='story';")
        if cur.fetchone():
            cur.execute("DELETE FROM story WHERE id = 'STORY-TEST-999'")
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='decision';")
        if cur.fetchone():
            cur.execute("DELETE FROM decision WHERE id = 'ADR-TEST-999'")
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='backlog';")
        if cur.fetchone():
            cur.execute("DELETE FROM backlog WHERE title = 'Add OpenTelemetry Logging'")
        conn.commit()
    except Exception:
        pass
    finally:
        if conn:
            conn.close()


def test_harness_summary_requires_login(client):
    """Anonymous users should be redirected or unauthorized."""
    response = client.get("/api/harness/summary")
    assert response.status_code == 401


def test_harness_summary_success(logged_in_client):
    """Get harness dashboard summary."""
    response = logged_in_client.get("/api/harness/summary")
    assert response.status_code == 200, f"Status: {response.status_code}, Body: {response.get_data(as_text=True)}"
    data = response.get_json()
    assert "stats" in data
    assert "stories" in data
    assert "decisions" in data
    assert "backlog" in data
    assert "traces" in data


def test_add_and_update_story(logged_in_client):
    """Create a new story and then update it."""
    story_payload = {
        "id": "STORY-TEST-999",
        "title": "Unit Test Story Integration",
        "lane": "tiny",
        "contract_doc": "docs/stories/story_test_999.md",
        "status": "planned",
        "notes": "Testing python routes"
    }
    response = logged_in_client.post(
        "/api/harness/story",
        data=json.dumps(story_payload),
        content_type="application/json"
    )
    assert response.status_code == 200, f"Status: {response.status_code}, Body: {response.get_data(as_text=True)}"
    res_data = response.get_json()
    assert res_data["success"] is True

    # Update the story
    update_payload = {
        "id": "STORY-TEST-999",
        "status": "in_progress",
        "evidence": "Successfully created testing harness",
        "proofs": {
            "unit": 1,
            "integration": 0,
            "e2e": 0,
            "platform": 1
        }
    }
    update_res = logged_in_client.post(
        "/api/harness/story/update",
        data=json.dumps(update_payload),
        content_type="application/json"
    )
    assert update_res.status_code == 200, f"Status: {update_res.status_code}, Body: {update_res.get_data(as_text=True)}"
    update_data = update_res.get_json()
    assert update_data["success"] is True


def test_add_decision(logged_in_client):
    """Create a new architecture decision record."""
    decision_payload = {
        "id": "ADR-TEST-999",
        "title": "Use SQLite for Harness Metadata",
        "status": "accepted",
        "doc_path": "docs/decisions/adr_test_999.md",
        "verify_cmd": "sqlite3 harness.db 'SELECT * FROM decisions;'",
        "predicted_impact": "Fast persistent storage with minimal setups",
        "notes": "Automated tests note"
    }
    response = logged_in_client.post(
        "/api/harness/decision",
        data=json.dumps(decision_payload),
        content_type="application/json"
    )
    assert response.status_code == 200, f"Status: {response.status_code}, Body: {response.get_data(as_text=True)}"
    data = response.get_json()
    assert data["success"] is True


def test_add_backlog_item(logged_in_client):
    """Create a new backlog suggestion."""
    backlog_payload = {
        "title": "Add OpenTelemetry Logging",
        "discovered_while": "Agent Run 4",
        "current_pain": "Hard to trace multiple async runs",
        "suggested_improvement": "Integrate telemetry dashboard",
        "risk": "medium",
        "status": "open",
        "predicted_impact": "Traceability",
        "notes": "Testing note"
    }
    response = logged_in_client.post(
        "/api/harness/backlog",
        data=json.dumps(backlog_payload),
        content_type="application/json"
    )
    assert response.status_code == 200, f"Status: {response.status_code}, Body: {response.get_data(as_text=True)}"
    data = response.get_json()
    assert data["success"] is True


def test_stream_agent_logs_missing_goal(logged_in_client):
    """Log streaming SSE endpoint should fail without a goal."""
    response = logged_in_client.get("/api/harness/agent/stream?provider=gemini")
    assert response.status_code == 400


def test_stream_agent_logs(logged_in_client):
    """Ensure log streaming SSE endpoint is accessible and returns event stream."""
    response = logged_in_client.get("/api/harness/agent/stream?provider=gemini&model=gemini-2.5-flash&goal=test-run-compilation")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["Content-Type"]


def test_harness_page_requires_login(client):
    """Anonymous users should be redirected to login page when trying to access /harness."""
    response = client.get("/harness")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_harness_page_success(logged_in_client):
    """Authenticated users should get the /harness HTML page."""
    response = logged_in_client.get("/harness")
    assert response.status_code == 200
    assert b"Harness Control Center" in response.data
