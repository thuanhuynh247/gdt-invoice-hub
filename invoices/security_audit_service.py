"""Security audit logging service for tracking administrative and session activities."""

from __future__ import annotations

from datetime import datetime, timezone
from flask import has_request_context, request, session
from extensions import db
from invoices.models import SecurityAuditLog


def log_security_event(
    event_category: str,
    event_details: str,
    username: str | None = None,
    tax_code: str | None = None,
    ip_address: str | None = None,
) -> SecurityAuditLog:
    """Log an administrative or compliance event to the immutable SecurityAuditLog table."""
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Resolve username
    if not username and has_request_context():
        username = session.get("username")
    if not username:
        username = "system"

    # Resolve tax taxpayer profile code
    if not tax_code and has_request_context():
        tax_code = session.get("tax_code")

    # Resolve IP address
    if not ip_address and has_request_context():
        if request.headers.getlist("X-Forwarded-For"):
            ip_address = request.headers.getlist("X-Forwarded-For")[0].split(",")[0].strip()
        else:
            ip_address = request.remote_addr

    log_entry = SecurityAuditLog(
        timestamp=timestamp,
        username=username,
        tax_code=tax_code,
        event_category=event_category,
        ip_address=ip_address,
        event_details=event_details,
    )

    db.session.add(log_entry)
    db.session.commit()
    return log_entry
