import pytest
from unittest.mock import MagicMock, patch
from invoices.models import Invoice, AIAuditResult
from invoices.service import recalculate_t_score_value, calculate_invoice_t_score
from invoices.scheduler import should_trigger_audit_agent, SchedulerThread
from datetime import datetime

class MockItem:
    def __init__(self, tax_rate="10%", amount_before_tax=1000000.0):
        self.tax_rate = tax_rate
        self.amount_before_tax = amount_before_tax

class MockInvoice:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", "HD-MOCK")
        self.seller_mst = kwargs.get("seller_mst", "0102030405")
        self.has_signature = kwargs.get("has_signature", True)
        self.signing_date = kwargs.get("signing_date", "2026-05-25 10:00:00")
        self.date = kwargs.get("date", "2026-05-25 09:00:00")
        self.items = kwargs.get("items", [])
        self.tax_amount = kwargs.get("tax_amount", 100000.0)
        self.payment_method = kwargs.get("payment_method", "Chuyển khoản")
        self.total_amount = kwargs.get("total_amount", 1100000.0)
        self.ai_audit_results = kwargs.get("ai_audit_results", [])
        self.t_score = 100
        self.t_rating = "A++"

def test_recalculate_t_score_value_perfect(app):
    # Perfect compliance -> score 100
    inv = MockInvoice(
        items=[MockItem(tax_rate="10%", amount_before_tax=1000000.0)],
        tax_amount=100000.0,
        payment_method="Chuyển khoản",
        total_amount=1100000.0
    )
    score, rating = recalculate_t_score_value(inv)
    assert score == 100
    assert rating == "A++"

def test_recalculate_t_score_value_mst_risk(app):
    # High risk MST in HIGH_RISK_MSTS -> -40
    inv = MockInvoice(
        seller_mst="0101234599",
        items=[MockItem(tax_rate="10%", amount_before_tax=1000000.0)],
        tax_amount=100000.0,
        payment_method="Chuyển khoản",
        total_amount=1100000.0
    )
    score, rating = recalculate_t_score_value(inv)
    assert score == 60
    assert rating == "D"

def test_recalculate_t_score_value_cash_limit(app):
    # Cash payment >= 5M VND -> -20
    inv = MockInvoice(
        items=[MockItem(tax_rate="10%", amount_before_tax=5000000.0)],
        tax_amount=500000.0,
        payment_method="Tiền mặt",
        total_amount=5500000.0
    )
    score, rating = recalculate_t_score_value(inv)
    assert score == 80
    assert rating == "B"

def test_recalculate_t_score_value_cash_limit_under(app):
    # Cash payment < 5M VND -> no deduction
    inv = MockInvoice(
        items=[MockItem(tax_rate="10%", amount_before_tax=4000000.0)],
        tax_amount=400000.0,
        payment_method="Tiền mặt",
        total_amount=4400000.0
    )
    score, rating = recalculate_t_score_value(inv)
    assert score == 100
    assert rating == "A++"

def test_recalculate_t_score_value_multiple_deductions(app):
    # MST warning (-40), signature delay (-20), math mismatch (-20), payment check (-20)
    # Total deduction 100 -> score 0
    inv = MockInvoice(
        seller_mst="0101234599", # -40
        has_signature=False, # -20
        date="2026-05-25 09:00:00",
        signing_date="2026-05-28 10:00:00", # -20
        items=[MockItem(tax_rate="10%", amount_before_tax=5000000.0)], # tax = 500k, declared = 400k (mismatch) -> -20
        tax_amount=400000.0,
        payment_method="Tiền mặt",
        total_amount=5500000.0 # -20
    )
    score, rating = recalculate_t_score_value(inv)
    assert score == 0
    assert rating == "F"

def test_should_trigger_audit_agent():
    settings = {
        "audit_agent_enabled": True,
        "audit_agent_schedule_time": "23:00",
        "last_audit_run": ""
    }
    now = datetime.now().replace(hour=23, minute=0, second=0, microsecond=0)
    assert should_trigger_audit_agent(settings, now) is True

    # Disabled
    settings["audit_agent_enabled"] = False
    assert should_trigger_audit_agent(settings, now) is False

    # Already run today
    settings["audit_agent_enabled"] = True
    settings["last_audit_run"] = now.date().isoformat()
    assert should_trigger_audit_agent(settings, now) is False

def test_calculate_invoice_t_score_db_update(app):
    from extensions import db
    # Insert temporary test invoice
    inv = Invoice(
        id="test-tscore-invoice-1",
        number="HD001",
        date="2026-05-25",
        seller_name="Test Company",
        seller_mst="0101234599", # high-risk MST to trigger deduction
        buyer_name="Buyer Company",
        buyer_mst="0504030201",
        total_amount=1000000,
        payment_method="Chuyển khoản",
        has_signature=True,
        t_score=100,
        t_rating="A++",
        imported_at="2026-05-25 00:00:00",
        ai_audit_results=[]
    )
    db.session.add(inv)
    db.session.commit()

    calculate_invoice_t_score(inv)
    
    # Assert values updated in DB
    refetched = db.session.get(Invoice, "test-tscore-invoice-1")
    assert refetched.t_score == 60
    assert refetched.t_rating == "D"

    # Cleanup
    db.session.delete(refetched)
    db.session.commit()

@patch("invoices.ai_service.AIComplianceAuditor.audit_invoice")
@patch("invoices.scheduler.SchedulerThread.send_compliance_alert")
def test_execute_autonomous_audit(mock_send_alert, mock_audit, app):
    from extensions import db
    # 1. Create one audited and one unaudited invoice
    inv1 = Invoice(
        id="test-auto-audit-1",
        number="HD1",
        date="2026-05-25",
        total_amount=1000000,
        payment_method="Chuyển khoản",
        ai_audited=True,
        t_score=100,
        t_rating="A++",
        imported_at="2026-05-25 00:00:00",
        ai_audit_results=[]
    )
    inv2 = Invoice(
        id="test-auto-audit-2",
        number="HD2",
        date="2026-05-25",
        total_amount=1000000,
        payment_method="Chuyển khoản",
        ai_audited=False,
        t_score=100,
        t_rating="A++",
        imported_at="2026-05-25 00:00:00",
        ai_audit_results=[]
    )
    db.session.add_all([inv1, inv2])
    db.session.commit()

    def mock_audit_side_effect(invoice):
        invoice.t_score = 45
        invoice.t_rating = "F"
        invoice.ai_audited = True
        db.session.commit()

    mock_audit.side_effect = mock_audit_side_effect

    thread = SchedulerThread(app)
    thread.execute_autonomous_audit({"recipient_email": "test@example.com"})

    # Check that audit was called on inv2 but not inv1
    mock_audit.assert_called_once()
    assert mock_audit.call_args[0][0].id == "test-auto-audit-2"

    # Check alert was dispatched since t_score < 50
    mock_send_alert.assert_called_once()
    assert mock_send_alert.call_args[0][1].id == "test-auto-audit-2"

    # Cleanup
    db.session.delete(inv1)
    db.session.delete(inv2)
    db.session.commit()

@patch("requests.post")
@patch("invoices.scheduler.SchedulerThread.send_smtp_message")
def test_send_compliance_alert(mock_smtp, mock_post, app):
    # Setup test invoice with F score
    inv = Invoice(
        id="test-alert-invoice",
        number="HD002",
        date="2026-05-25",
        seller_name="Test Company",
        seller_mst="0102030405",
        total_amount=6000000,
        payment_method="Tiền mặt",
        t_score=40,
        t_rating="F",
        imported_at="2026-05-25 00:00:00",
        ai_audit_results=[]
    )

    settings = {
        "recipient_email": "alert@example.com",
        "smtp_host": "smtp.example.com",
        "smtp_port": 587,
        "smtp_user": "user@example.com",
        "smtp_pass": "smtp_pass_encrypted",
        "smtp_use_tls": True,
        "telegram_enabled": True,
        "telegram_bot_token": "mock_token",
        "telegram_chat_id": "123456"
    }

    mock_post.return_value.status_code = 200

    thread = SchedulerThread(app)
    thread.send_compliance_alert(settings, inv)

    # Check telegram post was triggered
    mock_post.assert_called_once()
    url = mock_post.call_args[0][0]
    payload = mock_post.call_args[1]["json"]
    assert "mock_token" in url
    assert payload["chat_id"] == "123456"
    assert "CẢNH BÁO KIỂM TOÁN THUẾ" in payload["text"]

    # Check SMTP send mail was called
    mock_smtp.assert_called_once()
    assert mock_smtp.call_args[0][5] == "alert@example.com"
