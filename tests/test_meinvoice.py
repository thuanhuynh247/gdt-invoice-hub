"""
Tests for meInvoice advanced integration features.
Covers Partners directory, BC26 Tax usage reporting, and e-Invoice red-template print view.
"""

from __future__ import annotations


def test_partners_requires_login(client):
    """Anonymous requests to the partners endpoint must be rejected with 401."""
    response = client.get("/api/partners?from=2026-05-01&to=2026-05-20")
    assert response.status_code == 401


def test_partners_success(logged_in_client):
    """Authenticated request should retrieve structured list of unique partners with aggregated spend/tx count."""
    response = logged_in_client.get("/api/partners?from=2026-05-01&to=2026-05-20&direction=purchase")
    assert response.status_code == 200

    payload = response.get_json()
    assert "partners" in payload
    partners = payload["partners"]
    assert len(partners) > 0

    # Validate that at least one partner details match mock invoice providers
    # In mock data, INV-2026-0501 is "Cong ty A" and INV-2026-0518 is "Cong ty B"
    partner_names = [p["name"] for p in partners]
    assert "Cong ty A" in partner_names
    assert "Cong ty B" in partner_names

    # Check structure fields
    for partner in partners:
        assert "mst" in partner
        assert "address" in partner
        assert "transaction_count" in partner
        assert "total_spend" in partner


def test_reports_requires_login(client):
    """Anonymous requests to the reports endpoint must be rejected with 401."""
    response = client.get("/api/reports/usage?from=2026-05-01&to=2026-05-20")
    assert response.status_code == 401


def test_reports_success(logged_in_client):
    """Authenticated request should retrieve BC26 style invoice usage summaries with ranges."""
    response = logged_in_client.get("/api/reports/usage?from=2026-05-01&to=2026-05-20&direction=purchase")
    assert response.status_code == 200

    payload = response.get_json()
    assert "report" in payload
    report_items = payload["report"]
    assert len(report_items) > 0

    # Check structural layout fields of the BC26 report rows
    for item in report_items:
        assert "symbol" in item
        assert "start_number" in item
        assert "end_number" in item
        assert "total_used" in item
        assert "active_count" in item
        assert "cancelled_count" in item
        assert "cancelled_numbers" in item


def test_pdf_view_requires_login(client):
    """Anonymous requests to view printed HTML red-invoices must be blocked with 401."""
    response = client.get("/api/invoices/INV-2026-0501/pdf-view")
    assert response.status_code == 401


def test_pdf_view_success(logged_in_client):
    """Authenticated request to view an invoice print representation should return status 200 with HTML contents."""
    response = logged_in_client.get("/api/invoices/INV-2026-0501/pdf-view")
    assert response.status_code == 200
    
    html_content = response.get_data(as_text=True)
    # Check that critical Vietnamese billing components and mock item descriptions are present
    assert "HÓA ĐƠN GIÁ TRỊ GIA TĂNG" in html_content
    assert "Mã số thuế" in html_content
    assert "Laptop Dell Vostro 3520" in html_content
    assert "Chữ ký số" in html_content or "Signature" in html_content


def test_pdf_view_not_found(logged_in_client):
    """Attempting to print or render a non-existent invoice ID must return a 404 error."""
    response = logged_in_client.get("/api/invoices/INV-999999/pdf-view")
    assert response.status_code == 404


import io

MOCK_INVOICE_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<HDon>
  <DLHDon>
    <TTChung>
      <THDon>Hoa don gia tri gia tang</THDon>
      <KHMSHDon>1</KHMSHDon>
      <KHHDon>C26TBA</KHHDon>
      <SHDon>123</SHDon>
      <NLap>2026-05-21</NLap>
      <DVTTe>VND</DVTTe>
    </TTChung>
    <NDHDon>
      <NBan>
        <Ten>Cong ty A</Ten>
        <MST>0101234567</MST>
        <DChi>Ha Noi</DChi>
      </NBan>
      <NMua>
        <TenDonVi>Cong ty B</TenDonVi>
        <MST>0209876543</MST>
        <DChi>Sai Gon</DChi>
      </NMua>
      <DSCVDMuc>
        <HHDVu>
          <Ten>San pham test</Ten>
          <SLuong>2</SLuong>
          <DGia>100000</DGia>
          <ThTien>200000</ThTien>
          <TSuat>10%</TSuat>
          <TThue>20000</TThue>
        </HHDVu>
      </DSCVDMuc>
    </NDHDon>
    <TToan>
      <TgTCThue>200000</TgTCThue>
      <TgTThue>20000</TgTThue>
      <TgTTTBSo>220000</TgTTTBSo>
    </TToan>
  </DLHDon>
  <SignatureValue>some-sig-value</SignatureValue>
</HDon>
"""

def test_xml_upload_and_local_database_operations(logged_in_client):
    """Test importing invoices via XML upload, querying local db, searching items, and clearing db."""
    
    # 1. Clear database first
    clear_resp = logged_in_client.delete("/api/invoices/local/clear")
    assert clear_resp.status_code == 200

    # 2. Upload XML file
    data = {
        "files": (io.BytesIO(MOCK_INVOICE_XML), "test_invoice.xml")
    }
    upload_resp = logged_in_client.post(
        "/api/invoices/upload",
        data=data,
        content_type="multipart/form-data"
    )
    assert upload_resp.status_code == 200
    upload_payload = upload_resp.get_json()
    assert upload_payload["imported_count"] == 1

    # 3. Retrieve local invoices
    local_resp = logged_in_client.get("/api/invoices/local")
    assert local_resp.status_code == 200
    local_payload = local_resp.get_json()
    assert "invoices" in local_payload
    invoices = local_payload["invoices"]
    assert len(invoices) == 1
    
    inv = invoices[0]
    assert inv["number"] == "00000123"
    assert inv["seller_name"] == "Cong ty A"
    assert inv["seller_mst"] == "0101234567"
    assert inv["buyer_name"] == "Cong ty B"
    assert inv["amount_before_tax"] == 200000.0
    assert inv["total_amount"] == 220000.0
    assert "is_valid" in inv
    assert isinstance(inv["is_valid"], bool)

    # 4. Search local items
    search_resp = logged_in_client.get("/api/invoices/local/items?q=test")
    assert search_resp.status_code == 200
    search_payload = search_resp.get_json()
    assert "items" in search_payload
    items = search_payload["items"]
    assert len(items) == 1
    assert items[0]["item_name"] == "San pham test"
    assert items[0]["seller_name"] == "Cong ty A"

    # 5. Retrieve PDF view for local invoice
    pdf_resp = logged_in_client.get(f"/api/invoices/{inv['id']}/pdf-view")
    assert pdf_resp.status_code == 200
    html_content = pdf_resp.get_data(as_text=True)
    assert "San pham test" in html_content
    assert "Cong ty A" in html_content
    assert "Cong ty B" in html_content


def test_batch_download_zip(logged_in_client):
    """Test batch download of invoices packaging XMLs into a zip archive (Asynchronous)."""
    response = logged_in_client.post(
        "/api/invoices/batch-download",
        json={"month": "2026-05", "direction": "purchase"}
    )
    assert response.status_code == 202
    data = response.get_json()
    task_id = data["task_id"]

    import time
    completed = False
    for _ in range(50):
        status_res = logged_in_client.get(f"/api/invoices/batch-download/status/{task_id}")
        assert status_res.status_code == 200
        status_data = status_res.get_json()
        if status_data["status"] == "completed":
            completed = True
            break
        time.sleep(0.1)

    assert completed is True
    
    download_res = logged_in_client.get(f"/api/invoices/batch-download/download/{task_id}")
    assert download_res.status_code == 200
    assert download_res.headers["Content-Type"] == "application/zip"

    # Read the returned zip archive
    zip_bytes = download_res.get_data()
    import zipfile
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        namelist = z.namelist()
        assert len(namelist) > 0
        for name in namelist:
            assert name.endswith(".xml")



def test_smart_audit_scenarios(logged_in_client):
    """Test various smart audit warnings like duplicate check, tax mismatch, high risk MST, and missing signature."""
    
    # Clear local database first
    logged_in_client.delete("/api/invoices/local/clear")

    # 1. Missing digital signature warning & High-risk MST warning & Tax mismatch warning XML
    bad_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<HDon>
  <DLHDon>
    <TTChung>
      <THDon>Hoa don gia tri gia tang</THDon>
      <KHMSHDon>1</KHMSHDon>
      <KHHDon>C26TBA</KHHDon>
      <SHDon>999</SHDon>
      <NLap>2026-05-21</NLap>
      <DVTTe>VND</DVTTe>
    </TTChung>
    <NDHDon>
      <NBan>
        <Ten>Cong ty Nguy Hiem</Ten>
        <MST>0101234599</MST>
        <DChi>Ha Noi</DChi>
      </NBan>
      <NMua>
        <TenDonVi>Cong ty Mua</TenDonVi>
        <MST>0209876543</MST>
        <DChi>Sai Gon</DChi>
      </NMua>
      <DSCVDMuc>
        <HHDVu>
          <Ten>Dich vu sai thue</Ten>
          <SLuong>1</SLuong>
          <DGia>100000</DGia>
          <ThTien>100000</ThTien>
          <TSuat>10%</TSuat>
          <TThue>50000</TThue> <!-- Mismatch: 10% of 100k is 10k, but declared 50k -->
        </HHDVu>
      </DSCVDMuc>
    </NDHDon>
    <TToan>
      <TgTCThue>100000</TgTCThue>
      <TgTThue>50000</TgTThue>
      <TgTTTBSo>150000</TgTTTBSo>
    </TToan>
  </DLHDon>
  <!-- Missing SignatureValue tag completely -->
</HDon>
"""
    data = {
        "files": (io.BytesIO(bad_xml), "bad_invoice.xml")
    }
    upload_resp = logged_in_client.post(
        "/api/invoices/upload",
        data=data,
        content_type="multipart/form-data"
    )
    assert upload_resp.status_code == 200
    
    # Retrieve local invoices
    local_resp = logged_in_client.get("/api/invoices/local")
    assert local_resp.status_code == 200
    invoices = local_resp.get_json()["invoices"]
    assert len(invoices) == 1
    bad_inv = invoices[0]
    
    assert bad_inv["is_valid"] is False
    assert len(bad_inv["warnings"]) >= 3
    
    # Verify specific warning contents
    warnings_str = " ".join(bad_inv["warnings"])
    assert "MST Người bán" in warnings_str
    assert "Chênh lệch thuế suất" in warnings_str
    assert "chưa được ký số" in warnings_str

    # 2. Test duplicate check warning by uploading it again
    data2 = {
        "files": (io.BytesIO(bad_xml), "bad_invoice.xml")
    }
    upload_resp2 = logged_in_client.post(
        "/api/invoices/upload",
        data=data2,
        content_type="multipart/form-data"
    )
    assert upload_resp2.status_code == 200
    
    local_resp2 = logged_in_client.get("/api/invoices/local")
    invoices2 = local_resp2.get_json()["invoices"]
    assert len(invoices2) == 1 # Overwritten duplicate
    dup_inv = invoices2[0]
    dup_warnings_str = " ".join(dup_inv["warnings"])
    assert "đã tồn tại" in dup_warnings_str


def test_invoice_details_audit_metadata(logged_in_client):
    """Test that the invoice details endpoint returns warnings and is_valid fields."""
    logged_in_client.delete("/api/invoices/local/clear")
    # Upload an invoice to local DB first
    xml_data = """<?xml version="1.0" encoding="UTF-8"?>
<HDon>
  <DLHDon>
    <TTChung>
      <THDon>Hóa đơn giá trị gia tăng</THDon>
      <KHMSHDon>1</KHMSHDon>
      <KHHDon>C26TBA</KHHDon>
      <SHDon>00001234</SHDon>
      <NLap>2026-05-15</NLap>
    </TTChung>
    <NDHDon>
      <NBan>
        <Ten>Cong ty Ban</Ten>
        <MST>0101234567</MST>
        <DChi>Ha Noi</DChi>
      </NBan>
      <NMua>
        <TenDonVi>Cong ty Mua</TenDonVi>
        <MST>0301234567</MST>
        <DChi>Sai Gon</DChi>
      </NMua>
      <DSDVu>
        <HHDVu>
          <Ten>May vi tinh</Ten>
          <SLuong>1</SLuong>
          <DGia>10000000</DGia>
          <ThTien>10000000</ThTien>
          <TSuat>10%</TSuat>
          <TThue>1000000</TThue>
        </HHDVu>
      </DSDVu>
    </NDHDon>
  </DLHDon>
  <SignatureValue>dummy-signature</SignatureValue>
</HDon>
"""
    data = {
        "files": (io.BytesIO(xml_data.encode("utf-8")), "valid_test.xml")
    }
    upload_resp = logged_in_client.post(
        "/api/invoices/upload",
        data=data,
        content_type="multipart/form-data"
    )
    assert upload_resp.status_code == 200

    # Retrieve local invoice list to get the generated UUID
    list_resp = logged_in_client.get("/api/invoices/local")
    assert list_resp.status_code == 200
    invoices = list_resp.get_json()["invoices"]
    assert len(invoices) == 1
    invoice_id = invoices[0]["id"]

    # Request details for this invoice ID
    details_resp = logged_in_client.get(f"/api/invoices/{invoice_id}/details")
    assert details_resp.status_code == 200
    details = details_resp.get_json()
    
    assert "warnings" in details
    assert "is_valid" in details
    assert details["is_valid"] is False
    assert len(details["warnings"]) == 1
    assert "Chữ ký số" in details["warnings"][0]


def test_export_local_excel_unauthorized(client):
    """Test that exporting local Excel without logging in is unauthorized."""
    resp = client.get("/api/invoices/local/export-excel")
    assert resp.status_code in [302, 401]


def test_export_local_excel_authorized(logged_in_client):
    """Test that exporting local Excel as an authorized user returns the Excel file."""
    logged_in_client.delete("/api/invoices/local/clear")
    # First, ensure there is at least one invoice in the local db
    xml_data = """<?xml version="1.0" encoding="UTF-8"?>
<HDon>
  <DLHDon>
    <TTChung>
      <SHDon>0000999</SHDon>
      <NLap>2026-05-18</NLap>
      <KHDon>1C26TML</KHDon>
    </TTChung>
    <NDHDon>
      <NBan>
        <Ten>Vendor A</Ten>
        <MST>0100109106</MST>
      </NBan>
      <NMua>
        <Ten>Customer B</Ten>
        <MST>0301234567</MST>
      </NMua>
      <DSCVDMuc>
        <HHDVu>
          <Ten>Keyboard</Ten>
          <SLuong>2</SLuong>
          <DGia>500000</DGia>
          <ThTien>1000000</ThTien>
          <TSuat>10%</TSuat>
          <TThue>100000</TThue>
        </HHDVu>
      </DSCVDMuc>
    </NDHDon>
    <TToan>
      <TgTCThue>1000000</TgTCThue>
      <TgTThue>100000</TgTThue>
      <TgTTTBSo>1100000</TgTTTBSo>
    </TToan>
  </DLHDon>
  <SignatureValue>dummy-sig-2</SignatureValue>
</HDon>
"""
    data = {
        "files": (io.BytesIO(xml_data.encode("utf-8")), "valid_test_2.xml")
    }
    upload_resp = logged_in_client.post(
        "/api/invoices/upload",
        data=data,
        content_type="multipart/form-data"
    )
    assert upload_resp.status_code == 200

    # Call export endpoint
    export_resp = logged_in_client.get("/api/invoices/local/export-excel")
    assert export_resp.status_code == 200
    assert export_resp.content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert "Content-Disposition" in export_resp.headers
    assert "attachment" in export_resp.headers["Content-Disposition"]
    assert "audited_invoices" in export_resp.headers["Content-Disposition"]


def test_late_signing_audit(logged_in_client):
    """Test US-016: Delayed Digital Signature warning check."""
    logged_in_client.delete("/api/invoices/local/clear")

    # 1. Upload invoice with valid/same day signing time (No late warning)
    xml_valid = """<?xml version="1.0" encoding="UTF-8"?>
<HDon>
  <DLHDon>
    <TTChung>
      <SHDon>0000001</SHDon>
      <NLap>2026-05-15</NLap>
      <KHDon>1C26TML</KHDon>
    </TTChung>
    <NDHDon>
      <NBan>
        <Ten>Vendor Normal</Ten>
        <MST>0100109106</MST>
      </NBan>
      <NMua>
        <Ten>Customer B</Ten>
        <MST>0301234567</MST>
      </NMua>
      <DSCVDMuc>
        <HHDVu>
          <Ten>Item A</Ten>
          <SLuong>1</SLuong>
          <DGia>100000</DGia>
          <ThTien>100000</ThTien>
          <TSuat>10%</TSuat>
          <TThue>10000</TThue>
        </HHDVu>
      </DSCVDMuc>
    </NDHDon>
    <TToan>
      <TgTCThue>100000</TgTCThue>
      <TgTThue>10000</TgTThue>
      <TgTTTBSo>110000</TgTTTBSo>
    </TToan>
  </DLHDon>
  <SignatureValue>sig-valid</SignatureValue>
  <SigningTime>2026-05-15T15:30:00</SigningTime>
</HDon>
"""
    data_valid = {
        "files": (io.BytesIO(xml_valid.encode("utf-8")), "valid_signing.xml")
    }
    resp1 = logged_in_client.post("/api/invoices/upload", data=data_valid, content_type="multipart/form-data")
    assert resp1.status_code == 200

    local_resp1 = logged_in_client.get("/api/invoices/local")
    invoices1 = local_resp1.get_json()["invoices"]
    assert len(invoices1) == 1
    warnings_str1 = " ".join(invoices1[0]["warnings"])
    assert "ký số chậm" not in warnings_str1
    assert invoices1[0]["signing_date"] == "2026-05-15"

    # 2. Upload invoice with late signing time (Difference of 5 days > 24 hours)
    xml_late = """<?xml version="1.0" encoding="UTF-8"?>
<HDon>
  <DLHDon>
    <TTChung>
      <SHDon>0000002</SHDon>
      <NLap>2026-05-15</NLap>
      <KHDon>1C26TML</KHDon>
    </TTChung>
    <NDHDon>
      <NBan>
        <Ten>Vendor Late</Ten>
        <MST>0100109107</MST>
      </NBan>
      <NMua>
        <Ten>Customer B</Ten>
        <MST>0301234567</MST>
      </NMua>
      <DSCVDMuc>
        <HHDVu>
          <Ten>Item B</Ten>
          <SLuong>1</SLuong>
          <DGia>100000</DGia>
          <ThTien>100000</ThTien>
          <TSuat>10%</TSuat>
          <TThue>10000</TThue>
        </HHDVu>
      </DSCVDMuc>
    </NDHDon>
    <TToan>
      <TgTCThue>100000</TgTCThue>
      <TgTThue>10000</TgTThue>
      <TgTTTBSo>110000</TgTTTBSo>
    </TToan>
  </DLHDon>
  <SignatureValue>sig-late</SignatureValue>
  <SigningTime>2026-05-20T10:00:00</SigningTime>
</HDon>
"""
    data_late = {
        "files": (io.BytesIO(xml_late.encode("utf-8")), "late_signing.xml")
    }
    resp2 = logged_in_client.post("/api/invoices/upload", data=data_late, content_type="multipart/form-data")
    assert resp2.status_code == 200

    local_resp2 = logged_in_client.get("/api/invoices/local")
    invoices2 = local_resp2.get_json()["invoices"]
    assert len(invoices2) == 2
    
    late_inv = next(i for i in invoices2 if i["number"] == "00000002")
    warnings_str2 = " ".join(late_inv["warnings"])
    assert "ký số chậm" in warnings_str2
    assert "Ngày lập: 15/05/2026" in warnings_str2
    assert "Ngày ký: 20/05/2026" in warnings_str2
    assert late_inv["signing_date"] == "2026-05-20"


def test_payment_method_compliance_audit(logged_in_client):
    """Test US-018: Compliance check for cash payments on invoices >= 5 million VND."""
    logged_in_client.delete("/api/invoices/local/clear")

    # 1. Invoice under 5 million VND with cash payment method (TM) - No warnings expected
    xml_under_5m_cash = """<?xml version="1.0" encoding="UTF-8"?>
<HDon>
  <DLHDon>
    <TTChung>
      <SHDon>0000010</SHDon>
      <NLap>2026-05-15</NLap>
      <KHDon>1C26TML</KHDon>
      <HTTToan>TM</HTTToan>
    </TTChung>
    <NDHDon>
      <NBan>
        <Ten>Vendor A</Ten>
        <MST>0100109106</MST>
      </NBan>
      <NMua>
        <Ten>Customer B</Ten>
        <MST>0301234567</MST>
      </NMua>
      <DSCVDMuc>
        <HHDVu>
          <Ten>Item under 5M</Ten>
          <SLuong>1</SLuong>
          <DGia>4000000</DGia>
          <ThTien>4000000</ThTien>
          <TSuat>10%</TSuat>
          <TThue>400000</TThue>
        </HHDVu>
      </DSCVDMuc>
    </NDHDon>
    <TToan>
      <TgTCThue>4000000</TgTCThue>
      <TgTThue>400000</TgTThue>
      <TgTTTBSo>4400000</TgTTTBSo>
    </TToan>
  </DLHDon>
  <SignatureValue>sig-under-5m</SignatureValue>
</HDon>
"""
    data_under = {
        "files": (io.BytesIO(xml_under_5m_cash.encode("utf-8")), "under_5m_cash.xml")
    }
    resp1 = logged_in_client.post("/api/invoices/upload", data=data_under, content_type="multipart/form-data")
    assert resp1.status_code == 200

    # 2. Invoice >= 5 million VND with non-cash payment method (CK) - No warnings expected
    xml_over_5m_transfer = """<?xml version="1.0" encoding="UTF-8"?>
<HDon>
  <DLHDon>
    <TTChung>
      <SHDon>0000011</SHDon>
      <NLap>2026-05-15</NLap>
      <KHDon>1C26TML</KHDon>
      <HTTToan>CK</HTTToan>
    </TTChung>
    <NDHDon>
      <NBan>
        <Ten>Vendor A</Ten>
        <MST>0100109106</MST>
      </NBan>
      <NMua>
        <Ten>Customer B</Ten>
        <MST>0301234567</MST>
      </NMua>
      <DSCVDMuc>
        <HHDVu>
          <Ten>Item over 5M</Ten>
          <SLuong>1</SLuong>
          <DGia>6000000</DGia>
          <ThTien>6000000</ThTien>
          <TSuat>10%</TSuat>
          <TThue>600000</TThue>
        </HHDVu>
      </DSCVDMuc>
    </NDHDon>
    <TToan>
      <TgTCThue>6000000</TgTCThue>
      <TgTThue>600000</TgTThue>
      <TgTTTBSo>6600000</TgTTTBSo>
    </TToan>
  </DLHDon>
  <SignatureValue>sig-over-5m-ck</SignatureValue>
</HDon>
"""
    data_transfer = {
        "files": (io.BytesIO(xml_over_5m_transfer.encode("utf-8")), "over_5m_transfer.xml")
    }
    resp2 = logged_in_client.post("/api/invoices/upload", data=data_transfer, content_type="multipart/form-data")
    assert resp2.status_code == 200

    # 3. Invoice >= 5 million VND with cash payment method (TM/Tiền mặt) - Warning expected
    xml_over_5m_cash = """<?xml version="1.0" encoding="UTF-8"?>
<HDon>
  <DLHDon>
    <TTChung>
      <SHDon>0000012</SHDon>
      <NLap>2026-05-15</NLap>
      <KHDon>1C26TML</KHDon>
      <HTTToan>Tiền mặt</HTTToan>
    </TTChung>
    <NDHDon>
      <NBan>
        <Ten>Vendor A</Ten>
        <MST>0100109106</MST>
      </NBan>
      <NMua>
        <Ten>Customer B</Ten>
        <MST>0301234567</MST>
      </NMua>
      <DSCVDMuc>
        <HHDVu>
          <Ten>Item over 5M Cash</Ten>
          <SLuong>1</SLuong>
          <DGia>6000000</DGia>
          <ThTien>6000000</ThTien>
          <TSuat>10%</TSuat>
          <TThue>600000</TThue>
        </HHDVu>
      </DSCVDMuc>
    </NDHDon>
    <TToan>
      <TgTCThue>6000000</TgTCThue>
      <TgTThue>600000</TgTThue>
      <TgTTTBSo>6600000</TgTTTBSo>
    </TToan>
  </DLHDon>
  <SignatureValue>sig-over-5m-cash</SignatureValue>
</HDon>
"""
    data_cash = {
        "files": (io.BytesIO(xml_over_5m_cash.encode("utf-8")), "over_5m_cash.xml")
    }
    resp3 = logged_in_client.post("/api/invoices/upload", data=data_cash, content_type="multipart/form-data")
    assert resp3.status_code == 200

    # Fetch local invoices to verify warnings and payment methods
    local_resp = logged_in_client.get("/api/invoices/local")
    assert local_resp.status_code == 200
    invoices = local_resp.get_json()["invoices"]
    assert len(invoices) == 3

    inv_under = next(i for i in invoices if i["number"] == "00000010")
    inv_transfer = next(i for i in invoices if i["number"] == "00000011")
    inv_cash = next(i for i in invoices if i["number"] == "00000012")

    # Under 5M TM should have no compliance warnings
    assert not any("5 triệu VND trở lên" in w for w in inv_under["warnings"])
    assert inv_under["payment_method"] == "TM"

    # Over 5M CK should have no compliance warnings
    assert not any("5 triệu VND trở lên" in w for w in inv_transfer["warnings"])
    assert inv_transfer["payment_method"] == "CK"

    # Over 5M Cash must have the compliance warning
    assert inv_cash["payment_method"] == "Tiền mặt"
    warnings_str = " ".join(inv_cash["warnings"])
    assert "5 triệu VND trở lên" in warnings_str
    assert "được khấu trừ thuế" in warnings_str

    # Test details endpoint includes payment method
    details_resp = logged_in_client.get(f"/api/invoices/{inv_cash['id']}/details")
    assert details_resp.status_code == 200
    details = details_resp.get_json()
    assert details["payment_method"] == "Tiền mặt"


def test_invoice_duplicate_strategy_and_mutations(logged_in_client):
    """Test importing invoices with duplicate strategies, deleting a local invoice, and adjusting a local invoice."""
    # 1. Clear database first
    clear_resp = logged_in_client.delete("/api/invoices/local/clear")
    assert clear_resp.status_code == 200

    # 2. Upload initial XML file
    xml_data = """<?xml version="1.0" encoding="UTF-8"?>
<HDon>
  <DLHDon>
    <TTChung>
      <THDon>Hóa đơn giá trị gia tăng</THDon>
      <KHMSHDon>1</KHMSHDon>
      <KHHDon>C26TBA</KHHDon>
      <SHDon>00000999</SHDon>
      <NLap>2026-05-15</NLap>
    </TTChung>
    <NDHDon>
      <NBan>
        <Ten>Seller X</Ten>
        <MST>0100109106</MST>
        <DChi>Ha Noi</DChi>
      </NBan>
      <NMua>
        <TenDonVi>Buyer Y</TenDonVi>
        <MST>0301234567</MST>
        <DChi>Sai Gon</DChi>
      </NMua>
      <DSDVu>
        <HHDVu>
          <Ten>Item A</Ten>
          <SLuong>1</SLuong>
          <DGia>100000</DGia>
          <ThTien>100000</ThTien>
          <TSuat>10%</TSuat>
          <TThue>10000</TThue>
        </HHDVu>
      </DSDVu>
    </NDHDon>
  </DLHDon>
  <SignatureValue>sig-999</SignatureValue>
</HDon>
"""
    data = {
        "files": (io.BytesIO(xml_data.encode("utf-8")), "invoice_999.xml"),
        "duplicate_strategy": "skip"
    }
    resp = logged_in_client.post("/api/invoices/upload", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    res_payload = resp.get_json()
    assert res_payload["imported_count"] == 1
    assert res_payload["skipped_count"] == 0

    # 3. Upload duplicate XML with duplicate_strategy="skip"
    data_skip = {
        "files": (io.BytesIO(xml_data.encode("utf-8")), "invoice_999.xml"),
        "duplicate_strategy": "skip"
    }
    resp_skip = logged_in_client.post("/api/invoices/upload", data=data_skip, content_type="multipart/form-data")
    assert resp_skip.status_code == 200
    res_skip = resp_skip.get_json()
    assert res_skip["imported_count"] == 0
    assert res_skip["skipped_count"] == 1
    assert res_skip["overwritten_count"] == 0

    # 4. Upload duplicate XML with duplicate_strategy="overwrite"
    data_overwrite = {
        "files": (io.BytesIO(xml_data.encode("utf-8")), "invoice_999.xml"),
        "duplicate_strategy": "overwrite"
    }
    resp_overwrite = logged_in_client.post("/api/invoices/upload", data=data_overwrite, content_type="multipart/form-data")
    assert resp_overwrite.status_code == 200
    res_overwrite = resp_overwrite.get_json()
    assert res_overwrite["imported_count"] == 0
    assert res_overwrite["skipped_count"] == 0
    assert res_overwrite["overwritten_count"] == 1

    # 5. Fetch local invoices list
    list_resp = logged_in_client.get("/api/invoices/local")
    assert list_resp.status_code == 200
    invoices = list_resp.get_json()["invoices"]
    assert len(invoices) == 1
    invoice_id = invoices[0]["id"]

    # 6. Test PATCH /api/invoices/local/<id> adjustment
    patch_data = {
        "notes": "Adjusted notes content",
        "payment_method": "Tiền mặt",
        "total_amount": 15000000
    }
    patch_resp = logged_in_client.patch(f"/api/invoices/local/{invoice_id}", json=patch_data)
    assert patch_resp.status_code == 200
    patch_payload = patch_resp.get_json()
    assert "notes" in patch_payload["invoice"]
    assert patch_payload["invoice"]["notes"] == "Adjusted notes content"
    assert patch_payload["invoice"]["payment_method"] == "Tiền mặt"
    
    # 7. Check warnings are updated (should flag payment_method over 5M compliance warning!)
    assert any("5 triệu VND trở lên" in w for w in patch_payload["invoice"]["warnings"])

    # 8. Test DELETE /api/invoices/local/<id>
    del_resp = logged_in_client.delete(f"/api/invoices/local/{invoice_id}")
    assert del_resp.status_code == 200
    del_payload = del_resp.get_json()
    assert del_payload.get("status") == "success"

    # 9. Verify invoice is gone from database
    list_resp_after = logged_in_client.get("/api/invoices/local")
    assert list_resp_after.status_code == 200
    invoices_after = list_resp_after.get_json()["invoices"]
    assert len(invoices_after) == 0



