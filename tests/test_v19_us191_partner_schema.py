"""US-191: Partner Database Schema & Catalog Management API Tests."""

from __future__ import annotations

import pytest
from extensions import db
from invoices.models import Partner


def test_partner_model_attributes():
    """Verify decree_132_relationship column is defined in the model."""
    assert hasattr(Partner, "decree_132_relationship")
    
    partner = Partner(
        mst="1234567890",
        name="Test Company",
        address="Test Address",
        mst_status="Active",
        decree_132_relationship="A"
    )
    assert partner.decree_132_relationship == "A"
    
    d = partner.to_dict()
    assert "decree_132_relationship" in d
    assert d["decree_132_relationship"] == "A"


def test_get_partners_requires_auth(client):
    """Anonymous access to GET /api/partners should fail with 401."""
    response = client.get("/api/partners")
    assert response.status_code == 401


def test_get_partners_success(app, logged_in_client):
    """Authenticated user should be able to fetch partners."""
    with app.app_context():
        # Seed test partners
        p1 = Partner(mst="0101112223", name="Partner One", address="Address One", decree_132_relationship="B")
        p2 = Partner(mst="0202223334", name="Partner Two", address="Address Two", decree_132_relationship=None)
        db.session.add_all([p1, p2])
        db.session.commit()

    response = logged_in_client.get("/api/partners")
    print("RESPONSE STATUS:", response.status_code)
    print("RESPONSE DATA:", response.data)
    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload) >= 2
    
    # Check returned values
    msts = [p["mst"] for p in payload]
    assert "0101112223" in msts
    assert "0202223334" in msts
    
    p1_data = next(p for p in payload if p["mst"] == "0101112223")
    assert p1_data["decree_132_relationship"] == "B"
    
    p2_data = next(p for p in payload if p["mst"] == "0202223334")
    assert p2_data["decree_132_relationship"] == ""


def test_update_partner_decree_132_anonymous(client):
    """Anonymous access to POST /api/partners/<mst>/decree-132 should fail with 401."""
    response = client.post("/api/partners/0101112223/decree-132", json={"decree_132_relationship": "A"})
    assert response.status_code == 401


def test_update_partner_decree_132_viewer_forbidden(logged_in_client):
    """Viewer role should not be allowed to update decree 132 relationship."""
    with logged_in_client.session_transaction() as sess:
        sess["user_role"] = "viewer"
    
    response = logged_in_client.post("/api/partners/0101112223/decree-132", json={"decree_132_relationship": "A"})
    assert response.status_code == 403


def test_update_partner_decree_132_workflow(app, logged_in_client):
    """Verify updating partner decree 132 relationship code works correctly."""
    with app.app_context():
        p = Partner(mst="0303334445", name="Partner Three", address="Address Three", decree_132_relationship=None)
        db.session.add(p)
        db.session.commit()

    with logged_in_client.session_transaction() as sess:
        sess["user_role"] = "admin"

    # 1. 404 for non-existent partner
    response = logged_in_client.post("/api/partners/9999999999/decree-132", json={"decree_132_relationship": "A"})
    assert response.status_code == 404

    # 2. 400 for invalid relationship code (e.g. 'Z')
    response = logged_in_client.post("/api/partners/0303334445/decree-132", json={"decree_132_relationship": "Z"})
    assert response.status_code == 400
    assert "Mã liên kết không hợp lệ" in response.get_json()["error"]

    # 3. 200 for valid relationship code (lowercase 'a') - should be converted to uppercase 'A'
    response = logged_in_client.post("/api/partners/0303334445/decree-132", json={"decree_132_relationship": "a"})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["partner"]["decree_132_relationship"] == "A"

    # Verify db status
    with app.app_context():
        partner_db = db.session.get(Partner, "0303334445")
        assert partner_db.decree_132_relationship == "A"

    # 4. 200 for resetting relationship code (send empty string)
    response = logged_in_client.post("/api/partners/0303334445/decree-132", json={"decree_132_relationship": ""})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["partner"]["decree_132_relationship"] == ""

    with app.app_context():
        partner_db = db.session.get(Partner, "0303334445")
        assert partner_db.decree_132_relationship is None

    # 5. 200 for resetting relationship code (send None)
    response = logged_in_client.post("/api/partners/0303334445/decree-132", json={"decree_132_relationship": None})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["partner"]["decree_132_relationship"] == ""
