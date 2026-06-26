"""Pytest verification suite for V77 WAF Resilience, Proxy Manager, and Controller API.
"""

from __future__ import annotations

import json
import pytest
from flask import Flask
from extensions import db
from auth.proxy_manager import GDTProxyManager, proxy_manager
from invoices.models import SystemConfig

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
        # Seed default settings in DB
        db.session.add(SystemConfig(key="gdt_proxies", value="http://1.2.3.4:8080,http://5.6.7.8:8080"))
        db.session.commit()
        # Force proxy manager to sync with our freshly created DB configuration
        proxy_manager.sync_proxies()
        yield app
        db.drop_all()


# --- PROXY MANAGER CORE TESTS ---

def test_proxy_manager_sync_and_rotation(mock_app):
    with mock_app.app_context():
        # Check proxies synced from DB seed
        proxies = proxy_manager.get_all_proxy_stats()
        assert len(proxies) == 2
        urls = [p["url"] for p in proxies]
        assert "http://1.2.3.4:8080" in urls
        assert "http://5.6.7.8:8080" in urls

        # Check active proxy selection
        selected = proxy_manager.get_active_proxy()
        assert selected is not None
        assert selected["http"] in ["http://1.2.3.4:8080", "http://5.6.7.8:8080"]


def test_proxy_manager_failures_and_cooldown(mock_app):
    with mock_app.app_context():
        proxy_manager.clear_cooldowns()
        target = "http://1.2.3.4:8080"

        # Trigger single failure (not a WAF error, e.g. status 500)
        proxy_manager.report_failure(target, status_code=500, error_msg="Server Error")
        stats = proxy_manager.get_all_proxy_stats()
        target_stat = next(p for p in stats if p["url"] == target)
        
        assert target_stat["consecutive_failures"] == 1
        assert target_stat["status"] == "Active"

        # Triggering successive failures to exceed limit (consecutive_failures >= 3)
        for _ in range(2):
            proxy_manager.report_failure(target, status_code=500, error_msg="Server Error")
            
        stats2 = proxy_manager.get_all_proxy_stats()
        target_stat2 = next(p for p in stats2 if p["url"] == target)
        assert target_stat2["consecutive_failures"] == 3
        assert target_stat2["status"] == "CoolDown"
        assert target_stat2["cool_down_remaining"] > 0
        
        # Test getting next proxy when one is in cooldown
        next_p = proxy_manager.get_active_proxy()
        assert next_p is not None
        assert next_p["http"] == "http://5.6.7.8:8080"  # The only active proxy left

        # Test recovery on success
        proxy_manager.report_success(target, latency_ms=120.0)
        stats3 = proxy_manager.get_all_proxy_stats()
        target_stat3 = next(p for p in stats3 if p["url"] == target)
        assert target_stat3["consecutive_failures"] == 0
        assert target_stat3["status"] == "Active"


def test_global_cooldown_trigger(mock_app):
    with mock_app.app_context():
        proxy_manager.clear_cooldowns()
        assert proxy_manager.is_global_cooldown() is False

        # Simulate WAF trigger (e.g. status code 403)
        proxy_manager.report_failure("http://1.2.3.4:8080", status_code=403, error_msg="WAF Forbidden")

        assert proxy_manager.is_global_cooldown() is True
        assert proxy_manager.get_global_cooldown_remaining() > 0


# --- ROUTE / CONTROLLER API TESTS ---

def test_page_waf_resilience_view(mock_app):
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"

    res = client.get("/v77-waf-resilience")
    assert res.status_code == 200
    assert b"WAF Resilience" in res.data


def test_api_waf_resilience_status(mock_app):
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"

    res = client.get("/api/waf-resilience/status")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["status"] == "success"
    assert "global_cooldown_active" in data
    assert "proxies" in data
    assert len(data["proxies"]) == 2


def test_api_waf_resilience_control_actions(mock_app):
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"

    # 1. Clear Cooldowns
    res_clear = client.post("/api/waf-resilience/control", json={"action": "clear_cooldowns"})
    assert res_clear.status_code == 200
    assert b"success" in res_clear.data

    # 2. Add Proxy
    res_add = client.post("/api/waf-resilience/control", json={"action": "add_proxy", "proxy_url": "http://9.9.9.9:8080"})
    assert res_add.status_code == 200
    data_add = json.loads(res_add.data)
    assert data_add["status"] == "success"

    # Verify added in status
    res_status = client.get("/api/waf-resilience/status")
    data_status = json.loads(res_status.data)
    assert any(p["url"] == "http://9.9.9.9:8080" for p in data_status["proxies"])

    # 3. Simulate Request
    res_sim = client.post("/api/waf-resilience/control", json={
        "action": "simulate_request",
        "proxy_url": "http://9.9.9.9:8080",
        "status_code": 403,
        "latency_ms": 350.0
    })
    assert res_sim.status_code == 200

    # 4. Delete Proxy
    res_del = client.post("/api/waf-resilience/control", json={"action": "delete_proxy", "proxy_url": "http://9.9.9.9:8080"})
    assert res_del.status_code == 200
    
    # Verify deleted in status
    res_status2 = client.get("/api/waf-resilience/status")
    data_status2 = json.loads(res_status2.data)
    assert not any(p["url"] == "http://9.9.9.9:8080" for p in data_status2["proxies"])
