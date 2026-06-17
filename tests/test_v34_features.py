"""
Tests for V34: Invoice Aging Analysis & AR/AP Management.
US-460 & US-461.
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


class TestAgingClassification:
    def test_classify_current(self):
        from invoices.v34_service import _classify_aging
        assert _classify_aging(0) == "current"
        assert _classify_aging(-5) == "current"

    def test_classify_buckets(self):
        from invoices.v34_service import _classify_aging
        assert _classify_aging(15) == "1_30"
        assert _classify_aging(30) == "1_30"
        assert _classify_aging(45) == "31_60"
        assert _classify_aging(60) == "31_60"
        assert _classify_aging(75) == "61_90"
        assert _classify_aging(90) == "61_90"
        assert _classify_aging(91) == "90_plus"
        assert _classify_aging(200) == "90_plus"


class TestInvoiceAgingEngine:
    def test_aging_analysis_structure(self):
        from invoices.v34_service import analyze_invoice_aging
        result = analyze_invoice_aging("0109999999", "2026-06-10")
        assert result["status"] == "analyzed"
        assert result["taxpayer_mst"] == "0109999999"
        assert "accounts_receivable" in result
        assert "accounts_payable" in result

    def test_aging_buckets_complete(self):
        from invoices.v34_service import analyze_invoice_aging
        result = analyze_invoice_aging("0109999999", "2026-06-10")
        ar = result["accounts_receivable"]
        assert "current" in ar["buckets"]
        assert "1_30" in ar["buckets"]
        assert "31_60" in ar["buckets"]
        assert "61_90" in ar["buckets"]
        assert "90_plus" in ar["buckets"]

    def test_aging_totals_consistent(self):
        from invoices.v34_service import analyze_invoice_aging
        result = analyze_invoice_aging("0109999999", "2026-06-10")
        ar = result["accounts_receivable"]
        bucket_sum = sum(b["total"] for b in ar["buckets"].values())
        assert abs(bucket_sum - ar["total_outstanding"]) < 1.0

    def test_overdue_percentage(self):
        from invoices.v34_service import analyze_invoice_aging
        result = analyze_invoice_aging("0109999999", "2026-06-10")
        ar = result["accounts_receivable"]
        assert 0 <= ar["overdue_pct"] <= 100

    def test_default_as_of_date(self):
        from invoices.v34_service import analyze_invoice_aging
        result = analyze_invoice_aging("0109999999")
        assert result["status"] == "analyzed"
        assert result["as_of_date"] is not None


class TestHeatmapData:
    def test_heatmap_structure(self):
        from invoices.v34_service import analyze_invoice_aging, generate_aging_heatmap_data
        aging = analyze_invoice_aging("0109999999", "2026-06-10")
        heatmap = generate_aging_heatmap_data(aging)
        assert len(heatmap["sections"]) == 2
        assert heatmap["sections"][0]["key"] == "accounts_receivable"
        assert heatmap["sections"][1]["key"] == "accounts_payable"

    def test_heatmap_cells(self):
        from invoices.v34_service import analyze_invoice_aging, generate_aging_heatmap_data
        aging = analyze_invoice_aging("0109999999", "2026-06-10")
        heatmap = generate_aging_heatmap_data(aging)
        for section in heatmap["sections"]:
            assert len(section["cells"]) == 5
            for cell in section["cells"]:
                assert "bucket" in cell
                assert "color" in cell
                assert "percentage" in cell
                assert 0 <= cell["intensity"] <= 1.0


class TestAgingSwarm:
    def test_swarm_structure(self):
        from invoices.v34_service import run_aging_advisory_swarm
        result = run_aging_advisory_swarm("0109999999", "Công ty Test")
        assert result["status"] == "success"
        assert len(result["chat_steps"]) >= 3
        assert "report_markdown" in result
        assert "aging" in result

    def test_swarm_report_content(self):
        from invoices.v34_service import run_aging_advisory_swarm
        result = run_aging_advisory_swarm("0109999999", "Test Corp")
        assert "TUỔI NỢ" in result["report_markdown"]
        assert "PHẢI THU" in result["report_markdown"]
        assert "PHẢI TRẢ" in result["report_markdown"]


class TestV34Routes:
    def test_v34_page(self, client):
        resp = client.get("/v34-compliance")
        assert resp.status_code == 200

    def test_api_aging_analysis(self, client):
        resp = client.post("/api/compliance/invoice-aging", json={
            "as_of_date": "2026-06-10"
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "analyzed"

    def test_api_aging_heatmap(self, client):
        resp = client.post("/api/compliance/aging-heatmap", json={
            "as_of_date": "2026-06-10"
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["sections"]) == 2

    def test_api_swarm_v34(self, client):
        resp = client.post("/api/agents/swarm-v34-chat", json={
            "taxpayer_name": "Test Corp"
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert len(data["chat_steps"]) >= 3
