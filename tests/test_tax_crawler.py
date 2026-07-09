"""Pytest suite for the tax crawler, parser, and FTS5 indexing system."""

from __future__ import annotations

import os
import json
import pytest
import sqlite3
import tempfile
from flask import Flask
from extensions import db
from unittest.mock import patch, MagicMock
from invoices.tax_crawler_service import (
    extract_effective_date,
    clean_html_to_text,
    fetch_and_clean_url,
    ingest_crawled_content
)
from invoices.tax_advisor_service import get_rag_context

# Create a temporary database path for isolated test run
temp_db_fd, temp_db_path = tempfile.mkstemp(suffix=".db")

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    """Create and initialize the tables in the temporary database."""
    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()
    # Create the real tables matching tax_crawler_service
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tax_regulation_chunk (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_source TEXT,
            page_number INTEGER,
            effective_date TEXT,
            chunk_content TEXT,
            created_at TEXT
        );
    """)
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS tax_regulation_fts USING fts5(
            chunk_id UNINDEXED,
            chunk_content,
            document_source,
            page_number
        );
    """)
    conn.commit()
    conn.close()
    
    # Patch DB_PATH in service modules to point to our temp DB
    with patch("invoices.tax_crawler_service.DB_PATH", temp_db_path), \
         patch("invoices.tax_advisor_service.DB_PATH", temp_db_path):
        yield
        
    # Clean up the temp DB file after all tests finish
    os.close(temp_db_fd)
    if os.path.exists(temp_db_path):
        try:
            os.remove(temp_db_path)
        except OSError:
            pass

@pytest.fixture
def mock_app():
    app = Flask(__name__, template_folder="../templates")
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    db.init_app(app)
    
    from auth import auth_blueprint
    from invoices.routes import invoices_blueprint
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(invoices_blueprint)

    @app.route("/")
    def index():
        return "index"

    with app.app_context():
        db.create_all()
        yield app

def test_extract_effective_date():
    """Verify effective date extraction heuristic works for Vietnamese formats."""
    text_1 = "Luật Thuế giá trị gia tăng số 48/2024/QH15 có hiệu lực thi hành từ ngày 01/07/2026."
    assert extract_effective_date(text_1) == "2026-07-01"

    text_2 = "Quy định này áp dụng kể từ ngày 15/09/2024 tại các doanh nghiệp."
    assert extract_effective_date(text_2) == "2024-09-15"

    text_3 = "Không có thông tin ngày hiệu lực cụ thể ở đây."
    # The default is current date, so it returns today's string
    from datetime import datetime
    assert extract_effective_date(text_3) == datetime.now().strftime("%Y-%m-%d")

def test_clean_html_to_text():
    """Verify HTML cleaning strips scripts, styles, boilerplate, and formats text."""
    html = """
    <html>
    <head><style>body { color: red; }</style></head>
    <body>
        <nav>Menu link 1</nav>
        <div class="content">
            <h1>Luật Thuế GTGT mới</h1>
            <p>Nội dung <strong>chính sách</strong> thuế năm 2026.</p>
        </div>
        <footer>Bản quyền 2026</footer>
    </body>
    </html>
    """
    clean_text = clean_html_to_text(html)
    assert "Menu link 1" not in clean_text
    assert "Bản quyền 2026" not in clean_text
    assert "Luật Thuế GTGT mới" in clean_text
    assert "chính sách" in clean_text

@patch("invoices.tax_crawler_service.requests.get")
def test_fetch_and_clean_url(mock_get):
    """Test fetching and parsing a remote URL."""
    mock_response = MagicMock()
    mock_response.text = """
    <html>
    <title>Quyết Định 123/QĐ-BTC</title>
    <body>
        <div id="main-content">
            <p>Nội dung quyết định có hiệu lực thi hành từ ngày 01/01/2025.</p>
        </div>
    </body>
    </html>
    """
    mock_response.status_code = 200
    mock_response.apparent_encoding = "utf-8"
    mock_response.encoding = "utf-8"
    mock_get.return_value = mock_response

    title, content = fetch_and_clean_url("https://example.com/tax-law")
    assert title == "Quyết Định 123/QĐ-BTC"
    assert "hiệu lực thi hành từ ngày 01/01/2025" in content

def test_ingestion_and_rag_query():
    """Verify that document ingestion segments content and search queries yield results."""
    # Segment and ingest some text
    url = "https://example.com/law-48"
    title = "Luật Thuế 48/2024"
    text = "Đoạn văn thứ nhất nói về thuế suất thuế GTGT 10%. " * 50  # Over 200 words to test chunking
    text += "\nĐoạn văn thứ hai nói về hoàn thuế GTGT xuất khẩu nông sản có hiệu lực ngày 01/07/2026."
    
    with patch("invoices.tax_crawler_service.DB_PATH", temp_db_path), \
         patch("invoices.tax_advisor_service.DB_PATH", temp_db_path):
        result = ingest_crawled_content(url, title, text, "2026-07-01")
        assert result["success"] is True
        assert result["chunks_count"] > 1
        assert result["document_source"] == "Luật Thuế 48/2024 (Web)"
        
        # Query database using RAG function
        matches_str, citations = get_rag_context("hoàn thuế xuất khẩu nông sản")
        assert "nông sản" in matches_str
        assert "Luật Thuế 48/2024 (Web)" in matches_str

def test_api_crawl_endpoints(mock_app):
    """Verify Flask REST endpoints fetch, parse, and ingest documents successfully."""
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True

    # 1. Test Fetch Endpoint
    with patch("invoices.tax_crawler_service.fetch_and_clean_url") as mock_fetch:
        mock_fetch.return_value = (
            "Nghị Định 15/2022/NĐ-CP",
            "Nội dung giảm thuế GTGT xuống 8% có hiệu lực từ ngày 01/02/2022."
        )
        
        res = client.post("/api/tax/crawl/fetch", json={"url": "https://example.com/nd15"})
        assert res.status_code == 200
        data = json.loads(res.data)
        assert data["title"] == "Nghị Định 15/2022/NĐ-CP"
        assert data["effective_date"] == "2022-02-01"
        assert "giảm thuế GTGT xuống 8%" in data["preview"]

    # 2. Test Ingest Endpoint
    payload = {
        "url": "https://example.com/nd15",
        "title": "Nghị Định 15/2022/NĐ-CP",
        "text": "Nội dung chi tiết về việc giảm thuế GTGT xuống 8% cho nhiều nhóm sản phẩm và dịch vụ.",
        "effective_date": "2022-02-01"
    }
    with patch("invoices.tax_crawler_service.DB_PATH", temp_db_path):
        res_ingest = client.post("/api/tax/crawl/ingest", json=payload)
        assert res_ingest.status_code == 200
        data_ingest = json.loads(res_ingest.data)
        assert data_ingest["success"] is True
        assert data_ingest["chunks_count"] == 1


def test_new_crawler_portal_endpoints(mock_app):
    """Verify that new crawler portal and document management endpoints function correctly."""
    client = mock_app.test_client()
    with client.session_transaction() as sess:
        sess["logged_in"] = True

    with patch("invoices.tax_crawler_service.DB_PATH", temp_db_path), \
         patch("invoices.tax_advisor_service.DB_PATH", temp_db_path):
        
        # 1. Test Portal view route
        res_view = client.get("/tax-advisor/crawler")
        assert res_view.status_code == 200

        # Ingest a sample doc first to test documents, search, stats and delete
        payload = {
            "url": "https://example.com/cit-law",
            "title": "Nghị quyết 30/2026/NQ-QH",
            "text": "Nội dung luật thuế TNDN và các quy định khấu trừ thuế GTGT mới nhất năm 2026.",
            "effective_date": "2026-01-01"
        }
        res_ingest = client.post("/api/tax/crawl/ingest", json=payload)
        assert res_ingest.status_code == 200
        
        # 2. Test GET documents
        res_docs = client.get("/api/tax/documents")
        assert res_docs.status_code == 200
        docs_data = json.loads(res_docs.data)
        assert len(docs_data) > 0
        assert any(d["document_source"] == "Nghị quyết 30/2026/NQ-QH (Web)" for d in docs_data)
        
        # 3. Test Search Test
        res_search = client.get("/api/tax/search-test?query=TNDN")
        assert res_search.status_code == 200
        search_data = json.loads(res_search.data)
        assert len(search_data) > 0
        assert "TNDN" in search_data[0]["highlighted_content"] or "tndn" in search_data[0]["highlighted_content"].lower()

        # 4. Test Stats
        res_stats = client.get("/api/tax/crawler/stats")
        assert res_stats.status_code == 200
        stats_data = json.loads(res_stats.data)
        assert stats_data["total_documents"] >= 1
        assert stats_data["total_chunks"] >= 1
        assert "TNDN" in stats_data["categories"]
        
        # 5. Test DELETE document
        res_delete = client.delete("/api/tax/documents", json={"document_source": "Nghị quyết 30/2026/NQ-QH (Web)"})
        assert res_delete.status_code == 200
        delete_data = json.loads(res_delete.data)
        assert delete_data["success"] is True
        
        # Check documents are gone
        res_docs_after = client.get("/api/tax/documents")
        assert res_docs_after.status_code == 200
        docs_data_after = json.loads(res_docs_after.data)
        assert not any(d["document_source"] == "Nghị quyết 30/2026/NQ-QH (Web)" for d in docs_data_after)


def test_2026_decrees_ingestion_and_retrieval():
    """Verify that the ingestion of 2026 decrees into FTS works and yields accurate search hits."""
    from scripts.ingest_2026_regulations import DECREES
    
    with patch("invoices.tax_crawler_service.DB_PATH", temp_db_path), \
         patch("invoices.tax_advisor_service.DB_PATH", temp_db_path):
        
        # Clear first
        conn = sqlite3.connect(temp_db_path)
        cur = conn.cursor()
        cur.execute("DELETE FROM tax_regulation_chunk")
        cur.execute("DELETE FROM tax_regulation_fts")
        conn.commit()
        conn.close()

        # Ingest
        for name, info in DECREES.items():
            result = ingest_crawled_content(
                url="http://local-tax-authority/decree-update-2026",
                custom_title=info["title"],
                text=info["text"],
                effective_date=info["date"]
            )
            assert result["success"] is True
            assert result["chunks_count"] > 0

        # Now search test
        # 1. Search for PIT 253 changes
        matches, citations = get_rag_context("giảm trừ gia cảnh Nghị định 253")
        assert "253/2026" in matches or "nghidinh253_2026.pdf" in matches
        
        # 2. Search for TP EBITDA 30% Decree 255
        matches_tp, citations_tp = get_rag_context("chi phí lãi vay EBITDA 30%")
        assert "255/2026" in matches_tp or "nghidinh255_2026.pdf" in matches_tp

        # 3. Search for TMĐT e-commerce platforms Decree 252
        matches_ec, citations_ec = get_rag_context("TMĐT sàn thương mại điện tử nộp thay")
        assert "252/2026" in matches_ec or "nghidinh252_2026.pdf" in matches_ec

        # 4. Search for máy tính tiền Decree 254
        matches_inv, citations_inv = get_rag_context("máy tính tiền hóa đơn điện tử")
        assert "254/2026" in matches_inv or "nghidinh254_2026.pdf" in matches_inv


def test_production_db_has_2026_decrees():
    """Verify that the production database 'data/invoices.db' contains the ingested 2026 decrees."""
    prod_db_path = "data/invoices.db"
    if not os.path.exists(prod_db_path):
        pytest.skip("Production database data/invoices.db not found, skipping production check.")
        
    conn = sqlite3.connect(prod_db_path)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT document_source FROM tax_regulation_chunk WHERE effective_date = '2026-07-01'")
    docs = [r[0] for r in cur.fetchall()]
    conn.close()
    
    assert "nghidinh252_2026.pdf" in docs
    assert "nghidinh253_2026.pdf" in docs
    assert "nghidinh255_2026.pdf" in docs
    assert "nghidinh254_2026.pdf" in docs


