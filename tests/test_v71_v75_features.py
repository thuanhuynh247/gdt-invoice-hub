"""Pytest verification suite for V71-V75 Environmental Compliance Modules.
"""

from __future__ import annotations

import os
import json
import pytest
from flask import Flask
from invoices.multitenant_service import get_tenant_db_path, bootstrap_tenant_db
from invoices.v71_service import V71ComplianceService
from invoices.v72_service import V72ComplianceService
from invoices.v73_service import V73ComplianceService
from invoices.v74_service import V74ComplianceService
from invoices.v75_service import V75ComplianceService


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
    mst = "0102030499"
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


# --- V71 EPR TESTING ---
def test_v71_epr_standard(mock_tenant_db):
    service = V71ComplianceService()
    res = service.calculate_epr(mock_tenant_db, "laptop", 100.0)
    assert res["charge_rate"] == 20000.0
    assert res["gross_fee"] == 2000000.0
    assert res["final_fee"] == 2000000.0
    assert res["is_exempt"] is False

def test_v71_epr_export_exemption(mock_tenant_db):
    service = V71ComplianceService()
    res = service.calculate_epr(mock_tenant_db, "laptop", 100.0, is_export=True)
    assert res["final_fee"] == 0.0
    assert res["is_exempt"] is True
    assert res["exemption_type"] == "export_exemption"

def test_v71_epr_small_scale_exemption(mock_tenant_db):
    service = V71ComplianceService()
    # preceding_year_revenue < 30B VND
    res = service.calculate_epr(mock_tenant_db, "laptop", 100.0, preceding_year_revenue=25000000000.0)
    assert res["final_fee"] == 0.0
    assert res["is_exempt"] is True
    assert res["exemption_type"] == "small_scale_revenue_exemption"

    # preceding_year_import_value < 3B VND
    res2 = service.calculate_epr(mock_tenant_db, "battery", 100.0, preceding_year_import_value=2500000000.0)
    assert res2["final_fee"] == 0.0
    assert res2["is_exempt"] is True
    assert res2["exemption_type"] == "small_scale_import_exemption"


# --- V72 WASTEWATER TESTING ---
def test_v72_wastewater_flat_rate(mock_tenant_db):
    service = V72ComplianceService()
    # quarterly volume = 1000 m3 -> daily average = 11.1 m3/day (< 20)
    res = service.calculate_surcharge(mock_tenant_db, 1000.0, 150.0, 80.0)
    assert res["gross_fee"] == 375000.0
    assert res["final_fee"] == 375000.0
    assert res["is_exempt"] is False

def test_v72_wastewater_load_rate(mock_tenant_db):
    service = V72ComplianceService()
    # quarterly volume = 5000 m3 -> daily average = 55.5 m3/day (> 20)
    res = service.calculate_surcharge(mock_tenant_db, 5000.0, 300.0, 150.0, pb_mg_l=0.2, cd_mg_l=0.1)
    # COD load = 5000 * 300 / 1000 = 1500 kg -> fee = 1500 * 2000 = 3,000,000 VND
    # TSS load = 5000 * 150 / 1000 = 750 kg -> fee = 750 * 4000 = 3,000,000 VND
    # Pb load = 5000 * 0.2 / 1000 = 1.0 kg -> fee = 1.0 * 1,000,000 = 1,000,000 VND
    # Cd load = 5000 * 0.1 / 1000 = 0.5 kg -> fee = 0.5 * 10,000,000 = 5,000,000 VND
    # Total gross_fee = 12,000,000 VND
    assert res["gross_fee"] == 12000000.0
    assert res["final_fee"] == 12000000.0
    assert res["is_exempt"] is False

def test_v72_wastewater_exemptions(mock_tenant_db):
    service = V72ComplianceService()
    # cooling water
    res = service.calculate_surcharge(mock_tenant_db, 5000.0, 300.0, 150.0, cooling_water=True)
    assert res["final_fee"] == 0.0
    assert res["is_exempt"] is True


# --- V73 HAZARDOUS WASTE TESTING ---
def test_v73_hazardous_waste_disposal(mock_tenant_db):
    service = V73ComplianceService()
    res = service.calculate_hazardous_waste(mock_tenant_db, "category_a", 250.0, apply_license=False)
    # 250 * 2000 = 500k VND
    assert res["license_fee"] == 0.0
    assert res["disposal_fee"] == 500000.0
    assert res["final_fee"] == 500000.0

def test_v73_hazardous_waste_license(mock_tenant_db):
    service = V73ComplianceService()
    res = service.calculate_hazardous_waste(mock_tenant_db, "category_b", 100.0, apply_license=True, annual_weight_kg=1000.0)
    # 100 * 5000 = 500k disposal. Base license fee = 5M. Total = 5.5M.
    assert res["license_fee"] == 5000000.0
    assert res["disposal_fee"] == 500000.0
    assert res["final_fee"] == 5500000.0
    assert res["is_exempt"] is False

def test_v73_hazardous_waste_exemptions(mock_tenant_db):
    service = V73ComplianceService()
    res = service.calculate_hazardous_waste(mock_tenant_db, "category_b", 100.0, apply_license=True, is_research_lab=True)
    # License fee is exempt, but disposal fee remains. Total = 500k.
    assert res["license_fee"] == 0.0
    assert res["final_fee"] == 500000.0
    assert res["is_exempt"] is True


# --- V74 NOISE & VIBRATION TESTING ---
def test_v74_noise_vibration_day(mock_tenant_db):
    service = V74ComplianceService()
    # day limit: noise 70 dBA, vibration 0.055 m/s²
    # measured noise: 75 dBA (+5 dBA) -> 5 * 100k = 500k
    # measured vibration: 0.075 m/s² (+0.02 m/s²) -> (0.02 / 0.01) * 5M = 10M
    # Total = 10.5M
    res = service.calculate_surcharge(mock_tenant_db, 75.0, 0.075, shift="day")
    assert res["noise_surcharge"] == 500000.0
    assert res["vibration_surcharge"] == 10000000.0
    assert res["gross_fee"] == 10500000.0
    assert res["final_fee"] == 10500000.0
    assert res["is_exempt"] is False

def test_v74_noise_vibration_night(mock_tenant_db):
    service = V74ComplianceService()
    # night limit: noise 55 dBA, vibration 0.055 m/s²
    # measured noise: 58 dBA (+3 dBA) -> 3 * 100k = 300k
    # measured vibration: 0.045 m/s² (no exceedance) -> 0
    # multiplier = 1.5
    # Total = 300k * 1.5 = 450k
    res = service.calculate_surcharge(mock_tenant_db, 58.0, 0.045, shift="night")
    assert res["noise_surcharge"] == 300000.0
    assert res["vibration_surcharge"] == 0.0
    assert res["gross_fee"] == 450000.0
    assert res["final_fee"] == 450000.0

def test_v74_noise_vibration_exempt(mock_tenant_db):
    service = V74ComplianceService()
    res = service.calculate_surcharge(mock_tenant_db, 80.0, 0.080, traditional_festival=True)
    assert res["final_fee"] == 0.0
    assert res["is_exempt"] is True


# --- V75 PLASTICS LEVY TESTING ---
def test_v75_plastics_levy_standard(mock_tenant_db):
    service = V75ComplianceService()
    res = service.calculate_levy(mock_tenant_db, "plastic_bags", 250.0)
    assert res["charge_rate"] == 50000.0
    assert res["gross_fee"] == 12500000.0
    assert res["final_fee"] == 12500000.0
    assert res["is_exempt"] is False

def test_v75_plastics_levy_exempt(mock_tenant_db):
    service = V75ComplianceService()
    res = service.calculate_levy(mock_tenant_db, "plastic_packaging", 500.0, biodegradable_certified=True)
    assert res["final_fee"] == 0.0
    assert res["is_exempt"] is True


# --- FLASK API ROUTES TESTING ---
def test_flask_endpoints_v71_v75(mock_app, mock_tenant_db):
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["taxpayer_mst"] = mock_tenant_db

    # V71 check
    r1_page = client.get("/v71-compliance-hub")
    assert r1_page.status_code == 200
    r1_calc = client.post("/api/v71/calculate", json={
        "mst": mock_tenant_db,
        "product_category": "phone",
        "quantity": 1000.0
    })
    assert r1_calc.status_code == 200
    d1 = json.loads(r1_calc.data)
    assert d1["status"] == "success"
    assert d1["results"]["final_fee"] == 5000000.0

    # V72 check
    r2_page = client.get("/v72-compliance-hub")
    assert r2_page.status_code == 200
    r2_calc = client.post("/api/v72/calculate", json={
        "mst": mock_tenant_db,
        "volume_m3": 1000.0,
        "cod_mg_l": 100.0,
        "tss_mg_l": 50.0
    })
    assert r2_calc.status_code == 200
    d2 = json.loads(r2_calc.data)
    assert d2["status"] == "success"

    # V73 check
    r3_page = client.get("/v73-compliance-hub")
    assert r3_page.status_code == 200
    r3_calc = client.post("/api/v73/calculate", json={
        "mst": mock_tenant_db,
        "waste_category": "category_a",
        "weight_kg": 150.0,
        "apply_license": True
    })
    assert r3_calc.status_code == 200
    d3 = json.loads(r3_calc.data)
    assert d3["status"] == "success"

    # V74 check
    r4_page = client.get("/v74-compliance-hub")
    assert r4_page.status_code == 200
    r4_calc = client.post("/api/v74/calculate", json={
        "mst": mock_tenant_db,
        "noise_db": 82.0,
        "vibration_m_s2": 0.075,
        "shift": "day"
    })
    assert r4_calc.status_code == 200
    d4 = json.loads(r4_calc.data)
    assert d4["status"] == "success"

    # V75 check
    r5_page = client.get("/v75-compliance-hub")
    assert r5_page.status_code == 200
    r5_calc = client.post("/api/v75/calculate", json={
        "mst": mock_tenant_db,
        "plastic_category": "microbeads_cosmetics",
        "quantity_kg": 20.0
    })
    assert r5_calc.status_code == 200
    d5 = json.loads(r5_calc.data)
    assert d5["status"] == "success"
