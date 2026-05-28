"""Tests for Compliance Monitoring and Alert Hub (US-104, US-105)."""

from __future__ import annotations

import pytest
from invoices.compliance_hub import (
    ComplianceEngine,
    ComplianceRule,
    ComplianceAlert,
    create_threshold_rule,
    create_blacklist_rule,
)


class TestComplianceEngine:
    """US-104, US-105: Compliance Rule Engine and Alert Config."""

    def _sample_invoices(self):
        return [
            {
                "id": "INV-NORMAL",
                "seller_name": "Công ty Thường",
                "seller_mst": "0102030405",
                "total_amount": 100_000_000.0,
            },
            {
                "id": "INV-LARGE",
                "seller_name": "Công ty Lớn",
                "seller_mst": "0102030405",
                "total_amount": 600_000_000.0,
            },
            {
                "id": "INV-BLACKLISTED",
                "seller_name": "Công ty Ma",
                "seller_mst": "9999999999",
                "total_amount": 50_000_000.0,
            },
        ]

    def test_threshold_rule_triggers_alert(self):
        """Rule evaluating total_amount > 500M should trigger alert on large invoice."""
        engine = ComplianceEngine()
        rule = create_threshold_rule(
            rule_id=1,
            name="Hóa đơn lớn trên 500 triệu",
            field="total_amount",
            op=">",
            value=500_000_000.0,
            severity="warning",
            channels=["in_app"],
        )
        engine.add_rule(rule)

        invoices = self._sample_invoices()
        alerts = engine.evaluate_batch(invoices)

        # Should trigger on INV-LARGE, not on INV-NORMAL or INV-BLACKLISTED
        assert len(alerts) == 1
        assert alerts[0].invoice_id == "INV-LARGE"
        assert alerts[0].rule_id == 1
        assert "500000000" in alerts[0].message

    def test_blacklist_rule_triggers_alert(self):
        """Blacklist rule should trigger critical alert for blacklisted seller MST."""
        engine = ComplianceEngine()
        rule = create_blacklist_rule(
            rule_id=2,
            name="Người bán thuộc danh sách đen",
            blacklisted_msts=["9999999999"],
            severity="critical",
            channels=["in_app", "webhook"],
        )
        engine.add_rule(rule)

        invoices = self._sample_invoices()
        alerts = engine.evaluate_batch(invoices)

        assert len(alerts) == 1
        assert alerts[0].invoice_id == "INV-BLACKLISTED"
        assert alerts[0].severity == "critical"
        assert "webhook" in alerts[0].dispatched_channels

    def test_inactive_rule_does_not_fire(self):
        """Inactive rules should not trigger alerts."""
        engine = ComplianceEngine()
        rule = create_threshold_rule(
            rule_id=1,
            name="Rule ẩn",
            field="total_amount",
            op=">",
            value=10_000.0,
            severity="warning",
        )
        rule.is_active = False
        engine.add_rule(rule)

        invoices = self._sample_invoices()
        alerts = engine.evaluate_batch(invoices)
        assert len(alerts) == 0

    def test_acknowledge_alert(self):
        """Acknowledging an alert should update its status."""
        engine = ComplianceEngine()
        rule = create_threshold_rule(1, "Rule", "total_amount", ">", 10_000.0)
        engine.add_rule(rule)

        alerts = engine.evaluate_invoice({"id": "INV-1", "total_amount": 20_000.0})
        assert len(alerts) == 1
        alert_id = alerts[0].id

        assert engine.acknowledge_alert(alert_id) is True
        assert engine.get_alerts(acknowledged=True)[0].id == alert_id
        assert len(engine.get_alerts(acknowledged=False)) == 0

    def test_webhook_dispatch_payload(self):
        """Webhook dispatch should log payload correctly."""
        engine = ComplianceEngine()
        rule = create_blacklist_rule(1, "Blacklist", ["999"], channels=["webhook"])
        engine.add_rule(rule)

        engine.evaluate_invoice({"id": "INV-1", "seller_mst": "999"})
        log = engine.get_dispatch_log()
        
        assert len(log) == 1
        assert log[0]["channel"] == "webhook"
        assert log[0]["success"] is True
        assert "payload" in log[0]
        assert log[0]["payload"]["event"] == "compliance_alert"

    def test_remove_rule(self):
        """Removing a rule should prevent it from running."""
        engine = ComplianceEngine()
        rule = create_threshold_rule(1, "Rule", "total_amount", ">", 10_000.0)
        engine.add_rule(rule)
        assert len(engine.rules) == 1
        
        engine.remove_rule(1)
        assert len(engine.rules) == 0
