import pytest
from app import create_app
from invoices.v31_service import (
    vat_reconciliation_multi_period,
    build_form01_gtgt_xml,
    run_vat_anomaly_swarm
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
            sess["taxpayer_mst"] = "0109999999"
        yield client

def test_vat_reconciliation_multi_period_balanced():
    """Verify that balanced multi-period VAT data returns compliant status."""
    periods = [
        {"period": "Q1/2026", "output_vat": 100000000.0, "input_vat": 80000000.0},
        {"period": "Q2/2026", "output_vat": 120000000.0, "input_vat": 90000000.0}
    ]
    res = vat_reconciliation_multi_period("0109999999", periods)
    assert res["taxpayer_mst"] == "0109999999"
    assert res["summary"]["total_output_vat"] == 220000000.0
    assert res["summary"]["total_input_vat"] == 170000000.0
    assert res["periods"][0]["payable"] == 20000000.0
    assert res["periods"][1]["payable"] == 30000000.0
    assert res["summary"]["total_payable"] == 50000000.0

def test_vat_reconciliation_multi_period_unbalanced():
    """Verify that unbalanced multi-period VAT data triggers warnings and alerts."""
    periods = [
        {"period": "Q1/2026", "output_vat": 100000000.0, "input_vat": 150000000.0}, # Carry forward
        {"period": "Q2/2026", "output_vat": 120000000.0, "input_vat": 50000000.0}
    ]
    res = vat_reconciliation_multi_period("0109999999", periods)
    assert res["periods"][0]["carry_forward"] == 50000000.0
    assert res["periods"][0]["payable"] == 0.0
    assert res["periods"][1]["payable"] == 20000000.0
    assert res["periods"][1]["carry_forward"] == 0.0

def test_build_form01_gtgt_xml():
    """Verify GDT-compliant Form 01/GTGT XML generator output."""
    res = build_form01_gtgt_xml(
        taxpayer_mst="0109999999",
        taxpayer_name="Công ty TNHH Ánh Sáng",
        period="Q1/2026",
        output_vat=200000000.0,
        input_vat=150000000.0,
        carry_forward_prev=10000000.0
    )
    assert res["status"] == "success"
    xml_str = res["xml"]
    assert "HSoKhaiThue" in xml_str
    assert "0109999999" in xml_str
    assert "Công ty TNHH Ánh Sáng" in xml_str
    assert "Q1/2026" in xml_str
    assert "<ThueGTGT>10000000.0</ThueGTGT>" in xml_str
    assert "<ThueGTGT>150000000.0</ThueGTGT>" in xml_str
    assert "<ThueGTGT>200000000.0</ThueGTGT>" in xml_str

def test_run_vat_anomaly_swarm():
    """Verify VAT anomaly swarm discussion logs and generated audit reports."""
    res = run_vat_anomaly_swarm("0109999999", "Công ty TNHH Ánh Sáng")
    assert "chat_steps" in res
    assert len(res["chat_steps"]) > 0
    assert "report_markdown" in res
    assert "123/2020/NĐ-CP" in res["report_markdown"]
    assert "0109999999" in res["report_markdown"]

def test_v31_compliance_page(client):
    """Verify that the V31 compliance dashboard page loads successfully."""
    response = client.get("/v31-compliance")
    assert response.status_code == 200
    assert "Kê Khai" in response.data.decode("utf-8")
    assert "Đối Chiếu Thuế GTGT Đa Kỳ" in response.data.decode("utf-8")

def test_api_compliance_vat_reconciliation(client):
    """Verify the multi-period VAT reconciliation endpoint."""
    response = client.post("/api/compliance/vat-reconciliation", json={
        "taxpayer_mst": "0109999999",
        "periods": [
            {"period": "Q1/2026", "output_vat": 150000000, "input_vat": 130000000}
        ]
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data["summary"]["total_output_vat"] == 150000000.0
    assert data["summary"]["total_input_vat"] == 130000000.0

def test_api_compliance_form01_gtgt_xml(client):
    """Verify Form 01/GTGT XML builder endpoint."""
    response = client.post("/api/compliance/form01-gtgt-xml", json={
        "taxpayer_mst": "0109999999",
        "taxpayer_name": "Công ty TNHH Ánh Sáng",
        "period": "Q1/2026",
        "output_vat": 150000000,
        "input_vat": 130000000,
        "carry_forward_prev": 10000000
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert "<ThueGTGT>130000000.0</ThueGTGT>" in data["xml"]

def test_api_agents_swarm_v31_chat(client):
    """Verify the AI Swarm compliance discussion endpoint."""
    response = client.post("/api/agents/swarm-v31-chat", json={
        "taxpayer_mst": "0109999999",
        "taxpayer_name": "Công ty TNHH Ánh Sáng"
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert "chat_steps" in data
    assert "report_markdown" in data
