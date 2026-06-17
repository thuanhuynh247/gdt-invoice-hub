import pytest
from app import create_app
from invoices.v30_service import (
    calculate_transfer_pricing_risk,
    generate_tp_audit_dossier,
    SwarmV30Advisor
)

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["logged_in"] = True
            sess["user_role"] = "admin"
            sess["taxpayer_mst"] = "0109998887"
        yield client

def test_transfer_pricing_engine_compliant():
    """Verify that a compliant markup inside the arm's length range is classified correctly."""
    # Manufacturing range is 8.0% - 16.5%. Let's test 12.0%.
    res = calculate_transfer_pricing_risk(markup_pct=12.0, cost_of_goods=1000000000.0, sector="manufacturing")
    assert res["status"] == "Compliant"
    assert res["risk_score"] == 0
    assert res["adjustment_needed"] == 0.0
    assert res["cit_underpaid"] == 0.0
    assert res["total_financial_impact"] == 0.0

def test_transfer_pricing_engine_underpriced():
    """Verify that an underpriced markup triggers adjustments, CIT underpayment, and penalty calculations."""
    # Manufacturing range p35 is 8.0%, median is 12.0%.
    # Test 5.0% markup which is underpriced.
    cogs = 1000000000.0 # 1 Billion VND
    res = calculate_transfer_pricing_risk(markup_pct=5.0, cost_of_goods=cogs, sector="manufacturing")
    
    assert res["status"] == "Under-priced Risk"
    assert res["risk_score"] > 0
    
    # Revenue at 5%: 1.05 Billion
    # Revenue adjusted to median (12%): 1.12 Billion
    # Adjustment: 70 Million
    assert res["adjustment_needed"] == pytest.approx(70000000.0)
    # CIT underpaid (20%): 14 Million
    assert res["cit_underpaid"] == pytest.approx(14000000.0)
    # Penalty (20% of CIT underpaid): 2.8 Million
    assert res["penalty"] == pytest.approx(28000000.0 * 0.1)
    # Late payment interest: 14 Million * 0.03% * 365 = 1533000
    assert res["late_interest"] == pytest.approx(14000000.0 * 0.0003 * 365)
    
    expected_total = res["cit_underpaid"] + res["penalty"] + res["late_interest"]
    assert res["total_financial_impact"] == pytest.approx(expected_total)

def test_transfer_pricing_engine_overpriced():
    """Verify that an overpriced markup above p75 sets the warning status but no penalty adjustment."""
    # Services p75 is 20.0%. Test 25.0%.
    res = calculate_transfer_pricing_risk(markup_pct=25.0, cost_of_goods=500000000.0, sector="services")
    assert res["status"] == "High-priced Risk"
    assert res["risk_score"] == 30
    assert res["adjustment_needed"] == 0.0

def test_tp_audit_dossier_generation():
    """Verify that the Transfer Pricing Dossier contains statutory references and numbers."""
    cogs = 1000000000.0
    risk_details = calculate_transfer_pricing_risk(markup_pct=5.0, cost_of_goods=cogs, sector="manufacturing")
    
    dossier = generate_tp_audit_dossier(
        taxpayer_name="Công ty TNHH Thành Công",
        taxpayer_mst="0108924810",
        sector="manufacturing",
        markup_pct=5.0,
        cost_of_goods=cogs,
        risk_details=risk_details
    )
    
    assert "HỒ SƠ CHUẨN BỊ THANH TRA GIÁ GIAO DỊCH LIÊN KẾT" in dossier
    assert "132/2020/NĐ-CP" in dossier
    assert "0108924810" in dossier
    assert "Thành Công" in dossier
    assert "Trung vị" in dossier
    assert "Phạt hành vi khai thiếu thuế" in dossier

def test_v30_compliance_page(client):
    """Verify the V30 compliance landing page loads successfully."""
    response = client.get("/v30-compliance")
    assert response.status_code == 200
    assert "Giao Dịch Liên Kết & Xác Định Giá Chuyển Nhượng" in response.data.decode("utf-8")


def test_api_compliance_transfer_pricing_check(client):
    """Verify the Transfer Pricing checker API endpoint."""
    response = client.post("/api/compliance/transfer-pricing-check", json={
        "sector": "services",
        "markup_pct": 8.0,
        "cost_of_goods": 2000000000.0
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "Under-priced Risk"
    assert data["p35"] == 10.0
    assert "total_financial_impact" in data

def test_api_agents_swarm_v30_chat(client):
    """Verify the multi-agent swarm discussion and dossier generation endpoint."""
    response = client.post("/api/agents/swarm-v30-chat", json={
        "taxpayer_mst": "0108924810",
        "taxpayer_name": "Công ty TNHH Thành Công",
        "sector": "distribution",
        "markup_pct": 5.0,
        "cost_of_goods": 1000000000.0
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert "chat_steps" in data
    assert len(data["chat_steps"]) > 0
    assert "dossier" in data
    assert "Thành Công" in data["dossier"]
