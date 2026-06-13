"""Smart Invoice API compatibility tests."""

from __future__ import annotations

import json


def test_api_login_returns_captcha(client):
    """If captcha is not supplied, it must return a key and SVG content."""
    response = client.post(
        "/API/login",
        json={
            "username": "0316459946",
            "password": "Password123@",
            "captcha": "",
            "key": ""
        }
    )
    assert response.status_code == 200
    data = response.get_json()
    assert "key" in data
    assert "content" in data
    assert "<svg" in data["content"]


def test_api_login_authenticates_success(client):
    """If captcha and key are provided, it should return the JWT token string."""
    # First, get a captcha key
    response = client.post(
        "/API/login",
        json={
            "username": "0316459946",
            "password": "Password123@",
            "captcha": "",
            "key": ""
        }
    )
    data = response.get_json()
    key = data["key"]

    # Now call login with a captcha solution (mock mode accepts any captcha)
    response2 = client.post(
        "/API/login",
        json={
            "username": "0316459946",
            "password": "Password123@",
            "captcha": "ABCDE",
            "key": key
        }
    )
    assert response2.status_code == 200
    token = response2.data.decode("utf-8")
    assert token == "mock-session-0316459946"


def test_api_get_purchase_invoices(client):
    """Get purchase invoices using the compatibility endpoint."""
    token = "mock-session-0316459946"
    
    # Missing headers / auth
    response_no_auth = client.post(
        "/API/get_purchase/0316459946",
        json={
            "fromdate": "01/05/2026",
            "todate": "31/05/2026"
        }
    )
    assert response_no_auth.status_code == 401

    # Valid query
    response = client.post(
        "/API/get_purchase/0316459946",
        headers={"token": token},
        json={
            "fromdate": "01/05/2026",
            "todate": "31/05/2026"
        }
    )
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0
    # Check fields in the mapped output
    first_invoice = data[0]
    for field in ["khmshdon", "khhdon", "shdon", "ntao", "nbten", "nbmst", "nbdchi", "tgtcthue", "tgtthue", "tgtttbso", "dvtte", "cqt", "tchat", "tthai", "ttxly"]:
        assert field in first_invoice


def test_api_get_purchase_items(client):
    """Get detailed items for all matching purchase invoices."""
    token = "mock-session-0316459946"
    
    response = client.post(
        "/API/get_purchase_items/0316459946",
        headers={"token": token},
        json={
            "fromdate": "01/05/2026",
            "todate": "31/05/2026"
        }
    )
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) > 0
    
    # Check individual item fields
    first_item = data[0]
    for field in ["STT", "TChat", "MHHDVu", "THHDVu", "DVTinh", "SLuong", "DGia", "ThTien", "TSuat", "TLCKhau", "STCKhau"]:
        assert field in first_item
