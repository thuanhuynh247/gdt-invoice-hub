import pytest
from extensions import db
from invoices.models import Invoice, Partner, BlacklistedMST, LineItem, AIAuditResult
from invoices.supplier_risk_service import calculate_supplier_risk, get_all_suppliers_risk_radar

def test_supplier_risk_scoring_basic_and_blacklist(app):
    """Verify standard scoring and absolute blacklist F rating."""
    with app.app_context():
        # Clear existing
        Invoice.query.delete()
        Partner.query.delete()
        BlacklistedMST.query.delete()
        db.session.commit()

        seller_mst = "1111111111"
        taxpayer_mst = "9999999999"

        # 1. No invoices, normal supplier
        partner = Partner(mst=seller_mst, name="Test Supplier A", mst_status="Đang hoạt động (đã được cấp MST)")
        db.session.add(partner)
        db.session.commit()

        res = calculate_supplier_risk(seller_mst, taxpayer_mst)
        assert res["risk_score"] == 100
        assert res["trust_rating"] == "A++"
        assert len(res["flags"]) == 0

        # 2. Add to blacklist
        black = BlacklistedMST(mst=seller_mst, reason="Gian lận thuế")
        db.session.add(black)
        db.session.commit()

        res = calculate_supplier_risk(seller_mst, taxpayer_mst)
        assert res["risk_score"] == 0
        assert res["trust_rating"] == "F"
        assert "BLACKLISTED" in res["flags"]

        # Cleanup
        db.session.delete(black)
        db.session.delete(partner)
        db.session.commit()


def test_supplier_risk_volume_spikes(app):
    """Verify volume spike penalties for new and historical suppliers."""
    with app.app_context():
        Invoice.query.delete()
        Partner.query.delete()
        db.session.commit()

        seller_mst = "2222222222"
        taxpayer_mst = "9999999999"

        partner = Partner(mst=seller_mst, name="Test Supplier B", mst_status="Đang hoạt động (đã được cấp MST)")
        db.session.add(partner)

        # A. New supplier volume spike (> 500 million in one month)
        inv = Invoice(
            id="inv-new-spike",
            seller_mst=seller_mst,
            seller_name="Test Supplier B",
            taxpayer_mst=taxpayer_mst,
            total_amount=600000000.0,
            date="2026-05-10",
            has_signature=True,
            signing_date="2026-05-10",
            imported_at="2026-05-26"
        )
        db.session.add(inv)
        db.session.commit()

        res = calculate_supplier_risk(seller_mst, taxpayer_mst)
        assert "VOLUME_SPIKE" in res["flags"]
        assert res["risk_score"] == 80  # 100 - 20 = 80

        # B. Historical supplier volume spike (>3x of monthly average)
        Invoice.query.delete()
        db.session.commit()

        # Month 1: 10M, Month 2: 10M, Month 3: 10M, Month 4: 100M (Spike!)
        invoices = [
            Invoice(id="inv-h1", seller_mst=seller_mst, taxpayer_mst=taxpayer_mst, total_amount=10000000.0, date="2026-01-10", imported_at="2026-05-26"),
            Invoice(id="inv-h2", seller_mst=seller_mst, taxpayer_mst=taxpayer_mst, total_amount=10000000.0, date="2026-02-10", imported_at="2026-05-26"),
            Invoice(id="inv-h3", seller_mst=seller_mst, taxpayer_mst=taxpayer_mst, total_amount=10000000.0, date="2026-03-10", imported_at="2026-05-26"),
            Invoice(id="inv-h4", seller_mst=seller_mst, taxpayer_mst=taxpayer_mst, total_amount=100000000.0, date="2026-04-10", imported_at="2026-05-26")
        ]
        for idx, i in enumerate(invoices):
            # add signature details to avoid late signature penalty
            i.has_signature = True
            i.signing_date = i.date
            db.session.add(i)
        db.session.commit()

        res = calculate_supplier_risk(seller_mst, taxpayer_mst)
        assert "VOLUME_SPIKE" in res["flags"]
        assert res["risk_score"] == 80  # 100 - 20 = 80

        # Cleanup
        Invoice.query.delete()
        Partner.query.delete()
        db.session.commit()


def test_supplier_risk_late_digital_signing(app):
    """Verify late digital signing penalty is triggered correctly (> 20% of invoices are > 3 days late)."""
    with app.app_context():
        Invoice.query.delete()
        Partner.query.delete()
        db.session.commit()

        seller_mst = "3333333333"
        taxpayer_mst = "9999999999"

        partner = Partner(mst=seller_mst, name="Test Supplier C", mst_status="Đang hoạt động (đã được cấp MST)")
        db.session.add(partner)

        # 5 invoices total: 2 signed late (40% > 20% threshold)
        for i in range(3):
            inv = Invoice(
                id=f"inv-ok-{i}",
                seller_mst=seller_mst,
                taxpayer_mst=taxpayer_mst,
                total_amount=5000000.0,
                date="2026-05-10",
                has_signature=True,
                signing_date="2026-05-11",  # 1 day late
                imported_at="2026-05-26"
            )
            db.session.add(inv)

        for i in range(2):
            inv = Invoice(
                id=f"inv-late-{i}",
                seller_mst=seller_mst,
                taxpayer_mst=taxpayer_mst,
                total_amount=5000000.0,
                date="2026-05-10",
                has_signature=True,
                signing_date="2026-05-20",  # 10 days late!
                imported_at="2026-05-26"
            )
            db.session.add(inv)
        db.session.commit()

        res = calculate_supplier_risk(seller_mst, taxpayer_mst)
        assert "LATE_SIGNING" in res["flags"]
        assert res["risk_score"] == 85  # 100 - 15 = 85

        # Cleanup
        Invoice.query.delete()
        Partner.query.delete()
        db.session.commit()


def test_supplier_risk_cash_splitting(app):
    """Verify cash-splitting threshold detection penalty (>= 2 cash invoices in one month in [19M, 19.99M])."""
    with app.app_context():
        Invoice.query.delete()
        Partner.query.delete()
        db.session.commit()

        seller_mst = "4444444444"
        taxpayer_mst = "9999999999"

        partner = Partner(mst=seller_mst, name="Test Supplier D", mst_status="Đang hoạt động (đã được cấp MST)")
        db.session.add(partner)

        # 2 cash invoices just under 20M limit in the same month
        inv1 = Invoice(
            id="inv-split-1",
            seller_mst=seller_mst,
            taxpayer_mst=taxpayer_mst,
            total_amount=19500000.0,
            date="2026-05-10",
            payment_method="Tiền mặt",
            has_signature=True,
            signing_date="2026-05-10",
            imported_at="2026-05-26"
        )
        inv2 = Invoice(
            id="inv-split-2",
            seller_mst=seller_mst,
            taxpayer_mst=taxpayer_mst,
            total_amount=19800000.0,
            date="2026-05-15",
            payment_method="Tiền mặt",
            has_signature=True,
            signing_date="2026-05-15",
            imported_at="2026-05-26"
        )
        db.session.add(inv1)
        db.session.add(inv2)
        db.session.commit()

        res = calculate_supplier_risk(seller_mst, taxpayer_mst)
        assert "CASH_SPLITTING" in res["flags"]
        assert res["risk_score"] == 85  # 100 - 15 = 85

        # Cleanup
        Invoice.query.delete()
        Partner.query.delete()
        db.session.commit()


def test_supplier_risk_suspicious_items(app):
    """Verify keyword audit of suspicious advisory/management consulting line items."""
    with app.app_context():
        Invoice.query.delete()
        Partner.query.delete()
        db.session.commit()

        seller_mst = "5555555555"
        taxpayer_mst = "9999999999"

        partner = Partner(mst=seller_mst, name="Test Supplier E", mst_status="Đang hoạt động (đã được cấp MST)")
        db.session.add(partner)

        inv = Invoice(
            id="inv-suspicious",
            seller_mst=seller_mst,
            taxpayer_mst=taxpayer_mst,
            total_amount=60000000.0,
            date="2026-05-10",
            has_signature=True,
            signing_date="2026-05-10",
            imported_at="2026-05-26"
        )
        db.session.add(inv)
        db.session.flush()

        item = LineItem(
            invoice_id="inv-suspicious",
            item_name="Dịch vụ tư vấn quản lý doanh nghiệp chuyên sâu",
            quantity=1,
            unit_price=50000000.0,
            amount_before_tax=50000000.0
        )
        db.session.add(item)
        db.session.commit()

        res = calculate_supplier_risk(seller_mst, taxpayer_mst)
        assert "SUSPICIOUS_ITEMS" in res["flags"]
        assert res["risk_score"] == 85  # 100 - 15 = 85

        # Cleanup
        Invoice.query.delete()
        Partner.query.delete()
        db.session.commit()


def test_api_tax_risk_scoreboard_endpoint(logged_in_client, app):
    """Verify that calling the /api/reports/tax-risk-scoreboard endpoint returns rich analytics."""
    with app.app_context():
        Invoice.query.delete()
        Partner.query.delete()
        BlacklistedMST.query.delete()
        db.session.commit()

        # Add blacklisted MST
        black = BlacklistedMST(mst="8888888888", reason="Gian lận mua bán hóa đơn")
        db.session.add(black)
        
        # Add high-risk supplier with invoices
        seller_mst = "7777777777"
        partner = Partner(mst=seller_mst, name="Supplier High Risk Ltd", mst_status="Đang hoạt động (đã được cấp MST)")
        db.session.add(partner)

        # 2 cash invoices of 19.5M in the same month (triggers CASH_SPLITTING)
        for i in range(2):
            inv = Invoice(
                id=f"inv-end-{i}",
                seller_mst=seller_mst,
                seller_name="Supplier High Risk Ltd",
                taxpayer_mst="0309876543",  # Mock active taxpayer profile MST
                total_amount=19500000.0,
                date="2026-05-10",
                payment_method="Tiền mặt",
                has_signature=True,
                signing_date="2026-05-10",
                imported_at="2026-05-26"
            )
            db.session.add(inv)
        db.session.commit()

    # Session mock active taxpayer profile
    with logged_in_client.session_transaction() as sess:
        sess["taxpayer_mst"] = "0309876543"

    response = logged_in_client.get("/api/reports/tax-risk-scoreboard")
    assert response.status_code == 200
    data = response.json

    assert data["status"] == "success"
    assert "summary" in data
    assert "suppliers" in data
    
    # We should have at least 2 suppliers returned (one blacklisted, one high risk due to cash splitting)
    suppliers = data["suppliers"]
    assert len(suppliers) >= 2
    
    # Verify values mapped
    m_types = [s["supplier_mst"] for s in suppliers]
    assert "8888888888" in m_types
    assert "7777777777" in m_types

    # Cleanup
    with app.app_context():
        Invoice.query.delete()
        Partner.query.delete()
        BlacklistedMST.query.delete()
        db.session.commit()


def test_api_supplier_risk_radar_endpoints(logged_in_client, app):
    """Verify that calling the supplier-risk-radar endpoints works as specified by US-212."""
    with app.app_context():
        Invoice.query.delete()
        Partner.query.delete()
        BlacklistedMST.query.delete()
        db.session.commit()

        # Add mock partner and invoice
        seller_mst = "1212121212"
        partner = Partner(mst=seller_mst, name="Mock Supplier 12", mst_status="Đang hoạt động (đã được cấp MST)")
        db.session.add(partner)

        inv = Invoice(
            id="inv-mock-12",
            seller_mst=seller_mst,
            seller_name="Mock Supplier 12",
            taxpayer_mst="0309876543",
            total_amount=100000.0,
            date="2026-05-10",
            has_signature=True,
            signing_date="2026-05-10",
            imported_at="2026-05-26"
        )
        db.session.add(inv)
        db.session.commit()

    with logged_in_client.session_transaction() as sess:
        sess["taxpayer_mst"] = "0309876543"

    # 1. Test GET /api/reports/supplier-risk-radar
    response = logged_in_client.get("/api/reports/supplier-risk-radar")
    assert response.status_code == 200
    data = response.json
    assert data["status"] == "success"
    assert "summary" in data
    assert "suppliers" in data
    assert len(data["suppliers"]) >= 1
    assert data["suppliers"][0]["supplier_mst"] == "1212121212"
    assert data["suppliers"][0]["risk_score"] == 100

    # 2. Test POST /api/reports/supplier-risk-radar/blacklist
    response = logged_in_client.post("/api/reports/supplier-risk-radar/blacklist", json={
        "mst": "1212121212",
        "reason": "Hóa đơn ma"
    })
    assert response.status_code == 200
    assert response.json["status"] == "success"

    # Verify that the score drops to 0 after blacklisting
    response = logged_in_client.get("/api/reports/supplier-risk-radar")
    assert response.status_code == 200
    data = response.json
    assert data["suppliers"][0]["risk_score"] == 0
    assert data["suppliers"][0]["trust_rating"] == "F"

    # 3. Test DELETE /api/reports/supplier-risk-radar/blacklist/<mst>
    response = logged_in_client.delete("/api/reports/supplier-risk-radar/blacklist/1212121212")
    assert response.status_code == 200
    assert response.json["status"] == "success"

    # Verify score restores to 100 after removal
    response = logged_in_client.get("/api/reports/supplier-risk-radar")
    assert response.status_code == 200
    data = response.json
    assert data["suppliers"][0]["risk_score"] == 100
    assert data["suppliers"][0]["trust_rating"] == "A++"

    # Cleanup
    with app.app_context():
        Invoice.query.delete()
        Partner.query.delete()
        BlacklistedMST.query.delete()
        db.session.commit()


