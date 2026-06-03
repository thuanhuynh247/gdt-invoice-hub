"""Shared pytest fixtures."""

from __future__ import annotations

import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["TESTING"] = "True"

# Disable openpyxl LXML backend globally to avoid Python 3.14 serialization bugs
try:
    import openpyxl
    openpyxl.LXML = False
    import openpyxl.xml.functions
    from et_xmlfile import xmlfile
    openpyxl.xml.functions.xmlfile = xmlfile
    import openpyxl.worksheet._writer
    openpyxl.worksheet._writer.xmlfile = xmlfile
except Exception:
    pass


from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
local_temp = str(PROJECT_ROOT / "data" / "temp")
import os
os.makedirs(local_temp, exist_ok=True)
import tempfile
tempfile.tempdir = local_temp

import pytest


# Set test database URI in environment variables before app imports!
os.environ["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{PROJECT_ROOT}/data/test_invoices.db"

from app import create_app


@pytest.fixture
def app():
    """Create a Flask app configured for tests."""
    # Start with a clean test database file if possible
    test_db_path = PROJECT_ROOT / "data" / "test_invoices.db"
    if test_db_path.exists():
        try:
            test_db_path.unlink()
        except Exception:
            pass

    flask_app = create_app()
    flask_app.config.update(
        TESTING=True,
        GDT_USE_MOCK=True,
        PROPAGATE_EXCEPTIONS=True,
    )
    with flask_app.app_context():
        yield flask_app
        
        # Teardown database session and clean tables
        from extensions import db
        db.session.remove()
        try:
            db.drop_all()
        except Exception:
            pass
        try:
            db.engine.dispose()
        except Exception:
            pass

    # Stop background workers and join thread workers
    from auth.captcha import stop_captcha_prefetch_worker
    stop_captcha_prefetch_worker()

    from invoices.scheduler import stop_scheduler_worker
    stop_scheduler_worker()

    import threading
    for t in threading.enumerate():
        if t.name.startswith("BatchDownloadThread-"):
            try:
                t.join(timeout=1.0)
            except Exception:
                pass




@pytest.fixture
def client(app):
    """Return a Flask test client."""

    return app.test_client()


@pytest.fixture
def logged_in_client(client):
    """Seed an authenticated session for protected-route tests."""

    with client.session_transaction() as session:
        session["logged_in"] = True
        session["username"] = "tester"
        session["user_role"] = "admin"
        session["expires_at"] = "2099-05-20T00:00:00+00:00"
    return client


class OAuth2Sandbox:
    """Mock sandbox server for testing OAuth2 token flows and cloud sync APIs."""

    def __init__(self):
        self.request_log = []
        self.token_mapping = {
            "gdrive-refresh": "gdrive-access-token",
            "onedrive-refresh": "onedrive-access-token"
        }
        self.failed_refresh_tokens = set()
        self.expired_access_tokens = set()
        self.folders = {}  # folder_name -> folder_id
        self.upload_fails = False
        self.create_folder_fails = False
        self.refresh_fails = False
        self.network_error = False

    def add_token(self, refresh_token: str, access_token: str):
        self.token_mapping[refresh_token] = access_token

    def expire_token(self, access_token: str):
        self.expired_access_tokens.add(access_token)

    def fail_refresh(self, refresh_token: str):
        self.failed_refresh_tokens.add(refresh_token)

    def handle_request(self, method, url, *args, **kwargs):
        self.request_log.append({
            "method": method,
            "url": url,
            "headers": kwargs.get("headers"),
            "data": kwargs.get("data"),
            "json": kwargs.get("json"),
            "files": kwargs.get("files")
        })

        import requests
        if self.network_error:
            raise requests.exceptions.ConnectionError("Network communication failed")

        from unittest.mock import MagicMock
        resp = MagicMock(spec=requests.Response)
        resp.raise_for_status = MagicMock()

        # Check authorization headers for expired token simulation
        headers = kwargs.get("headers") or {}
        auth_header = headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            if token in self.expired_access_tokens:
                resp.status_code = 401
                resp.json.return_value = {"error": {"message": "Invalid credentials", "code": "InvalidAuthenticationToken"}}
                resp.raise_for_status.side_effect = requests.exceptions.HTTPError("401 Client Error: Unauthorized", response=resp)
                return resp

        # Google Drive / token refresh
        if "oauth2.googleapis.com/token" in url:
            if self.refresh_fails:
                resp.status_code = 400
                resp.json.return_value = {"error": "invalid_grant"}
                resp.raise_for_status.side_effect = requests.exceptions.HTTPError("400 Client Error: Bad Request", response=resp)
                return resp
            data = kwargs.get("data") or {}
            rt = data.get("refresh_token")
            if rt in self.failed_refresh_tokens or rt not in self.token_mapping:
                resp.status_code = 400
                resp.json.return_value = {"error": "invalid_grant"}
                resp.raise_for_status.side_effect = requests.exceptions.HTTPError("400 Client Error: Bad Request", response=resp)
                return resp
            resp.status_code = 200
            resp.json.return_value = {
                "access_token": self.token_mapping[rt],
                "expires_in": 3600,
                "token_type": "Bearer"
            }
            return resp

        # OneDrive / token refresh
        elif "login.microsoftonline.com" in url:
            if self.refresh_fails:
                resp.status_code = 400
                resp.json.return_value = {"error": "invalid_grant"}
                resp.raise_for_status.side_effect = requests.exceptions.HTTPError("400 Client Error: Bad Request", response=resp)
                return resp
            data = kwargs.get("data") or {}
            rt = data.get("refresh_token")
            if rt in self.failed_refresh_tokens or rt not in self.token_mapping:
                resp.status_code = 400
                resp.json.return_value = {"error": "invalid_grant"}
                resp.raise_for_status.side_effect = requests.exceptions.HTTPError("400 Client Error: Bad Request", response=resp)
                return resp
            resp.status_code = 200
            resp.json.return_value = {
                "access_token": self.token_mapping[rt],
                "expires_in": 3600,
                "token_type": "Bearer"
            }
            return resp

        # Google Drive / create or find folder
        elif "www.googleapis.com/drive/v3/files" in url:
            if method.upper() == "GET":
                if self.create_folder_fails:
                    resp.status_code = 500
                    resp.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error", response=resp)
                    return resp
                # Find folder
                import re
                from urllib.parse import unquote
                unquoted_url = unquote(url)
                # Query can be in params
                q = kwargs.get("params", {}).get("q", "") or ""
                if not q and "q=" in unquoted_url:
                    q = unquoted_url.split("q=")[1].split("&")[0]
                match = re.search(r"name\s*=\s*'([^']+)'", q)
                if match:
                    folder_name = match.group(1)
                    if folder_name in self.folders:
                        resp.status_code = 200
                        resp.json.return_value = {"files": [{"id": self.folders[folder_name]}]}
                        return resp
                resp.status_code = 200
                resp.json.return_value = {"files": []}
                return resp

            elif method.upper() == "POST":
                if self.create_folder_fails:
                    resp.status_code = 500
                    resp.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error", response=resp)
                    return resp
                json_data = kwargs.get("json") or {}
                folder_name = json_data.get("name", "new-folder")
                folder_id = f"folder-id-{folder_name}"
                self.folders[folder_name] = folder_id
                resp.status_code = 200
                resp.json.return_value = {"id": folder_id}
                return resp

        # Google Drive / upload file
        elif "www.googleapis.com/upload/drive/v3/files" in url:
            if self.upload_fails:
                resp.status_code = 500
                resp.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error", response=resp)
                return resp
            resp.status_code = 200
            resp.json.return_value = {"id": "uploaded-gdrive-file-id"}
            return resp

        # OneDrive / upload file or other operations
        elif "graph.microsoft.com" in url:
            if self.upload_fails:
                resp.status_code = 500
                resp.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error", response=resp)
                return resp
            resp.status_code = 201 if method.upper() == "PUT" else 200
            resp.json.return_value = {"id": "uploaded-onedrive-file-id"}
            return resp

        # Default fallback
        resp.status_code = 200
        resp.json.return_value = {}
        return resp


@pytest.fixture
def oauth_sandbox():
    """Interceptor fixture to sandbox third-party OAuth2 and Cloud Sync requests."""
    sandbox = OAuth2Sandbox()
    import requests

    original_get = requests.get
    original_post = requests.post
    original_put = requests.put
    original_request = requests.request

    def mock_get(url, *args, **kwargs):
        return sandbox.handle_request("GET", url, *args, **kwargs)

    def mock_post(url, *args, **kwargs):
        return sandbox.handle_request("POST", url, *args, **kwargs)

    def mock_put(url, *args, **kwargs):
        return sandbox.handle_request("PUT", url, *args, **kwargs)

    def mock_request(method, url, *args, **kwargs):
        return sandbox.handle_request(method, url, *args, **kwargs)

    requests.get = mock_get
    requests.post = mock_post
    requests.put = mock_put
    requests.request = mock_request

    try:
        yield sandbox
    finally:
        requests.get = original_get
        requests.post = original_post
        requests.put = original_put
        requests.request = original_request

