"""
Tests for TaxpayerProfile model and database schema migrations.
Verifies multi-MST profile properties, cascade behaviors, and columns.
"""

from __future__ import annotations

import pytest
from extensions import db
from invoices.models import Invoice, TaxpayerProfile


def test_taxpayer_profile_creation(app):
    """Verify that we can create, retrieve, and delete taxpayer profiles in the database."""
    with app.app_context():
        # Clear existing
        Invoice.query.delete()
        TaxpayerProfile.query.delete()
        db.session.commit()

        # Create taxpayer profile
        profile = TaxpayerProfile(
            mst="1234567890",
            company_name="Công ty TNHH Giải pháp Đám mây",
            gdt_username="gdt_user_123",
            gdt_password_encrypted="encrypted_password_blob_here",
            is_active=True,
            created_at="2026-05-25 11:45:00"
        )
        db.session.add(profile)
        db.session.commit()

        # Retrieve profile
        fetched = db.session.get(TaxpayerProfile, "1234567890")
        assert fetched is not None
        assert fetched.company_name == "Công ty TNHH Giải pháp Đám mây"
        assert fetched.gdt_username == "gdt_user_123"
        assert fetched.gdt_password_encrypted == "encrypted_password_blob_here"
        assert fetched.is_active is True

        # Assert to_dict representation
        p_dict = fetched.to_dict()
        assert p_dict["mst"] == "1234567890"
        assert p_dict["company_name"] == "Công ty TNHH Giải pháp Đám mây"
        assert p_dict["gdt_username"] == "gdt_user_123"
        assert p_dict["is_active"] is True
        assert "gdt_password_encrypted" not in p_dict  # Password should not be exposed in dict


def test_taxpayer_profile_cascade_delete(app):
    """Verify that deleting a taxpayer profile cascades deletes to related invoices."""
    with app.app_context():
        # Clear existing
        Invoice.query.delete()
        TaxpayerProfile.query.delete()
        db.session.commit()

        # Create profile
        profile = TaxpayerProfile(
            mst="0109999999",
            company_name="Tenant ABC",
            gdt_username="username_abc",
            gdt_password_encrypted="secret",
            is_active=True,
            created_at="2026-05-25 11:45:00"
        )
        db.session.add(profile)

        # Create related invoice
        inv = Invoice(
            id="test-cascade-inv-99",
            number="99",
            date="2026-05-25",
            seller_name="Seller X",
            seller_mst="88888888",
            total_amount=200.0,
            taxpayer_mst="0109999999",
            imported_at="2026-05-25 11:45:00"
        )
        db.session.add(inv)
        db.session.commit()

        # Verify relationship link
        fetched_inv = db.session.get(Invoice, "test-cascade-inv-99")
        assert fetched_inv is not None
        assert fetched_inv.taxpayer_mst == "0109999999"
        assert fetched_inv.taxpayer.company_name == "Tenant ABC"

        # Delete profile
        db.session.delete(profile)
        db.session.commit()

        # Verify profile is deleted
        assert db.session.get(TaxpayerProfile, "0109999999") is None

        # Verify cascade delete of related invoices
        assert db.session.get(Invoice, "test-cascade-inv-99") is None


def test_schema_migration_columns(app):
    """Verify that the dynamic migration script added the taxpayer_mst column to the invoice table."""
    with app.app_context():
        res = db.session.execute(db.text("PRAGMA table_info(invoice);")).fetchall()
        columns = [r[1] for r in res]
        assert "taxpayer_mst" in columns


def test_api_profiles_requires_login(client):
    """Verify that profile API endpoints require authentication."""
    r_get = client.get("/api/profiles")
    assert r_get.status_code == 401

    r_post = client.post("/api/profiles", json={})
    assert r_post.status_code == 401

    r_delete = client.delete("/api/profiles/1234567890")
    assert r_delete.status_code == 401


def test_api_profiles_crud_lifecycle(logged_in_client, app):
    """Verify the full lifecycle (GET, POST, DELETE) of taxpayer profiles via API."""
    with app.app_context():
        # Clear existing database
        Invoice.query.delete()
        TaxpayerProfile.query.delete()
        db.session.commit()

    # 1. Post a new profile with invalid fields (e.g. wrong MST format)
    r_fail = logged_in_client.post("/api/profiles", json={
        "mst": "123",
        "company_name": "Invalid MST Co",
        "gdt_username": "user123",
        "gdt_password": "pass"
    })
    assert r_fail.status_code == 400
    assert "Mã số thuế không đúng định dạng" in r_fail.get_json()["error"]

    # 2. Post a valid profile
    r_success = logged_in_client.post("/api/profiles", json={
        "mst": "0101234567",
        "company_name": "Công ty TNHH Giải pháp Đám mây",
        "gdt_username": "gdt_user_abc",
        "gdt_password": "gdt_secret_password"
    })
    assert r_success.status_code == 200
    payload = r_success.get_json()
    assert payload["success"] is True
    assert payload["profile"]["mst"] == "0101234567"
    assert payload["profile"]["company_name"] == "Công ty TNHH Giải pháp Đám mây"

    # Verify decryption on database level
    with app.app_context():
        from auth.crypto import decrypt_password
        db_profile = db.session.get(TaxpayerProfile, "0101234567")
        assert db_profile is not None
        assert decrypt_password(db_profile.gdt_password_encrypted) == "gdt_secret_password"

    # 3. Get profiles list
    r_list = logged_in_client.get("/api/profiles")
    assert r_list.status_code == 200
    list_payload = r_list.get_json()
    assert len(list_payload) == 1
    assert list_payload[0]["mst"] == "0101234567"

    # 4. Update the profile
    r_update = logged_in_client.post("/api/profiles", json={
        "mst": "0101234567",
        "company_name": "Công ty TNHH Cập nhật",
        "gdt_username": "new_gdt_user",
        "gdt_password": "new_gdt_password"
    })
    assert r_update.status_code == 200
    assert r_update.get_json()["profile"]["company_name"] == "Công ty TNHH Cập nhật"

    # 5. Delete the profile
    r_delete = logged_in_client.delete("/api/profiles/0101234567")
    assert r_delete.status_code == 200
    assert r_delete.get_json()["success"] is True

    # Verify deleted
    with app.app_context():
        assert db.session.get(TaxpayerProfile, "0101234567") is None

    # Delete not found
    r_delete_404 = logged_in_client.delete("/api/profiles/0101234567")
    assert r_delete_404.status_code == 404


def test_api_switch_profile(logged_in_client, app):
    """Verify that switching taxpayer profiles alters session and filters local invoices."""
    with app.app_context():
        # Clear existing
        Invoice.query.delete()
        TaxpayerProfile.query.delete()
        db.session.commit()

        # Create two profiles
        p1 = TaxpayerProfile(
            mst="0101111111",
            company_name="Company One",
            gdt_username="user1",
            gdt_password_encrypted="enc1",
            is_active=True,
            created_at="2026-05-25 11:45:00"
        )
        p2 = TaxpayerProfile(
            mst="0202222222",
            company_name="Company Two",
            gdt_username="user2",
            gdt_password_encrypted="enc2",
            is_active=True,
            created_at="2026-05-25 11:45:00"
        )
        db.session.add_all([p1, p2])

        # Create invoices for both
        i1 = Invoice(
            id="inv-p1",
            number="01",
            date="2026-05-25",
            seller_name="Seller A",
            total_amount=100.0,
            taxpayer_mst="0101111111",
            imported_at="2026-05-25 11:45:00"
        )
        i2 = Invoice(
            id="inv-p2",
            number="02",
            date="2026-05-25",
            seller_name="Seller B",
            total_amount=200.0,
            taxpayer_mst="0202222222",
            imported_at="2026-05-25 11:45:00"
        )
        db.session.add_all([i1, i2])
        db.session.commit()

    # 1. Switch to Company One
    r_switch = logged_in_client.post("/api/profiles/switch", json={"mst": "0101111111"})
    assert r_switch.status_code == 200
    assert r_switch.get_json()["active_taxpayer_mst"] == "0101111111"

    # Verify session active profile
    with logged_in_client.session_transaction() as session:
        assert session["active_taxpayer_mst"] == "0101111111"

    # 2. Get local invoices, should only return inv-p1
    r_invs = logged_in_client.get("/api/invoices/local")
    assert r_invs.status_code == 200
    payload = r_invs.get_json()
    assert len(payload["invoices"]) == 1
    assert payload["invoices"][0]["id"] == "inv-p1"

    # 3. Switch to "all" (reset)
    r_reset = logged_in_client.post("/api/profiles/switch", json={"mst": "all"})
    assert r_reset.status_code == 200
    assert r_reset.get_json()["active_taxpayer_mst"] is None

    # Get local invoices, should return both
    r_invs_all = logged_in_client.get("/api/invoices/local")
    assert r_invs_all.status_code == 200
    assert len(r_invs_all.get_json()["invoices"]) == 2


