"""Tests for the public free-tool routes (no auth required).

Verifies:
- Public pages render without login
- Penalty API accepts valid inputs and returns correct structure
- Input validation rejects invalid data
- Penalty math matches expected Decree 125/2020 rules
"""

from __future__ import annotations

import json
import pytest

from app import create_app


@pytest.fixture()
def client():
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as c:
        yield c


# ────────────────────────────────────────────────────────────────
# Page rendering (public, no login)
# ────────────────────────────────────────────────────────────────

class TestPublicPages:
    """Public tool pages should be accessible without login."""

    def test_tools_index_renders(self, client):
        rv = client.get("/tools/")
        assert rv.status_code == 200
        assert "Công Cụ Thuế Miễn Phí" in rv.data.decode("utf-8")

    def test_penalty_calculator_page_renders(self, client):
        rv = client.get("/tools/tax-penalty-calculator")
        assert rv.status_code == 200
        html = rv.data.decode("utf-8")
        assert "Nghị định 125/2020" in html
        assert "Tính Phạt Chậm Nộp Thuế" in html

    def test_penalty_page_has_seo_meta(self, client):
        rv = client.get("/tools/tax-penalty-calculator")
        html = rv.data.decode("utf-8")
        assert "application/ld+json" in html
        assert "FinanceApplication" in html

    def test_tools_page_no_redirect_to_login(self, client):
        """Public pages must NOT redirect to login."""
        rv = client.get("/tools/", follow_redirects=False)
        assert rv.status_code == 200  # Not 302


# ────────────────────────────────────────────────────────────────
# Penalty API calculation
# ────────────────────────────────────────────────────────────────

class TestPenaltyAPI:
    """Tax penalty calculator API (public, no auth)."""

    def _post(self, client, data):
        return client.post(
            "/tools/api/penalty-calculate",
            data=json.dumps(data),
            content_type="application/json",
        )

    def test_basic_underdeclaration(self, client):
        """20% fine + 0.03%/day interest on 100M VND, 90 days late."""
        rv = self._post(client, {
            "underpaid_tax": 100_000_000,
            "due_date": "2026-01-01",
            "payment_date": "2026-04-01",
            "evasion_multiplier": 0.0,
            "has_mitigating_factors": False,
        })
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["status"] == "success"
        c = data["calculation"]
        assert c["late_days"] == 90
        assert c["under_declaration_fine"] == 20_000_000  # 20% of 100M
        assert c["late_interest"] == 2_700_000  # 100M * 0.0003 * 90
        assert c["evasion_fine"] == 0
        assert c["total_penalties"] == 22_700_000
        assert c["total_liability"] == 122_700_000

    def test_evasion_penalty(self, client):
        """Evasion at 2x multiplier should produce evasion_fine = 2 * tax."""
        rv = self._post(client, {
            "underpaid_tax": 50_000_000,
            "due_date": "2026-03-01",
            "payment_date": "2026-06-01",
            "evasion_multiplier": 2.0,
            "has_mitigating_factors": False,
        })
        data = rv.get_json()
        c = data["calculation"]
        # When evasion_multiplier > 0, under_declaration_fine = 0
        assert c["under_declaration_fine"] == 0
        assert c["evasion_fine"] == 100_000_000  # 2x * 50M
        assert c["late_days"] == 92

    def test_mitigating_factors_reduce_fines(self, client):
        """Mitigating factors should reduce fines by 20%."""
        rv = self._post(client, {
            "underpaid_tax": 100_000_000,
            "due_date": "2026-01-01",
            "payment_date": "2026-04-01",
            "evasion_multiplier": 0.0,
            "has_mitigating_factors": True,
        })
        c = rv.get_json()["calculation"]
        # 20% of 100M = 20M, reduced 20% = 16M
        assert c["under_declaration_fine"] == 16_000_000
        # Late interest is NOT reduced by mitigating factors
        assert c["late_interest"] == 2_700_000

    def test_zero_late_days(self, client):
        """Payment on due date should have 0 late days and 0 interest."""
        rv = self._post(client, {
            "underpaid_tax": 200_000_000,
            "due_date": "2026-06-01",
            "payment_date": "2026-06-01",
        })
        c = rv.get_json()["calculation"]
        assert c["late_days"] == 0
        assert c["late_interest"] == 0

    def test_early_payment(self, client):
        """Payment before due date should also have 0 late days."""
        rv = self._post(client, {
            "underpaid_tax": 100_000_000,
            "due_date": "2026-06-15",
            "payment_date": "2026-06-01",
        })
        c = rv.get_json()["calculation"]
        assert c["late_days"] == 0
        assert c["late_interest"] == 0

    # ── Validation ──

    def test_reject_zero_tax(self, client):
        rv = self._post(client, {
            "underpaid_tax": 0,
            "due_date": "2026-01-01",
            "payment_date": "2026-04-01",
        })
        assert rv.status_code == 400
        assert "error" in rv.get_json()

    def test_reject_missing_dates(self, client):
        rv = self._post(client, {
            "underpaid_tax": 100_000_000,
            "due_date": "",
            "payment_date": "",
        })
        assert rv.status_code == 400

    def test_reject_negative_tax(self, client):
        rv = self._post(client, {
            "underpaid_tax": -500_000,
            "due_date": "2026-01-01",
            "payment_date": "2026-04-01",
        })
        assert rv.status_code == 400

    def test_has_decree_reference(self, client):
        """Result should cite the legal basis."""
        rv = self._post(client, {
            "underpaid_tax": 100_000_000,
            "due_date": "2026-01-01",
            "payment_date": "2026-04-01",
        })
        c = rv.get_json()["calculation"]
        assert "125/2020" in c["decree_reference"]


class TestFCTAPI:
    """FCT calculator API (public, no auth)."""

    def _post(self, client, data):
        return client.post(
            "/tools/api/fct-calculate",
            data=json.dumps(data),
            content_type="application/json",
        )

    def test_fct_calculator_page_renders(self, client):
        rv = client.get("/tools/fct-calculator")
        assert rv.status_code == 200
        html = rv.data.decode("utf-8")
        assert "Tính Thuế Nhà Thầu" in html
        assert "Thông tư 103/2014" in html

    def test_fct_calculation_net(self, client):
        """Test FCT calculation for Net contract (gross-up)."""
        rv = self._post(client, {
            "contract_value": 100_000_000,
            "contract_type": "net",
            "industry_type": "services"
        })
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["status"] == "success"
        c = data["calculation"]
        assert c["contract_value"] == 100_000_000
        assert c["cit_rate"] == 0.05
        assert c["vat_rate"] == 0.05
        assert c["cit_revenue"] == 105_263_158.0
        assert c["gross_revenue"] == 110_803_324.0
        assert c["fct_cit"] == 5_263_158.0
        assert c["fct_vat"] == 5_540_166.0
        assert c["total_fct"] == 10_803_324.0
        assert c["net_value"] == 100_000_000.0

    def test_fct_calculation_gross(self, client):
        """Test FCT calculation for Gross contract."""
        rv = self._post(client, {
            "contract_value": 100_000_000,
            "contract_type": "gross",
            "industry_type": "services"
        })
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["status"] == "success"
        c = data["calculation"]
        assert c["contract_value"] == 100_000_000
        assert c["gross_revenue"] == 100_000_000.0
        assert c["fct_vat"] == 5_000_000.0  # 5% of 100M
        assert c["cit_revenue"] == 95_000_000.0  # 100M - 5M
        assert c["fct_cit"] == 4_750_000.0  # 5% of 95M
        assert c["total_fct"] == 9_750_000.0
        assert c["net_value"] == 90_250_000.0

    def test_fct_validation_reject_invalid_inputs(self, client):
        # zero contract value
        rv = self._post(client, {
            "contract_value": 0,
            "contract_type": "net",
            "industry_type": "services"
        })
        assert rv.status_code == 400

        # negative contract value
        rv = self._post(client, {
            "contract_value": -5000,
            "contract_type": "net",
            "industry_type": "services"
        })
        assert rv.status_code == 400

        # invalid contract type
        rv = self._post(client, {
            "contract_value": 100000,
            "contract_type": "invalid",
            "industry_type": "services"
        })
        assert rv.status_code == 400

        # invalid industry type
        rv = self._post(client, {
            "contract_value": 100000,
            "contract_type": "net",
            "industry_type": "invalid_industry"
        })
        assert rv.status_code == 400

