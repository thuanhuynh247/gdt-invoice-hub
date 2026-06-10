"""
Tests for V37: CEO Intelligence Dashboard, Tax Planning, Fixed Assets & AI Linker.
US-490, US-491, US-492, US-493, US-494, US-495.
"""

import pytest
from datetime import datetime, date
from app import create_app
from extensions import db
from invoices.models import Invoice, LineItem, FixedAsset, DepreciationEntry, TaxFilingRecord

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
        # Clear specific tables to avoid interference
        db.session.query(DepreciationEntry).delete()
        db.session.query(FixedAsset).delete()
        db.session.query(TaxFilingRecord).delete()
        db.session.query(LineItem).delete()
        db.session.query(Invoice).delete()
        db.session.commit()
        yield

class TestCEODashboardAndTaxPlanningServices:
    def test_ceo_health_score_defaults(self):
        from invoices.v37_service import CEOIntelligenceService
        res = CEOIntelligenceService.calculate_financial_health_score("0102030405")
        assert res["overall_score"] > 0
        assert "sub_scores" in res
        assert res["sub_scores"]["cash_score"] == 85.0

    def test_ceo_sankey_data(self):
        from invoices.v37_service import CEOIntelligenceService
        res = CEOIntelligenceService.generate_sankey_data("0102030405")
        assert "nodes" in res
        assert "links" in res
        assert len(res["nodes"]) == 7

    def test_tax_projection_and_npv(self):
        from invoices.v37_service import MultiYearTaxPlanningService
        res = MultiYearTaxPlanningService.generate_tax_projection("0102030405", years_forward=3)
        assert len(res["projection"]) == 3
        
        npv_res = MultiYearTaxPlanningService.optimize_tax_npv(res, discount_rate=0.08)
        assert "comparison" in npv_res
        assert "recommended_strategy" in npv_res

    def test_tax_calendar_deadlines(self):
        from invoices.v37_service import TaxFilingCalendarService
        deadlines = TaxFilingCalendarService.generate_filing_deadlines(2026)
        # 12 monthly VAT + 4 quarterly VAT + 4 quarterly CIT + 2 annual = 22
        assert len(deadlines) == 22
        
        # Populate
        TaxFilingCalendarService.populate_calendar_db(2026)
        records = TaxFilingRecord.query.all()
        assert len(records) == 22

        # Mark as filed
        rec = records[0]
        success = TaxFilingCalendarService.mark_filed(rec.id, "2026-02-15")
        assert success is True
        assert rec.status == "Filed"
        assert rec.filed_date == "2026-02-15"

        # Compliance score
        score = TaxFilingCalendarService.calculate_compliance_score()
        assert score > 0

    def test_fixed_asset_depreciation(self):
        from invoices.v37_service import FixedAssetDepreciationEngine
        
        asset = FixedAsset(
            asset_code="FA-001",
            name="Máy tính server",
            category="Computers",
            acquisition_date="2026-01-01",
            original_cost=50000000.0,
            residual_value=2000000.0,
            useful_life_months=36,
            depreciation_method="straight_line",
            status="active"
        )
        db.session.add(asset)
        db.session.commit()

        # Straight-line depreciation calculation
        dep = FixedAssetDepreciationEngine.calculate_depreciation(asset, "2026-01")
        # monthly depreciation: (50M - 2M) / 36 = 1,333,333.33
        assert dep["depreciation_amount"] == 1333333.33
        assert dep["net_book_value"] == 48666666.67

        # Schedule generation
        sched = FixedAssetDepreciationEngine.generate_depreciation_schedule(asset.id)
        assert len(sched) == 36
        assert sched[35]["net_book_value"] == 2000000.0

        # Declining balance factor logic
        asset.depreciation_method = "declining_balance"
        db.session.commit()
        dep_db = FixedAssetDepreciationEngine.calculate_depreciation(asset, "2026-01")
        # factor is 1.5 because useful life is 3 years
        # rate = 1/3 * 1.5 = 0.5 annually, i.e., 50%
        # monthly rate opening year = (50M * 0.5) / 12 = 2,083,333.33
        assert dep_db["depreciation_amount"] == 2083333.33

        # Disposal
        disp = FixedAssetDepreciationEngine.dispose_asset(asset.id, "2026-06-01", 30000000.0)
        assert asset.status == "disposed"
        assert "gain_loss" in disp

    def test_ai_linker_and_validator(self):
        # Create a purchase invoice of 45M VND
        inv = Invoice(
            id="seller-sym-num",
            seller_mst="999888777",
            buyer_mst="0102030405",
            taxpayer_mst="0102030405",
            total_amount=45000000.0,
            seller_name="Công ty phân phối máy tính",
            imported_at="2026-06-10",
            is_cancelled=False
        )
        db.session.add(inv)
        db.session.commit()

        # Add line item
        item = LineItem(
            invoice_id=inv.id,
            item_name="Hệ thống máy tính Dell Workstation",
            quantity=1,
            unit_price=45000000.0,
            amount_before_tax=45000000.0
        )
        db.session.add(item)
        db.session.commit()

        from invoices.v37_service import AIInvoiceAssetLinker
        candidates = AIInvoiceAssetLinker.auto_detect_fixed_assets("0102030405")
        assert len(candidates) == 1
        assert candidates[0]["invoice_id"] == inv.id
        assert candidates[0]["suggested_category"] == "Thiết bị dụng cụ quản lý"
        assert candidates[0]["suggested_useful_life_months"] == 36

        # Validator
        asset = FixedAsset(
            asset_code="FA-002",
            name="Workstation Dell",
            category="Thiết bị dụng cụ quản lý",
            acquisition_date="2026-01-01",
            original_cost=45000000.0,
            useful_life_months=36, # compliant
        )
        val = AIInvoiceAssetLinker.validate_depreciation_compliance(asset)
        assert val["is_compliant"] is True

        asset.useful_life_months = 12 # too low! limit is 3 years (36 months)
        val2 = AIInvoiceAssetLinker.validate_depreciation_compliance(asset)
        assert val2["is_compliant"] is False
        assert "warning" in val2 and val2["warning"] is not None


class TestV37ComplianceRoutes:
    def test_v37_ceo_dashboard_page(self, client):
        resp = client.get("/v37-ceo-dashboard")
        assert resp.status_code == 200

    def test_api_ceo_dashboard(self, client):
        resp = client.get("/api/ceo-dashboard")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert "health_score" in data
        assert "commentary" in data

    def test_api_ceo_dashboard_sankey(self, client):
        resp = client.get("/api/ceo-dashboard/sankey")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "nodes" in data
        assert "links" in data

    def test_api_tax_planning_projection(self, client):
        resp = client.get("/api/tax-planning/projection?years=3")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "projection" in data
        assert "npv_optimization" in data

    def test_api_tax_planning_calendar(self, client):
        resp = client.get("/api/tax-planning/calendar")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "calendar" in data
        assert "compliance_score" in data

    def test_api_tax_planning_calendar_mark_filed(self, client):
        # Insert a record first
        rec = TaxFilingRecord(tax_type="VAT", period="2026-01", deadline="2026-02-20", status="Pending")
        db.session.add(rec)
        db.session.commit()

        resp = client.post("/api/tax-planning/calendar/mark-filed", json={
            "record_id": rec.id,
            "filed_date": "2026-02-18",
            "xml_file_path": "/data/xml/vat_2026_01.xml"
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"

    def test_api_assets_crud(self, client):
        # Create
        resp = client.post("/api/assets", json={
            "asset_code": "ASSET-999",
            "name": "Camera giám sát xưởng",
            "category": "Máy móc thiết bị",
            "acquisition_date": "2026-06-01",
            "original_cost": 32000000.0,
            "residual_value": 1000000.0,
            "useful_life_months": 48,
            "depreciation_method": "straight_line"
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        asset_id = data["asset"]["id"]

        # List
        resp_list = client.get("/api/assets")
        assert resp_list.status_code == 200
        data_list = resp_list.get_json()
        assert len(data_list["assets"]) > 0

        # Schedule
        resp_sched = client.get(f"/api/assets/schedule?asset_id={asset_id}")
        assert resp_sched.status_code == 200
        data_sched = resp_sched.get_json()
        assert len(data_sched["schedule"]) == 48

        # Validate
        resp_val = client.get(f"/api/assets/validate?asset_id={asset_id}")
        assert resp_val.status_code == 200
        data_val = resp_val.get_json()
        assert "validation" in data_val

        # Auto detect candidates
        resp_det = client.get("/api/assets/auto-detect")
        assert resp_det.status_code == 200

        # Dispose
        resp_disp = client.post("/api/assets/dispose", json={
            "asset_id": asset_id,
            "disposed_date": "2026-08-01",
            "disposal_proceeds": 25000000.0
        })
        assert resp_disp.status_code == 200
        data_disp = resp_disp.get_json()
        assert data_disp["status"] == "success"
