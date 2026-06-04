"""Tests for Stage 27+ VAT Refund, API signature, Webhooks and RAG endpoints."""

from __future__ import annotations

import json
import time
import hmac
import hashlib
from datetime import datetime
from extensions import db
from invoices.models import Invoice, LineItem, TaxpayerProfile, WebhookSubscription


def _seed_test_data(app):
    with app.app_context():
        LineItem.query.delete()
        Invoice.query.delete()
        TaxpayerProfile.query.delete()
        WebhookSubscription.query.delete()
        db.session.commit()

        # Seed profile
        profile = TaxpayerProfile(
            mst="0109998887",
            company_name="CONG TY TEST TECH GLOBAL",
            gdt_username="tester_gdt",
            gdt_password_encrypted="encrypted",
            is_active=True,
            created_at=datetime.now().isoformat()
        )
        db.session.add(profile)
        db.session.commit()

        # Seed invoice
        inv = Invoice(
            id="INV-V27-001",
            filename="inv_v27_001.xml",
            invoice_type="purchase",
            number="10001",
            date="2026-05-12",
            currency="VND",
            seller_mst="0104444333",
            seller_name="NHA CUNG CAP A",
            buyer_mst="0109998887",
            buyer_name="CONG TY TEST TECH GLOBAL",
            amount_before_tax=100000000.0,
            tax_amount=10000000.0,
            total_amount=110000000.0,
            has_signature=True,
            taxpayer_mst="0109998887",
            imported_at=datetime.now().isoformat()
        )
        db.session.add(inv)
        db.session.commit()


def test_vat_refund_endpoints(logged_in_client, app):
    _seed_test_data(app)

    # 1. Test POST /api/audit/vat-refund-eligibility
    resp = logged_in_client.post(
        "/api/audit/vat-refund-eligibility",
        json={"mst": "0109998887"}
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "is_eligible" in data

    # 2. Test POST /api/audit/export-refund-xml
    resp = logged_in_client.post(
        "/api/audit/export-refund-xml",
        json={
            "mst": "0109998887",
            "eligible_invoice_ids": ["INV-V27-001"],
            "bank_account": "123456789",
            "bank_name": "Techcombank",
            "reason_type": "export"
        }
    )
    assert resp.status_code == 200
    assert resp.mimetype == "application/xml"
    assert b"<HSoThueDTu" in resp.data


def test_v1_rest_signature_endpoints(logged_in_client, app):
    _seed_test_data(app)

    secret = app.config.get("SECRET_KEY", "super-secret-key")
    timestamp = str(int(time.time()))

    # 1. Unsigned requests should fail with 401
    resp = logged_in_client.get("/api/v1/invoices?mst=0109998887")
    assert resp.status_code == 401

    # 2. Signed GET request for invoices
    query_str = "mst=0109998887"
    message = f"{timestamp}.{query_str}".encode("utf-8")
    signature = f"sha256={hmac.new(secret.encode('utf-8'), message, hashlib.sha256).hexdigest()}"

    headers = {
        "X-GDT-Signature": signature,
        "X-GDT-Timestamp": timestamp
    }
    resp = logged_in_client.get(f"/api/v1/invoices?{query_str}", headers=headers)
    assert resp.status_code == 200
    invoices = resp.get_json()
    assert len(invoices) == 1
    assert invoices[0]["id"] == "INV-V27-001"

    # 3. Signed GET request for compliance scores
    resp = logged_in_client.get(f"/api/v1/compliance-scores?{query_str}", headers=headers)
    assert resp.status_code == 200
    scores = resp.get_json()
    assert scores["mst"] == "0109998887"
    assert "average_t_score" in scores


def test_webhook_registry_and_dispatch(logged_in_client, app):
    _seed_test_data(app)

    # 1. Register Webhook
    resp = logged_in_client.post(
        "/api/v1/webhooks/register",
        json={
            "mst": "0109998887",
            "url": "https://callback.my-erp.com/webhook",
            "secret": "web-secret",
            "event_topics": ["invoice.created", "invoice.updated"]
        }
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["status"] == "success"
    assert len(data["subscriptions"]) == 2
    sub_id = data["subscriptions"][0]["id"]

    # 2. Dispatch Test Webhook
    resp = logged_in_client.post(
        "/api/v1/webhooks/dispatch-test",
        json={
            "subscription_id": sub_id,
            "payload": {"hello": "world"}
        }
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"


def test_tax_rag_and_defense_letter(logged_in_client, app):
    _seed_test_data(app)

    # 1. Tax RAG Query
    resp = logged_in_client.post(
        "/api/audit/tax-rag-query",
        json={"question": "Thời điểm xuất hóa đơn GTGT là khi nào?"}
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "answer" in data
    assert "Nghị định 123/2020/NĐ-CP" in data["answer"]

    # 2. Draft Defense Letter
    resp = logged_in_client.post(
        "/api/audit/draft-defense-letter",
        json={
            "invoice_id": "INV-V27-001",
            "issue_type": "Ký sai thời điểm",
            "seller": "CONG TY DU PHONG A",
            "amount": 120000000.0,
            "taxpayer_mst": "0109998887"
        }
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert "Nghị định số 125/2020/NĐ-CP" in data["draft_letter"]


def test_interactive_fallbacks_and_normalization(logged_in_client, app):
    _seed_test_data(app)

    # 1. Test E-Commerce normalization with raw_logs key
    mock_logs = [
        {"order_id": "ORD-TIKTOK-4001", "order_date": "2025-06-01", "gross_revenue": 750000.0, "commission_fee": 22500.0, "platform": "tiktok"},
        {"order_id": "ORD-LAZADA-5002", "order_date": "2025-06-02", "gross_revenue": 1400000.0, "commission_fee": 42000.0, "platform": "lazada"}
    ]
    resp = logged_in_client.post(
        "/api/ecommerce/normalize-orders",
        json={"taxpayer_mst": "0109998887", "raw_logs": mock_logs}
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert data["count"] == 2
    assert data["orders"][0]["order_id"] == "ORD-TIKTOK-4001"
    assert data["orders"][0]["gross_revenue"] == 750000.0

    # 2. Test E-Commerce reconciliation using session-cached normalized orders
    resp = logged_in_client.get("/api/ecommerce/reconcile?taxpayer_mst=0109998887")
    assert resp.status_code == 200
    recon_data = resp.get_json()
    assert recon_data["total_platform_orders"] == 2
    assert recon_data["total_platform_revenue"] == 2150000.0

    # 3. Test Payroll Audit Summary with empty employees list
    resp = logged_in_client.post(
        "/api/payroll/audit-summary",
        json={"taxpayer_mst": "0109998887"}
    )
    assert resp.status_code == 200
    payroll_data = resp.get_json()
    assert len(payroll_data["employees"]) == 5
    assert "compliance_score" in payroll_data

    # 4. Test Payroll Export PIT XML with empty employees list
    resp = logged_in_client.post(
        "/api/payroll/export-pit-xml",
        json={"taxpayer_mst": "0109998887", "tax_year": 2025}
    )
    assert resp.status_code == 200
    xml_data = resp.get_json()
    assert xml_data["status"] == "success"
    assert "05/QTT-TNCN" in xml_data["xml"]
