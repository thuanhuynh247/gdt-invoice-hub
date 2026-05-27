"""Tests for the GDT MST Status Verification service."""

from __future__ import annotations

import os
from unittest.mock import patch, MagicMock

import pytest

from invoices.mst_service import (
    check_mst_status,
    STATUS_ACTIVE,
    STATUS_SUSPENDED,
    STATUS_CLOSED,
    STATUS_NOT_FOUND,
    STATUS_UNKNOWN,
)


def test_mst_service_mock_mode():
    """Test that mock MST codes return the correct predefined tax statuses."""
    with patch.dict(os.environ, {"GDT_USE_MOCK": "true"}):
        # Cong ty A -> ACTIVE
        res_a = check_mst_status("0101234567")
        assert res_a["status"] == STATUS_ACTIVE
        assert res_a["source"] == "mock"

        # Cong ty C -> SUSPENDED
        res_c = check_mst_status("0301222334")
        assert res_c["status"] == STATUS_SUSPENDED

        # Cong ty B -> CLOSED
        res_b = check_mst_status("020976543")
        assert res_b["status"] == STATUS_CLOSED

        # Unrecognized MST -> defaults to ACTIVE
        res_unknown = check_mst_status("9999999999")
        assert res_unknown["status"] == STATUS_ACTIVE


def test_mst_service_empty_input():
    """Test that empty or non-digit MST inputs return NOT_FOUND status."""
    res_empty = check_mst_status("")
    assert res_empty["status"] == STATUS_NOT_FOUND

    res_letters = check_mst_status("ABCDEF")
    assert res_letters["status"] == STATUS_NOT_FOUND


@patch("requests.get")
def test_mst_service_live_scraper_active(mock_get):
    """Test the live scraper with a mock response representing an active company."""
    # Set mock response
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = """
    <html>
        <body>
            <table>
                <tr>
                    <td class="info-label">Trạng thái hoạt động</td>
                    <td>Đang hoạt động (đã được cấp MST)</td>
                </tr>
            </table>
        </body>
    </html>
    """
    mock_get.return_value = mock_resp

    with patch.dict(os.environ, {"GDT_USE_MOCK": "false"}):
        res = check_mst_status("0101234567")
        assert res["status"] == STATUS_ACTIVE
        assert res["source"] == "live_scraper"


@patch("requests.get")
def test_mst_service_live_scraper_closed(mock_get):
    """Test the live scraper with a mock response representing a closed company."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = """
    <html>
        <body>
            <div>Trạng thái: Ngừng hoạt động, đã đóng MST</div>
        </body>
    </html>
    """
    mock_get.return_value = mock_resp

    with patch.dict(os.environ, {"GDT_USE_MOCK": "false"}):
        res = check_mst_status("020976543")
        assert res["status"] == STATUS_CLOSED
        assert res["source"] == "live_scraper"


@patch("requests.get")
def test_mst_service_live_scraper_error(mock_get):
    """Test that live scraper exceptions default to UNKNOWN status."""
    mock_get.side_effect = Exception("Connection timeout")

    with patch.dict(os.environ, {"GDT_USE_MOCK": "false"}):
        res = check_mst_status("0101234567")
        assert res["status"] == STATUS_UNKNOWN
        assert res["source"] == "live_exception"


def test_mst_smart_audit_warnings():
    """Test that the 7th smart audit check adds warnings for non-active seller MSTs."""
    from invoices.service import _run_smart_audits

    # Mock DB
    local_db = []

    # Active seller
    inv_active = {
        "seller_mst": "0101234567",
        "symbol": "1C262026",
        "number": "0000501",
        "total_amount": 1000000.0,
        "payment_method": "CK"
    }
    
    with patch.dict(os.environ, {"GDT_USE_MOCK": "true"}):
        warns_active = _run_smart_audits(inv_active, local_db)
        # Should not have any warning for ACTIVE status
        assert not any("trạng thái" in w for w in warns_active)

        # Closed seller (Cong ty B -> 020976543)
        inv_closed = {
            "seller_mst": "020976543",
            "symbol": "1C262026",
            "number": "0000502",
            "total_amount": 1000000.0,
            "payment_method": "CK"
        }
        warns_closed = _run_smart_audits(inv_closed, local_db)
        assert any("Ngừng hoạt động, đã đóng MST" in w for w in warns_closed)

        # Suspended seller (Cong ty C -> 0301222334)
        inv_suspended = {
            "seller_mst": "0301222334",
            "symbol": "1C262026",
            "number": "0000503",
            "total_amount": 1000000.0,
            "payment_method": "CK"
        }
        warns_suspended = _run_smart_audits(inv_suspended, local_db)
        assert any("Tạm ngừng hoạt động" in w for w in warns_suspended)

