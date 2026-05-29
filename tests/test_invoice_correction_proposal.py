"""
Integration and Unit Tests for AI InvoiceCorrectionProposal Engine (US-133).
Verifies automatic proposal draft generation, accept (approve), and reject flows with full SQLAlchemy multi-tenancy.
"""

from __future__ import annotations

import json
from unittest.mock import patch, MagicMock
import pytest

from extensions import db
from invoices.models import Invoice, LineItem, AIAuditResult, InvoiceCorrectionProposal
from invoices.ai_service import AIComplianceAuditor, apply_correction_proposal
from invoices.scheduler import save_scheduler_settings


@pytest.fixture
def proposal_setup(app):
    """Seed base data and configure AI settings for testing."""
    with app.app_context():
        # Clear existing tables
        InvoiceCorrectionProposal.query.delete()
        AIAuditResult.query.delete()
        LineItem.query.delete()
        Invoice.query.delete()
        db.session.commit()

        # Seed sample invoice
        inv = Invoice(
            id="0109998887-AB-00001",
            number="00001",
            date="2026-05-25",
            seller_name="Cong ty TNHH San Xuat Thuong Mai",
            seller_mst="0109998887",
            seller_address="Ha Noi",
            buyer_name="Cong ty TNHH Mua Hang",
            buyer_mst="0208887776",
            buyer_address="TP HCM",
            amount_before_tax=30000000.0,
            tax_amount=2400000.0,
            total_amount=32400000.0,
            has_signature=True,
            signing_date="2026-05-25",
            payment_method="TM",
            is_cancelled=False,
            imported_at="2026-05-25 10:00:00",
            taxpayer_mst="0208887776"
        )
        db.session.add(inv)
        db.session.commit()

        # Seed line items
        item1 = LineItem(
            invoice_id=inv.id,
            item_name="Bia lon Heineken phục vụ liên hoan",
            quantity=10.0,
            unit_price=300000.0,
            amount_before_tax=3000000.0,
            tax_rate="8%",
            tax_amount=240000.0,
            expense_category="Chưa phân loại"
        )
        db.session.add(item1)
        db.session.commit()

        # Configure scheduler settings to enable AI auditing
        save_scheduler_settings({
            "ai_enabled": True,
            "ai_provider": "ollama",
            "ai_model_name": "gemma-4",
            "ai_ollama_endpoint": "http://localhost:11434"
        })


class TestInvoiceCorrectionProposal:
    """Test Suite for AI Auditor InvoiceCorrectionProposal & Draft Proposals."""

    @patch("invoices.ai_service.requests.post")
    def test_automatic_proposal_generation(self, mock_post, app, proposal_setup):
        """Verify that AI Compliance audit automatically generates draft correction proposals."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Return mock JSON response containing warnings
        mock_response.json.return_value = {
            "message": {
                "content": json.dumps({
                    "anomalies": [
                        {
                            "warning_type": "cash_payment_risk",
                            "item_name": "",
                            "explanation": "Giao dịch có tổng trị giá 32.4 triệu VND lớn hơn ngưỡng 20 triệu nhưng thanh toán tiền mặt (TM). Đề xuất đổi sang CK."
                        },
                        {
                            "warning_type": "personal_purchase",
                            "item_name": "Bia lon Heineken phục vụ liên hoan",
                            "explanation": "Bia phục vụ liên hoan cá nhân không được trừ khi tính thuế TNDN."
                        }
                    ]
                })
            }
        }
        mock_post.return_value = mock_response

        with app.app_context():
            invoice = Invoice.query.first()
            assert invoice is not None

            auditor = AIComplianceAuditor()
            warnings = auditor.audit_invoice(invoice)

            # Assert warnings created
            assert len(warnings) == 2
            
            # Assert draft proposals automatically generated in database
            proposals = InvoiceCorrectionProposal.query.filter_by(invoice_id=invoice.id).all()
            assert len(proposals) == 2

            types = [p.correction_type for p in proposals]
            assert "payment_method" in types
            assert "non_deductible_expense" in types

            # Check details of cash payment risk proposal
            pm_proposal = next(p for p in proposals if p.correction_type == "payment_method")
            assert pm_proposal.original_value == "TM"
            assert pm_proposal.proposed_value == "CK"
            assert pm_proposal.status == "pending"
            assert "Điều 15 Thông tư 219" in pm_proposal.ai_explanation

    def test_approve_payment_method_proposal(self, app, proposal_setup):
        """Verify that approving a payment_method proposal updates the invoice correctly."""
        with app.app_context():
            invoice = Invoice.query.first()
            
            proposal = InvoiceCorrectionProposal(
                invoice_id=invoice.id,
                taxpayer_mst=invoice.taxpayer_mst,
                correction_type="payment_method",
                original_value="TM",
                proposed_value="CK",
                ai_explanation="Test payment method correction",
                status="pending",
                created_at="2026-05-29 10:00:00",
                updated_at="2026-05-29 10:00:00"
            )
            db.session.add(proposal)
            db.session.commit()

            success = apply_correction_proposal(proposal)
            assert success is True
            assert proposal.status == "approved"

            # Reload invoice and check payment method
            db.session.refresh(invoice)
            assert invoice.payment_method == "CK"

    def test_approve_non_deductible_proposal(self, app, proposal_setup):
        """Verify that approving a non_deductible proposal sets expense_category to 'Chi phí không được trừ'."""
        with app.app_context():
            invoice = Invoice.query.first()
            item = invoice.items[0]
            assert item.expense_category == "Chưa phân loại"

            orig_payload = json.dumps({"item_name": item.item_name, "deductible": True})
            prop_payload = json.dumps({"item_name": item.item_name, "deductible": False})

            proposal = InvoiceCorrectionProposal(
                invoice_id=invoice.id,
                taxpayer_mst=invoice.taxpayer_mst,
                correction_type="non_deductible_expense",
                original_value=orig_payload,
                proposed_value=prop_payload,
                ai_explanation="Test non-deductible category proposal",
                status="pending",
                created_at="2026-05-29 10:00:00",
                updated_at="2026-05-29 10:00:00"
            )
            db.session.add(proposal)
            db.session.commit()

            success = apply_correction_proposal(proposal)
            assert success is True
            assert proposal.status == "approved"

            # Reload item and check expense category
            db.session.refresh(item)
            assert item.expense_category == "Chi phí không được trừ"

    def test_approve_tax_rate_proposal(self, app, proposal_setup):
        """Verify that approving a tax_rate proposal updates item tax rate, amount and invoice totals."""
        with app.app_context():
            invoice = Invoice.query.first()
            item = invoice.items[0]
            assert item.tax_rate == "8%"
            
            orig_payload = json.dumps({"item_name": item.item_name, "tax_rate": "8%"})
            prop_payload = json.dumps({"item_name": item.item_name, "tax_rate": "10%"})

            proposal = InvoiceCorrectionProposal(
                invoice_id=invoice.id,
                taxpayer_mst=invoice.taxpayer_mst,
                correction_type="tax_rate",
                original_value=orig_payload,
                proposed_value=prop_payload,
                ai_explanation="Test tax rate proposal correction to 10%",
                status="pending",
                created_at="2026-05-29 10:00:00",
                updated_at="2026-05-29 10:00:00"
            )
            db.session.add(proposal)
            db.session.commit()

            success = apply_correction_proposal(proposal)
            assert success is True
            assert proposal.status == "approved"

            # Reload item and invoice
            db.session.refresh(item)
            db.session.refresh(invoice)

            assert item.tax_rate == "10%"
            assert item.tax_amount == item.amount_before_tax * 0.10
            assert invoice.tax_amount == item.tax_amount
            assert invoice.total_amount == invoice.amount_before_tax + invoice.tax_amount

    def test_rest_endpoints(self, client, app, proposal_setup):
        """Verify HTTP endpoints for getting, approving, and rejecting correction proposals."""
        # Log in test user
        with client.session_transaction() as sess:
            sess["logged_in"] = True
            sess["username"] = "admin"
            sess["user_role"] = "admin"

        # Seed proposal (app fixture already provides app_context)
        invoice = Invoice.query.first()
        invoice_id = invoice.id
        proposal = InvoiceCorrectionProposal(
            invoice_id=invoice_id,
            taxpayer_mst=invoice.taxpayer_mst,
            correction_type="payment_method",
            original_value="TM",
            proposed_value="CK",
            ai_explanation="Test endpoint proposal",
            status="pending",
            created_at="2026-05-29 10:00:00",
            updated_at="2026-05-29 10:00:00"
        )
        db.session.add(proposal)
        db.session.commit()
        proposal_id = proposal.id

        # 1. Get proposals by invoice
        resp = client.get(f"/api/invoices/local/{invoice_id}/correction-proposals")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["id"] == proposal_id

        # 2. Get all proposals for current tenant MST
        resp = client.get("/api/correction-proposals")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["taxpayer_mst"] == "0208887776"

        # 3. Approve proposal via REST
        resp = client.post(f"/api/correction-proposals/{proposal_id}/approve")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "success"

        # Verify applied
        db.session.expire_all()
        p = db.session.get(InvoiceCorrectionProposal, proposal_id)
        assert p.status == "approved"
        inv = db.session.get(Invoice, invoice_id)
        assert inv.payment_method == "CK"

        # Create another proposal to test reject
        proposal_reject = InvoiceCorrectionProposal(
            invoice_id=invoice_id,
            taxpayer_mst="0208887776",
            correction_type="payment_method",
            original_value="TM",
            proposed_value="CK",
            ai_explanation="Test endpoint proposal reject",
            status="pending",
            created_at="2026-05-29 10:00:00",
            updated_at="2026-05-29 10:00:00"
        )
        db.session.add(proposal_reject)
        db.session.commit()
        reject_id = proposal_reject.id

        # 4. Reject proposal via REST
        resp = client.post(f"/api/correction-proposals/{reject_id}/reject")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "success"

        db.session.expire_all()
        p2 = db.session.get(InvoiceCorrectionProposal, reject_id)
        assert p2.status == "rejected"


