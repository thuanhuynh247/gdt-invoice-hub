"""Integration tests for V12 Rolling 30/60/90-day Cash Flow Projection (US-150) and Interactive Scenario Simulator (US-151)."""

from __future__ import annotations

from datetime import date, timedelta
import pytest

from extensions import db
from invoices.models import Invoice, TaxpayerProfile
from invoices.cashflow_service import calculate_cashflow_projection, simulate_scenario


def _seed_cashflow_invoices(app):
    """Seed test invoices inside the database context for cash flow tests."""
    with app.app_context():
        # Clear tables
        Invoice.query.delete()
        TaxpayerProfile.query.delete()
        db.session.commit()

        # Seed profile
        profile = TaxpayerProfile(
            mst="0101234567",
            company_name="Apex Global Ltd",
            gdt_username="apex_user",
            gdt_password_encrypted="hash_pass",
            is_active=True,
            created_at="2026-05-30T00:00:00Z"
        )
        db.session.add(profile)
        db.session.commit()

        # Seed invoices
        # 1. Receivable: Due on 2026-06-15 (16 days from 2026-05-30)
        inv1 = Invoice(
            id="0101234567-1C26TBA-0000001",
            filename="recv1.xml",
            invoice_type="Hóa đơn GTGT",
            symbol="1C26TBA",
            number="0000001",
            date="2026-05-15",
            due_date="2026-06-15",
            currency="VND",
            seller_name="Apex Global Ltd",
            seller_mst="0101234567",
            buyer_name="Client Corp A",
            buyer_mst="0909090909",
            amount_before_tax=10000000.0,
            tax_amount=1000000.0,
            total_amount=11000000.0,
            imported_at="2026-05-30T01:00:00Z",
            import_status="imported",
            taxpayer_mst="0101234567",
            is_cancelled=False
        )

        # 2. Receivable: Due on 2026-07-15 (46 days from 2026-05-30)
        inv2 = Invoice(
            id="0101234567-1C26TBA-0000002",
            filename="recv2.xml",
            invoice_type="Hóa đơn GTGT",
            symbol="1C26TBA",
            number="0000002",
            date="2026-05-20",
            due_date="2026-07-15",
            currency="VND",
            seller_name="Apex Global Ltd",
            seller_mst="0101234567",
            buyer_name="Client Corp B",
            buyer_mst="0808080808",
            amount_before_tax=20000000.0,
            tax_amount=2000000.0,
            total_amount=22000000.0,
            imported_at="2026-05-30T01:00:00Z",
            import_status="imported",
            taxpayer_mst="0101234567",
            is_cancelled=False
        )

        # 3. Payable: Due on 2026-06-10 (11 days from 2026-05-30)
        inv3 = Invoice(
            id="9999999999-1C26TBA-0000100",
            filename="pay1.xml",
            invoice_type="Hóa đơn GTGT",
            symbol="1C26TBA",
            number="0000100",
            date="2026-05-10",
            due_date="2026-06-10",
            currency="VND",
            seller_name="Supplier Corp X",
            seller_mst="9999999999",
            buyer_name="Apex Global Ltd",
            buyer_mst="0101234567",
            amount_before_tax=5000000.0,
            tax_amount=500000.0,
            total_amount=5500000.0,
            imported_at="2026-05-30T01:00:00Z",
            import_status="imported",
            taxpayer_mst="0101234567",
            is_cancelled=False
        )

        # 4. Cancelled Invoice: Should be completely ignored by cash flow engine
        inv4 = Invoice(
            id="0101234567-1C26TBA-0000003",
            filename="cancelled.xml",
            invoice_type="Hóa đơn GTGT",
            symbol="1C26TBA",
            number="0000003",
            date="2026-05-12",
            due_date="2026-06-12",
            currency="VND",
            seller_name="Apex Global Ltd",
            seller_mst="0101234567",
            buyer_name="Client Corp C",
            buyer_mst="0707070707",
            amount_before_tax=15000000.0,
            tax_amount=1500000.0,
            total_amount=16500000.0,
            imported_at="2026-05-30T01:00:00Z",
            import_status="imported",
            taxpayer_mst="0101234567",
            is_cancelled=True
        )

        db.session.add_all([inv1, inv2, inv3, inv4])
        db.session.commit()


def test_calculate_cashflow_projections_engine(app):
    """Test standard projection logic without simulation adjustments."""
    _seed_cashflow_invoices(app)
    as_of = date(2026, 5, 30)

    with app.app_context():
        res = calculate_cashflow_projection(taxpayer_mst="0101234567", as_of=as_of)

        # Verify projections structures
        assert "30d" in res["projections"]
        assert "60d" in res["projections"]
        assert "90d" in res["projections"]

        # 30-day projection:
        # Receivables: inv1 (11,000,000)
        # Payables: inv3 (5,500,000)
        # VAT Liability: (1,000,000 - 500,000) = 500,000 (from non-paid active invoices)
        # Net Cash Flow: 11,000,000 - 5,500,000 - 500,000 = 5,000,000
        p30 = res["projections"]["30d"]
        assert p30["total_receivables"] == 11000000.0
        assert p30["total_payables"] == 5500000.0
        assert p30["net_cash_flow"] == 5000000.0

        # 60-day projection:
        # Receivables: inv1 + inv2 (11,000,000 + 22,000,000 = 33,000,000)
        # Payables: inv3 (5,500,000)
        # Net Cash Flow: 33,000,000 - 5,500,000 - 2,500,000 (projected VAT) = 25,000,000
        p60 = res["projections"]["60d"]
        assert p60["total_receivables"] == 33000000.0
        assert p60["total_payables"] == 5500000.0

        # Verify timeline length
        assert len(res["daily_timeline"]) == 91  # 0 to 90 days


def test_simulate_scenario_delays_and_rejections(app):
    """Test what-if simulation scenarios with client delays and rejection rates."""
    _seed_cashflow_invoices(app)
    as_of = date(2026, 5, 30)

    with app.app_context():
        # Scenario A: Delay payment by 20 days.
        # inv1 due date (June 15) shifted by 20 days -> July 5 (Outside 30-day projection horizon)
        res_delayed = simulate_scenario(
            taxpayer_mst="0101234567",
            delay_days=20,
            as_of=as_of
        )
        p30_delayed = res_delayed["projections"]["30d"]
        # Receivables in 30d drops to 0 because inv1 is now due on July 5
        assert p30_delayed["total_receivables"] == 0.0

        # Scenario B: 25% rejection rate on receivables.
        # Original 60d receivables = 33,000,000.
        # With 25% rejection -> 33,000,000 * 0.75 = 24,750,000
        res_rejected = simulate_scenario(
            taxpayer_mst="0101234567",
            rejection_rate=0.25,
            as_of=as_of
        )
        p60_rejected = res_rejected["projections"]["60d"]
        assert p60_rejected["total_receivables"] == 24750000.0


def test_cashflow_api_endpoints(client, app):
    """Test cashflow web pages and APIs."""
    _seed_cashflow_invoices(app)

    with client.session_transaction() as sess:
        sess["user_id"] = "1"
        sess["logged_in"] = True
        sess["username"] = "viewer_user"
        sess["user_role"] = "viewer"
        sess["expires_at"] = "2099-05-20T00:00:00+00:00"
        sess["active_taxpayer_mst"] = "0101234567"

    # GET Page
    resp = client.get("/cashflow")
    assert resp.status_code == 200

    # GET Projection JSON API
    resp = client.get("/api/finance/cashflow")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "projections" in data
    assert "30d" in data["projections"]

    # POST Simulation API
    resp = client.post("/api/finance/simulate", json={
        "delay_days": 10,
        "rejection_rate": 0.1,
        "vat_adjustment": 500000.0
    })
    assert resp.status_code == 200
    sim_data = resp.get_json()
    assert sim_data["scenario_applied"]["delay_days"] == 10
    assert sim_data["scenario_applied"]["rejection_rate"] == 0.1
