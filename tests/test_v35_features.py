"""
Tests for V35: Unified Audit Control Room & Tax Stress Simulator.
US-470, US-471, US-472, US-473, US-474, US-475.
"""

import os
import zipfile
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

@pytest.fixture(autouse=True)
def app_context():
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        yield

class TestTaxHealthScoreEngine:
    def test_health_score_calculation_range(self):
        from invoices.v35_service import calculate_tax_health_score
        result = calculate_tax_health_score("0109999999")
        assert 0 <= result["health_score"] <= 100
        assert "svg_tree" in result
        assert "errors" in result
        assert "critical" in result["errors"]
        assert "major" in result["errors"]
        assert "minor" in result["errors"]

    def test_svg_tree_structure(self):
        from invoices.v35_service import calculate_tax_health_score
        result = calculate_tax_health_score("0109999999")
        svg_tree = result["svg_tree"]
        assert "nodes" in svg_tree
        assert "edges" in svg_tree
        # Verify root node exists
        root_node = next((n for n in svg_tree["nodes"] if n["id"] == "root"), None)
        assert root_node is not None
        assert root_node["type"] == "root"

class TestTaxStressSimulator:
    def test_simulation_lenient(self):
        from invoices.v35_service import run_tax_stress_simulation
        res = run_tax_stress_simulation("0109999999", 1.0, "lenient")
        assert res["strictness"] == "lenient"
        assert "metrics" in res
        assert res["metrics"]["disallowed_vat"] >= 0

    def test_simulation_strict(self):
        from invoices.v35_service import run_tax_stress_simulation
        res = run_tax_stress_simulation("0109999999", 1.0, "strict")
        assert res["strictness"] == "strict"
        # Strict mode should disallow more or equal invoices compared to lenient
        res_lenient = run_tax_stress_simulation("0109999999", 1.0, "lenient")
        assert res["disallowed_count"] >= res_lenient["disallowed_count"]

class TestDefenseBriefcaseAndXml:
    def test_briefcase_zip_creation_and_contents(self):
        from invoices.v35_service import build_defense_briefcase
        zip_path = build_defense_briefcase("0109999999", [])
        
        # Verify file exists
        assert os.path.exists(zip_path)
        assert zipfile.is_zipfile(zip_path)
        
        # Inspect contents
        with zipfile.ZipFile(zip_path, 'r') as zf:
            namelist = zf.namelist()
            assert "audited_invoices_report.md" in namelist
            assert "disallowed_invoices_ledger.csv" in namelist
            assert "gdt_form_04_ss.xml" in namelist
            
            # Read and verify Form 04 XML root element
            xml_data = zf.read("gdt_form_04_ss.xml").decode('utf-8')
            assert "<HSoThueDTu" in xml_data
            assert "04/SS-HDDT" in xml_data

        # Cleanup test zip
        try:
            os.remove(zip_path)
        except OSError:
            pass

class TestV35SwarmChat:
    def test_swarm_discussion_timeline(self):
        from invoices.v35_service import run_v35_swarm
        steps = run_v35_swarm("0109999999")
        assert len(steps) >= 5
        for s in steps:
            assert "agent" in s
            assert "role" in s
            assert "message" in s
            assert "avatar_class" in s
            assert "timestamp" in s

class TestV35ComplianceRoutes:
    def test_compliance_page_route(self, client):
        resp = client.get("/v35-compliance")
        assert resp.status_code == 200

    def test_api_health_route(self, client):
        resp = client.post("/api/compliance/v35-health", json={"taxpayer_mst": "0109999999"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert "health_score" in data

    def test_api_stress_test_route(self, client):
        resp = client.post("/api/compliance/stress-test", json={
            "taxpayer_mst": "0109999999",
            "scan_rate": 0.8,
            "strictness": "strict"
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["strictness"] == "strict"
        assert "metrics" in data

    def test_api_defense_package_route(self, client):
        resp = client.post("/api/compliance/defense-package", json={
            "taxpayer_mst": "0109999999",
            "invoice_ids": []
        })
        assert resp.status_code == 200
        assert resp.mimetype == "application/zip"
        # Validate downloaded zip size
        assert len(resp.data) > 0

    def test_api_swarm_v35_chat_route(self, client):
        resp = client.post("/api/agents/swarm-v35-chat", json={"taxpayer_mst": "0109999999"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) >= 5
