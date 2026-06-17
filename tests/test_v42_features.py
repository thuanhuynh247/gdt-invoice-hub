import pytest
from datetime import datetime
from extensions import db
from invoices.models import TransferPricingBenchmark, ECommercePlatformTransaction, ECommerceReconciliationReport, Invoice
from invoices.v42_service import AdvancedAuditService

@pytest.fixture(autouse=True)
def setup_test_data(app):
    with app.app_context():
        db.create_all()
        
        # Add a mock invoice for matching with Shopee/Lazada transactions
        inv = Invoice(
            id="0102030405-SP-998101",
            filename="inv_shopee.xml",
            invoice_type="sale",
            template_code="01GTKT",
            symbol="SP/26E",
            number="998101",
            date="2026-06-11",
            seller_mst="0102030405",
            seller_name="Viet taxpayer corp",
            buyer_mst="0908070605",
            buyer_name="Nguyễn Văn A",
            total_amount=250000000.0,  # 250M VND
            payment_method="Chuyển khoản",
            taxpayer_mst="0102030405",
            imported_at="2026-06-11 00:00:00"
        )
        db.session.add(inv)
        db.session.commit()
        
        yield
        
        db.session.remove()
        db.drop_all()


def test_transfer_pricing_benchmarks(client):
    """US-540: Verify benchmarking adjustments logic."""
    txns = [
        {"transaction_type": "Sale", "amount": 1000000000.0, "taxpayer_margin": 0.035},  # Less than p25 (0.045) -> Adjusted
        {"transaction_type": "Loan", "amount": 500000000.0, "taxpayer_margin": 0.060}    # Less than p75 (0.075) -> Compliant
    ]

    res = AdvancedAuditService.calculate_transfer_pricing_benchmarks("0102030405", txns)
    
    assert res["total_cit_adjustment"] > 0.0
    items = res["items"]
    assert len(items) == 2
    
    # Check adjustment calculation details
    sale_item = next(x for x in items if x["transaction_type"] == "Sale")
    assert sale_item["status"] == "Adjusted"
    # Adjusted adjustment = (median - margin) * amount = (0.065 - 0.035) * 10^9 = 0.03 * 10^9 = 30,000,000
    assert sale_item["adjustment_amount"] == 30000000.0

    loan_item = next(x for x in items if x["transaction_type"] == "Loan")
    assert loan_item["status"] == "Compliant"
    assert loan_item["adjustment_amount"] == 0.0


def test_form_01_132_xml_generation(client):
    """US-541: Verify Decree 132 XML creation."""
    tp_data = [
        {
            "transaction_type": "Sale",
            "method_used": "TNMM",
            "taxpayer_margin": 0.035,
            "benchmark_p25": 0.045,
            "benchmark_median": 0.065,
            "benchmark_p75": 0.085,
            "adjustment_amount": 30000000.0,
            "status": "Adjusted"
        }
    ]
    xml_str = AdvancedAuditService.generate_form_01_132_xml("0102030405", "Viet Taxpayer Corp", 2026, tp_data)
    
    assert "<toaKhai01_132>" in xml_str
    assert "<mst>0102030405</mst>" in xml_str
    assert "<tongChiPhiDieuChinhTNDN>30000000.00</tongChiPhiDieuChinhTNDN>" in xml_str


def test_ecommerce_circular80_reconciliation(client):
    """US-542: Verify platform transaction matching with local sale invoices."""
    platform_txns = [
        {"transaction_id": "SP-998101", "platform_name": "Shopee", "transaction_date": "2026-06-11", "buyer_name": "Nguyễn Văn A", "amount": 250000000.0},
        {"transaction_id": "TK-772892", "platform_name": "TikTok Shop", "transaction_date": "2026-06-11", "buyer_name": "Trần Thị B", "amount": 120000000.0}
    ]

    res = AdvancedAuditService.reconcile_ecommerce_transactions("0102030405", platform_txns)
    
    report = res["report"]
    txns = res["transactions"]
    
    assert report["total_platform_transactions"] == 2
    assert report["matched_count"] == 1
    assert report["mismatch_count"] == 1
    assert report["gap_amount"] == 120000000.0  # TikTok txn is unmatched
    assert report["compliance_status"] == "GapsFound"
    
    shopee_txn = next(x for x in txns if x["platform_name"] == "Shopee")
    assert shopee_txn["invoice_matched_id"] is not None
    assert shopee_txn["vat_withheld"] == 2500000.0  # 1% VAT
    assert shopee_txn["pit_withheld"] == 1250000.0  # 0.5% PIT


def test_v42_routes(logged_in_client):
    """US-543: Verify endpoint availability and routing correctness."""
    # Test HTML view
    resp = logged_in_client.get("/v42-advanced-audit")
    assert resp.status_code == 200
    assert "Quyết toán thuế Nâng cao & Giao dịch liên kết v42".encode("utf-8") in resp.data

    # Test API calculate TP
    resp_calc = logged_in_client.post("/api/v42/transfer-pricing/calculate", json={
        "mst": "0102030405",
        "transactions": [{"transaction_type": "Sale", "amount": 5000000000, "taxpayer_margin": 0.035}]
    })
    assert resp_calc.status_code == 200
    assert resp_calc.get_json()["status"] == "success"

    # Test API export XML
    resp_xml = logged_in_client.post("/api/v42/transfer-pricing/export-xml", json={
        "mst": "0102030405",
        "taxpayer_name": "Test Company",
        "year": 2026,
        "tp_items": [{
            "transaction_type": "Sale",
            "method_used": "TNMM",
            "taxpayer_margin": 0.035,
            "benchmark_p25": 0.045,
            "benchmark_median": 0.065,
            "benchmark_p75": 0.085,
            "adjustment_amount": 150000000.0,
            "status": "Adjusted"
        }]
    })
    assert resp_xml.status_code == 200
    assert "xml_content" in resp_xml.get_json()

    # Test API reconcile E-commerce
    resp_eco = logged_in_client.post("/api/v42/ecommerce/reconcile", json={
        "mst": "0102030405",
        "transactions": [{"transaction_id": "SP-998101", "platform_name": "Shopee", "amount": 250000000}]
    })
    assert resp_eco.status_code == 200
    assert resp_eco.get_json()["status"] == "success"

    # Test API dashboard-data
    resp_dash = logged_in_client.get("/api/v42/dashboard-data?mst=0102030405")
    assert resp_dash.status_code == 200
    assert "debate" in resp_dash.get_json()
