"""
Tests for US-140: Immutable Security Audit Logger.
Verifies:
- SecurityAuditLog model creation and fields
- Immutability enforcement (update/delete blocked at ORM level)
- log_security_event helper service
- AUTH triggers on login success, login failure, and logout
- DELETE triggers on invoice deletion
- PROFILE triggers on profile switch/create/delete
- UPDATE triggers on settings changes
"""

from __future__ import annotations

import pytest
from extensions import db
from invoices.models import SecurityAuditLog


# ---------------------------------------------------------------------------
# Model & Immutability
# ---------------------------------------------------------------------------

class TestSecurityAuditLogModel:
    """Test SecurityAuditLog model creation and immutability constraints."""

    def test_create_log_entry(self, app):
        """Verify that a SecurityAuditLog entry can be created and read."""
        with app.app_context():
            entry = SecurityAuditLog(
                timestamp="2026-05-30T00:00:00Z",
                username="admin",
                tax_code="0101234567",
                event_category="AUTH",
                ip_address="127.0.0.1",
                event_details="Test login event",
            )
            db.session.add(entry)
            db.session.commit()

            fetched = db.session.get(SecurityAuditLog, entry.id)
            assert fetched is not None
            assert fetched.username == "admin"
            assert fetched.event_category == "AUTH"
            assert fetched.event_details == "Test login event"
            assert fetched.tax_code == "0101234567"
            assert fetched.ip_address == "127.0.0.1"

    def test_immutable_no_update(self, app):
        """Verify that updating a SecurityAuditLog entry raises ValueError."""
        with app.app_context():
            entry = SecurityAuditLog(
                timestamp="2026-05-30T00:00:01Z",
                username="admin",
                event_category="AUTH",
                event_details="Original detail",
            )
            db.session.add(entry)
            db.session.commit()

            entry.event_details = "Tampered detail"
            with pytest.raises(ValueError, match="immutable"):
                db.session.commit()
            db.session.rollback()

    def test_immutable_no_delete(self, app):
        """Verify that deleting a SecurityAuditLog entry raises ValueError."""
        with app.app_context():
            entry = SecurityAuditLog(
                timestamp="2026-05-30T00:00:02Z",
                username="admin",
                event_category="AUTH",
                event_details="Should not be deletable",
            )
            db.session.add(entry)
            db.session.commit()

            db.session.delete(entry)
            with pytest.raises(ValueError, match="immutable"):
                db.session.commit()
            db.session.rollback()


# ---------------------------------------------------------------------------
# Service helper
# ---------------------------------------------------------------------------

class TestLogSecurityEventService:
    """Test the log_security_event helper function."""

    def test_log_event_with_explicit_params(self, app):
        """Verify log_security_event creates a log entry with provided params."""
        with app.app_context():
            from invoices.security_audit_service import log_security_event

            entry = log_security_event(
                "DELETE",
                "Deleted invoice xyz",
                username="auditor_jane",
                tax_code="0109999999",
                ip_address="192.168.1.1",
            )
            assert entry.id is not None
            assert entry.username == "auditor_jane"
            assert entry.event_category == "DELETE"
            assert entry.event_details == "Deleted invoice xyz"
            assert entry.tax_code == "0109999999"
            assert entry.ip_address == "192.168.1.1"

    def test_log_event_defaults_to_system(self, app):
        """Verify that username defaults to 'system' when no session context."""
        with app.app_context():
            from invoices.security_audit_service import log_security_event

            entry = log_security_event("UPDATE", "System-triggered update")
            assert entry.username == "system"


# ---------------------------------------------------------------------------
# AUTH triggers (login success, login failure, logout)
# ---------------------------------------------------------------------------

class TestAuthAuditTriggers:
    """Test that login/logout actions produce SecurityAuditLog entries."""

    def test_login_success_creates_log(self, client, app):
        """Verify successful login creates an AUTH log entry."""
        # Use mock GDT login (GDT_USE_MOCK=True in test config)
        client.post("/api/auth/login", json={
            "username": "admin",
            "password": "password123",
        })
        with app.app_context():
            logs = SecurityAuditLog.query.filter_by(event_category="AUTH").all()
            success_logs = [l for l in logs if "logged in successfully" in (l.event_details or "")]
            assert len(success_logs) >= 1

    def test_login_failure_creates_log(self, client, app):
        """Verify failed login creates an AUTH log entry."""
        from unittest.mock import patch
        from auth.service import AuthenticationError

        with patch("auth.routes.authenticate_user", side_effect=AuthenticationError("Sai mat khau")):
            client.post("/api/auth/login", json={
                "username": "wrong_user",
                "password": "wrong_pass",
                "captcha": "XXXX",
            })
        with app.app_context():
            logs = SecurityAuditLog.query.filter_by(event_category="AUTH").all()
            fail_logs = [l for l in logs if "login failed" in (l.event_details or "").lower()]
            assert len(fail_logs) >= 1

    def test_logout_creates_log(self, logged_in_client, app):
        """Verify logout creates an AUTH log entry."""
        logged_in_client.post("/api/auth/logout")
        with app.app_context():
            logs = SecurityAuditLog.query.filter_by(event_category="AUTH").all()
            logout_logs = [l for l in logs if "logged out" in (l.event_details or "").lower()]
            assert len(logout_logs) >= 1


# ---------------------------------------------------------------------------
# DELETE triggers
# ---------------------------------------------------------------------------

class TestDeleteAuditTriggers:
    """Test that invoice deletion actions produce SecurityAuditLog entries."""

    def test_delete_single_invoice_creates_log(self, logged_in_client, app):
        """Verify deleting a single invoice creates a DELETE log entry."""
        # Create a test invoice first
        with app.app_context():
            from invoices.models import Invoice
            inv = Invoice(
                id="audit-test-del-001",
                number="001",
                date="2026-05-30",
                seller_name="Test Seller",
                total_amount=100.0,
                imported_at="2026-05-30 00:00:00",
            )
            db.session.add(inv)
            db.session.commit()

        # Delete it via API
        logged_in_client.delete("/api/invoices/local/audit-test-del-001")

        with app.app_context():
            logs = SecurityAuditLog.query.filter_by(event_category="DELETE").all()
            del_logs = [l for l in logs if "audit-test-del-001" in (l.event_details or "")]
            assert len(del_logs) >= 1


# ---------------------------------------------------------------------------
# PROFILE triggers
# ---------------------------------------------------------------------------

class TestProfileAuditTriggers:
    """Test that profile management actions produce SecurityAuditLog entries."""

    def test_switch_profile_creates_log(self, logged_in_client, app):
        """Verify switching taxpayer profile creates a PROFILE log entry."""
        # Create a profile to switch to
        with app.app_context():
            from invoices.models import TaxpayerProfile
            if not db.session.get(TaxpayerProfile, "0101111111"):
                p = TaxpayerProfile(
                    mst="0101111111",
                    company_name="Audit Test Co",
                    gdt_username="u1",
                    gdt_password_encrypted="e1",
                    is_active=True,
                    created_at="2026-05-30 00:00:00",
                )
                db.session.add(p)
                db.session.commit()

        logged_in_client.post("/api/profiles/switch", json={"mst": "0101111111"})

        with app.app_context():
            logs = SecurityAuditLog.query.filter_by(event_category="PROFILE").all()
            switch_logs = [l for l in logs if "Switched" in (l.event_details or "") and "0101111111" in (l.event_details or "")]
            assert len(switch_logs) >= 1

    def test_switch_to_all_creates_log(self, logged_in_client, app):
        """Verify switching to 'all' creates a PROFILE log entry."""
        logged_in_client.post("/api/profiles/switch", json={"mst": "all"})

        with app.app_context():
            logs = SecurityAuditLog.query.filter_by(event_category="PROFILE").all()
            all_logs = [l for l in logs if "no filter" in (l.event_details or "")]
            assert len(all_logs) >= 1


# ---------------------------------------------------------------------------
# UPDATE triggers
# ---------------------------------------------------------------------------

class TestUpdateAuditTriggers:
    """Test that settings/config updates produce SecurityAuditLog entries."""

    def test_settings_update_creates_log(self, logged_in_client, app):
        """Verify updating application settings creates an UPDATE log entry."""
        logged_in_client.post("/api/settings", json={
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
        })

        with app.app_context():
            logs = SecurityAuditLog.query.filter_by(event_category="UPDATE").all()
            settings_logs = [l for l in logs if "application settings" in (l.event_details or "")]
            assert len(settings_logs) >= 1
