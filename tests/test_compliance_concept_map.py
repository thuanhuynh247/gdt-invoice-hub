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
