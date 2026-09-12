"""Unit & Integration Tests for Ultra-Lean Webapp Optimizer (Goal Execution)."""

from __future__ import annotations
import pytest

from invoices.service import get_lean_invoice_stats
from invoices.ai_tax_advisor import compress_rag_context
from invoices.timesfm_engine import TimesFMPatchDecoder


def test_get_lean_invoice_stats_unit(app):
    """Verify single-pass invoice statistics aggregation."""
    with app.app_context():
        stats = get_lean_invoice_stats("0109998887")
        assert "total_count" in stats
        assert "total_revenue" in stats
        assert "total_vat" in stats
        assert "cancelled_count" in stats
        assert "avg_t_score" in stats
        assert isinstance(stats["total_count"], int)


def test_compress_rag_context_unit():
    """Verify decree RAG context token compression and fluff pruning."""
    raw = (
        "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐộc lập - Tự do - Hạnh phúc\n\n"
        "THÔNG TƯ 99/2025/TT-BTC QUY ĐỊNH HƯỚNG DẪN THUẾ GTGT\n"
        + ("Nội dung điều khoản chi tiết quy định về hoàn thuế... " * 100)
    )
    compressed = compress_rag_context(raw, max_tokens=100)
    assert "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM" not in compressed
    assert len(compressed) <= 500
    assert "..." in compressed


def test_timesfm_lru_caching_unit():
    """Verify TimesFMPatchDecoder LRU cache hit and acceleration."""
    decoder = TimesFMPatchDecoder(patch_size=3)
    series = [100.0, 110.0, 120.0, 130.0, 140.0, 150.0]

    # First run (computes)
    res1 = decoder.decode_multi_horizon(series, horizon=6)
    assert hasattr(decoder, "_cache")
    assert len(decoder._cache) > 0

    # Second run (cache hit)
    res2 = decoder.decode_multi_horizon(series, horizon=6)
    assert res1 == res2


def test_api_system_lean_metrics_endpoint(client):
    """Verify /api/system/lean-metrics endpoint integration in Flask app."""
    with client.session_transaction() as sess:
        sess["username"] = "admin"
        sess["role"] = "admin"
        sess["logged_in"] = True
        sess["taxpayer_mst"] = "0109998887"
        sess["active_taxpayer_mst"] = "0109998887"

    response = client.get("/api/system/lean-metrics")
    assert response.status_code == 200
    data = response.get_json()

    assert data["status"] == "success"
    assert "query_latency_ms" in data
    assert "memory_rss_mb" in data
    assert data["sqlite_journal_mode"] == "WAL"
    assert data["lean_optimization_grade"] == "A++"
    assert "invoice_stats" in data
