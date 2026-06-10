"""
Tests for V33 features: CIT Quarterly Provisional Declaration Engine,
Form 01A/TNDN XML Builder, Tax Compliance Calendar, and CIT Optimization Swarm.
US-450 & US-451.
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
            sess["taxpayer_mst"] = "0109999999"
        yield c


# ── US-450: CIT Quarterly Calculation Engine ────────────────────────────────────

class TestCITQuarterlyEngine:
    def test_basic_cit_calculation(self):
        from invoices.v33_service import calculate_cit_quarterly
        result = calculate_cit_quarterly(
            "0109999999", quarter=1, year=2026,
            revenue=5_000_000_000, cogs=3_000_000_000,
            operating_expenses=800_000_000,
        )
        assert result["status"] == "calculated"
        assert result["gross_profit"] == 2_000_000_000
        assert result["operating_income"] == 1_200_000_000
        assert result["taxable_income"] == 1_200_000_000
        assert result["cit_rate"] == 0.20
        assert result["cit_payable"] == 240_000_000

    def test_preferential_rate(self):
        from invoices.v33_service import calculate_cit_quarterly
        result = calculate_cit_quarterly(
            "0109999999", quarter=2, year=2026,
            revenue=2_000_000_000, cogs=1_000_000_000,
            operating_expenses=500_000_000,
            preferential_rate=0.10,
        )
        assert result["cit_rate"] == 0.10
        assert result["cit_payable"] == 50_000_000

    def test_loss_carry_forward(self):
        from invoices.v33_service import calculate_cit_quarterly
        result = calculate_cit_quarterly(
            "0109999999", quarter=3, year=2026,
            revenue=1_000_000_000, cogs=600_000_000,
            operating_expenses=200_000_000,
            carry_forward_loss=100_000_000,
        )
        assert result["carry_forward_loss_applied"] == 100_000_000
        assert result["taxable_income"] == 100_000_000
        assert result["cit_payable"] == 20_000_000

    def test_negative_income_zero_tax(self):
        from invoices.v33_service import calculate_cit_quarterly
        result = calculate_cit_quarterly(
            "0109999999", quarter=4, year=2026,
            revenue=500_000_000, cogs=400_000_000,
            operating_expenses=200_000_000,
        )
        assert result["taxable_income"] == 0
        assert result["cit_payable"] == 0

    def test_quarterly_deadline(self):
        from invoices.v33_service import calculate_cit_quarterly
        r1 = calculate_cit_quarterly("X", 1, 2026, 1e9, 5e8, 2e8)
        assert r1["filing_deadline"] == "2026-04-30"
        r2 = calculate_cit_quarterly("X", 4, 2026, 1e9, 5e8, 2e8)
        assert r2["filing_deadline"] == "2027-01-31"

    def test_other_income_and_expenses(self):
        from invoices.v33_service import calculate_cit_quarterly
        result = calculate_cit_quarterly(
            "0109999999", quarter=1, year=2026,
            revenue=1_000_000_000, cogs=500_000_000,
            operating_expenses=200_000_000,
            other_income=50_000_000, other_expenses=30_000_000,
        )
        assert result["pre_tax_income"] == 320_000_000
        assert result["cit_payable"] == 64_000_000


# ── US-450: Form 01A/TNDN XML Builder ──────────────────────────────────────────

class TestForm01ATNDN:
    def test_xml_generation(self):
        from invoices.v33_service import build_form01a_tndn_xml
        result = build_form01a_tndn_xml(
            "0109999999", "Công ty TNHH Test", 1, 2026,
            5_000_000_000, 3_000_000_000, 800_000_000,
        )
        assert result["status"] == "success"
        assert result["form_type"] == "01A/TNDN"
        assert "<HSoThueDTu>" in result["xml_content"]
        assert "<MNT>01A/TNDN</MNT>" in result["xml_content"]
        assert "0109999999" in result["xml_content"]
        assert "Q1/2026" in result["xml_content"]

    def test_xml_contains_tax_values(self):
        from invoices.v33_service import build_form01a_tndn_xml
        result = build_form01a_tndn_xml(
            "0109999999", "Test Corp", 2, 2026,
            2_000_000_000, 1_000_000_000, 500_000_000,
        )
        xml = result["xml_content"]
        assert "ct26" in xml  # taxable income field
        assert "ct28" in xml  # CIT payable field
        assert result["calculation"]["cit_payable"] == 100_000_000


# ── US-451: Tax Compliance Calendar ─────────────────────────────────────────────

class TestTaxComplianceCalendar:
    def test_calendar_structure(self):
        from invoices.v33_service import get_tax_compliance_calendar
        cal = get_tax_compliance_calendar(2026)
        assert cal["year"] == 2026
        assert len(cal["months"]) == 12

    def test_calendar_deadlines_exist(self):
        from invoices.v33_service import get_tax_compliance_calendar
        cal = get_tax_compliance_calendar(2026)
        jan = cal["months"][0]
        assert jan["month"] == 1
        assert jan["month_name"] == "Tháng 1"
        assert len(jan["deadlines"]) >= 1
        codes = [d["code"] for d in jan["deadlines"]]
        assert "CIT-Q4" in codes

    def test_calendar_deadline_status(self):
        from invoices.v33_service import get_tax_compliance_calendar
        cal = get_tax_compliance_calendar(2026)
        for month_entry in cal["months"]:
            for dl in month_entry["deadlines"]:
                assert dl["status"] in ("filed", "upcoming", "pending")
                assert "date" in dl
                assert "type" in dl

    def test_calendar_all_types_present(self):
        from invoices.v33_service import get_tax_compliance_calendar
        cal = get_tax_compliance_calendar(2026)
        all_types = set()
        for m in cal["months"]:
            for d in m["deadlines"]:
                all_types.add(d["type"])
        assert "VAT" in all_types
        assert "CIT" in all_types
        assert "PIT" in all_types


# ── US-451: CIT Optimization Swarm ──────────────────────────────────────────────

class TestCITOptimizationSwarm:
    def test_swarm_returns_chat_steps(self):
        from invoices.v33_service import run_cit_optimization_swarm
        result = run_cit_optimization_swarm(
            "0109999999", "Công ty Test", 1, 2026,
            5_000_000_000, 3_000_000_000, 800_000_000,
        )
        assert result["status"] == "success"
        assert len(result["chat_steps"]) >= 3
        assert "report_markdown" in result
        assert "calculation" in result

    def test_swarm_report_content(self):
        from invoices.v33_service import run_cit_optimization_swarm
        result = run_cit_optimization_swarm(
            "0109999999", "Test Corp", 2, 2026,
            2_000_000_000, 1_000_000_000, 500_000_000,
        )
        assert "THUẾ TNDN" in result["report_markdown"]
        assert "Quý 2/2026" in result["report_markdown"]


# ── API Route Tests ─────────────────────────────────────────────────────────────

class TestV33Routes:
    def test_v33_compliance_page(self, client):
        resp = client.get("/v33-compliance")
        assert resp.status_code == 200

    def test_api_cit_quarterly(self, client):
        resp = client.post("/api/compliance/cit-quarterly", json={
            "quarter": 1, "year": 2026,
            "revenue": 5000000000, "cogs": 3000000000,
            "operating_expenses": 800000000,
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "calculated"
        assert data["cit_payable"] == 240000000

    def test_api_form01a_xml(self, client):
        resp = client.post("/api/compliance/form01a-tndn-xml", json={
            "taxpayer_name": "Test Corp",
            "quarter": 1, "year": 2026,
            "revenue": 5000000000, "cogs": 3000000000,
            "operating_expenses": 800000000,
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert "<HSoThueDTu>" in data["xml_content"]

    def test_api_tax_calendar(self, client):
        resp = client.get("/api/compliance/tax-calendar?year=2026")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["year"] == 2026
        assert len(data["months"]) == 12

    def test_api_swarm_v33_chat(self, client):
        resp = client.post("/api/agents/swarm-v33-chat", json={
            "taxpayer_name": "Test Corp",
            "quarter": 1, "year": 2026,
            "revenue": 5000000000, "cogs": 3000000000,
            "operating_expenses": 800000000,
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert len(data["chat_steps"]) >= 3
