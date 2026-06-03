"""Tests for the background scheduler and email dispatching module."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, time, timedelta
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from invoices.scheduler import (
    add_scheduler_log,
    get_scheduler_logs,
    load_scheduler_settings,
    save_scheduler_settings,
    should_trigger,
    trigger_scheduled_export_job,
)


@pytest.fixture
def temp_db(app, monkeypatch):
    """Fixture to mock a clean temporary JSON database for settings."""
    from extensions import db
    from invoices.models import SystemConfig, SchedulerLog
    try:
        SystemConfig.query.delete()
        SchedulerLog.query.delete()
        db.session.commit()
    except Exception:
        db.session.rollback()

    temp_dir = tempfile.TemporaryDirectory()
    db_path = os.path.join(temp_dir.name, "invoices_db.json")

    # Set mock db path
    monkeypatch.setattr("invoices.scheduler.DB_FILE", db_path)
    monkeypatch.setattr("invoices.service.DB_FILE", db_path)
    monkeypatch.setattr("invoices.mst_service.DB_FILE", db_path)

    yield db_path

    try:
        SystemConfig.query.delete()
        SchedulerLog.query.delete()
        db.session.commit()
    except Exception:
        db.session.rollback()
    temp_dir.cleanup()


def test_load_default_settings(temp_db):
    """Test loading settings when no database exists."""
    settings = load_scheduler_settings()
    assert settings["smtp_host"] == ""
    assert settings["smtp_port"] == 587
    assert settings["schedule_enabled"] is False
    assert settings["schedule_interval"] == "daily"


def test_save_and_load_settings(temp_db):
    """Test saving settings encrypts credentials."""
    new_settings = {
        "smtp_host": "smtp.mail.com",
        "smtp_port": 465,
        "smtp_user": "user@mail.com",
        "smtp_pass": "securePass123",
        "smtp_use_tls": True,
        "schedule_enabled": True,
        "recipient_email": "rec@mail.com",
        "schedule_interval": "weekly",
        "schedule_time": "14:30",
        "schedule_weekday": 2,
        "gdt_username": "123456",
        "gdt_password": "gdtPassword456",
    }

    # Save settings
    save_scheduler_settings(new_settings)

    # Query the SQLite database directly to verify password encryption
    from extensions import db
    from invoices.models import SystemConfig
    smtp_pass_cfg = db.session.get(SystemConfig, "smtp_pass")
    gdt_pass_cfg = db.session.get(SystemConfig, "gdt_password")
    assert smtp_pass_cfg is not None
    assert smtp_pass_cfg.value != "securePass123"
    assert gdt_pass_cfg is not None
    assert gdt_pass_cfg.value != "gdtPassword456"

    # Load settings via scheduler API (raw storage values are returned)
    loaded = load_scheduler_settings()
    assert loaded["smtp_pass"] != "securePass123"
    assert loaded["gdt_password"] != "gdtPassword456"
    assert loaded["smtp_host"] == "smtp.mail.com"
    assert loaded["schedule_interval"] == "weekly"

    # Saving with loaded settings preserves encryption
    save_scheduler_settings(loaded)
    loaded_again = load_scheduler_settings()
    assert loaded_again["smtp_pass"] == loaded["smtp_pass"]



def test_scheduler_logging(temp_db):
    """Test scheduler log limits and storage."""
    # Ensure logs start empty
    assert len(get_scheduler_logs()) == 0

    # Add 60 logs (limit should cap it at 50)
    for i in range(60):
        add_scheduler_log("SUCCESS", f"Log iteration {i}")

    logs = get_scheduler_logs()
    assert len(logs) == 50
    # First item in list is the newest log
    assert logs[0]["details"] == "Log iteration 59"
    assert logs[-1]["details"] == "Log iteration 10"


def test_should_trigger():
    """Test should_trigger helper logic."""
    # Base configuration: trigger daily at 08:00
    settings = {
        "schedule_enabled": True,
        "schedule_interval": "daily",
        "schedule_time": "08:00",
        "schedule_weekday": 0,
        "last_run": None,
    }

    # Test Enabled flag
    disabled_settings = settings.copy()
    disabled_settings["schedule_enabled"] = False
    assert should_trigger(disabled_settings, datetime(2026, 5, 20, 8, 0, 0)) is False

    # Test Match Time
    # If clock says 07:54 (6 minutes away), should not trigger
    assert should_trigger(settings, datetime(2026, 5, 20, 7, 54, 0)) is False
    # Clock says 08:00, matches
    assert should_trigger(settings, datetime(2026, 5, 20, 8, 0, 0)) is True
    # Clock says 08:02, matches (window range of 5 minutes is allowed)
    assert should_trigger(settings, datetime(2026, 5, 20, 8, 2, 0)) is True
    # Clock says 08:06, window elapsed, should not trigger
    assert should_trigger(settings, datetime(2026, 5, 20, 8, 6, 0)) is False

    # Test Last Run protection (no double dispatch in same calendar day)
    already_run_settings = settings.copy()
    already_run_settings["last_run"] = "2026-05-20"
    # Even if time matches, last run is today
    assert should_trigger(already_run_settings, datetime(2026, 5, 20, 8, 0, 0)) is False
    # Next day at matching time, should trigger
    assert should_trigger(already_run_settings, datetime(2026, 5, 21, 8, 0, 0)) is True

    # Test Weekly Interval weekday matching
    weekly_settings = settings.copy()
    weekly_settings["schedule_interval"] = "weekly"
    weekly_settings["schedule_weekday"] = 2  # Wednesday (0=Monday, 2=Wednesday)

    # 2026-05-20 is a Wednesday (weekday = 2)
    assert should_trigger(weekly_settings, datetime(2026, 5, 20, 8, 0, 0)) is True
    # 2026-05-21 is a Thursday (weekday = 3), should not trigger even if time matches
    assert should_trigger(weekly_settings, datetime(2026, 5, 21, 8, 0, 0)) is False


@patch("invoices.scheduler.smtplib.SMTP")
@patch("invoices.service.fetch_invoices")
def test_trigger_scheduled_export_job(mock_fetch_invoices, mock_smtp, app, temp_db):
    """Test the complete scheduled job execution path and email generation."""
    # Setup mock invoice fetcher to return empty list
    mock_fetch_invoices.return_value = []

    # Setup settings
    settings = {
        "smtp_host": "smtp.test.com",
        "smtp_port": 587,
        "smtp_user": "sender@test.com",
        "smtp_pass": "smtp_secret_pass",
        "smtp_use_tls": True,
        "schedule_enabled": True,
        "recipient_email": "receiver@test.com",
        "schedule_interval": "daily",
        "schedule_time": "08:00",
        "gdt_username": "tax123",
        "gdt_password": "gdt_secret_pass",
    }

    # Mock the SMTP connection object
    smtp_instance = MagicMock()
    mock_smtp.return_value = smtp_instance

    with app.app_context():
        save_scheduler_settings(settings)
        trigger_scheduled_export_job(app)

    # Verify fetch was called
    assert mock_fetch_invoices.call_count == 2
    
    # Verify SMTP calls were made to send report
    mock_smtp.assert_called_once_with("smtp.test.com", 587, timeout=20)
    smtp_instance.starttls.assert_called_once()
    smtp_instance.login.assert_called_once_with("sender@test.com", "smtp_secret_pass")
    smtp_instance.sendmail.assert_called_once()

    # Verify log entry success
    logs = get_scheduler_logs()
    assert len(logs) == 1
    assert logs[0]["status"] == "SUCCESS"
    assert "Tổng số: 0 hóa đơn" in logs[0]["details"]


def test_api_endpoints(logged_in_client, temp_db):
    """Test HTTP API endpoints for settings and logs."""
    # 1. GET /api/settings
    resp = logged_in_client.get("/api/settings")
    assert resp.status_code == 200
    data = resp.json
    assert data["smtp_host"] == ""
    assert data["schedule_enabled"] is False

    # 2. POST /api/settings
    payload = {
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "smtp_user": "abc@gmail.com",
        "smtp_pass": "mypass123",
        "smtp_use_tls": True,
        "schedule_enabled": True,
        "recipient_email": "target@mail.com",
        "schedule_interval": "daily",
        "schedule_time": "09:00",
        "schedule_weekday": 0,
        "gdt_username": "mst123",
        "gdt_password": "gdtpass123",
        "audit_agent_enabled": True,
        "audit_agent_schedule_time": "22:30",
        "telegram_enabled": True,
        "telegram_bot_token": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
        "telegram_chat_id": "-100123456789",
    }
    resp = logged_in_client.post("/api/settings", json=payload)
    assert resp.status_code == 200
    assert resp.json["status"] == "success"

    # Check settings saved correctly via GET
    resp = logged_in_client.get("/api/settings")
    data = resp.json
    assert data["smtp_host"] == "smtp.gmail.com"
    assert data["smtp_pass"] == "••••••••"  # Masked
    assert data["audit_agent_enabled"] is True
    assert data["audit_agent_schedule_time"] == "22:30"
    assert data["telegram_enabled"] is True
    assert data["telegram_bot_token"] == "••••••••"  # Masked
    assert data["telegram_chat_id"] == "-100123456789"

    # 3. GET /api/settings/logs
    resp = logged_in_client.get("/api/settings/logs")
    assert resp.status_code == 200
    assert isinstance(resp.json, list)

    # 4. POST /api/settings/test-email (mock SMTP)
    with patch("invoices.scheduler.smtplib.SMTP") as mock_smtp:
        smtp_instance = MagicMock()
        mock_smtp.return_value = smtp_instance

        test_payload = {
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "smtp_user": "abc@gmail.com",
            "smtp_pass": "mypass123",
            "smtp_use_tls": True,
            "recipient_email": "test-to@gmail.com",
        }
        resp = logged_in_client.post("/api/settings/test-email", json=test_payload)
        assert resp.status_code == 200
        assert resp.json["status"] == "success"
        mock_smtp.assert_called_once_with("smtp.gmail.com", 587, timeout=20)
        smtp_instance.starttls.assert_called_once()
        smtp_instance.login.assert_called_once_with("abc@gmail.com", "mypass123")
        smtp_instance.sendmail.assert_called_once()


@patch("invoices.scheduler.smtplib.SMTP")
@patch("invoices.service.import_xml_invoice")
@patch("invoices.service.download_invoice_xml")
@patch("invoices.service.fetch_invoices")
def test_scheduled_export_multi_mst(mock_fetch_invoices, mock_download_xml, mock_import_xml, mock_smtp, app, temp_db):
    """Verify that background scheduled export iterates and crawls through multiple active taxpayer profiles."""
    from extensions import db
    from invoices.models import TaxpayerProfile
    from auth.crypto import encrypt_password

    # Setup mock invoices to return
    mock_fetch_invoices.return_value = [{"id": "inv-1", "date": "2026-05-25", "amount": 100.0, "status": "Gốc", "issuer": "Seller A", "description": "Desc"}]
    mock_download_xml.return_value = b"<xml></xml>"
    mock_import_xml.return_value = {"import_status": "imported"}

    # Setup settings
    settings = {
        "smtp_host": "smtp.test.com",
        "smtp_port": 587,
        "smtp_user": "sender@test.com",
        "smtp_pass": "smtp_secret_pass",
        "smtp_use_tls": True,
        "schedule_enabled": True,
        "recipient_email": "receiver@test.com",
        "schedule_interval": "daily",
        "schedule_time": "08:00",
    }

    smtp_instance = MagicMock()
    mock_smtp.return_value = smtp_instance

    with app.app_context():
        # Clear profiles first
        TaxpayerProfile.query.delete()

        # Add two profiles
        p1 = TaxpayerProfile(
            mst="0101111111",
            company_name="Company One",
            gdt_username="user1",
            gdt_password_encrypted=encrypt_password("pass1"),
            is_active=True,
            created_at="2026-05-25 11:45:00"
        )
        p2 = TaxpayerProfile(
            mst="0202222222",
            company_name="Company Two",
            gdt_username="user2",
            gdt_password_encrypted=encrypt_password("pass2"),
            is_active=True,
            created_at="2026-05-25 11:45:00"
        )
        db.session.add_all([p1, p2])
        db.session.commit()

        save_scheduler_settings(settings)
        trigger_scheduled_export_job(app)

    # 2 profiles x 2 directions (buy + sell) = 4 calls
    assert mock_fetch_invoices.call_count == 4

    # Verify download and import calls
    assert mock_download_xml.call_count == 4
    assert mock_import_xml.call_count == 4

    # Verify log entry success shows both profiles' results consolidated
    logs = get_scheduler_logs()
    assert len(logs) == 1
    assert logs[0]["status"] == "SUCCESS"
    # consolidate: each profile fetched 2 invoices (1 buy + 1 sell) = 4 total invoices
    assert "Tổng số: 4 hóa đơn" in logs[0]["details"]

