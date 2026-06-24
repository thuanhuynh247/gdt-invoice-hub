"""Pytest verification suite for V76 Headroom AI Context Optimization & Telemetry Hub.
"""

from __future__ import annotations

import os
import json
import pytest
from flask import Flask
from extensions import db
from invoices.multitenant_service import get_tenant_db_path, bootstrap_tenant_db
from invoices.models import HeadroomTelemetry
from invoices.ai_service import compress_and_log


@pytest.fixture
def mock_app():
    app = Flask(__name__, template_folder="../templates")
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    db.init_app(app)
    
    from auth import auth_blueprint
    from invoices.routes import invoices_blueprint
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(invoices_blueprint)

    @app.route("/")
    def index():
        return "index"

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def mock_tenant_db():
    mst = "0102030499"
    db_path = get_tenant_db_path(mst)
    if os.path.exists(db_path):
        try:
            os.unlink(db_path)
        except Exception:
            pass
    bootstrap_tenant_db(mst)
    yield mst
    if os.path.exists(db_path):
        try:
            os.unlink(db_path)
        except Exception:
            pass


# --- CORE HEADROOM INTEGRATION TESTING ---
def test_compress_and_log_disabled(mock_app):
    with mock_app.app_context():
        settings = {"ai_headroom_enabled": False}
        sys_prompt = "System instructions..."
        user_prompt = "User question..."
        
        # When disabled, should return unchanged prompts immediately
        res_sys, res_user = compress_and_log("TestCaller", settings, sys_prompt, user_prompt)
        assert res_sys == sys_prompt
        assert res_user == user_prompt


def test_compress_and_log_enabled(mock_app):
    with mock_app.app_context():
        # Clean up any existing logs
        HeadroomTelemetry.query.delete()
        db.session.commit()

        settings = {
            "ai_headroom_enabled": True,
            "ai_model_name": "gemma-4",
            "ai_headroom_compress_user_messages": True,
            "ai_headroom_target_ratio": 0.5,
            "ai_headroom_protect_recent": 0
        }
        sys_prompt = "This is a very long instruction that we want to optimize for token count."
        user_prompt = "This is a long message from a user inquiring about tax calculations."
        
        # Call the helper
        res_sys, res_user = compress_and_log("TestCaller", settings, sys_prompt, user_prompt)
        
        # Verify it successfully returns strings (compressed or fallbacked)
        assert isinstance(res_sys, str)
        assert isinstance(res_user, str)
        
        # Verify a telemetry record was committed to the DB
        logs = HeadroomTelemetry.query.all()
        assert len(logs) == 1
        log = logs[0]
        assert log.caller == "TestCaller"
        assert log.model_name == "gemma-4"
        assert log.tokens_before > 0
        assert log.tokens_after > 0
        assert log.tokens_saved >= 0
        assert 0.0 <= log.compression_ratio <= 1.0


# --- FLASK API & ROUTE TESTING ---
def test_v76_headroom_hub_view(mock_app):
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"

    # GET /v76-headroom-hub should return 200
    res = client.get("/v76-headroom-hub")
    assert res.status_code == 200
    assert b"Headroom AI Context Hub" in res.data


def test_api_headroom_stats(mock_app):
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"

    with mock_app.app_context():
        # Seed a dummy telemetry log
        telemetry = HeadroomTelemetry(
            timestamp="2026-06-24 12:00:00",
            caller="TestCaller",
            model_name="gemma-4",
            tokens_before=100,
            tokens_after=60,
            tokens_saved=40,
            compression_ratio=0.6,
            transforms_applied='["test:transform"]'
        )
        db.session.add(telemetry)
        db.session.commit()

    # GET /api/headroom/stats should return JSON containing correct aggregations
    res = client.get("/api/headroom/stats")
    assert res.status_code == 200
    data = json.loads(res.data)
    
    assert data["headroom_installed"] is True
    assert data["total_calls"] == 1
    assert data["total_tokens_before"] == 100
    assert data["total_tokens_after"] == 60
    assert data["total_tokens_saved"] == 40
    assert data["average_compression_ratio"] == 0.4  # (100 - 60) / 100 = 0.4 (which is 40% saved)
    assert len(data["recent_events"]) == 1
    assert data["recent_events"][0]["caller"] == "TestCaller"


def test_api_headroom_playground(mock_app):
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"

    # POST /api/headroom/playground with valid payload should perform compression
    payload = {
        "system_prompt": "You are a specialized AI audit advisor.",
        "user_content": "Analyze these tax invoices and find VAT discrepancies.",
        "model_name": "gemma-4",
        "compress_user_messages": True,
        "target_ratio": 0.5,
        "protect_recent": 0
    }
    
    res = client.post("/api/headroom/playground", json=payload)
    assert res.status_code == 200
    data = json.loads(res.data)
    
    assert data["status"] == "success"
    assert "tokens_before" in data
    assert "tokens_after" in data
    assert "tokens_saved" in data
    assert "compression_ratio" in data
    assert "transforms_applied" in data
    assert "compressed_system_prompt" in data
    assert "compressed_user_content" in data
