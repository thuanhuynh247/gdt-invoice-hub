"""Tests for the Provider Registry API endpoints."""

import io
import pytest


@pytest.fixture(autouse=True)
def disable_security_filters(app):
    with app.app_context():
        from invoices.scheduler import save_scheduler_settings
        save_scheduler_settings({
            "signature_filter_enabled": False,
            "blacklist_filter_enabled": False
        })



def test_provider_list_requires_login(client):
    """Verify /api/providers requires authentication."""
    response = client.get("/api/providers")
    assert response.status_code in [302, 401]


def test_provider_list_success(logged_in_client):
    """Verify /api/providers returns the full provider registry."""
    response = logged_in_client.get("/api/providers")
    assert response.status_code == 200
    data = response.get_json()
    assert "providers" in data
    assert "count" in data
    assert data["count"] > 0
    # Check that known providers are present
    msts = [p["mst"] for p in data["providers"]]
    assert "0101243150" in msts  # MISA
    assert "0100684378" in msts  # VNPT
    assert "0101360697" in msts  # BKAV
    assert "0100109106" in msts  # Viettel


def test_provider_list_structure(logged_in_client):
    """Verify each provider entry has the required metadata fields."""
    response = logged_in_client.get("/api/providers")
    data = response.get_json()
    for provider in data["providers"][:5]:  # Check first 5
        assert "mst" in provider
        assert "name" in provider
        assert "short" in provider
        assert "icon" in provider
        assert "color" in provider
        assert "bg" in provider


def test_provider_stats_requires_login(client):
    """Verify /api/providers/stats requires authentication."""
    response = client.get("/api/providers/stats")
    assert response.status_code in [302, 401]


def test_provider_stats_empty_database(logged_in_client):
    """Verify /api/providers/stats returns empty stats when no invoices exist."""
    # Clear database first
    logged_in_client.delete("/api/invoices/local/clear")

    response = logged_in_client.get("/api/providers/stats")
    assert response.status_code == 200
    data = response.get_json()
    assert "stats" in data
    assert "total_invoices" in data
    assert "total_providers" in data
    assert data["total_invoices"] == 0


def test_provider_stats_with_invoices(logged_in_client):
    """Verify /api/providers/stats correctly calculates provider distribution."""
    # Clear and upload test invoices
    logged_in_client.delete("/api/invoices/local/clear")

    xml_data = """<?xml version="1.0" encoding="UTF-8"?>
<HDon>
  <DLHDon>
    <TTChung>
      <THDon>Hóa đơn giá trị gia tăng</THDon>
      <KHMSHDon>1</KHMSHDon>
      <KHHDon>C26TBA</KHHDon>
      <SHDon>00000801</SHDon>
      <NLap>2026-06-01</NLap>
      <MSTTCGP>0101243150</MSTTCGP>
    </TTChung>
    <NDHDon>
      <NBan>
        <Ten>Seller MISA</Ten>
        <MST>0100109106</MST>
        <DChi>Ha Noi</DChi>
      </NBan>
      <NMua>
        <TenDonVi>Buyer Test</TenDonVi>
        <MST>0301234567</MST>
        <DChi>Sai Gon</DChi>
      </NMua>
      <DSDVu>
        <HHDVu>
          <Ten>Item A</Ten>
          <SLuong>2</SLuong>
          <DGia>500000</DGia>
          <ThTien>1000000</ThTien>
          <TSuat>10%</TSuat>
          <TThue>100000</TThue>
        </HHDVu>
      </DSDVu>
    </NDHDon>
  </DLHDon>
  <SignatureValue>sig-801</SignatureValue>
</HDon>
"""
    upload_data = {
        "files": (io.BytesIO(xml_data.encode("utf-8")), "invoice_801.xml"),
        "duplicate_strategy": "skip"
    }
    resp = logged_in_client.post("/api/invoices/upload", data=upload_data, content_type="multipart/form-data")
    assert resp.status_code == 200
    upload_result = resp.get_json()
    assert upload_result.get("imported_count", 0) >= 1, f"Upload failed: {upload_result}"

    # Verify invoice was persisted in local database
    list_resp = logged_in_client.get("/api/invoices/local")
    assert list_resp.status_code == 200
    list_data = list_resp.get_json()
    assert len(list_data.get("invoices", [])) >= 1, f"No invoices in local DB: {list_data}"

    # Now check provider stats
    stats_resp = logged_in_client.get("/api/providers/stats")
    assert stats_resp.status_code == 200
    stats_data = stats_resp.get_json()
    assert stats_data["total_invoices"] >= 1
    assert stats_data["total_providers"] >= 1

    # Find MISA in stats
    misa_stats = [s for s in stats_data["stats"] if s["mst"] == "0101243150"]
    assert len(misa_stats) == 1
    assert misa_stats[0]["count"] >= 1
    assert misa_stats[0]["short"] == "MISA"
    assert misa_stats[0]["name"] == "MISA meInvoice"


def test_provider_registry_module():
    """Verify the provider_registry module functions work correctly."""
    from invoices.provider_registry import get_provider_info, get_all_providers, PROVIDER_REGISTRY

    # Known provider
    info = get_provider_info("0101243150")
    assert info["short"] == "MISA"
    assert info["icon"] == "cpu-fill"

    # Unknown provider
    info = get_provider_info("9999999999")
    assert info["short"] == "Khác"

    # Empty provider
    info = get_provider_info("")
    assert info["name"] == ""

    # All providers list
    providers = get_all_providers()
    assert len(providers) == len(PROVIDER_REGISTRY)
    assert all("mst" in p for p in providers)
