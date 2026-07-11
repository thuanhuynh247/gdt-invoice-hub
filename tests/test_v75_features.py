import os
import json
import pytest
import sqlite3
from flask import Flask
from invoices.v75_service import V75ComplianceService
from invoices.multitenant_service import get_tenant_db_path, bootstrap_tenant_db

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

def test_v75_plastics_levy_service_standard_rates(mock_tenant_db):
    """
    US-893 Requirement 1: Base rates for plastic bags, cups/straws, and EPS boxes.
    Note: In V75 compliance service, these are represented by:
      - plastic_bags (base rate: 50,000 VND/kg)
      - plastic_packaging (covers cups/straws/EPS boxes/other packaging, base rate: 30,000 VND/kg)
      - microbeads_cosmetics (base rate: 150,000 VND/kg)
    """
    service = V75ComplianceService()

    # 1. Plastic bags rate check
    res_bags = service.calculate_levy(mock_tenant_db, "plastic_bags", 10.0)
    assert res_bags["charge_rate"] == 50000.0
    assert res_bags["gross_fee"] == 500000.0
    assert res_bags["final_fee"] == 500000.0
    assert res_bags["is_exempt"] is False

    # 2. Plastic packaging (cups/straws/EPS boxes) rate check
    res_packaging = service.calculate_levy(mock_tenant_db, "plastic_packaging", 20.0)
    assert res_packaging["charge_rate"] == 30000.0
    assert res_packaging["gross_fee"] == 600000.0
    assert res_packaging["final_fee"] == 600000.0
    assert res_packaging["is_exempt"] is False

    # 3. Cosmetics microbeads rate check
    res_microbeads = service.calculate_levy(mock_tenant_db, "microbeads_cosmetics", 5.0)
    assert res_microbeads["charge_rate"] == 150000.0
    assert res_microbeads["gross_fee"] == 750000.0
    assert res_microbeads["final_fee"] == 750000.0
    assert res_microbeads["is_exempt"] is False


def test_v75_plastics_levy_service_exemptions(mock_tenant_db):
    """
    US-893 Requirement 2: Biodegradable plastic, export packaging, and agricultural mulching film exemptions.
    Note: Under V75:
      - biodegradable_certified represents certified biodegradable plastic and agricultural mulching film exemptions.
      - medical_containment represents medical waste containment and specialized packaging exemptions.
    """
    service = V75ComplianceService()

    # 1. Certified biodegradable plastic exemption
    res_biodeg = service.calculate_levy(mock_tenant_db, "plastic_packaging", 100.0, biodegradable_certified=True)
    assert res_biodeg["gross_fee"] == 3000000.0
    assert res_biodeg["final_fee"] == 0.0
    assert res_biodeg["is_exempt"] is True
    assert "certified biodegradable material status" in res_biodeg["notes"]

    # 2. Medical containment exemption
    res_medical = service.calculate_levy(mock_tenant_db, "plastic_bags", 50.0, medical_containment=True)
    assert res_medical["gross_fee"] == 2500000.0
    assert res_medical["final_fee"] == 0.0
    assert res_medical["is_exempt"] is True
    assert "medical containment packaging standard compliance" in res_medical["notes"]

    # 3. Combined exemptions
    res_both = service.calculate_levy(mock_tenant_db, "microbeads_cosmetics", 10.0, biodegradable_certified=True, medical_containment=True)
    assert res_both["gross_fee"] == 1500000.0
    assert res_both["final_fee"] == 0.0
    assert res_both["is_exempt"] is True


def test_v75_plastics_levy_service_validation(mock_tenant_db):
    """Verify validation constraints for V75 service."""
    service = V75ComplianceService()

    # Negative quantity validation
    with pytest.raises(ValueError, match="Quantity in kg must be non-negative"):
        service.calculate_levy(mock_tenant_db, "plastic_bags", -5.0)

    # Invalid category validation
    with pytest.raises(ValueError, match="Invalid plastic category"):
        service.calculate_levy(mock_tenant_db, "unknown_category", 10.0)


def test_v75_plastics_levy_persistence_and_history(mock_tenant_db):
    """
    US-893 Requirement 4: Persistence of plastic levy logs.
    Verifies that the logs are properly saved to the multitenant isolation db, and history/annual summary work.
    """
    service = V75ComplianceService()
    
    # Initialize connection to ensure the tables are created
    service.get_tenant_connection(mock_tenant_db).close()

    # Clean database trace
    db_path = get_tenant_db_path(mock_tenant_db)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM plastics_levy_logs")
    conn.commit()
    conn.close()

    # Log two distinct entries
    service.calculate_levy(mock_tenant_db, "plastic_bags", 10.0)
    service.calculate_levy(mock_tenant_db, "plastic_packaging", 20.0, biodegradable_certified=True)

    # Verify database directly to check persistence
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM plastics_levy_logs ORDER BY id ASC")
    rows = cur.fetchall()
    conn.close()

    assert len(rows) == 2
    
    # Assert fields are correctly persisted
    assert rows[0][1] == "plastic_bags"
    assert rows[0][2] == 10.0
    assert rows[0][3] == 0  # False
    assert rows[0][4] == 0  # False
    assert rows[0][5] == 50000.0
    assert rows[0][6] == 500000.0
    assert rows[0][7] == 500000.0
    assert rows[0][8] == 0  # False

    assert rows[1][1] == "plastic_packaging"
    assert rows[1][2] == 20.0
    assert rows[1][3] == 1  # True
    assert rows[1][4] == 0  # False
    assert rows[1][5] == 30000.0
    assert rows[1][6] == 600000.0
    assert rows[1][7] == 0.0
    assert rows[1][8] == 1  # True

    # Check history retrieval
    history = service.get_history(mock_tenant_db, limit=5)
    assert len(history) == 2
    assert history[0]["plastic_category"] == "plastic_packaging"
    assert history[1]["plastic_category"] == "plastic_bags"

    # Check annual summary
    summary = service.get_annual_summary(mock_tenant_db)
    assert summary["total_shipments"] == 2
    assert summary["total_quantity_kg"] == 30.0
    assert summary["total_gross_fee"] == 1100000.0
    assert summary["total_final_fee"] == 500000.0
    assert summary["total_exempt_fee"] == 600000.0
    assert summary["exempt_count"] == 1
    assert summary["charged_count"] == 1

    # Check deletion
    log_id = history[0]["id"]
    deleted = service.delete_log(mock_tenant_db, log_id)
    assert deleted is True

    # Re-verify history count
    history_after = service.get_history(mock_tenant_db)
    assert len(history_after) == 1
    assert history_after[0]["id"] != log_id


def test_v75_flask_api_routes(mock_app, mock_tenant_db):
    """
    US-893 Requirement 3: Flask REST API routes.
    Covers the endpoints:
      - /v75-compliance-hub
      - /api/v75/calculate
      - /api/v75/compliance-data
      - /api/v75/annual-summary
      - /api/v75/delete-log
    """
    client = mock_app.test_client()
    
    # 1. Check redirect to login if not authenticated
    r_unauth = client.get("/v75-compliance-hub")
    assert r_unauth.status_code == 302

    # Authenticate the user
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["taxpayer_mst"] = mock_tenant_db

    # 2. Check compliance hub rendering (GET /v75-compliance-hub)
    r_page = client.get("/v75-compliance-hub")
    assert r_page.status_code == 200
    assert b"Single-Use Plastics Levy Hub" in r_page.data or b"Plastics Levy & Ocean Pollution" in r_page.data

    # Initialize connection to ensure the tables are created
    service = V75ComplianceService()
    service.get_tenant_connection(mock_tenant_db).close()

    # Clean the database to start fresh
    db_path = get_tenant_db_path(mock_tenant_db)
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("DELETE FROM plastics_levy_logs")
    conn.commit()
    conn.close()

    # 3. Check calculate API (POST /api/v75/calculate)
    r_calc = client.post("/api/v75/calculate", json={
        "mst": mock_tenant_db,
        "plastic_category": "microbeads_cosmetics",
        "quantity_kg": 15.0,
        "biodegradable_certified": False,
        "medical_containment": False
    })
    assert r_calc.status_code == 200
    d_calc = json.loads(r_calc.data)
    assert d_calc["status"] == "success"
    assert d_calc["results"]["final_fee"] == 2250000.0

    # 4. Check compliance data API (GET /api/v75/compliance-data)
    r_data = client.get(f"/api/v75/compliance-data?mst={mock_tenant_db}")
    assert r_data.status_code == 200
    d_data = json.loads(r_data.data)
    assert d_data["status"] == "success"
    assert "microbeads_standard" in d_data
    assert "bags_standard" in d_data
    assert "packaging_exempt" in d_data
    assert "debate" in d_data
    assert "consensus_summary" in d_data
    assert len(d_data["history"]) >= 1

    # 5. Check annual summary API (GET /api/v75/annual-summary)
    r_summary = client.get(f"/api/v75/annual-summary?mst={mock_tenant_db}")
    assert r_summary.status_code == 200
    d_summary = json.loads(r_summary.data)
    assert d_summary["status"] == "success"
    assert d_summary["summary"]["total_shipments"] >= 1

    # Get log ID to delete
    log_id = d_data["history"][0]["id"]

    # 6. Check delete log API (POST /api/v75/delete-log)
    r_delete = client.post("/api/v75/delete-log", json={
        "mst": mock_tenant_db,
        "log_id": log_id
    })
    assert r_delete.status_code == 200
    d_delete = json.loads(r_delete.data)
    assert d_delete["status"] == "success"
    assert d_delete["deleted"] is True

    # Re-fetch compliance data to verify it was deleted
    r_data_after = client.get(f"/api/v75/compliance-data?mst={mock_tenant_db}")
    d_data_after = json.loads(r_data_after.data)
    assert not any(h["id"] == log_id for h in d_data_after["history"])
