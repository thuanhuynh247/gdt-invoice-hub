"""
Tests for V36: Annual CIT Finalization & Loss Carry-Forward Suite.
US-480, US-481, US-482, US-483, US-484, US-485.
"""

import pytest
from app import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess["logged_in"] = True
            sess["taxpayer_mst"] = "0102030405"
        yield c

@pytest.fixture(autouse=True)
def app_context():
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        yield

class TestCITFinalizationService:
    def test_calculate_cit(self):
        from invoices.v36_service import CITFinalizationService
        # No loss carry forward, 20% CIT rate
        res = CITFinalizationService.calculate_cit(
            revenue=1000, cogs=600, selling_expenses=100, admin_expenses=50,
            non_deductible_adjustments=50, loss_offset=0, cit_rate=0.20, holiday_discount=0.0
        )
        assert res["net_accounting_profit"] == 250
        assert res["taxable_income_before_loss"] == 300
        assert res["applied_loss"] == 0
        assert res["taxable_income"] == 300
        assert res["cit_liability"] == 60

    def test_calculate_cit_with_holiday_and_loss(self):
        from invoices.v36_service import CITFinalizationService
        # 50% discount, 100 loss carry forward
        res = CITFinalizationService.calculate_cit(
            revenue=1000, cogs=600, selling_expenses=100, admin_expenses=50,
            non_deductible_adjustments=50, loss_offset=100, cit_rate=0.20, holiday_discount=0.5
        )
        assert res["net_accounting_profit"] == 250
        assert res["taxable_income_before_loss"] == 300
        assert res["applied_loss"] == 100
        assert res["taxable_income"] == 200
        assert res["cit_before_incentives"] == 40
        assert res["cit_liability"] == 20

    def test_optimize_loss_carry_forward(self):
        from invoices.v36_service import CITFinalizationService
        hist_losses = {2021: 100, 2022: 50, 2023: 150}
        proj_profits = {2026: 200}
        tax_holidays = {2026: {"tax_free": False, "reduction": 0.5}} # 10% effective tax rate

        opt = CITFinalizationService.optimize_loss_carry_forward(
            hist_losses, proj_profits, tax_holidays, cit_rate=0.20
        )
        # 2021 loss expires in 2026 (2021 + 5 = 2026) so it's active.
        # Check active losses offset chronologically
        assert len(opt["offset_schedule"]) > 0
        total_offset = sum(item["amount_offset"] for item in opt["offset_schedule"])
        assert total_offset == 200 # Profit capacity is 200, so we can offset 200 of 300 total loss.

    def test_generate_cit_xml(self):
        from invoices.v36_service import CITFinalizationService
        cit_data = {
            "revenue": 1000, "cogs": 600, "selling_expenses": 100, "admin_expenses": 100,
            "net_accounting_profit": 200, "taxable_income_before_loss": 250,
            "applied_loss": 100, "cit_liability": 30
        }
        loss_data = {
            "historical_losses": {2021: 150},
            "prior_offsets": {2021: 0},
            "offset_schedule": [{"loss_year": 2021, "profit_year": 2026, "amount_offset": 100}],
            "expired_losses": {2021: 0}
        }
        xml_str = CITFinalizationService.generate_cit_xml(
            mst="0102030405", taxpayer_name="TEST COMPANY", year=2026,
            cit_data=cit_data, loss_data=loss_data
        )
        assert "<hoSoKhaiThue>" in xml_str
        assert "<toaKhai>" in xml_str
        assert "<phuLuc_03_1A>" in xml_str
        assert "<phuLuc_03_2A>" in xml_str
        assert "<namPhatSinh>2021</namPhatSinh>" in xml_str

class TestV36ComplianceRoutes:
    def test_cit_finalization_page_route(self, client):
        resp = client.get("/v36-cit-finalization")
        assert resp.status_code == 200

    def test_api_cit_calculate_route(self, client):
        resp = client.post("/api/cit/calculate", json={
            "revenue": 1000, "cogs": 600, "selling_expenses": 100, "admin_expenses": 100,
            "non_deductible_adjustments": 50, "loss_offset": 50
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["taxable_income_before_loss"] == 250
        assert data["applied_loss"] == 50
        assert data["taxable_income"] == 200

    def test_api_cit_optimize_losses_route(self, client):
        resp = client.post("/api/cit/optimize-losses", json={
            "historical_losses": {"2021": 150, "2022": 50},
            "projected_profits": {"2026": 200},
            "tax_holidays": {"2026": {"tax_free": False, "reduction": 0.5}}
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert "offset_schedule" in data
        assert "remaining_losses" in data

    def test_api_cit_export_xml_route(self, client):
        resp = client.post("/api/cit/export-xml", json={
            "mst": "0102030405",
            "year": 2026,
            "cit_data": {
                "revenue": 1000, "cogs": 600, "selling_expenses": 100, "admin_expenses": 100,
                "net_accounting_profit": 200, "taxable_income_before_loss": 250,
                "applied_loss": 100, "cit_liability": 30
            },
            "loss_data": {
                "historical_losses": {"2021": 150},
                "prior_offsets": {"2021": 0},
                "offset_schedule": [{"loss_year": 2021, "profit_year": 2026, "amount_offset": 100}],
                "expired_losses": {"2021": 0}
            }
        })
        assert resp.status_code == 200
        assert resp.mimetype == "application/xml"
        assert len(resp.data) > 0

    def test_api_cit_swarm_chat_route(self, client):
        resp = client.post("/api/cit/swarm-chat", json={
            "cit_data": {"revenue": 1000, "cit_liability": 30},
            "loss_data": {"historical_losses": {2021: 150}}
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert "debate" in data
        assert "memo" in data
