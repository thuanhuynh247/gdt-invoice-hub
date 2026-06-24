"""Pytest verification suite for v70 Ozone-Depleting Substances (ODS) Quotas & Fees compliance.

Covers: All 5 chemical groups, cumulative threshold logic, save_to_db parameter,
exemption categories, history retrieval, annual summary, delete-log, and API routes.
"""

from __future__ import annotations

import os
import json
import pytest
from flask import Flask
from invoices.multitenant_service import get_tenant_db_path, bootstrap_tenant_db
from invoices.v70_service import V70ComplianceService


@pytest.fixture
def mock_app():
    app = Flask(__name__, template_folder="../templates")
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["BASE_DATA_DIR"] = os.path.dirname(__file__)
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
    mst = "0102030470"
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


# ──────────────────────────────────────────────────────────
# Core Chemical Group Tests
# ──────────────────────────────────────────────────────────

def test_ods_cfc_charge(mock_tenant_db):
    """CFC substance ODS charge: 250,000 VND/kg. ODP factor: 1.0."""
    service = V70ComplianceService()
    res = service.calculate_ods(
        mock_tenant_db, "CFC batch 1", "cfc", weight_kg=100.0, exemption_category="none"
    )
    assert res["odp_factor"] == 1.0
    assert res["odp_weight_eq"] == 100.0
    assert res["license_charge_rate"] == 250000.0
    assert res["final_fee"] == 25000000.0
    assert res["is_exempt"] is False
    # Frontend-mapped keys should match
    assert res["odp_equivalent_kg"] == res["odp_weight_eq"]
    assert res["base_rate_per_kg"] == res["license_charge_rate"]
    assert res["effective_fee_vnd"] == res["final_fee"]


def test_ods_hcfc_charge(mock_tenant_db):
    """HCFC substance ODS charge: 15,000 VND/kg. ODP factor: 0.055."""
    service = V70ComplianceService()
    res = service.calculate_ods(
        mock_tenant_db, "R-22 Refrigerant", "hcfc", weight_kg=1000.0, exemption_category="none"
    )
    assert res["odp_factor"] == 0.055
    assert res["odp_weight_eq"] == pytest.approx(55.0)
    assert res["license_charge_rate"] == 15000.0
    assert res["final_fee"] == 15000000.0


def test_ods_hfc_charge(mock_tenant_db):
    """HFC substance ODS charge: 8,000 VND/kg. ODP factor: 0.0."""
    service = V70ComplianceService()
    res = service.calculate_ods(
        mock_tenant_db, "HFC-134a", "hfc", weight_kg=500.0, exemption_category="none"
    )
    assert res["odp_factor"] == 0.0
    assert res["odp_weight_eq"] == 0.0
    assert res["license_charge_rate"] == 8000.0
    assert res["final_fee"] == 4000000.0


def test_ods_halon_charge(mock_tenant_db):
    """Halon substance ODS charge: 2,500,000 VND/kg. ODP factor: 10.0."""
    service = V70ComplianceService()
    res = service.calculate_ods(
        mock_tenant_db, "Halon-1301", "halon", weight_kg=10.0, exemption_category="none"
    )
    assert res["odp_factor"] == 10.0
    assert res["odp_weight_eq"] == 100.0
    assert res["license_charge_rate"] == 2500000.0
    assert res["final_fee"] == 25000000.0


def test_ods_methyl_bromide_charge(mock_tenant_db):
    """Methyl Bromide ODS charge: 150,000 VND/kg. ODP factor: 0.6."""
    service = V70ComplianceService()
    res = service.calculate_ods(
        mock_tenant_db, "Methyl Bromide Fumigant", "methyl_bromide", weight_kg=200.0, exemption_category="none"
    )
    assert res["odp_factor"] == 0.6
    assert res["odp_weight_eq"] == pytest.approx(120.0)
    assert res["license_charge_rate"] == 150000.0
    assert res["final_fee"] == 30000000.0


# ──────────────────────────────────────────────────────────
# Exemption Tests
# ──────────────────────────────────────────────────────────

def test_ods_low_volume_exemption(mock_tenant_db):
    """Low volume exemption: weight_kg < 50.0."""
    service = V70ComplianceService()
    res = service.calculate_ods(
        mock_tenant_db, "CFC batch 2", "cfc", weight_kg=30.0, exemption_category="none"
    )
    assert res["is_exempt"] is True
    assert res["final_fee"] == 0.0


def test_ods_medical_exemption(mock_tenant_db):
    """Medical inhaler exemption (medical_use category)."""
    service = V70ComplianceService()
    res = service.calculate_ods(
        mock_tenant_db, "Inhaler CFC gas", "cfc", weight_kg=200.0, exemption_category="medical_use"
    )
    assert res["is_exempt"] is True
    assert res["final_fee"] == 0.0
    assert res["exemption_category"] == "medical_use"


def test_ods_research_exemption(mock_tenant_db):
    """Research / laboratory exemption."""
    service = V70ComplianceService()
    res = service.calculate_ods(
        mock_tenant_db, "Lab standard CFC-12", "cfc", weight_kg=50.0, exemption_category="research_study"
    )
    assert res["is_exempt"] is True
    assert res["final_fee"] == 0.0
    assert res["exemption_category"] == "research_study"


# ──────────────────────────────────────────────────────────
# Cumulative Annual Threshold Tests
# ──────────────────────────────────────────────────────────

def test_cumulative_threshold_partial_exemption(mock_tenant_db):
    """When cumulative imports cross 50 kg, the portion above threshold is charged."""
    service = V70ComplianceService()
    # First shipment: 40 kg — should be fully exempt (auto low-volume)
    r1 = service.calculate_ods(mock_tenant_db, "CFC Small-1", "cfc", weight_kg=40.0, exemption_category="none")
    assert r1["is_exempt"] is True
    assert r1["final_fee"] == 0.0

    # Second shipment: 30 kg — cumulative becomes 70 kg, exceeding 50 kg
    # The 10 kg portion that pushed over 50 kg should be exempt,
    # and the 20 kg above threshold should be charged.
    r2 = service.calculate_ods(mock_tenant_db, "CFC Small-2", "cfc", weight_kg=30.0, exemption_category="none")
    assert r2["is_exempt"] is False
    # prev_cumulative=40, total_cumulative=70, exempt_portion=10, chargeable=20
    expected_fee = 20.0 * 250000.0  # 5,000,000 VND
    assert r2["final_fee"] == expected_fee


def test_cumulative_threshold_full_denial(mock_tenant_db):
    """When annual cumulative already exceeds 50 kg, subsequent shipments get no waiver."""
    service = V70ComplianceService()
    # Ship 60 kg first — exceeds 50 kg so it gets partial charge
    service.calculate_ods(mock_tenant_db, "CFC Bulk", "cfc", weight_kg=60.0, exemption_category="none")

    # Second 20 kg shipment — cumulative already 60 kg, so full charge
    r2 = service.calculate_ods(mock_tenant_db, "CFC Extra", "cfc", weight_kg=20.0, exemption_category="none")
    assert r2["is_exempt"] is False
    assert r2["final_fee"] == 20.0 * 250000.0


def test_cumulative_weight_tracking(mock_tenant_db):
    """Verify get_cumulative_annual_weight counts ALL shipments (including exempt)."""
    service = V70ComplianceService()
    assert service.get_cumulative_annual_weight(mock_tenant_db) == 0.0

    # Non-exempt shipment
    service.calculate_ods(mock_tenant_db, "HCFC Standard", "hcfc", weight_kg=500.0, exemption_category="none")
    assert service.get_cumulative_annual_weight(mock_tenant_db) == 500.0

    # Exempt shipment should ALSO count toward cumulative total
    service.calculate_ods(mock_tenant_db, "CFC Medical", "cfc", weight_kg=100.0, exemption_category="medical_use")
    assert service.get_cumulative_annual_weight(mock_tenant_db) == 600.0


# ──────────────────────────────────────────────────────────
# save_to_db Parameter Tests
# ──────────────────────────────────────────────────────────

def test_save_to_db_false_no_persistence(mock_tenant_db):
    """save_to_db=False should not create any database records."""
    service = V70ComplianceService()
    service.calculate_ods(
        mock_tenant_db, "Phantom CFC", "cfc", weight_kg=100.0,
        exemption_category="none", save_to_db=False
    )
    history = service.get_history(mock_tenant_db)
    assert len(history) == 0


def test_save_to_db_true_persists(mock_tenant_db):
    """save_to_db=True (default) should create a database record."""
    service = V70ComplianceService()
    service.calculate_ods(
        mock_tenant_db, "Real CFC", "cfc", weight_kg=100.0,
        exemption_category="none", save_to_db=True
    )
    history = service.get_history(mock_tenant_db)
    assert len(history) == 1
    assert history[0]["substance_name"] == "Real CFC"


# ──────────────────────────────────────────────────────────
# History, Annual Summary & Delete Tests
# ──────────────────────────────────────────────────────────

def test_ods_history(mock_tenant_db):
    service = V70ComplianceService()
    service.calculate_ods(mock_tenant_db, "Inhaler CFC gas", "cfc", weight_kg=200.0, exemption_category="medical_use")
    history = service.get_history(mock_tenant_db)
    assert len(history) >= 1
    assert history[0]["substance_name"] == "Inhaler CFC gas"
    # Verify stored exemption_category is preserved
    assert history[0]["exemption_category"] == "medical_use"


def test_annual_summary(mock_tenant_db):
    """Verify the annual summary aggregation method."""
    service = V70ComplianceService()
    service.calculate_ods(mock_tenant_db, "CFC-1", "cfc", weight_kg=100.0, exemption_category="none")
    service.calculate_ods(mock_tenant_db, "CFC-2", "cfc", weight_kg=200.0, exemption_category="medical_use")
    summary = service.get_annual_summary(mock_tenant_db)
    assert summary["total_shipments"] == 2
    # Only non-exempt counts toward total weight for waiver calc
    assert summary["total_fees_vnd"] > 0
    assert "waiver_remaining_kg" in summary


def test_delete_log(mock_tenant_db):
    """Verify delete_log removes the correct entry."""
    service = V70ComplianceService()
    service.calculate_ods(mock_tenant_db, "Delete-Me", "hcfc", weight_kg=100.0, exemption_category="none")
    history = service.get_history(mock_tenant_db)
    assert len(history) == 1
    log_id = history[0]["id"]
    assert service.delete_log(mock_tenant_db, log_id) is True
    assert len(service.get_history(mock_tenant_db)) == 0
    # Deleting non-existent log returns False
    assert service.delete_log(mock_tenant_db, 99999) is False


# ──────────────────────────────────────────────────────────
# API Route Tests
# ──────────────────────────────────────────────────────────

def test_api_routes_v70(mock_app, mock_tenant_db):
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["taxpayer_mst"] = mock_tenant_db

    res_page = client.get("/v70-compliance-hub")
    assert res_page.status_code == 200

    res_calc = client.post("/api/v70/calculate", json={
        "mst": mock_tenant_db,
        "substance_name": "API ODS HCFC",
        "substance_group": "hcfc",
        "weight_kg": 200.0,
        "exemption_category": "none"
    })
    assert res_calc.status_code == 200
    data = json.loads(res_calc.data)
    assert data["status"] == "success"
    # HCFC ODP = 0.055. Licensing charge rate = 15,000 VND/kg.
    # final_fee = 200 * 15,000 = 3,000,000 VND.
    assert data["results"]["final_fee"] == 3000000.0

    res_data = client.get(f"/api/v70/compliance-data?mst={mock_tenant_db}")
    assert res_data.status_code == 200
    d = json.loads(res_data.data)
    assert d["status"] == "success"
    assert "cfc_standard" in d
    assert "hcfc_standard" in d
    assert "medical_exempt" in d
    assert "cumulative_annual_weight" in d


def test_api_annual_summary_route(mock_app, mock_tenant_db):
    """Verify the /api/v70/annual-summary endpoint."""
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["taxpayer_mst"] = mock_tenant_db

    res = client.get(f"/api/v70/annual-summary?mst={mock_tenant_db}")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["status"] == "success"
    assert "summary" in data
    assert "waiver_remaining_kg" in data["summary"]


def test_api_delete_log_route(mock_app, mock_tenant_db):
    """Verify the /api/v70/delete-log endpoint."""
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["taxpayer_mst"] = mock_tenant_db

    # Create a log entry first via the API (ensures same DB path)
    res_calc = client.post("/api/v70/calculate", json={
        "mst": mock_tenant_db,
        "substance_name": "To-Delete",
        "substance_group": "hfc",
        "weight_kg": 10.0,
        "exemption_category": "none"
    })
    assert res_calc.status_code == 200

    # Fetch history to get the log_id
    service = V70ComplianceService(mock_app.config["BASE_DATA_DIR"])
    history = service.get_history(mock_tenant_db)
    assert len(history) >= 1
    log_id = history[0]["id"]

    # Delete via API
    res = client.post("/api/v70/delete-log", json={"mst": mock_tenant_db, "log_id": log_id})
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["status"] == "success"

    # Attempt to delete again — should 404
    res2 = client.post("/api/v70/delete-log", json={"mst": mock_tenant_db, "log_id": log_id})
    assert res2.status_code == 404
