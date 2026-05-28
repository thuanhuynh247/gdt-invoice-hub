"""Real-Time Compliance Monitoring & Alert Hub (US-104, US-105).

Provides a configurable rule engine for invoice compliance monitoring
and multi-channel alert dispatch (webhook, email, in-app notifications).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class ComplianceRule:
    """A configurable compliance monitoring rule."""
    id: int
    name: str
    rule_type: str       # 'threshold', 'blacklist', 'pattern'
    condition: dict      # {"field": "total_amount", "op": ">", "value": 500000000}
    severity: str = "warning"  # 'info', 'warning', 'critical'
    channels: list = field(default_factory=lambda: ["in_app"])
    is_active: bool = True
    created_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ComplianceAlert:
    """An alert triggered by a compliance rule."""
    id: int
    rule_id: int
    rule_name: str
    severity: str
    message: str
    invoice_id: str = ""
    dispatched_channels: list = field(default_factory=list)
    acknowledged: bool = False
    triggered_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class ComplianceEngine:
    """Rule engine that evaluates invoices against compliance rules."""

    OPERATORS = {
        ">": lambda a, b: a > b,
        ">=": lambda a, b: a >= b,
        "<": lambda a, b: a < b,
        "<=": lambda a, b: a <= b,
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
        "in": lambda a, b: a in b,
        "contains": lambda a, b: b in str(a),
    }

    def __init__(self):
        self.rules: list[ComplianceRule] = []
        self.alerts: list[ComplianceAlert] = []
        self._alert_counter = 0
        self._dispatch_log: list[dict] = []

    def add_rule(self, rule: ComplianceRule):
        """Register a compliance rule."""
        self.rules.append(rule)

    def remove_rule(self, rule_id: int):
        """Remove a rule by ID."""
        self.rules = [r for r in self.rules if r.id != rule_id]

    def get_active_rules(self) -> list[ComplianceRule]:
        """Return only active rules."""
        return [r for r in self.rules if r.is_active]

    def evaluate_invoice(self, invoice: dict) -> list[ComplianceAlert]:
        """Evaluate a single invoice against all active rules."""
        triggered = []
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        for rule in self.get_active_rules():
            if self._matches_condition(invoice, rule.condition):
                self._alert_counter += 1
                alert = ComplianceAlert(
                    id=self._alert_counter,
                    rule_id=rule.id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    message=self._build_message(rule, invoice),
                    invoice_id=invoice.get("id", ""),
                    dispatched_channels=[],
                    acknowledged=False,
                    triggered_at=now,
                )

                # Dispatch to configured channels
                for channel in rule.channels:
                    success = self._dispatch(channel, alert)
                    if success:
                        alert.dispatched_channels.append(channel)

                self.alerts.append(alert)
                triggered.append(alert)

        return triggered

    def evaluate_batch(self, invoices: list[dict]) -> list[ComplianceAlert]:
        """Evaluate multiple invoices against all active rules."""
        all_alerts = []
        for inv in invoices:
            all_alerts.extend(self.evaluate_invoice(inv))
        return all_alerts

    def acknowledge_alert(self, alert_id: int) -> bool:
        """Mark an alert as acknowledged."""
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                return True
        return False

    def get_alerts(self, severity: str | None = None, acknowledged: bool | None = None) -> list[ComplianceAlert]:
        """Filter and retrieve alerts."""
        result = self.alerts
        if severity is not None:
            result = [a for a in result if a.severity == severity]
        if acknowledged is not None:
            result = [a for a in result if a.acknowledged == acknowledged]
        return result

    def get_dispatch_log(self) -> list[dict]:
        """Return the dispatch log for debugging and auditing."""
        return list(self._dispatch_log)

    def _matches_condition(self, invoice: dict, condition: dict) -> bool:
        """Evaluate whether an invoice matches a rule condition."""
        field_name = condition.get("field", "")
        op_name = condition.get("op", "==")
        threshold = condition.get("value")

        actual = invoice.get(field_name)
        if actual is None:
            return False

        op_func = self.OPERATORS.get(op_name)
        if op_func is None:
            return False

        try:
            return op_func(actual, threshold)
        except (TypeError, ValueError):
            return False

    def _build_message(self, rule: ComplianceRule, invoice: dict) -> str:
        """Build a human-readable alert message."""
        inv_id = invoice.get("id", "N/A")
        field_name = rule.condition.get("field", "")
        actual_value = invoice.get(field_name, "N/A")

        return (
            f"[{rule.severity.upper()}] Rule '{rule.name}' triggered on invoice {inv_id}: "
            f"{field_name}={actual_value} (condition: {rule.condition.get('op', '')} {rule.condition.get('value', '')})"
        )

    def _dispatch(self, channel: str, alert: ComplianceAlert) -> bool:
        """Dispatch an alert to a specific channel.

        Returns True if dispatch was successful.
        """
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        entry = {
            "channel": channel,
            "alert_id": alert.id,
            "rule_name": alert.rule_name,
            "severity": alert.severity,
            "invoice_id": alert.invoice_id,
            "dispatched_at": now,
            "success": True,
        }

        if channel == "webhook":
            # In production: requests.post(webhook_url, json=payload)
            entry["payload"] = {
                "event": "compliance_alert",
                "alert": alert.to_dict(),
            }
        elif channel == "email":
            # In production: send via SMTP
            entry["subject"] = f"[{alert.severity.upper()}] Compliance Alert: {alert.rule_name}"
            entry["body"] = alert.message
        elif channel == "in_app":
            # In-app notifications stored in alerts list
            pass
        else:
            entry["success"] = False

        self._dispatch_log.append(entry)
        return entry["success"]


# ── Factory Helpers ───────────────────────────────────────────────

def create_threshold_rule(
    rule_id: int,
    name: str,
    field: str,
    op: str,
    value: Any,
    severity: str = "warning",
    channels: list | None = None,
) -> ComplianceRule:
    """Create a threshold-based compliance rule."""
    return ComplianceRule(
        id=rule_id,
        name=name,
        rule_type="threshold",
        condition={"field": field, "op": op, "value": value},
        severity=severity,
        channels=channels or ["in_app"],
        created_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )


def create_blacklist_rule(
    rule_id: int,
    name: str,
    blacklisted_msts: list[str],
    severity: str = "critical",
    channels: list | None = None,
) -> ComplianceRule:
    """Create a blacklist MST compliance rule."""
    return ComplianceRule(
        id=rule_id,
        name=name,
        rule_type="blacklist",
        condition={"field": "seller_mst", "op": "in", "value": blacklisted_msts},
        severity=severity,
        channels=channels or ["in_app", "webhook"],
        created_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
