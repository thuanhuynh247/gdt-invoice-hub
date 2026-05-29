"""
Tests for Signature and Blacklist settings filter switches.
"""

from __future__ import annotations

import json
from unittest.mock import patch, MagicMock
import pytest

from extensions import db
from invoices.scheduler import save_scheduler_settings, load_scheduler_settings


def test_signature_and_blacklist_settings_saving_and_loading(app):
    """Test that signature_filter_enabled and blacklist_filter_enabled settings are correctly saved and loaded with defaults."""
    with app.app_context():
        # Clear SystemConfig to ensure defaults are loaded correctly without pollution
        from invoices.models import SystemConfig
        try:
            SystemConfig.query.delete()
            db.session.commit()
        except Exception:
            db.session.rollback()

        # Test defaults first
        defaults = load_scheduler_settings()
        assert defaults.get("signature_filter_enabled") is not False
        assert defaults.get("blacklist_filter_enabled") is not False

        # Save toggled off
        settings_payload = {
            "signature_filter_enabled": False,
            "blacklist_filter_enabled": False
        }
        save_scheduler_settings(settings_payload)
        
        loaded = load_scheduler_settings()
        assert loaded["signature_filter_enabled"] is False
        assert loaded["blacklist_filter_enabled"] is False

        # Save toggled back on
        settings_payload_on = {
            "signature_filter_enabled": True,
            "blacklist_filter_enabled": True
        }
        save_scheduler_settings(settings_payload_on)
        
        loaded_on = load_scheduler_settings()
        assert loaded_on["signature_filter_enabled"] is True
        assert loaded_on["blacklist_filter_enabled"] is True


def test_settings_api_integration(logged_in_client, app):
    """Test that the settings API endpoint successfully stores and retrieves the new settings."""
    payload = {
        "smtp_host": "smtp.test.com",
        "smtp_port": 587,
        "smtp_user": "test@test.com",
        "smtp_pass": "pass123",
        "smtp_use_tls": True,
        "schedule_enabled": True,
        "recipient_email": "admin@test.com",
        "schedule_interval": "daily",
        "schedule_time": "08:00",
        "schedule_weekday": 0,
        "gdt_username": "mst123",
        "gdt_password": "gdtpass123",
        "ai_enabled": True,
        "ai_provider": "gemini",
        "ai_model_name": "gemini-1.5-flash",
        "ai_ollama_endpoint": "http://localhost:11434",
        "ai_api_key": "fakekey",
        "ai_system_prompt": "Audit now",
        "audit_agent_enabled": True,
        "audit_agent_schedule_time": "23:00",
        "telegram_enabled": False,
        "telegram_bot_token": "",
        "telegram_chat_id": "",
        "auto_dunning_enabled": False,
        "signature_filter_enabled": False,
        "blacklist_filter_enabled": False
    }

    # Save settings via API
    response = logged_in_client.post("/api/settings", json=payload)
    assert response.status_code == 200
    
    # Retrieve settings via API
    response_get = logged_in_client.get("/api/settings")
    assert response_get.status_code == 200
    retrieved = response_get.get_json()
    
    assert retrieved["signature_filter_enabled"] is False
    assert retrieved["blacklist_filter_enabled"] is False
