import json
import os
from datetime import datetime
from flask import session
from invoices.models import Invoice, LineItem, TaxpayerProfile, db
from invoices.service import XML_DIR

def test_issue_invoice_page_auth(client):
    """Test that accessing the e-invoice page redirects to login when unauthenticated."""
    response = client.get("/issue-invoice")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_issue_invoice_flow(client, app):
    """Test the complete draft, sign, download, and listing flow for local e-invoices."""
    # 1. Login and set active taxpayer profile
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_id"] = 1
        sess["username"] = "admin"
        sess["role"] = "admin"
        sess["active_taxpayer_mst"] = "1122334455"

    with app.app_context():
        # Clean any old mock records with the test MST
        Invoice.query.filter_by(seller_mst="1122334455").delete()
        TaxpayerProfile.query.filter_by(mst="1122334455").delete()
        
        # Create active taxpayer profile
        profile = TaxpayerProfile(
            mst="1122334455",
            company_name="Cong ty TNHH Thuong mai GDT",
            gdt_username="gdt_user",
            gdt_password_encrypted="encrypted_pwd",
            is_active=True,
            created_at=datetime.now().isoformat()
        )
        db.session.add(profile)
        db.session.commit()

    # 2. Issue Draft
    draft_payload = {
        "buyer_mst": "9988776655",
        "buyer_name": "Cong ty Doi tac GDT",
        "buyer_address": "456 Duong Doi tac, HCMC",
        "symbol": "1C26TYY",
        "items": [
            {
                "item_name": "Laptop Dell XPS",
                "unit": "Chiec",
                "quantity": 2.0,
                "unit_price": 30000000.0,
                "tax_rate": "10%"
            },
            {
                "item_name": "Dich vu lap dat",
                "unit": "Lan",
                "quantity": 1.0,
                "unit_price": 5000000.0,
                "tax_rate": "8%"
            }
        ]
    }

    resp = client.post(
        "/api/invoices/issue/draft",
        data=json.dumps(draft_payload),
        content_type="application/json"
    )
    
    assert resp.status_code == 200
    data = json.loads(resp.data.decode("utf-8"))
    assert data["status"] == "success"
    assert "invoice" in data
    
    inv_id = data["invoice"]["id"]
    assert inv_id.startswith("1122334455-1C26TYY-")
    assert data["invoice"]["invoice_status"] == "draft"
    assert data["invoice"]["amount_before_tax"] == 65000000.0  # (2 * 30M) + (1 * 5M)
    assert data["invoice"]["tax_amount"] == 6400000.0         # (10% * 60M) + (8% * 5M)
    assert data["invoice"]["total_amount"] == 71400000.0       # 65M + 6.4M
    assert "bảy mươi mốt triệu" in data["invoice"]["amount_in_words"].lower()

    # 3. Ký số Hóa đơn (USB Token Sign)
    sign_payload = {
        "invoice_id": inv_id
    }
    
    resp_sign = client.post(
        "/api/invoices/issue/sign",
        data=json.dumps(sign_payload),
        content_type="application/json"
    )
    
    assert resp_sign.status_code == 200
    data_sign = json.loads(resp_sign.data.decode("utf-8"))
    assert data_sign["status"] == "success"
    assert data_sign["invoice_id"] == inv_id
    assert "xml_preview" in data_sign

    # 4. Verify Local Storage and Signature state
    with app.app_context():
        inv_record = Invoice.query.get(inv_id)
        assert inv_record is not None
        assert inv_record.invoice_status == "Gốc"
        assert inv_record.import_status == "imported"
        assert inv_record.has_signature is True
        
        # Verify XML file in XML_DIR
        xml_filename = f"invoice_{inv_id}.xml"
        xml_path = os.path.join(XML_DIR, xml_filename)
        assert os.path.exists(xml_path)
        
        with open(xml_path, "r", encoding="utf-8") as f:
            xml_content = f.read()
            assert "<Signature xmlns=" in xml_content
            assert "<DigestValue>" in xml_content
            assert "<SignatureValue>" in xml_content
            assert "Cong ty Doi tac GDT" in xml_content

    # 5. Verify local e-invoice is listed in /api/invoices/local
    resp_list = client.get("/api/invoices/local?taxpayer_mst=1122334455")
    assert resp_list.status_code == 200
    data_list = json.loads(resp_list.data.decode("utf-8"))
    assert "invoices" in data_list
    assert len(data_list["invoices"]) > 0
    
    matching_invoices = [i for i in data_list["invoices"] if i["id"] == inv_id]
    assert len(matching_invoices) == 1
    assert matching_invoices[0]["invoice_status"] == "Gốc"

    # 6. Verify XML Download retrieves the signed Circular 78 package
    resp_download = client.get(f"/api/invoices/{inv_id}/download")
    assert resp_download.status_code == 200
    downloaded_xml = resp_download.data.decode("utf-8")
    assert "<Signature xmlns=" in downloaded_xml
    assert inv_id in downloaded_xml
