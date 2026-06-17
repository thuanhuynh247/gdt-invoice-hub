import pytest
from app import create_app
from invoices.v29_service import check_ghost_company, generate_audit_mitigation_letter, get_tax_knowledge_graph

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

def test_ghost_company_checker():
    """Verify ghost company checker flags the blacklisted MSTs correctly and scores risks."""
    # Test safe/non-blacklisted
    res_safe = check_ghost_company("0109998887", "Công ty TNHH Giải pháp Ánh Sáng", 100000)
    assert res_safe["risk_score"] == 0
    assert res_safe["status"] == "Safe"
    
    # Test blacklisted MST (e.g. Khánh An)
    res_blacklisted = check_ghost_company("0316482931", "Công ty TNHH Thương mại Dịch vụ Khánh An", 50000000)
    assert res_blacklisted["risk_score"] >= 60
    assert res_blacklisted["status"] in ["Warning", "Critical"]
    assert any("Tổng cục Thuế" in f for f in res_blacklisted["flags"])

def test_audit_defense_letter_generation():
    """Verify that the mitigation/defense letter generator formats details properly."""
    letter = generate_audit_mitigation_letter(
        seller_mst="0316482931",
        seller_name="Công ty TNHH Khánh An",
        invoice_value=150000000,
        payment_method="Chuyển khoản liên ngân hàng 247"
    )
    assert "0316482931" in letter
    assert "Khánh An" in letter
    assert "150,000,000" in letter
    assert "Chuyển khoản liên ngân hàng 247" in letter

def test_tax_knowledge_graph_structure():
    """Verify the shape and node keys of the tax regulations knowledge graph."""
    graph = get_tax_knowledge_graph()
    assert "nodes" in graph
    assert "edges" in graph
    assert len(graph["nodes"]) > 0
    assert len(graph["edges"]) > 0
    # Confirm major tax nodes are present
    node_ids = [n["id"] for n in graph["nodes"]]
    assert "ND123" in node_ids
    assert "TT80" in node_ids
    assert "LQLT38" in node_ids

def test_api_compliance_ghost_check_endpoint(client):
    """Verify API POST /api/compliance/ghost-check return correct JSON."""
    response = client.post("/api/compliance/ghost-check", json={
        "seller_mst": "0316482931",
        "seller_name": "Công ty TNHH Khánh An",
        "invoice_value": 250000000
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data["mst"] == "0316482931"
    assert "risk_score" in data
    assert "status" in data

def test_api_compliance_defense_letter_endpoint(client):
    """Verify API POST /api/compliance/defense-letter returns the correct text block."""
    response = client.post("/api/compliance/defense-letter", json={
        "seller_mst": "0108924810",
        "seller_name": "Công ty Cổ phần Vật liệu Xây dựng Trường Thịnh",
        "invoice_value": 500000000,
        "payment_method": "Ủy nhiệm chi"
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "Trường Thịnh" in data["letter"]

def test_api_compliance_tax_knowledge_graph_endpoint(client):
    """Verify API GET /api/compliance/tax-knowledge-graph structure."""
    response = client.get("/api/compliance/tax-knowledge-graph")
    assert response.status_code == 200
    data = response.get_json()
    assert "nodes" in data
    assert "edges" in data

def test_api_agents_swarm_v29_chat_endpoint(client):
    """Verify API POST /api/agents/swarm-v29-chat returns simulated chat steps."""
    response = client.post("/api/agents/swarm-v29-chat", json={
        "seller_mst": "0316482931",
        "seller_name": "Khánh An",
        "invoice_value": 150000000
    })
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert "chat_steps" in data
    assert len(data["chat_steps"]) > 0
    assert "report_markdown" in data
