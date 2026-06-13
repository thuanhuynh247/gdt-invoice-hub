"""Tests for Group Fund (US-700+ / PRD-FUND) module features and business logic."""

from __future__ import annotations

import json
import os
import pytest
from flask import Flask
from extensions import db
from invoices.models import GroupFund, FundTransaction, TenantGroup

@pytest.fixture
def mock_app():
    """Create a self-contained Flask app configured for testing in isolation without background workers."""
    app = Flask(__name__, template_folder="../templates")
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["BASE_DATA_DIR"] = os.path.join(os.path.dirname(__file__), "..", "data")

    # Initialize extensions
    db.init_app(app)

    # Register blueprints
    from auth import auth_blueprint
    from invoices.routes import invoices_blueprint
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(invoices_blueprint)

    @app.route("/")
    def index():
        return "index"

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(mock_app):
    """Return test client of mock_app."""
    return mock_app.test_client()


@pytest.fixture
def auth_session(client):
    """Authenticate session as admin to access protected endpoints."""
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "admin"
        sess["user_role"] = "admin"
    return client


def test_create_group_fund_success(auth_session, mock_app):
    """Verify group fund creation with a valid name starting at balance 0."""
    with mock_app.app_context():
        # Ensure default TenantGroup is present
        group = TenantGroup(group_name="Tập đoàn GDT Hub", admin_username="admin", taxpayer_msts='["12345"]')
        db.session.add(group)
        db.session.commit()
        group_id = group.id

    # Create new fund
    res = auth_session.post("/api/group-fund", json={
        "group_id": group_id,
        "name": "Quỹ Phòng Hành Chính 101",
        "currency": "VND"
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["status"] == "success"
    assert data["fund"]["name"] == "Quỹ Phòng Hành Chính 101"
    assert data["fund"]["currency"] == "VND"

    # Query the fund state
    res_get = auth_session.get(f"/api/group-fund?group_id={group_id}")
    assert res_get.status_code == 200
    fund_data = res_get.get_json()
    assert fund_data["fund_exists"] is True
    assert fund_data["balance"] == 0.0
    assert fund_data["total_deposits"] == 0.0
    assert fund_data["total_expenses"] == 0.0


def test_create_group_fund_missing_name(auth_session, mock_app):
    """Verify creating a fund with a blank/missing name fails with a 400 error."""
    with mock_app.app_context():
        group = TenantGroup(group_name="Tập đoàn GDT Hub", admin_username="admin", taxpayer_msts='["12345"]')
        db.session.add(group)
        db.session.commit()
        group_id = group.id

    res = auth_session.post("/api/group-fund", json={
        "group_id": group_id,
        "name": ""
    })
    assert res.status_code == 400
    assert "Tên quỹ không được để trống" in res.get_json()["error"]


def test_log_deposit_success_and_balance_update(auth_session, mock_app):
    """Verify logging a valid deposit updates transaction history and balance."""
    with mock_app.app_context():
        group = TenantGroup(group_name="Tập đoàn GDT Hub", admin_username="admin", taxpayer_msts='["12345"]')
        db.session.add(group)
        db.session.commit()
        group_id = group.id

        fund = GroupFund(group_id=group_id, name="Quỹ Tự Động", currency="VND", created_at="2026-06-13T00:00:00Z")
        db.session.add(fund)
        db.session.commit()
        fund_id = fund.id

    # Log deposit
    res = auth_session.post("/api/group-fund/deposit", json={
        "fund_id": fund_id,
        "payer": "Nguyễn Văn A",
        "amount": 1500000.0,
        "date": "2026-06-12"
    })
    assert res.status_code == 201
    assert res.get_json()["status"] == "success"

    # Fetch fund balance
    res_get = auth_session.get(f"/api/group-fund?group_id={group_id}")
    assert res_get.status_code == 200
    fund_data = res_get.get_json()
    assert fund_data["balance"] == 1500000.0
    assert fund_data["total_deposits"] == 1500000.0


def test_log_deposit_invalid_amount(auth_session, mock_app):
    """Verify logging deposit with invalid amount <= 0 or empty is rejected."""
    with mock_app.app_context():
        group = TenantGroup(group_name="Tập đoàn GDT Hub", admin_username="admin", taxpayer_msts='["12345"]')
        db.session.add(group)
        db.session.commit()
        group_id = group.id

        fund = GroupFund(group_id=group_id, name="Quỹ Tự Động", currency="VND", created_at="2026-06-13T00:00:00Z")
        db.session.add(fund)
        db.session.commit()
        fund_id = fund.id

    res = auth_session.post("/api/group-fund/deposit", json={
        "fund_id": fund_id,
        "payer": "Nguyễn Văn A",
        "amount": -500,
        "date": "2026-06-12"
    })
    assert res.status_code == 400
    assert "lớn hơn 0" in res.get_json()["error"]

    res_empty = auth_session.post("/api/group-fund/deposit", json={
        "fund_id": fund_id,
        "payer": "Nguyễn Văn A",
        "amount": "",
        "date": "2026-06-12"
    })
    assert res_empty.status_code == 400
    assert "không hợp lệ hoặc để trống" in res_empty.get_json()["error"]


def test_log_expense_success_and_balance_update(auth_session, mock_app):
    """Verify logging a valid expense decreases the balance and appears in history."""
    with mock_app.app_context():
        group = TenantGroup(group_name="Tập đoàn GDT Hub", admin_username="admin", taxpayer_msts='["12345"]')
        db.session.add(group)
        db.session.commit()
        group_id = group.id

        fund = GroupFund(group_id=group_id, name="Quỹ Tự Động", currency="VND", created_at="2026-06-13T00:00:00Z")
        db.session.add(fund)
        db.session.commit()
        fund_id = fund.id

        # Seed initial deposit
        tx = FundTransaction(
            fund_id=fund_id,
            transaction_type="deposit",
            amount=1000000.0,
            date="2026-06-12",
            payer="admin",
            description="Seed",
            created_at="2026-06-12T00:00:00Z"
        )
        db.session.add(tx)
        db.session.commit()

    # Log expense
    res = auth_session.post("/api/group-fund/expense", json={
        "fund_id": fund_id,
        "description": "Mua văn phòng phẩm",
        "amount": 200000.0,
        "date": "2026-06-13"
    })
    assert res.status_code == 201
    assert res.get_json()["status"] == "success"

    # Get updated balance
    res_get = auth_session.get(f"/api/group-fund?group_id={group_id}")
    assert res_get.get_json()["balance"] == 800000.0


def test_transaction_history_sorting(auth_session, mock_app):
    """Verify that transaction history lists deposits and expenses sorted by date descending."""
    with mock_app.app_context():
        group = TenantGroup(group_name="Tập đoàn GDT Hub", admin_username="admin", taxpayer_msts='["12345"]')
        db.session.add(group)
        db.session.commit()
        group_id = group.id

        fund = GroupFund(group_id=group_id, name="Quỹ Tự Động", currency="VND", created_at="2026-06-13T00:00:00Z")
        db.session.add(fund)
        db.session.commit()
        fund_id = fund.id

    # Insert transactions out of order
    auth_session.post("/api/group-fund/deposit", json={
        "fund_id": fund_id, "payer": "A", "amount": 100, "date": "2026-06-10"
    })
    auth_session.post("/api/group-fund/expense", json={
        "fund_id": fund_id, "description": "B", "amount": 50, "date": "2026-06-15"
    })
    auth_session.post("/api/group-fund/deposit", json={
        "fund_id": fund_id, "payer": "C", "amount": 200, "date": "2026-06-12"
    })

    # Fetch history
    res = auth_session.get(f"/api/group-fund/transactions?fund_id={fund_id}")
    assert res.status_code == 200
    txs = res.get_json()

    assert len(txs) == 3
    # Check descending order of date: 2026-06-15, then 2026-06-12, then 2026-06-10
    assert txs[0]["date"] == "2026-06-15"
    assert txs[1]["date"] == "2026-06-12"
    assert txs[2]["date"] == "2026-06-10"
