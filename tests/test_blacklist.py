import pytest
from invoices.models import Invoice, BlacklistedMST
from invoices.service import recalculate_t_score_value, import_xml_invoice
from extensions import db

def test_blacklist_api_requires_login(client):
    """Verify that calling blacklist APIs without logging in returns 401."""
    # List
    response = client.get("/api/blacklist")
    assert response.status_code == 401

    # Add
    response = client.post("/api/blacklist", json={"mst": "0101234599", "reason": "Test"})
    assert response.status_code == 401

    # Delete
    response = client.delete("/api/blacklist/0101234599")
    assert response.status_code == 401


def test_blacklist_crud_lifecycle(logged_in_client, app):
    """Verify that admin/auditor can add, list, and delete from blacklist."""
    with app.app_context():
        # Clear existing
        BlacklistedMST.query.delete()
        db.session.commit()

    # 1. Add to blacklist
    response = logged_in_client.post("/api/blacklist", json={
        "mst": "1234567890",
        "reason": "Mua bán hóa đơn khống"
    })
    assert response.status_code == 200
    assert response.json["status"] == "success"

    # 2. List blacklist
    response = logged_in_client.get("/api/blacklist")
    assert response.status_code == 200
    data = response.json
    assert len(data) == 1
    assert data[0]["mst"] == "1234567890"
    assert data[0]["reason"] == "Mua bán hóa đơn khống"

    # 3. Delete from blacklist
    response = logged_in_client.delete("/api/blacklist/1234567890")
    assert response.status_code == 200
    assert response.json["status"] == "success"

    # 4. Verify gone
    response = logged_in_client.get("/api/blacklist")
    assert len(response.json) == 0


def test_tscore_drops_to_zero_for_blacklisted_mst(app):
    """Verify that an invoice from a blacklisted MST has its T-Score drop to 0 and rating to F."""
    with app.app_context():
        # Ensure blacklisted MST exists
        BlacklistedMST.query.delete()
        db.session.commit()

        blacklist_item = BlacklistedMST(mst="0109876543", reason="Hành vi trốn thuế nghiêm trọng")
        db.session.add(blacklist_item)
        db.session.commit()

        # Create mock invoice issued by this blacklisted MST
        inv = Invoice(
            id="test-blacklist-inv",
            seller_mst="0109876543",
            has_signature=True,
            total_amount=1000000,
            payment_method="Chuyển khoản",
            date="2026-05-26",
            signing_date="2026-05-26"
        )

        score, rating = recalculate_t_score_value(inv)
        assert score == 0
        assert rating == "F"

        # Cleanup
        db.session.delete(blacklist_item)
        db.session.commit()


def test_import_blacklisted_invoice_warning(app):
    """Verify that importing an XML invoice from a blacklisted MST adds a critical warning."""
    xml_data = """<?xml version="1.0" encoding="UTF-8"?>
<HDon>
  <DLHDon>
    <TTChung>
      <THDon>Hóa đơn giá trị gia tăng</THDon>
      <KHMSHDon>1</KHMSHDon>
      <KHHDon>C26TBA</KHHDon>
      <SHDon>99998888</SHDon>
      <NLap>2026-05-26</NLap>
    </TTChung>
    <NDHDon>
      <NBan>
        <Ten>Cong ty Lua Dao</Ten>
        <MST>0109999999</MST>
        <DChi>Ha Noi</DChi>
      </NBan>
      <NMua>
        <TenDonVi>Cong ty Mua Hang</TenDonVi>
        <MST>0309876543</MST>
        <DChi>TP HCM</DChi>
      </NMua>
      <DSDVu>
        <HHDVu>
          <Ten>Dich vu khong co that</Ten>
          <SLuong>1</SLuong>
          <DGia>1000000</DGia>
          <ThTien>1000000</ThTien>
          <TSuat>10%</TSuat>
          <TThue>100000</TThue>
        </HHDVu>
      </DSDVu>
    </NDHDon>
  </DLHDon>
</HDon>
"""
    with app.app_context():
        Invoice.query.delete()
        BlacklistedMST.query.delete()
        db.session.commit()

        # Add MST to blacklist
        blacklist_item = BlacklistedMST(mst="0109999999", reason="Mua bán hóa đơn khống")
        db.session.add(blacklist_item)
        db.session.commit()

        # Import XML
        res = import_xml_invoice(xml_data.encode("utf-8"), "fraud.xml")
        
        # Verify warnings and T-Score
        record = db.session.get(Invoice, res["id"])
        assert record is not None
        assert record.t_score == 0
        assert record.t_rating == "F"
        assert any("CRITICAL_BLACKLIST_ALERT" in w for w in record.warnings)

        # Cleanup
        db.session.delete(blacklist_item)
        db.session.delete(record)
        db.session.commit()
