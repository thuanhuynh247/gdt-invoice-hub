import pytest
import json
from datetime import datetime, date
from app import create_app
from extensions import db
from invoices.models import Invoice, Partner, FixedAsset, DepreciationEntry, TaxpayerProfile, BlacklistedMST
from invoices.v39_service import DeferredTaxService, CashFlowStressService, SupplierRiskNetworkService

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    
    with app.app_context():
        db.create_all()
        
        # Seed taxpayer profile
        tp = TaxpayerProfile(
            mst="0102030405",
            company_name="Antigravity Test Corporation",
            gdt_username="antigravity_admin",
            gdt_password_encrypted="pass123",
            created_at="2026-01-01"
        )
        db.session.add(tp)
        
        # Seed supplier partner catalog
        supplier_p = Partner(
            mst="0908070605",
            name="Nha Cung Cap Tin Cay",
            address="Hanoi, Vietnam",
            mst_status="ACTIVE",
            mst_last_checked="2026-06-01 12:00:00"
        )
        db.session.add(supplier_p)
        
        # Seed fixed assets with various depreciation configs (accounting vs TT45 limits)
        asset_compliant = FixedAsset(
            asset_code="FA-COMP-01",
            name="Laptop Lenovo ThinkPad",
            category="Thiết bị dụng cụ quản lý",
            acquisition_date="2026-01-15",
            original_cost=36000000.0,
            residual_value=0.0,
            useful_life_months=36,  # 36 months = 3 years (Compliant with minimum 36 months under TT45)
            depreciation_method="straight_line",
            status="active"
        )
        
        asset_non_compliant = FixedAsset(
            asset_code="FA-NONCOMP-01",
            name="MacBook Pro M3 Max",
            category="Thiết bị dụng cụ quản lý",
            acquisition_date="2026-01-15",
            original_cost=48000000.0,
            residual_value=0.0,
            useful_life_months=24,  # 24 months = 2 years (Less than minimum 36 months under TT45)
            depreciation_method="straight_line",
            status="active"
        )
        
        db.session.add(asset_compliant)
        db.session.add(asset_non_compliant)
        
        # Seed invoices for cash flow and supplier check
        inv1 = Invoice(
            id="0908070605-AA-00001",
            number="00001",
            date="2026-06-01",
            taxpayer_mst="0102030405",
            seller_mst="0908070605",
            buyer_mst="0102030405",
            seller_name="Nha Cung Cap Tin Cay",
            buyer_name="Antigravity Test Corporation",
            total_amount=120000000.0,  # 120M purchase
            tax_amount=12000000.0,
            is_cancelled=False,
            payment_method="CK",
            import_status="imported",
            imported_at="2026-06-01"
        )
        
        inv2 = Invoice(
            id="0102030405-BB-00002",
            number="00002",
            date="2026-06-05",
            taxpayer_mst="0102030405",
            seller_mst="0102030405",
            buyer_mst="0908070605",
            seller_name="Antigravity Test Corporation",
            buyer_name="Nha Cung Cap Tin Cay",
            total_amount=350000000.0,  # 350M sale
            tax_amount=35000000.0,
            is_cancelled=False,
            payment_method="CK",
            import_status="imported",
            imported_at="2026-06-05"
        )
        
        db.session.add(inv1)
        db.session.add(inv2)
        
        db.session.commit()
        
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def test_vas17_deferred_tax_engine(client):
    """US-510: Verify the engine computes temporary differences, permanent differences, and DTA values."""
    res = DeferredTaxService.calculate_vas17_deferred_tax("0102030405", 2026)
    
    assert res["taxpayer_mst"] == "0102030405"
    assert res["year"] == 2026
    assert res["accounting_profit"] == 2000000000.0
    
    # Non-compliant asset (MacBook Pro useful life = 24 months vs TT45 minimum = 36 months)
    # Accounting annual = 48M / 24 * 12 = 24M
    # Tax annual = 48M / 36 * 12 = 16M
    # Temporary difference = 24M - 16M = 8M VND
    depr_diffs = res["depreciation_differences"]
    assert len(depr_diffs) == 1
    assert depr_diffs[0]["asset_code"] == "FA-NONCOMP-01"
    assert abs(depr_diffs[0]["temporary_difference"] - 8000000.0) < 0.01

    # Provisions (simulated)
    assert len(res["deductible_differences"]) == 3
    assert res["deferred_tax_assets"] > 0.0


def test_vas17_journal_entries(client):
    """US-511: Verify suggested journal bookings are generated when DTA changes."""
    entries = DeferredTaxService.generate_journal_entries("0102030405", 2026)
    assert len(entries) > 0
    assert entries[0]["account_debit"] == "8212"
    assert entries[0]["account_credit"] == "243"
    assert entries[0]["amount"] > 0.0


def test_cash_flow_stress_testing(client):
    """US-512: Verify cash stress simulation runway months, status alerts, and SVG gauges."""
    # Baseline simulation (DSO = 0, DPO = 0)
    sim = CashFlowStressService.run_cash_stress_simulation("0102030405", 0, 0)
    assert sim["current_cash"] == 2500000000.0
    assert sim["monthly_opex"] == 450000000.0
    assert sim["dso_days"] == 0
    assert sim["dpo_days"] == 0
    assert "Runway" in sim["gauge_svg"]
    
    # Stress test case: DSO increases to 60 days
    sim_stress = CashFlowStressService.run_cash_stress_simulation("0102030405", 60, 0)
    assert sim_stress["dso_days"] == 60
    assert sim_stress["runway_months"] < 12.0 or sim_stress["risk_level"] in ["Red", "Amber"]


def test_supplier_network_graph(client):
    """US-513: Verify nodes, links, and SVG layout code are built properly."""
    net = SupplierRiskNetworkService.build_supplier_network_graph("0102030405")
    assert len(net["nodes"]) >= 2  # Center node + 1 supplier node
    assert len(net["links"]) >= 1
    
    center_node = next(n for n in net["nodes"] if n["type"] == "center")
    assert center_node["id"] == "0102030405"
    
    supplier_nodes = [n for n in net["nodes"] if n["type"] == "supplier"]
    assert any(sn["id"] == "0908070605" for sn in supplier_nodes)
    assert "svg" in net["svg_graph"]


def test_live_gdt_scraper_check(client):
    """US-514: Verify live scraper state checks, blacklist triggers, and partner catalog updates."""
    # Verify standard active check
    from invoices.mst_service import STATUS_ACTIVE
    res = SupplierRiskNetworkService.simulate_gdt_scraper_check("0908070605")
    assert res["gdt_status"] == STATUS_ACTIVE
    
    # Add partner to blacklist database and verify it triggers a status update
    blacklist_entry = BlacklistedMST(mst="0908070605", reason="Violating Tax Invoice Regulations")
    db.session.add(blacklist_entry)
    db.session.commit()
    
    res_blacklisted = SupplierRiskNetworkService.simulate_gdt_scraper_check("0908070605")
    assert res_blacklisted["gdt_status"] == "BLACKLISTED"
    
    # Confirm partner catalog updated cache
    partner = Partner.query.filter_by(mst="0908070605").first()
    assert partner.mst_status == "BLACKLISTED"


def test_api_routes_unauthorized(client):
    """Check unauthorized redirection/error states."""
    res_page = client.get("/v39-deferred-tax-and-risk")
    assert res_page.status_code == 401
    
    res_api = client.get("/api/v39/deferred-tax")
    assert res_api.status_code == 401
