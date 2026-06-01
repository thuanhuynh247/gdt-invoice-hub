"""
Tests for US-141: Audit Trail Viewer UI & CSV/PDF Export.
Verifies:
- Audit trail page route (authentication & role gating)
- GET /api/audit-logs with filtering and pagination
- GET /api/audit-logs/export/csv
- GET /api/audit-logs/export/pdf
"""

from __future__ import annotations

import pytest
from extensions import db
from invoices.models import SecurityAuditLog


def _seed_audit_logs(app, count=5):
    """Seed some SecurityAuditLog entries for testing."""
    with app.app_context():
        for i in range(count):
            entry = SecurityAuditLog(
                timestamp=f"2026-05-{20+i:02d}T10:00:00Z",
                username="admin" if i % 2 == 0 else "auditor_jane",
                tax_code="0101234567" if i % 3 == 0 else None,
                event_category=["AUTH", "PROFILE", "DELETE", "UPDATE", "REPAIR"][i % 5],
                ip_address="127.0.0.1",
                event_details=f"Test event #{i+1} for audit trail viewer",
            )
            db.session.add(entry)
        db.session.commit()


class TestAuditTrailPage:
    """Test the audit trail viewer page route."""

    def test_page_requires_login(self, client):
        """Verify that the audit trail page redirects when not logged in."""
        r = client.get("/audit-trail")
        assert r.status_code in (302, 401)

    def test_page_renders_for_admin(self, logged_in_client):
        """Verify that admin can access the audit trail page."""
        r = logged_in_client.get("/audit-trail")
        assert r.status_code == 200
        assert "Giám sát" in r.data.decode("utf-8")

    def test_page_denied_for_viewer(self, client):
        """Verify that viewer role cannot access audit trail."""
        with client.session_transaction() as sess:
            sess["logged_in"] = True
            sess["username"] = "viewer_user"
            sess["user_role"] = "viewer"
            sess["expires_at"] = "2099-05-20T00:00:00+00:00"
        r = client.get("/audit-trail")
        assert r.status_code == 403


class TestAuditLogsAPI:
    """Test the GET /api/audit-logs endpoint."""

    def test_list_audit_logs(self, logged_in_client, app):
        """Verify listing audit logs returns expected structure."""
        _seed_audit_logs(app, 5)
        r = logged_in_client.get("/api/audit-logs")
        assert r.status_code == 200
        data = r.get_json()
        assert "logs" in data
        assert "total" in data
        assert data["total"] >= 5
        assert len(data["logs"]) >= 5

    def test_filter_by_category(self, logged_in_client, app):
        """Verify filtering by event category works."""
        _seed_audit_logs(app, 5)
        r = logged_in_client.get("/api/audit-logs?category=AUTH")
        assert r.status_code == 200
        data = r.get_json()
        for log in data["logs"]:
            assert log["event_category"] == "AUTH"

    def test_filter_by_username(self, logged_in_client, app):
        """Verify filtering by username works."""
        _seed_audit_logs(app, 5)
        r = logged_in_client.get("/api/audit-logs?username=auditor")
        assert r.status_code == 200
        data = r.get_json()
        for log in data["logs"]:
            assert "auditor" in log["username"].lower()

    def test_filter_by_keyword(self, logged_in_client, app):
        """Verify filtering by keyword in event_details works."""
        _seed_audit_logs(app, 5)
        r = logged_in_client.get("/api/audit-logs?keyword=audit+trail+viewer")
        assert r.status_code == 200
        data = r.get_json()
        assert data["total"] >= 1

    def test_pagination(self, logged_in_client, app):
        """Verify pagination params are respected."""
        _seed_audit_logs(app, 10)
        r = logged_in_client.get("/api/audit-logs?page=1&per_page=3")
        assert r.status_code == 200
        data = r.get_json()
        assert len(data["logs"]) == 3
        assert data["per_page"] == 3

    def test_requires_auth(self, client):
        """Verify audit logs API requires authentication."""
        r = client.get("/api/audit-logs")
        assert r.status_code == 401


class TestAuditLogsExport:
    """Test audit log CSV and PDF export endpoints."""

    def test_csv_export(self, logged_in_client, app):
        """Verify CSV export returns valid CSV content."""
        _seed_audit_logs(app, 3)
        r = logged_in_client.get("/api/audit-logs/export/csv")
        assert r.status_code == 200
        assert r.content_type == "text/csv; charset=utf-8"
        assert "Content-Disposition" in r.headers
        assert "audit_trail_" in r.headers["Content-Disposition"]

        csv_text = r.data.decode("utf-8")
        lines = csv_text.strip().split("\n")
        assert len(lines) >= 4  # header + 3 data rows
        assert "ID" in lines[0]
        assert "Timestamp" in lines[0]

    def test_csv_export_with_filter(self, logged_in_client, app):
        """Verify CSV export respects filters."""
        _seed_audit_logs(app, 5)
        r = logged_in_client.get("/api/audit-logs/export/csv?category=AUTH")
        assert r.status_code == 200
        csv_text = r.data.decode("utf-8")
        # All data rows should contain AUTH
        lines = csv_text.strip().split("\n")
        for line in lines[1:]:  # skip header
            if line.strip():
                assert "AUTH" in line

    def test_pdf_export(self, logged_in_client, app):
        """Verify PDF (HTML) export returns valid HTML content."""
        _seed_audit_logs(app, 3)
        r = logged_in_client.get("/api/audit-logs/export/pdf")
        assert r.status_code == 200
        assert r.content_type == "text/html; charset=utf-8"
        html = r.data.decode("utf-8")
        assert "Báo cáo Nhật ký Bảo mật" in html
        assert "GDT Invoice Hub" in html

    def test_export_requires_auth(self, client):
        """Verify export endpoints require authentication."""
        r_csv = client.get("/api/audit-logs/export/csv")
        assert r_csv.status_code == 401
        r_pdf = client.get("/api/audit-logs/export/pdf")
        assert r_pdf.status_code == 401
