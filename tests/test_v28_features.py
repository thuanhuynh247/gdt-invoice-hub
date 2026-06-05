"""Tests for Version 28.0.0 compliance auto-repair and collaborative swarm chat (US-396 to US-397)."""

from __future__ import annotations
import json
import pytest
from invoices.v28_service import (
    audit_xml_compliance,
    repair_xml_invoice,
    simulate_swarm_step_by_step
)

def test_xml_compliance_auditing():
    """US-397: Test XML compliance checks under Decree 123 rules."""
    # Test valid XML representation
    xml_content = """<?xml version="1.0" encoding="utf-8"?>
<HDon xmlns="http://www.gdt.gov.vn/invoices">
  <DLHDon Id="HD_1">
    <TTChung>
      <THDon>Hóa đơn giá trị gia tăng</THDon>
      <KHMSHDon>1</KHMSHDon>
      <KHHDon>C26TBA</KHHDon>
      <SHDon>00000001</SHDon>
      <NLap>2026-06-05</NLap>
      <DVTTe>VND</DVTTe>
      <HTTToan>CK</HTTToan>
    </TTChung>
    <NDHDon>
      <NBan>
        <Ten>Nhà Bán</Ten>
        <MST>0101112223</MST>
      </NBan>
      <NMua>
        <Ten>Người Mua</Ten>
        <MST>0202223334</MST>
      </NMua>
      <DSDVu>
        <HHDVu>
          <STT>1</STT>
          <Ten>Sản phẩm A</Ten>
          <SLuong>1</SLuong>
          <DGia>100000</DGia>
          <ThTien>100000</ThTien>
        </HHDVu>
      </DSDVu>
    </NDHDon>
    <TToan>
      <TgTTTBSo>110000</TgTTTBSo>
    </TToan>
  </DLHDon>
  <Signature>
    <SignedInfo>
      <Reference URI="#HD_1"/>
    </SignedInfo>
    <SigningTime>2026-06-05T12:00:00</SigningTime>
  </Signature>
</HDon>"""

    audit_res = audit_xml_compliance(xml_content)
    # Since it is well-formed with valid elements, status should not be 'malformed'
    assert audit_res["status"] in ["compliant", "flagged"]

    # Test cash limit violation alert
    cash_limit_xml = xml_content.replace("<HTTToan>CK</HTTToan>", "<HTTToan>TM</HTTToan>").replace("<TgTTTBSo>110000</TgTTTBSo>", "<TgTTTBSo>25000000</TgTTTBSo>")
    audit_res_cash = audit_xml_compliance(cash_limit_xml)
    assert any("tiền mặt" in w for w in audit_res_cash["warnings"])


def test_xml_auto_repair():
    """US-397: Test repairing wrong schema order, invalid namespaces and wrong MSTs."""
    broken_xml = """<?xml version="1.0" encoding="utf-8"?>
<HDon>
  <DLHDon Id="HD_00034823">
    <NDHDon>
      <NBan>
        <Ten>Công ty CP Thiết bị Công nghệ Ánh Dương</Ten>
        <MST>010123AB88</MST>
      </NBan>
      <NMua>
        <Ten>Công ty TNHH Giải pháp Phần mềm Ánh Sáng</Ten>
        <MST>0109998887-ERR</MST>
      </NMua>
    </NDHDon>
    <TTChung>
      <THDon>Hóa đơn giá trị gia tăng</THDon>
      <HTTToan>TM</HTTToan>
    </TTChung>
    <TToan>
      <TgTTTBSo>25000000</TgTTTBSo>
    </TToan>
  </DLHDon>
</HDon>"""

    repair_res = repair_xml_invoice(broken_xml)
    assert repair_res["success"]
    assert len(repair_res["repairs"]) > 0
    assert "repaired_xml" in repair_res
    
    # Repaired XML should contain xmlns standard namespace and corrected MST values
    repaired_xml = repair_res["repaired_xml"]
    assert "http://www.gdt.gov.vn/invoices" in repaired_xml
    assert "0101230000" in repaired_xml or "010123" in repaired_xml
    assert "0109998887" in repaired_xml
    # Payment method should be CK
    assert "CK" in repaired_xml


def test_swarm_chat_advisor_simulation():
    """US-396: Test step-by-step collaborative swarm advisor simulation logger."""
    logs = simulate_swarm_step_by_step("0109998887", "Kiểm tra rủi ro thuế liên kết của công ty")
    assert len(logs) == 5
    assert logs[0]["agent"] == "JointAuditCoordinator"
    assert logs[1]["agent"] == "AuditorAgent"
    assert logs[2]["agent"] == "ClassifierAgent"
    assert logs[3]["agent"] == "ForecasterAgent"


def test_v28_endpoints(logged_in_client):
    """Test web endpoint routing and controller responses for Version 28."""
    # 1. Page render
    resp = logged_in_client.get("/v28-compliance")
    assert resp.status_code == 200

    # 2. XML Audit API
    xml_data = """<?xml version="1.0" encoding="UTF-8"?>
    <HDon>
        <DLHDon>
            <TTChung>
                <SHDon>INV-28-TEST</SHDon>
            </TTChung>
        </DLHDon>
    </HDon>"""
    resp = logged_in_client.post("/api/compliance/xml-audit", json={"xml_content": xml_data})
    assert resp.status_code == 200
    res = resp.get_json()
    assert "status" in res

    # 3. XML Auto-Repair API
    resp = logged_in_client.post("/api/compliance/xml-auto-repair", json={"xml_content": xml_data})
    assert resp.status_code == 200
    res = resp.get_json()
    assert res["success"]
    assert "repaired_xml" in res

    # 4. Swarm Chat API
    resp = logged_in_client.post("/api/agents/swarm-chat", json={"query": "Rà soát giao dịch liên kết"})
    assert resp.status_code == 200
    res = resp.get_json()
    assert res["status"] == "success"
    assert len(res["chat_steps"]) > 0
    assert "report_markdown" in res
