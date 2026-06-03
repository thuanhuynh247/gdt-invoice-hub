import pytest
from unittest.mock import patch, MagicMock
from invoices.cloud_service import CloudSyncService
from invoices.models import Invoice, SystemConfig
from invoices.scheduler import save_scheduler_settings
from app import create_app
from extensions import db

@pytest.fixture(scope="module")
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture(scope="function")
def session(app):
    with app.app_context():
        # Clear existing tables to ensure isolation
        db.session.query(SystemConfig).delete()
        db.session.query(Invoice).delete()
        db.session.commit()
        yield db.session
        db.session.rollback()

def test_resolve_folder_structure():
    service = CloudSyncService()
    
    # Standard invoice mock
    invoice = {
        "buyer_mst": "0109999999",
        "date": "2026-05-25"
    }
    mst, year, month = service.resolve_folder_structure(invoice)
    assert mst == "0109999999"
    assert year == "2026"
    assert month == "05"

    # Fallback to seller_mst and missing date
    invoice_fallback = {
        "seller_mst": "0201122334",
        "date": ""
    }
    mst, year, month = service.resolve_folder_structure(invoice_fallback)
    assert mst == "0201122334"
    assert year == "2026"
    assert month == "05"

@patch("requests.post")
def test_refresh_gdrive_token(mock_post):
    service = CloudSyncService()
    
    # Success scenario
    mock_response = MagicMock()
    mock_response.json.return_value = {"access_token": "gdrive-access-token-123"}
    mock_post.return_value = mock_response
    
    token = service.refresh_gdrive_token("client_id", "client_secret", "refresh_token")
    assert token == "gdrive-access-token-123"
    mock_post.assert_called_once()
    
    # Missing args
    assert service.refresh_gdrive_token("", "sec", "ref") is None

@patch("requests.post")
def test_refresh_onedrive_token(mock_post):
    service = CloudSyncService()
    
    # Failure scenario
    mock_post.side_effect = Exception("Network timeout")
    token = service.refresh_onedrive_token("client_id", "client_secret", "refresh_token")
    assert token is None

@patch("requests.get")
@patch("requests.post")
def test_get_or_create_gdrive_folder(mock_post, mock_get):
    service = CloudSyncService()
    
    # 1. Folder exists
    mock_get_resp = MagicMock()
    mock_get_resp.json.return_value = {"files": [{"id": "existing-folder-id"}]}
    mock_get.return_value = mock_get_resp
    
    folder_id = service.get_or_create_gdrive_folder("mock-token", "HoaDon_DienTu")
    assert folder_id == "existing-folder-id"
    mock_post.assert_not_called()

    # 2. Folder does not exist, trigger create
    mock_get_resp.json.return_value = {"files": []}
    mock_post_resp = MagicMock()
    mock_post_resp.json.return_value = {"id": "new-folder-id"}
    mock_post.return_value = mock_post_resp
    
    folder_id_new = service.get_or_create_gdrive_folder("mock-token", "HoaDon_DienTu")
    assert folder_id_new == "new-folder-id"
    mock_post.assert_called_once()

@patch("requests.post")
def test_upload_to_gdrive(mock_post):
    service = CloudSyncService()
    
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"id": "gdrive-file-id-abc"}
    mock_post.return_value = mock_resp
    
    file_id = service.upload_to_gdrive("token", "file.xml", b"content", "parent-id")
    assert file_id == "gdrive-file-id-abc"

@patch("requests.put")
def test_upload_to_onedrive(mock_put):
    service = CloudSyncService()
    
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"id": "onedrive-file-id-123"}
    mock_put.return_value = mock_resp
    
    file_id = service.upload_to_onedrive("token", "/path/to/file.xml", b"content")
    assert file_id == "onedrive-file-id-123"

def test_sync_invoice_to_cloud_mock_mode(app, session):
    service = CloudSyncService()
    
    # 1. Create a mock invoice in the database
    mock_invoice = Invoice(
        id="test-sync-1",
        date="2026-05-25",
        seller_mst="0101234567",
        symbol="XYZ/26E",
        number="0001234",
        imported_at="2026-05-25T12:00:00"
    )
    session.add(mock_invoice)
    session.commit()
    
    # 2. Sync with disabled settings
    res_disabled = service.sync_invoice_to_cloud("test-sync-1", b"xml_bytes")
    assert res_disabled["gdrive_sync"] is False
    assert res_disabled["onedrive_sync"] is False

    # 3. Enable settings and sync in TESTING mode (mock mode)
    save_scheduler_settings({
        "gdrive_enabled": True,
        "gdrive_client_id": "gdrive-client",
        "gdrive_client_secret": "gdrive-secret",
        "gdrive_refresh_token": "gdrive-refresh",
        "onedrive_enabled": True,
        "onedrive_client_id": "onedrive-client",
        "onedrive_client_secret": "onedrive-secret",
        "onedrive_refresh_token": "onedrive-refresh"
    })
    
    res_enabled = service.sync_invoice_to_cloud("test-sync-1", b"xml_bytes", b"pdf_bytes")
    assert res_enabled["gdrive_sync"] is True
    assert res_enabled["gdrive_file_id"] == "mock-gdrive-file-id"
    assert res_enabled["onedrive_sync"] is True
    assert res_enabled["onedrive_file_id"] == "mock-onedrive-file-id"


def test_get_decrypted_setting():
    from auth.crypto import encrypt_password
    service = CloudSyncService()
    secret = "my-secret-password"
    encrypted = encrypt_password(secret)
    
    # Test decryption
    decrypted = service.get_decrypted_setting({"key": encrypted}, "key")
    assert decrypted == secret

    # Test non-encrypted value
    assert service.get_decrypted_setting({"key": "plain-text"}, "key") == "plain-text"

    # Test error fallback (bad format)
    assert service.get_decrypted_setting({"key": "gAAAAA-bad-token"}, "key") == "gAAAAA-bad-token"


@patch("requests.post")
def test_refresh_gdrive_token_failure(mock_post):
    service = CloudSyncService()
    # Post exception
    mock_post.side_effect = Exception("HTTP Error")
    assert service.refresh_gdrive_token("id", "sec", "ref") is None


@patch("requests.post")
def test_refresh_onedrive_token_incomplete(mock_post):
    service = CloudSyncService()
    # Missing args
    assert service.refresh_onedrive_token("id", "", "ref") is None


@patch("requests.get")
@patch("requests.post")
def test_get_or_create_gdrive_folder_errors(mock_post, mock_get):
    service = CloudSyncService()
    # 1. Search exception
    mock_get.side_effect = Exception("Network Error")
    assert service.get_or_create_gdrive_folder("token", "folder") is None

    # 2. Search success but create fails
    mock_get.side_effect = None
    mock_get.return_value.json.return_value = {"files": []}
    mock_post.side_effect = Exception("Creation failed")
    assert service.get_or_create_gdrive_folder("token", "folder") is None


@patch("requests.post")
def test_upload_to_gdrive_error(mock_post):
    service = CloudSyncService()
    mock_post.side_effect = Exception("Upload error")
    assert service.upload_to_gdrive("token", "file.xml", b"content") is None


@patch("requests.put")
def test_upload_to_onedrive_error(mock_put):
    service = CloudSyncService()
    mock_put.side_effect = Exception("Upload error")
    assert service.upload_to_onedrive("token", "file.xml", b"content") is None


def test_resolve_folder_structure_fallbacks():
    service = CloudSyncService()
    # No MST fallback on custom dictionary / object
    class MockInvoice:
        buyer_mst = None
        seller_mst = None
        date = 12345  # Not a string, triggers exception on split()
    
    mst, year, month = service.resolve_folder_structure(MockInvoice())
    assert mst == "0109999999"
    assert year == "2026"
    assert month == "05"


@patch("invoices.cloud_service.requests")
def test_sync_invoice_to_cloud_live_and_failures(mock_req, app, session):
    service = CloudSyncService()
    
    # 1. Invoice not found
    res = service.sync_invoice_to_cloud("missing-id", b"xml")
    assert res["gdrive_sync"] is False
    assert res["onedrive_sync"] is False

    # 2. Add a mock invoice
    invoice = Invoice(
        id="test-live-sync-1",
        date="2026-05-25",
        seller_mst="0101234567",
        symbol="XYZ/26E",
        number="0001234",
        imported_at="2026-05-25T12:00:00"
    )
    session.add(invoice)
    session.commit()

    # Enable cloud settings
    save_scheduler_settings({
        "gdrive_enabled": True,
        "gdrive_client_id": "gdrive-client",
        "gdrive_client_secret": "gdrive-secret",
        "gdrive_refresh_token": "gdrive-refresh",
        "onedrive_enabled": True,
        "onedrive_client_id": "onedrive-client",
        "onedrive_client_secret": "onedrive-secret",
        "onedrive_refresh_token": "onedrive-refresh"
    })

    # Setup side effects to handle live API call URLs
    def mock_post_handler(url, *args, **kwargs):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        if "oauth2.googleapis.com/token" in url:
            resp.json.return_value = {"access_token": "gdrive-access-token"}
        elif "login.microsoftonline.com" in url:
            resp.json.return_value = {"access_token": "onedrive-access-token"}
        elif "upload/drive/v3/files" in url:
            resp.json.return_value = {"id": "uploaded-gdrive-file-id"}
        elif "drive/v3/files" in url:  # create folder
            resp.json.return_value = {"id": "created-folder-id"}
        else:
            resp.json.return_value = {}
        return resp

    mock_req.post.side_effect = mock_post_handler

    def mock_get_handler(url, *args, **kwargs):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        if "drive/v3/files" in url:
            resp.json.return_value = {"files": [{"id": "existing-folder-id"}]}
        else:
            resp.json.return_value = {}
        return resp

    mock_req.get.side_effect = mock_get_handler

    def mock_put_handler(url, *args, **kwargs):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        if "graph.microsoft.com" in url:
            resp.json.return_value = {"id": "uploaded-onedrive-file-id"}
        else:
            resp.json.return_value = {}
        return resp

    mock_req.put.side_effect = mock_put_handler

    # Temporarily set app config to live mode (TESTING = False)
    app.config["TESTING"] = False
    try:
        res_live = service.sync_invoice_to_cloud("test-live-sync-1", b"xml_bytes", b"pdf_bytes")
        assert res_live["gdrive_sync"] is True
        assert res_live["gdrive_file_id"] == "uploaded-gdrive-file-id"
        assert res_live["onedrive_sync"] is True
        assert res_live["onedrive_file_id"] == "uploaded-onedrive-file-id"
    finally:
        app.config["TESTING"] = True


def test_get_app_context(app):
    service = CloudSyncService(app=app)
    with service._get_app_context():
        pass


@patch("requests.post")
def test_get_or_create_gdrive_folder_with_parent(mock_post):
    service = CloudSyncService()
    mock_post_resp = MagicMock()
    mock_post_resp.json.return_value = {"id": "new-folder-with-parent"}
    mock_post.return_value = mock_post_resp
    
    with patch("requests.get") as mock_get:
        mock_get.return_value.json.return_value = {"files": []}
        folder_id = service.get_or_create_gdrive_folder("mock-token", "Folder", parent_id="parent-123")
        assert folder_id == "new-folder-with-parent"


def test_sync_invoice_to_cloud_with_sandbox(oauth_sandbox, app, session):
    """Test full cloud synchronization sequence using the new OAuth2Sandbox fixture."""
    service = CloudSyncService()
    
    # 1. Add mock invoice to session
    invoice = Invoice(
        id="test-sandbox-sync-1",
        date="2026-05-25",
        seller_mst="0101234567",
        symbol="XYZ/26E",
        number="0001234",
        imported_at="2026-05-25T12:00:00"
    )
    session.add(invoice)
    session.commit()

    # 2. Enable cloud sync settings
    save_scheduler_settings({
        "gdrive_enabled": True,
        "gdrive_client_id": "gdrive-client",
        "gdrive_client_secret": "gdrive-secret",
        "gdrive_refresh_token": "gdrive-refresh",
        "onedrive_enabled": True,
        "onedrive_client_id": "onedrive-client",
        "onedrive_client_secret": "onedrive-secret",
        "onedrive_refresh_token": "onedrive-refresh"
    })

    # 3. Trigger sync with app.config["TESTING"]=False to run actual sync flows (intercepted by sandbox)
    app.config["TESTING"] = False
    try:
        res = service.sync_invoice_to_cloud("test-sandbox-sync-1", b"xml_bytes", b"pdf_bytes")
        assert res["gdrive_sync"] is True
        assert res["gdrive_file_id"] == "uploaded-gdrive-file-id"
        assert res["onedrive_sync"] is True
        assert res["onedrive_file_id"] == "uploaded-onedrive-file-id"

        # 4. Verify captured logs
        assert len(oauth_sandbox.request_log) > 0
        urls = [req["url"] for req in oauth_sandbox.request_log]
        assert any("oauth2.googleapis.com/token" in u for u in urls)
        assert any("login.microsoftonline.com" in u for u in urls)
        assert any("drive/v3/files" in u for u in urls)
        assert any("graph.microsoft.com" in u for u in urls)
    finally:
        app.config["TESTING"] = True


def test_sync_invoice_to_cloud_sandbox_failures(oauth_sandbox, app, session):
    """Test cloud synchronization under simulated failure states configured in OAuth2Sandbox."""
    service = CloudSyncService()
    
    invoice = Invoice(
        id="test-sandbox-fail-1",
        date="2026-05-25",
        seller_mst="0101234567",
        symbol="XYZ/26E",
        number="0001234",
        imported_at="2026-05-25T12:00:00"
    )
    session.add(invoice)
    session.commit()

    save_scheduler_settings({
        "gdrive_enabled": True,
        "gdrive_client_id": "gdrive-client",
        "gdrive_client_secret": "gdrive-secret",
        "gdrive_refresh_token": "gdrive-refresh",
        "onedrive_enabled": True,
        "onedrive_client_id": "onedrive-client",
        "onedrive_client_secret": "onedrive-secret",
        "onedrive_refresh_token": "onedrive-refresh"
    })

    # 1. Test token refresh failure
    oauth_sandbox.refresh_fails = True
    app.config["TESTING"] = False
    try:
        res = service.sync_invoice_to_cloud("test-sandbox-fail-1", b"xml_bytes", b"pdf_bytes")
        assert res["gdrive_sync"] is False
        assert res["onedrive_sync"] is False
    finally:
        app.config["TESTING"] = True

    # 2. Test upload endpoint failure
    oauth_sandbox.refresh_fails = False
    oauth_sandbox.upload_fails = True
    app.config["TESTING"] = False
    try:
        res = service.sync_invoice_to_cloud("test-sandbox-fail-1", b"xml_bytes", b"pdf_bytes")
        assert res["gdrive_sync"] is False
        assert res["onedrive_sync"] is False
    finally:
        app.config["TESTING"] = True

    # 3. Test folder creation server error: sync succeeds by falling back to root
    oauth_sandbox.upload_fails = False
    oauth_sandbox.create_folder_fails = True
    app.config["TESTING"] = False
    try:
        import json
        oauth_sandbox.request_log.clear()
        res = service.sync_invoice_to_cloud("test-sandbox-fail-1", b"xml_bytes", b"pdf_bytes")
        assert res["gdrive_sync"] is True
        
        # Verify no parents are present in upload payload metadata
        upload_req = next(r for r in oauth_sandbox.request_log if "upload/drive/v3/files" in r["url"])
        metadata = json.loads(upload_req["files"]["metadata"][1])
        assert "parents" not in metadata
    finally:
        app.config["TESTING"] = True

    # 4. Test network communication failure (ConnectionError)
    oauth_sandbox.create_folder_fails = False
    oauth_sandbox.network_error = True
    app.config["TESTING"] = False
    try:
        res = service.sync_invoice_to_cloud("test-sandbox-fail-1", b"xml_bytes", b"pdf_bytes")
        assert res["gdrive_sync"] is False
        assert res["onedrive_sync"] is False
    finally:
        app.config["TESTING"] = True

    # 5. Test expired access tokens (401 response)
    oauth_sandbox.network_error = False
    oauth_sandbox.expired_access_tokens.add("gdrive-access-token")
    oauth_sandbox.expired_access_tokens.add("onedrive-access-token")
    app.config["TESTING"] = False
    try:
        res = service.sync_invoice_to_cloud("test-sandbox-fail-1", b"xml_bytes", b"pdf_bytes")
        assert res["gdrive_sync"] is False
        assert res["onedrive_sync"] is False
    finally:
        app.config["TESTING"] = True




