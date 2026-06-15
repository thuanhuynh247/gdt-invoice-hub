"""Pytest verification suite for Compliance Concept Map Explorer.
"""

from __future__ import annotations

import os
import json
import pytest
from flask import Flask

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

def test_concept_map_route_anonymous(mock_app):
    """Verify that anonymous users are redirected to login."""
    client = mock_app.test_client()
    res = client.get("/compliance-concept-map")
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]

def test_concept_map_route_authenticated(mock_app):
    """Verify that logged-in users can access the concept map page."""
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["taxpayer_mst"] = "0102030470"

    res = client.get("/compliance-concept-map")
    assert res.status_code == 200
    assert b"Compliance Concept Map Explorer" in res.data

def test_concept_map_api(mock_app):
    """Verify the JSON structure returned by the concept map API."""
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["taxpayer_mst"] = "0102030470"

    res = client.get("/api/compliance/concept-map")
    assert res.status_code == 200
    data = json.loads(res.data)
    
    assert "nodes" in data
    assert "links" in data
    
    # Check for v26, v53, v70 and correct properties
    nodes = data["nodes"]
    v26 = next((n for n in nodes if n["id"] == "v26"), None)
    v53 = next((n for n in nodes if n["id"] == "v53"), None)
    v70 = next((n for n in nodes if n["id"] == "v70"), None)
    
    assert v26 is not None
    assert v26["group"] == "income"
    assert v26["risk"] == "high"
    
    assert v53 is not None
    assert v53["group"] == "environmental"
    assert v53["risk"] == "high"
    
    assert v70 is not None
    assert v70["group"] == "environmental"
    assert v70["risk"] == "medium"
    
    # Check relationships
    links = data["links"]
    assert len(links) > 0
    rel = next((l for l in links if l["source"] == "v53" and l["target"] == "v70"), None)
    assert rel is not None
    assert rel["type"] == "subset"

def test_concept_map_expand_api(mock_app):
    """Verify that the Concept Map Expander API returns 7-page field guide data."""
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["taxpayer_mst"] = "0102030470"

    # Test v53 guide
    res = client.get("/api/compliance/concept-map/expand/v53")
    assert res.status_code == 200
    data = json.loads(res.data)
    assert data["status"] == "success"
    assert data["mst"] == "0102030470"
    assert len(data["pages"]) == 7
    assert data["pages"][0]["title"] == "1. Định Hướng (Orientation)"
    assert "v53" in data["pages"][0]["content"].lower() or "môi trường" in data["pages"][0]["content"].lower()

    # Test invalid compliance node version
    res = client.get("/api/compliance/concept-map/expand/v999")
    assert res.status_code == 404
    data = json.loads(res.data)
    assert data["status"] == "error"


def test_concept_map_api_with_violations(app):
    """Verify dynamic compliance violations count and recommended links based on invoice line items."""
    from extensions import db
    from invoices.models import Invoice, LineItem
    
    # Run within app context
    with app.app_context():
        # Clean up any existing invoices first
        LineItem.query.delete()
        Invoice.query.delete()
        db.session.commit()
        
        # Create a taxpayer invoice with warning and matching item
        inv = Invoice(
            id="0102030470-AA22E-0000001",
            taxpayer_mst="0102030470",
            seller_mst="0102030470",
            symbol="AA22E",
            number="0000001",
            invoice_type="selling",
            imported_at="2026-06-15 00:00:00"
        )
        inv.warnings = ["Thuế suất GTGT không chính xác", "Lỗi định dạng XML"]
        db.session.add(inv)
        db.session.commit()
        
        # Add line items containing fuel and ODS chemicals
        item1 = LineItem(
            invoice_id=inv.id,
            item_name="Dầu DO 0.05S-II (Fuel Diesel)",
            quantity=100.0,
            unit_price=20000.0,
            amount_before_tax=2000000.0
        )
        item2 = LineItem(
            invoice_id=inv.id,
            item_name="Hóa chất làm lạnh HCFC-22 (ODS chemical)",
            quantity=50.0,
            unit_price=150000.0,
            amount_before_tax=7500000.0
        )
        db.session.add(item1)
        db.session.add(item2)
        db.session.commit()

    # Now call the endpoint as an authenticated user
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["taxpayer_mst"] = "0102030470"
        
    res = client.get("/api/compliance/concept-map")
    assert res.status_code == 200
    data = json.loads(res.data)
    
    # Node v27 (XML Format) and v47 (VAT Rate) should have violation counts
    nodes = {n["id"]: n for n in data["nodes"]}
    assert nodes["v27"]["violations_count"] == 1
    assert nodes["v47"]["violations_count"] == 1
    
    # Verify recommended links are generated dynamically based on fuel and ODS item names
    suggested_links = data["suggested_links"]
    assert len(suggested_links) == 2
    
    # 1. VAT -> EP Tax Link for fuel
    fuel_link = next((l for l in suggested_links if l["source"] == "v47" and l["target"] == "v53"), None)
    assert fuel_link is not None
    assert "Fuel EP Tax Link" in fuel_link["label"]
    
    # 2. EP Tax -> ODS Quota Link for chemical
    ods_link = next((l for l in suggested_links if l["source"] == "v53" and l["target"] == "v70"), None)
    assert ods_link is not None
    assert "ODS Quotas Link" in ods_link["label"]


