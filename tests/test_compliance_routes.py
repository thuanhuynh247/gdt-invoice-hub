"""Tests for the Dynamic Compliance Rulebook REST endpoints (US-120)."""

from __future__ import annotations

import json
import pytest
from invoices.models import Invoice, LineItem
from extensions import db


def test_get_compliance_rulebook_requires_login(client):
    """Verify that anonymous users are blocked with 401 when fetching rulebook."""
    response = client.get("/api/compliance/rulebook")
    assert response.status_code == 401


def test_get_compliance_rulebook_default(logged_in_client):
    """Verify that a default rulebook is returned when no custom one exists."""
    response = logged_in_client.get("/api/compliance/rulebook")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "success"
    assert "rulebook" in payload
    assert payload["rulebook"]["name"] == "Default Compliance Rulebook"
    assert len(payload["rulebook"]["rules"]) == 1


def test_update_compliance_rulebook_validation(logged_in_client):
    """Verify that uploading an invalid rulebook DSL fails with 400."""
    invalid_payload = {
        "rulebook": {
            "name": "Invalid Rulebook",
            "rules": [
                {
                    "id": "r1",
                    "name": "Missing severity and expression"
                }
            ]
        }
    }
    response = logged_in_client.post(
        "/api/compliance/rulebook",
        json=invalid_payload
    )
    assert response.status_code == 400
    payload = response.get_json()
    assert "error" in payload
    assert "Lỗi cú pháp DSL Rulebook" in payload["error"]


def test_update_compliance_rulebook_success(app, logged_in_client):
    """Verify that a valid rulebook DSL is successfully persisted."""
    valid_payload = {
        "rulebook": {
            "name": "Enterprise Audit Rulebook",
            "rules": [
                {
                    "id": "dsl_rule_01",
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
    }
    response = logged_in_client.post(
        "/api/compliance/rulebook",
        json=valid_payload
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "success"
    assert "message" in payload
    assert "Cập nhật DSL Rulebook thành công." in payload["message"]

    # Verify we can fetch it now
    get_response = logged_in_client.get("/api/compliance/rulebook")
    assert get_response.status_code == 200
    get_payload = get_response.get_json()
    assert get_payload["rulebook"]["name"] == "Enterprise Audit Rulebook"
    assert len(get_payload["rulebook"]["rules"]) == 1


def test_evaluate_compliance_endpoint(app, logged_in_client):
    """Verify that compliance evaluation runs against specified invoices."""
    with app.app_context():
        # Setup a dummy invoice for evaluation
        invoice_id = "INV-EVAL-TEST"
        Invoice.query.filter_by(id=invoice_id).delete()
        
        inv = Invoice(
            id=invoice_id,
            filename="eval_test.xml",
            payment_method="Thanh toán Tiền mặt",
            total_amount=25_000_000.0,
            amount_before_tax=25_000_000.0,
            tax_amount=0.0,
            imported_at="2026-05-29T00:00:00Z",
            import_status="imported"
        )
        db.session.add(inv)
        db.session.commit()

    # Define custom rules
    valid_payload = {
        "rulebook": {
            "name": "Cash Check Rulebook",
            "rules": [
                {
                    "id": "dsl_cash_limit",
                    "name": "Cash Payment Limit Violation",
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
    }
    
    # 1. Update the rulebook first
    resp1 = logged_in_client.post("/api/compliance/rulebook", json=valid_payload)
    assert resp1.status_code == 200

    # 2. Evaluate invoice
    eval_payload = {
        "invoice_ids": [invoice_id]
    }
    response = logged_in_client.post("/api/compliance/evaluate", json=eval_payload)
    assert response.status_code == 200
    
    payload = response.get_json()
    assert payload["status"] == "success"
    assert "alerts" in payload
    assert len(payload["alerts"]) == 1
    assert payload["alerts"][0]["rule_id"] == "dsl_cash_limit"
    assert payload["alerts"][0]["severity"] == "critical"

    # Cleanup database
    with app.app_context():
        Invoice.query.filter_by(id=invoice_id).delete()
        db.session.commit()


def test_map_ifrs_endpoint(app, logged_in_client):
    """Verify that multi-jurisdictional mapping maps standard properties and currencies."""
    invoice_id = "INV-MAP-IFRS-TEST"
    
    with app.app_context():
        Invoice.query.filter_by(id=invoice_id).delete()
        
        inv = Invoice(
            id=invoice_id,
            filename="map_test.xml",
            seller_name="AWS Europe SARL",
            seller_mst="8099887766",  # Foreign MST
            buyer_name="Tập đoàn Đại Nam",
            buyer_mst="0312345678",
            total_amount=50_800_000.0,
            amount_before_tax=50_800_000.0,
            tax_amount=0.0,
            imported_at="2026-05-29T00:00:00Z",
            import_status="imported"
        )
        db.session.add(inv)
        db.session.commit()

    payload = {
        "invoice_ids": [invoice_id],
        "reporting_currency": "USD",
        "fct_category": "services"
    }
    
    response = logged_in_client.post("/api/compliance/map-ifrs", json=payload)
    assert response.status_code == 200
    
    data = response.get_json()
    assert data["status"] == "success"
    assert data["reporting_currency"] == "USD"
    assert len(data["mapped_invoices"]) == 1
    
    mapped_inv = data["mapped_invoices"][0]
    assert mapped_inv["document_number"] == invoice_id
    assert mapped_inv["supplier_name"] == "AWS Europe SARL"
    assert mapped_inv["amount_in_base"] == 50_800_000.0
    
    # 50,800,000 / 25,400 = 2,000 USD
    assert mapped_inv["amount_in_reporting"] == 2000.0
    
    # FCT validation: VAT = 5% (2.54M), CIT = 5% (2.54M)
    fct = mapped_inv["fct_liability"]
    assert fct["is_applicable"] is True
    assert fct["vat_amount"] == 2_540_000.0
    assert fct["cit_amount"] == 2_540_000.0
    assert fct["total_fct_liability"] == 5_080_000.0

    # Cleanup database
    with app.app_context():
        Invoice.query.filter_by(id=invoice_id).delete()
        db.session.commit()


def test_tax_risk_scoreboard_endpoint(app, logged_in_client):
    """Verify that the tax-risk-scoreboard gathers correct statistics and lists high-risk suppliers."""
    invoice_id = "INV-SCOREBOARD-TEST"
    
    with app.app_context():
        # Setup clean state
        Invoice.query.filter_by(id=invoice_id).delete()
        from invoices.models import BlacklistedMST
        BlacklistedMST.query.filter_by(mst="8099887766").delete()
        
        # 1. Add a blacklisted supplier
        blacklisted = BlacklistedMST(
            mst="8099887766",
            reason="Trốn thuế nghiêm trọng",
            blacklisted_at="2026-05-29T00:00:00Z"
        )
        db.session.add(blacklisted)
        
        # 2. Add an invoice from this blacklisted supplier
        inv = Invoice(
            id=invoice_id,
            filename="scoreboard_test.xml",
            seller_name="AWS Europe SARL",
            seller_mst="8099887766",
            buyer_name="Tập đoàn Đại Nam",
            buyer_mst="0312345678",
            total_amount=50_800_000.0,
            amount_before_tax=50_800_000.0,
            tax_amount=0.0,
            has_signature=False,
            payment_method="Tiền mặt",
            imported_at="2026-05-29T00:00:00Z",
            import_status="imported",
            taxpayer_mst="0312345678"
        )
        db.session.add(inv)
        db.session.commit()

    # Set taxpayer MST in session to match the invoice
    with logged_in_client.session_transaction() as sess:
        sess["taxpayer_mst"] = "0312345678"

    response = logged_in_client.get("/api/reports/tax-risk-scoreboard")
    assert response.status_code == 200
    
    data = response.get_json()
    assert data["status"] == "success"
    
    # 3. Assert counts and values
    summary = data["summary"]
    assert summary["total_analyzed"] >= 1
    assert summary["total_with_warnings"] >= 1
    assert summary["total_value_at_risk"] >= 50_800_000.0
    assert summary["blacklist_warnings_count"] >= 1
    assert summary["signature_violations_count"] >= 1
    assert summary["payment_type_flags_count"] >= 1
    
    # 4. Assert supplier breakdown
    suppliers = data["suppliers"]
    assert len(suppliers) >= 1
    
    aws_supplier = next((s for s in suppliers if s["supplier_mst"] == "8099887766"), None)
    assert aws_supplier is not None
    assert aws_supplier["supplier_name"] == "AWS Europe SARL"
    assert aws_supplier["is_blacklisted"] is True
    assert aws_supplier["warnings_count"] >= 1
    assert aws_supplier["total_value"] >= 50_800_000.0

    # Cleanup database
    with app.app_context():
        Invoice.query.filter_by(id=invoice_id).delete()
        from invoices.models import BlacklistedMST
        BlacklistedMST.query.filter_by(mst="8099887766").delete()
        db.session.commit()


