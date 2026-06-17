"""Pytest verification suite for v55 Import-Export Tax (IET) Law 107/2016/QH13.

Verifies correct IET rates for imports and exports, processing contract exemptions,
temporary import/re-export exemptions, low-value gift thresholds, and REST JSON API endpoints.
"""

from __future__ import annotations

import os
import json
import sqlite3
import pytest
from flask import Flask
from invoices.multitenant_service import get_tenant_db_path, bootstrap_tenant_db
from invoices.v55_service import V55ComplianceService


@pytest.fixture
def mock_app():
    """Create a mock Flask app context with base configurations."""
    app = Flask(__name__, template_folder="../templates")
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["BASE_DATA_DIR"] = os.path.join(os.path.dirname(__file__), "..", "data")

    from auth import auth_blueprint
    from invoices.routes import invoices_blueprint
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(invoices_blueprint)

    @app.route("/")
    def index():
        return "index"

    return app


@pytest.fixture
def mock_tenant_db():
    """Ensure a clean tenant DB for testing."""
    mst = "0102030495"
    db_path = get_tenant_db_path(mst)

    if os.path.exists(db_path):
        try:
            os.unlink(db_path)
        except Exception:
            pass

    bootstrap_tenant_db(mst)
    yield mst

    if os.path.exists(db_path):
        try:
            os.unlink(db_path)
        except Exception:
            pass


def test_iet_calculation(mock_tenant_db):
    """Test calculations and exemptions for various import/export configurations."""
    mst = mock_tenant_db
    service = V55ComplianceService()

    # Commercial import preferential (MFN 10%)
    res = service.calculate_import_export_duty(mst, "Heavy Machinery", "import", 2.0, 150000000.0, "preferential", "commercial")
    assert res["standard_rate"] == 0.10
    assert res["effective_rate"] == 0.10
    assert res["duty_amount"] == 30000000.0
    assert res["is_exempt"] is False

    # Processing contract import (100% exempt)
    res = service.calculate_import_export_duty(mst, "Raw Textile", "import", 10000.0, 5000.0, "preferential", "processing contract")
    assert res["standard_rate"] == 0.10
    assert res["effective_rate"] == 0.0
    assert res["duty_amount"] == 0.0
    assert res["is_exempt"] is True
    assert "processing contract" in res["exemption_reason"]

    # Low-value courier gift import (<= 2,000,000 VND, exempt)
    res = service.calculate_import_export_duty(mst, "Sample Product", "import", 1.0, 1500000.0, "preferential", "gift")
    assert res["standard_rate"] == 0.10
    assert res["effective_rate"] == 0.0
    assert res["duty_amount"] == 0.0
    assert res["is_exempt"] is True
    assert "Low-value gift" in res["exemption_reason"]

    # High-value gift import (> 2,000,000 VND, taxable)
    res = service.calculate_import_export_duty(mst, "Luxury Sample", "import", 1.0, 5000000.0, "preferential", "gift")
    assert res["standard_rate"] == 0.10
    assert res["effective_rate"] == 0.10
    assert res["duty_amount"] == 500000.0
    assert res["is_exempt"] is False

    # Export raw materials (MFN 10%)
    res = service.calculate_import_export_duty(mst, "Coal Ore", "export", 100.0, 5000000.0, "preferential", "commercial")
    assert res["standard_rate"] == 0.10
    assert res["effective_rate"] == 0.10
    assert res["duty_amount"] == 50000000.0
    assert res["is_exempt"] is False


def test_api_routes_v55(mock_app, mock_tenant_db):
    """Test V55 endpoints, template render, and database records extraction."""
    client = mock_app.test_client()

    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["taxpayer_mst"] = mock_tenant_db

    # GET compliance hub UI
    res_page = client.get("/v55-compliance-hub")
    assert res_page.status_code == 200
    assert b"Import-Export Tax Compliance" in res_page.data or b"IET" in res_page.data

    # POST calculation
    res_calc = client.post("/api/v55/calculate", json={
        "mst": mock_tenant_db,
        "cargo_name": "Sample Gift Box",
        "cargo_type": "import",
        "quantity": 1,
        "unit_price": 1200000.0,
        "tariff_type": "preferential",
        "goods_purpose": "gift"
    })
    assert res_calc.status_code == 200
    data_calc = json.loads(res_calc.data)
    assert data_calc["status"] == "success"
    assert data_calc["results"]["is_exempt"] is True
    assert data_calc["results"]["duty_amount"] == 0.0

    # GET baseline compliance data
    res_data = client.get(f"/api/v55/compliance-data?mst={mock_tenant_db}")
    assert res_data.status_code == 200
    data = json.loads(res_data.data)
    assert data["status"] == "success"
    assert "import_mfn" in data
    assert "processing_exempt" in data
    assert "export_minerals" in data
    assert "gift_exempt" in data
    assert len(data["history"]) > 0
