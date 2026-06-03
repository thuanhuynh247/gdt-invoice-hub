import json
import pytest
from app import create_app
from extensions import db
from invoices.models import TenantGroup, TaxpayerProfile


@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False
    })

    with app.app_context():
        db.create_all()
        
        # Seed some TaxpayerProfiles
        db.session.add(TaxpayerProfile(
            mst="0101234567", 
            company_name="Cong ty TNHH A", 
            gdt_username="user_a", 
            gdt_password_encrypted="pass_a", 
            is_active=True,
            created_at="2026-05-30T10:00:00Z"
        ))
        db.session.add(TaxpayerProfile(
            mst="0102030405", 
            company_name="Cong ty Co phan B", 
            gdt_username="user_b", 
            gdt_password_encrypted="pass_b", 
            is_active=True,
            created_at="2026-05-30T10:00:00Z"
        ))
        
        # TenantGroup "Tập đoàn GDT Hub" is already auto-seeded by app.py's startup hook.
        # We can query and update its taxpayer_msts to match our seeded profiles.
        group = TenantGroup.query.filter_by(group_name="Tập đoàn GDT Hub").first()
        if not group:
            group = TenantGroup(
                group_name="Tập đoàn GDT Hub",
                admin_username="admin",
                taxpayer_msts=json.dumps(["0101234567", "0102030405"])
            )
            db.session.add(group)
        else:
            group.taxpayer_msts = json.dumps(["0101234567", "0102030405"])
            
        db.session.commit()

        yield app

        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_consolidated_dashboard_requires_login(client):
    """Test that unauthorized guests cannot view the dashboard (returns 401 via @roles_required)."""
    response = client.get("/consolidated-dashboard")
    assert response.status_code == 401
    data = response.get_json()
    assert "Phien dang nhap da het han" in data["error"]


def test_consolidated_dashboard_as_admin(client):
    """Test that authenticated admin can render the dashboard."""
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "admin"
        sess["user_role"] = "admin"

    response = client.get("/consolidated-dashboard")
    assert response.status_code == 200
    
    html_content = response.data.decode("utf-8")
    assert "Bảng Điều Hối Hợp Nhất Tập Đoàn" in html_content or "Hợp nhất" in html_content


def test_api_tenant_groups(client):
    """Test GET and POST for tenant groups API."""
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "admin"
        sess["user_role"] = "admin"

    # Test GET
    response = client.get("/api/tenant/groups")
    assert response.status_code == 200
    groups = response.get_json()
    assert len(groups) >= 1
    assert groups[0]["group_name"] == "Tập đoàn GDT Hub"
    assert "0101234567" in groups[0]["taxpayer_msts"]

    # Test POST
    post_data = {
        "group_name": "Tập đoàn GDT Hub Mới",
        "taxpayer_msts": ["0101234567", "0208887776"]
    }
    response = client.post("/api/tenant/groups", json=post_data)
    assert response.status_code == 200
    res_data = response.get_json()
    assert res_data["status"] == "success"
    assert res_data["group"]["group_name"] == "Tập đoàn GDT Hub Mới"
    assert "0208887776" in res_data["group"]["taxpayer_msts"]


def test_api_tenant_consolidated(client):
    """Test consolidated API aggregates correct metrics."""
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["username"] = "admin"
        sess["user_role"] = "admin"

    response = client.get("/api/tenant/consolidated")
    assert response.status_code == 200
    data = response.get_json()
    assert data["group_name"] == "Tập đoàn GDT Hub"
    assert "summary" in data
    assert "entities" in data
    assert len(data["entities"]) == 2
    assert data["entities"][0]["mst"] == "0101234567"
    assert data["entities"][0]["name"] == "Cong ty TNHH A"
