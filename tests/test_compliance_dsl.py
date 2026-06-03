"""Tests for the Dynamic Rulebook DSL Interpreter & Schema Validator (US-120)."""

from __future__ import annotations

import pytest
from invoices.compliance_hub import (
    ComplianceEngine,
    validate_rulebook_dsl,
)


class TestComplianceDSL:
    """US-120: Dynamic Rulebook DSL & Rule Interpreter Validation Suite."""

    def _sample_invoice(self) -> dict:
        return {
            "id": "INV-DSL-001",
            "seller_name": "Công ty TNHH Giải pháp Phần mềm",
            "seller_mst": "0109876543",
            "buyer_name": "Tập đoàn Đại Nam",
            "buyer_mst": "0312345678",
            "payment_method": "Tiền mặt / Cash",
            "total_amount": 25_000_000.0,
            "items": [
                {
                    "item_name": "Thiết bị định tuyến mạng Cisco",
                    "unit": "Cái",
                    "quantity": 1,
                    "unit_price": 20_000_000.0,
                    "amount_before_tax": 20_000_000.0,
                    "tax_rate": "10%",
                    "tax_amount": 2_000_000.0,
                    "expense_category": "Thiết bị IT",
                },
                {
                    "item_name": "Dây cáp mạng CAT6",
                    "unit": "Cuộn",
                    "quantity": 2,
                    "unit_price": 2_500_000.0,
                    "amount_before_tax": 5_000_000.0,
                    "tax_rate": "0%",
                    "tax_amount": 0.0,
                    "expense_category": "Vật tư phụ",
                }
            ]
        }

    def test_validate_valid_dsl(self):
        """Verify that a valid rulebook DSL passes validation successfully."""
        rulebook = {
            "rules": [
                {
                    "id": "dsl_rule_01",
                    "name": "Cảnh báo giao dịch tiền mặt trên 20 triệu",
                    "severity": "critical",
                    "channels": ["in_app", "webhook"],
                    "expression": {
                        "and": [
                            {"field": "payment_method", "op": "contains", "value": "Tiền mặt"},
                            {"field": "total_amount", "op": ">=", "value": 20_000_000.0}
                        ]
                    }
                },
                {
                    "id": "dsl_rule_02",
                    "name": "Kiểm tra mặt hàng có thuế suất 10%",
                    "severity": "warning",
                    "channels": ["in_app"],
                    "expression": {
                        "any_item": {
                            "field": "tax_rate", "op": "==", "value": "10%"
                        }
                    }
                }
            ]
        }
        ok, err = validate_rulebook_dsl(rulebook)
        assert ok is True
        assert err is None

    def test_validate_invalid_dsl_structure(self):
        """Verify that validation catches structural anomalies or missing attributes."""
        # Missing rules list
        ok, err = validate_rulebook_dsl({"name": "Rulebook trống"})
        assert ok is False
        assert "must contain a list of 'rules'" in err

        # Rules is not a list
        ok, err = validate_rulebook_dsl({"rules": "not-a-list"})
        assert ok is False
        assert "'rules' must be a JSON array" in err

        # Missing required rule fields
        ok, err = validate_rulebook_dsl({"rules": [{"id": "r1"}]})
        assert ok is False
        assert "missing required key 'name'" in err

    def test_validate_invalid_expressions(self):
        """Verify that validation catches malformed condition expressions."""
        bad_rulebook = {
            "rules": [
                {
                    "id": "r1",
                    "name": "Rule lỗi toán tử",
                    "severity": "warning",
                    "channels": ["in_app"],
                    "expression": {
                        "field": "total_amount",
                        "op": "INVALID_OP",
                        "value": 1000
                    }
                }
            ]
        }
        ok, err = validate_rulebook_dsl(bad_rulebook)
        assert ok is False
        assert "invalid or missing operator" in err

    def test_evaluate_and_dsl_rule(self):
        """Verify that an AND condition dynamic rule fires when all sub-conditions match."""
        engine = ComplianceEngine()
        rulebook = {
            "rules": [
                {
                    "id": "dsl_cash_limit",
                    "name": "Giao dịch tiền mặt lớn",
                    "severity": "critical",
                    "channels": ["in_app"],
                    "expression": {
                        "and": [
                            {"field": "payment_method", "op": "contains", "value": "Tiền mặt"},
                            {"field": "total_amount", "op": ">=", "value": 20_000_000.0}
                        ]
                    }
                }
            ]
        }
        engine.set_rulebook(rulebook)
        
        invoice = self._sample_invoice()
        alerts = engine.evaluate_invoice(invoice)
        
        assert len(alerts) == 1
        assert alerts[0].rule_id == "dsl_cash_limit"
        assert alerts[0].severity == "critical"

    def test_evaluate_or_dsl_rule(self):
        """Verify that an OR condition dynamic rule fires when at least one condition matches."""
        engine = ComplianceEngine()
        rulebook = {
            "rules": [
                {
                    "id": "dsl_blacklist_or_large",
                    "name": "MST đen hoặc hóa đơn khủng",
                    "severity": "warning",
                    "expression": {
                        "or": [
                            {"field": "seller_mst", "op": "==", "value": "9999999999"},
                            {"field": "total_amount", "op": ">", "value": 100_000_000.0}
                        ]
                    }
                }
            ]
        }
        engine.set_rulebook(rulebook)
        
        # Test case 1: Neither matches
        inv = self._sample_invoice()
        assert len(engine.evaluate_invoice(inv)) == 0

        # Test case 2: MST matches
        inv_mst = self._sample_invoice()
        inv_mst["seller_mst"] = "9999999999"
        alerts = engine.evaluate_invoice(inv_mst)
        assert len(alerts) == 1
        assert alerts[0].rule_id == "dsl_blacklist_or_large"

    def test_evaluate_not_dsl_rule(self):
        """Verify that a NOT condition dynamic rule flips boolean outcomes correctly."""
        engine = ComplianceEngine()
        rulebook = {
            "rules": [
                {
                    "id": "dsl_non_vnd",
                    "name": "Ngoại tệ khác VND",
                    "severity": "info",
                    "expression": {
                        "not": {"field": "currency", "op": "==", "value": "VND"}
                    }
                }
            ]
        }
        engine.set_rulebook(rulebook)
        
        # Invoice has no currency (which behaves as not == VND)
        inv = self._sample_invoice()
        alerts = engine.evaluate_invoice(inv)
        assert len(alerts) == 1
        assert alerts[0].rule_id == "dsl_non_vnd"

    def test_evaluate_item_level_any_item(self):
        """Verify that item-level inspections check inner attributes across line items."""
        engine = ComplianceEngine()
        rulebook = {
            "rules": [
                {
                    "id": "dsl_it_equipment",
                    "name": "Hóa đơn có thiết bị IT",
                    "severity": "info",
                    "expression": {
                        "any_item": {
                            "field": "expense_category", "op": "==", "value": "Thiết bị IT"
                        }
                    }
                }
            ]
        }
        engine.set_rulebook(rulebook)
        
        inv = self._sample_invoice()
        alerts = engine.evaluate_invoice(inv)
        assert len(alerts) == 1
        assert alerts[0].rule_id == "dsl_it_equipment"

    def test_evaluate_item_level_all_items(self):
        """Verify that 'all_items' condition is met only if all lines satisfy the check."""
        engine = ComplianceEngine()
        rulebook = {
            "rules": [
                {
                    "id": "dsl_all_taxable",
                    "name": "Tất cả các dòng đều chịu thuế",
                    "severity": "warning",
                    "expression": {
                        "all_items": {
                            "field": "tax_rate", "op": "!=", "value": "0%"
                        }
                    }
                }
            ]
        }
        engine.set_rulebook(rulebook)
        
        # One item has 10%, one has 0% -> should not fire
        inv = self._sample_invoice()
        assert len(engine.evaluate_invoice(inv)) == 0

        # Change second item to 10% -> should fire
        inv["items"][1]["tax_rate"] = "10%"
        alerts = engine.evaluate_invoice(inv)
        assert len(alerts) == 1
        assert alerts[0].rule_id == "dsl_all_taxable"
