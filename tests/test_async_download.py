"""Tests for the asynchronous batch invoice downloading pipeline."""

from __future__ import annotations

import time
import zipfile
from io import BytesIO
from invoices.routes import DOWNLOAD_TASKS


def test_batch_download_requires_login(client):
    """Anonymous requests must be rejected with 401."""
    response = client.post("/api/invoices/batch-download", json={"month": "2026-05"})
    assert response.status_code == 401


def test_batch_download_missing_month(logged_in_client):
    """Requests with empty month must return 400."""
    response = logged_in_client.post("/api/invoices/batch-download", json={"month": ""})
    assert response.status_code == 400


def test_batch_download_async_flow(logged_in_client):
    """Verify standard asynchronous flow: launch task -> poll status -> retrieve ZIP."""
    # 1. Trigger the download task
    response = logged_in_client.post(
        "/api/invoices/batch-download",
        json={"month": "2026-05", "direction": "purchase"}
    )
    assert response.status_code == 202
    data = response.get_json()
    assert "task_id" in data
    assert data["status"] == "pending"

    task_id = data["task_id"]

    # 2. Poll until completed (since it runs mock mode, it completes almost instantly)
    # We will poll up to 5 seconds with small sleep
    max_attempts = 50
    completed = False
    status_data = None

    for _ in range(max_attempts):
        status_res = logged_in_client.get(f"/api/invoices/batch-download/status/{task_id}")
        assert status_res.status_code == 200
        status_data = status_res.get_json()
        assert status_data["task_id"] == task_id
        if status_data["status"] == "completed":
            completed = True
            break
        elif status_data["status"] == "failed":
            raise AssertionError(f"Task failed: {status_data['error']}")
        time.sleep(0.1)

    assert completed is True
    assert status_data["progress"] == 100
    assert status_data["total"] > 0
    assert status_data["completed_count"] == status_data["total"]

    # 3. Retrieve the ZIP file
    download_res = logged_in_client.get(f"/api/invoices/batch-download/download/{task_id}")
    assert download_res.status_code == 200
    assert download_res.mimetype == "application/zip"

    # Verify zip content structure
    zip_buf = BytesIO(download_res.data)
    with zipfile.ZipFile(zip_buf, "r") as zf:
        namelist = zf.namelist()
        assert len(namelist) > 0
        for name in namelist:
            assert name.endswith(".xml")

    # 4. Try retrieving again; it should be deleted from memory (404)
    second_res = logged_in_client.get(f"/api/invoices/batch-download/download/{task_id}")
    assert second_res.status_code == 404
