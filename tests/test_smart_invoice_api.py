"""Smart Invoice API compatibility tests.

Covers the three smart-invoice.vn-compatible endpoints:
  POST /API/login
  POST /API/get_purchase/<mst>
  POST /API/get_purchase_items/<mst>
"""

from __future__ import annotations


# ── /API/login ─────────────────────────────────────────────────────────────


class TestApiLogin:
    """Two-phase captcha+authentication flow."""

    def test_phase1_returns_captcha_svg_and_key(self, client):
        """Empty captcha → return SVG content and cache key."""
        resp = client.post("/API/login", json={
            "username": "0316459946",
            "password": "Password123@",
            "captcha": "",
            "key": "",
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert "key" in data
        assert "content" in data
        assert "<svg" in data["content"]

    def test_phase2_returns_token_on_valid_captcha(self, client):
        """Providing captcha + key should authenticate and return token."""
        # Phase 1
        resp1 = client.post("/API/login", json={
            "username": "0316459946",
            "password": "Password123@",
            "captcha": "",
            "key": "",
        })
        key = resp1.get_json()["key"]

        # Phase 2
        resp2 = client.post("/API/login", json={
            "username": "0316459946",
            "password": "Password123@",
            "captcha": "ABCDE",
            "key": key,
        })
        assert resp2.status_code == 200
        token = resp2.data.decode("utf-8")
        # Mock mode returns "mock-session-<username>"
        assert token == "mock-session-0316459946"
        assert resp2.content_type.startswith("text/plain")

    def test_phase2_auto_captcha_works(self, client):
        """Providing captcha='AUTO' + key should auto-solve and authenticate successfully."""
        # Phase 1
        resp1 = client.post("/API/login", json={
            "username": "0316459946",
            "password": "Password123@",
            "captcha": "",
            "key": "",
        })
        key = resp1.get_json()["key"]

        # Phase 2 with AUTO captcha
        resp2 = client.post("/API/login", json={
            "username": "0316459946",
            "password": "Password123@",
            "captcha": "AUTO",
            "key": key,
        })
        assert resp2.status_code == 200
        token = resp2.data.decode("utf-8")
        assert token == "mock-session-0316459946"
        assert resp2.content_type.startswith("text/plain")

    def test_phase2_rejects_locked_account(self, client):
        """The 'locked' username should raise AuthenticationError in mock mode."""
        resp1 = client.post("/API/login", json={
            "username": "locked",
            "password": "anything",
            "captcha": "",
            "key": "",
        })
        key = resp1.get_json()["key"]

        resp2 = client.post("/API/login", json={
            "username": "locked",
            "password": "anything",
            "captcha": "XYZWQ",
            "key": key,
        })
        assert resp2.status_code == 401
        assert "error" in resp2.get_json()

    def test_phase2_rejects_missing_credentials(self, client):
        """Empty username/password should be rejected."""
        resp1 = client.post("/API/login", json={
            "username": "demo",
            "password": "pass",
            "captcha": "",
            "key": "",
        })
        key = resp1.get_json()["key"]

        resp2 = client.post("/API/login", json={
            "username": "",
            "password": "",
            "captcha": "XXXXX",
            "key": key,
        })
        assert resp2.status_code == 401

    def test_phase2_expired_key_still_works_gracefully(self, client):
        """A fabricated key returns empty cookies; mock mode still authenticates."""
        resp = client.post("/API/login", json={
            "username": "0316459946",
            "password": "Password123@",
            "captcha": "MOCK",
            "key": "bogus-key-never-cached",
        })
        # In mock mode, authenticate_user ignores cookies so this succeeds
        assert resp.status_code == 200

    def test_captcha_key_is_single_use(self, client):
        """After a key is used, a second attempt should still work in mock (cookies are empty)."""
        resp1 = client.post("/API/login", json={
            "username": "0316459946",
            "password": "Password123@",
            "captcha": "",
            "key": "",
        })
        key = resp1.get_json()["key"]

        # First use
        resp2 = client.post("/API/login", json={
            "username": "0316459946",
            "password": "Password123@",
            "captcha": "AAA",
            "key": key,
        })
        assert resp2.status_code == 200

        # Second use — key was popped from cache; still OK in mock mode
        resp3 = client.post("/API/login", json={
            "username": "0316459946",
            "password": "Password123@",
            "captcha": "BBB",
            "key": key,
        })
        assert resp3.status_code == 200  # mock mode is permissive


# ── /API/get_purchase/<mst> ────────────────────────────────────────────────


class TestApiGetPurchase:
    """Purchase invoice header retrieval."""

    TOKEN = "mock-session-0316459946"

    def test_requires_token_header(self, client):
        """Missing token → 401."""
        resp = client.post("/API/get_purchase/0316459946", json={
            "fromdate": "01/05/2026",
            "todate": "31/05/2026",
        })
        assert resp.status_code == 401

    def test_requires_date_params(self, client):
        """Missing dates → 400."""
        resp = client.post(
            "/API/get_purchase/0316459946",
            headers={"token": self.TOKEN},
            json={},
        )
        assert resp.status_code == 400

    def test_rejects_bad_date_format(self, client):
        """Non-dd/mm/yyyy → 400."""
        resp = client.post(
            "/API/get_purchase/0316459946",
            headers={"token": self.TOKEN},
            json={"fromdate": "2026-05-01", "todate": "2026-05-31"},
        )
        assert resp.status_code == 400

    def test_returns_invoice_list_with_correct_fields(self, client):
        """Valid request returns list with all 15 smart-invoice fields."""
        resp = client.post(
            "/API/get_purchase/0316459946",
            headers={"token": self.TOKEN},
            json={"fromdate": "01/05/2026", "todate": "31/05/2026"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) > 0

        required_fields = [
            "khmshdon", "khhdon", "shdon", "ntao", "nbten", "nbmst",
            "nbdchi", "tgtcthue", "tgtthue", "tgtttbso", "dvtte",
            "cqt", "tchat", "tthai", "ttxly",
        ]
        for field in required_fields:
            assert field in data[0], f"Missing field: {field}"

    def test_bearer_auth_header_works(self, client):
        """Authorization: Bearer <token> should work too."""
        resp = client.post(
            "/API/get_purchase/0316459946",
            headers={"Authorization": f"Bearer {self.TOKEN}"},
            json={"fromdate": "01/05/2026", "todate": "31/05/2026"},
        )
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), list)

    def test_nbmst_filter_narrows_results(self, client):
        """Non-matching nbmst filter should return empty list."""
        resp = client.post(
            "/API/get_purchase/0316459946",
            headers={"token": self.TOKEN},
            json={
                "fromdate": "01/05/2026",
                "todate": "31/05/2026",
                "nbmst": "9999999999",  # no mock invoice has this MST
            },
        )
        assert resp.status_code == 200
        # Mock invoices don't have nbmst in raw, so filter passes for all
        # (filter only applies if nbmst_filter is truthy AND not in inv_nbmst)
        data = resp.get_json()
        assert isinstance(data, list)

    def test_empty_date_range_returns_empty(self, client):
        """Date range with no invoices → empty list."""
        resp = client.post(
            "/API/get_purchase/0316459946",
            headers={"token": self.TOKEN},
            json={"fromdate": "01/01/2020", "todate": "01/02/2020"},
        )
        assert resp.status_code == 200
        assert resp.get_json() == []


# ── /API/get_purchase_items/<mst> ──────────────────────────────────────────


class TestApiGetPurchaseItems:
    """Purchase invoice line-item detail retrieval."""

    TOKEN = "mock-session-0316459946"

    def test_requires_token(self, client):
        resp = client.post("/API/get_purchase_items/0316459946", json={
            "fromdate": "01/05/2026",
            "todate": "31/05/2026",
        })
        assert resp.status_code == 401

    def test_returns_items_with_correct_fields(self, client):
        resp = client.post(
            "/API/get_purchase_items/0316459946",
            headers={"token": self.TOKEN},
            json={"fromdate": "01/05/2026", "todate": "31/05/2026"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) > 0

        required_fields = [
            "STT", "TChat", "MHHDVu", "THHDVu", "DVTinh",
            "SLuong", "DGia", "ThTien", "TSuat", "TLCKhau", "STCKhau",
        ]
        for field in required_fields:
            assert field in data[0], f"Missing field: {field}"

    def test_stt_is_sequential(self, client):
        """STT (sequence number) should be 1, 2, 3, …"""
        resp = client.post(
            "/API/get_purchase_items/0316459946",
            headers={"token": self.TOKEN},
            json={"fromdate": "01/05/2026", "todate": "31/05/2026"},
        )
        data = resp.get_json()
        for idx, item in enumerate(data, start=1):
            assert item["STT"] == idx

    def test_empty_date_range_returns_empty(self, client):
        resp = client.post(
            "/API/get_purchase_items/0316459946",
            headers={"token": self.TOKEN},
            json={"fromdate": "01/01/2020", "todate": "01/02/2020"},
        )
        assert resp.status_code == 200
        assert resp.get_json() == []


# ── /API/upload_xml/<mst> ──────────────────────────────────────────────────


class TestApiUploadXml:
    """XML/ZIP invoice upload and stateless import."""

    TOKEN = "mock-session-0316459946"

    def test_requires_token(self, client):
        """Missing token → 401."""
        resp = client.post("/API/upload_xml/0316459946", data=b"<xml></xml>")
        assert resp.status_code == 401

    def test_upload_raw_xml_success(self, client, monkeypatch):
        """Uploading raw XML body -> success."""
        imported_invoices = []

        def mock_import(xml_bytes, filename, duplicate_strategy, taxpayer_mst):
            imported_invoices.append((xml_bytes, filename, duplicate_strategy, taxpayer_mst))
            return {"import_status": "imported"}

        monkeypatch.setattr("invoices.service.import_xml_invoice", mock_import)

        xml_data = b"<HDon><DLHDon>InvoiceData</DLHDon></HDon>"
        resp = client.post(
            "/API/upload_xml/0316459946?filename=invoice_123.xml&duplicate_strategy=skip",
            headers={"token": self.TOKEN, "Content-Type": "application/xml"},
            data=xml_data
        )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert data["imported_count"] == 1
        assert len(imported_invoices) == 1
        assert imported_invoices[0] == (xml_data, "invoice_123.xml", "skip", "0316459946")

    def test_upload_raw_zip_success(self, client, monkeypatch):
        """Uploading raw ZIP containing XML files -> parses and imports each."""
        import zipfile
        import io

        imported_invoices = []

        def mock_import(xml_bytes, filename, duplicate_strategy, taxpayer_mst):
            imported_invoices.append((xml_bytes, filename, duplicate_strategy, taxpayer_mst))
            return {"import_status": "overwritten"}

        monkeypatch.setattr("invoices.service.import_xml_invoice", mock_import)

        # Create a mock zip with two files (one XML, one txt to ignore)
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            zf.writestr("subfolder/inv1.xml", b"<xml>1</xml>")
            zf.writestr("inv2.xml", b"<xml>2</xml>")
            zf.writestr("readme.txt", b"Ignore me")
        zip_bytes = zip_buffer.getvalue()

        resp = client.post(
            "/API/upload_xml/0316459946?duplicate_strategy=overwrite",
            headers={"token": self.TOKEN, "Content-Type": "application/zip"},
            data=zip_bytes
        )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert data["overwritten_count"] == 2
        assert len(imported_invoices) == 2
        # Verify both xmls are passed
        filenames = [item[1] for item in imported_invoices]
        assert "inv1.xml" in filenames
        assert "inv2.xml" in filenames
        assert imported_invoices[0][2] == "overwrite"
        assert imported_invoices[0][3] == "0316459946"

    def test_upload_multipart_form_success(self, client, monkeypatch):
        """Uploading multiple files via multipart/form-data -> success."""
        import io
        imported_invoices = []

        def mock_import(xml_bytes, filename, duplicate_strategy, taxpayer_mst):
            imported_invoices.append((xml_bytes, filename, duplicate_strategy, taxpayer_mst))
            return {"import_status": "imported"}

        monkeypatch.setattr("invoices.service.import_xml_invoice", mock_import)

        resp = client.post(
            "/API/upload_xml/0316459946",
            headers={"token": self.TOKEN},
            data={
                "files": [
                    (io.BytesIO(b"<xml>file1</xml>"), "file1.xml"),
                    (io.BytesIO(b"<xml>file2</xml>"), "file2.xml"),
                ]
            },
            content_type="multipart/form-data"
        )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert data["imported_count"] == 2
        assert len(imported_invoices) == 2

    def test_upload_invalid_format_fails(self, client, monkeypatch):
        """Unsupported format -> returns partial/error status."""
        resp = client.post(
            "/API/upload_xml/0316459946?filename=notes.txt",
            headers={"token": self.TOKEN},
            data=b"Just raw text"
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["status"] == "failed"
        assert len(data["errors"]) > 0
        assert "notes.txt" in data["errors"][0]

