"""Real-Time Compliance Monitoring & Alert Hub (US-104, US-105, US-120).

Provides a configurable rule engine for invoice compliance monitoring,
dynamic Rulebook DSL interpreter with schema validation,
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
    rule_id: Any
    rule_name: str
    severity: str
    message: str
    invoice_id: str = ""
    dispatched_channels: list = field(default_factory=list)
    acknowledged: bool = False
    triggered_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def validate_rulebook_dsl(rulebook: dict) -> tuple[bool, str | None]:
    """Validate the rulebook DSL schema structure.
    
    Returns (True, None) if valid, or (False, error_message) if invalid.
    """
    if not isinstance(rulebook, dict):
        return False, "Rulebook must be a JSON object"
    
    if "rules" not in rulebook:
        return False, "Rulebook must contain a list of 'rules'"
    
    rules = rulebook["rules"]
    if not isinstance(rules, list):
        return False, "'rules' must be a JSON array"
    
    valid_operators = {">", ">=", "<", "<=", "==", "!=", "in", "contains"}
    valid_severities = {"info", "warning", "critical"}
    
    def validate_expr(expr: dict, is_item: bool = False) -> tuple[bool, str | None]:
        if not isinstance(expr, dict):
            return False, f"Expression must be a JSON object, got: {expr}"
        
        connectors = {"and", "or", "not", "any_item", "all_items", "field"}
        keys = set(expr.keys())
        active_connectors = keys.intersection(connectors)
        
        if not active_connectors:
            return False, f"Expression must contain at least one valid key: {connectors}"
            
        if len(active_connectors) > 1:
            return False, f"Expression cannot combine multiple top-level keys in a single node: {active_connectors}"
            
        conn = list(active_connectors)[0]
        
        if conn in ("and", "or"):
            conditions = expr[conn]
            if not isinstance(conditions, list):
                return False, f"'{conn}' value must be a list of sub-expressions"
            for c in conditions:
                ok, err = validate_expr(c, is_item)
                if not ok:
                    return False, err
                    
        elif conn == "not":
            ok, err = validate_expr(expr["not"], is_item)
            if not ok:
                return False, err
                
        elif conn in ("any_item", "all_items"):
            if is_item:
                return False, f"Nested item-level checks '{conn}' are not allowed inside item evaluations"
            ok, err = validate_expr(expr[conn], is_item=True)
            if not ok:
                return False, err
                
        elif conn == "field":
            field_name = expr.get("field")
            if not isinstance(field_name, str) or not field_name:
                return False, "comparison must have a non-empty string 'field'"
            
            op = expr.get("op")
            if op not in valid_operators:
                return False, f"invalid or missing operator 'op': '{op}'. Valid: {valid_operators}"
                
            if "value" not in expr:
                return False, "comparison must specify a 'value'"
                
        return True, None
        
    for i, rule in enumerate(rules):
        if not isinstance(rule, dict):
            return False, f"Rule at index {i} must be a JSON object"
        
        for required_key in ("id", "name", "expression"):
            if required_key not in rule:
                return False, f"Rule at index {i} is missing required key '{required_key}'"
                
        severity = rule.get("severity", "warning")
        if severity not in valid_severities:
            return False, f"Rule at index {i} has invalid severity: '{severity}'. Valid: {valid_severities}"
            
        channels = rule.get("channels", ["in_app"])
        if not isinstance(channels, list):
            return False, f"Rule at index {i} channels must be a list"
            
        expression = rule.get("expression")
        ok, err = validate_expr(expression)
        if not ok:
            return False, f"Rule '{rule.get('name')}' has invalid expression: {err}"
            
    return True, None


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
        self.active_rulebook: dict | None = None
        self._alert_counter = 0
        self._dispatch_log: list[dict] = []

    def set_rulebook(self, rulebook: dict):
        """Set active dynamic DSL rulebook."""
        self.active_rulebook = rulebook

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
        """Evaluate a single invoice against all active rules and DSL rulebook."""
        triggered = []
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        # 1. Evaluate standard rules
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

        # 2. Evaluate dynamic DSL rulebook if active
        if self.active_rulebook and "rules" in self.active_rulebook:
            for rule_dict in self.active_rulebook["rules"]:
                if not rule_dict.get("is_active", True):
                    continue
                expr = rule_dict.get("expression")
                if expr and self._evaluate_expression(invoice, expr):
                    self._alert_counter += 1
                    severity = rule_dict.get("severity", "warning")
                    alert = ComplianceAlert(
                        id=self._alert_counter,
                        rule_id=rule_dict.get("id"),
                        rule_name=rule_dict.get("name"),
                        severity=severity,
                        message=self._build_dsl_message(rule_dict, invoice),
                        invoice_id=invoice.get("id", ""),
                        dispatched_channels=[],
                        acknowledged=False,
                        triggered_at=now,
                    )

                    channels = rule_dict.get("channels", ["in_app"])
                    for channel in channels:
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

    def _evaluate_expression(self, invoice: dict, expr: dict) -> bool:
        """Recursively evaluate a DSL expression against an invoice."""
        if not isinstance(expr, dict):
            return False

        # 1. AND connector
        if "and" in expr:
            conditions = expr["and"]
            if not isinstance(conditions, list) or not conditions:
                return False
            return all(self._evaluate_expression(invoice, cond) for cond in conditions)

        # 2. OR connector
        if "or" in expr:
            conditions = expr["or"]
            if not isinstance(conditions, list):
                return False
            return any(self._evaluate_expression(invoice, cond) for cond in conditions)

        # 3. NOT connector
        if "not" in expr:
            return not self._evaluate_expression(invoice, expr["not"])

        # 4. Item-level checks (any_item, all_items)
        if "any_item" in expr:
            nested = expr["any_item"]
            items = invoice.get("items", [])
            if not isinstance(items, list):
                return False
            return any(self._evaluate_item_expression(item, nested) for item in items)

        if "all_items" in expr:
            nested = expr["all_items"]
            items = invoice.get("items", [])
            if not isinstance(items, list) or not items:
                return False
            return all(self._evaluate_item_expression(item, nested) for item in items)

        # 5. Direct comparison rule (field, op, value)
        if "field" in expr:
            field_name = expr.get("field", "")
            op_name = expr.get("op", "==")
            target_value = expr.get("value")

            actual = invoice.get(field_name)
            if actual is None:
                return False

            op_func = self.OPERATORS.get(op_name)
            if op_func is None:
                return False

            try:
                if isinstance(target_value, (int, float)) and isinstance(actual, str):
                    try:
                        actual = float(actual)
                    except ValueError:
                        pass
                return op_func(actual, target_value)
            except (TypeError, ValueError):
                return False

        return False

    def _evaluate_item_expression(self, item: dict, expr: dict) -> bool:
        """Evaluate a DSL expression against an individual line item."""
        if not isinstance(expr, dict):
            return False

        # Nested AND, OR, NOT inside item evaluations
        if "and" in expr:
            conditions = expr["and"]
            if not isinstance(conditions, list) or not conditions:
                return False
            return all(self._evaluate_item_expression(item, cond) for cond in conditions)

        if "or" in expr:
            conditions = expr["or"]
            if not isinstance(conditions, list):
                return False
            return any(self._evaluate_item_expression(item, cond) for cond in conditions)

        if "not" in expr:
            return not self._evaluate_item_expression(item, expr["not"])

        if "field" in expr:
            field_name = expr.get("field", "")
            op_name = expr.get("op", "==")
            target_value = expr.get("value")

            actual = item.get(field_name)
            if actual is None:
                return False

            op_func = self.OPERATORS.get(op_name)
            if op_func is None:
                return False

            try:
                if isinstance(target_value, (int, float)) and isinstance(actual, str):
                    try:
                        actual = float(actual)
                    except ValueError:
                        pass
                return op_func(actual, target_value)
            except (TypeError, ValueError):
                return False

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

    def _build_dsl_message(self, rule_dict: dict, invoice: dict) -> str:
        """Build a human-readable alert message for DSL rulebook rules."""
        inv_id = invoice.get("id", "N/A")
        severity = rule_dict.get("severity", "warning").upper()
        return f"[{severity}] DSL Rule '{rule_dict.get('name')}' triggered on invoice {inv_id}"

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
            entry["payload"] = {
                "event": "compliance_alert",
                "alert": alert.to_dict(),
            }
        elif channel == "email":
            entry["subject"] = f"[{alert.severity.upper()}] Compliance Alert: {alert.rule_name}"
            entry["body"] = alert.message
        elif channel == "in_app":
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
