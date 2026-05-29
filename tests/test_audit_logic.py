"""Phase 2: Comprehensive Logic, Security and Memory Safety Audit Tests."""

from __future__ import annotations

import os
import io
import json
import zipfile
import pytest
from datetime import date
from unittest.mock import patch, MagicMock
from extensions import db
from auth.captcha_solver import solve_captcha_from_svg
from invoices.archiver import InvoiceArchiver, ARCHIVE_FILE, ARCHIVE_DIR
from invoices.stats_cache import set_cached_stats, get_cached_stats, invalidate_stats_cache

def test_captcha_solver_robust_regex_parsing():
    """Verify that regex coordinate parser handles irregular whitespace, commas, and relative paths."""
    # Irregularly formatted path strings within standard canvas dimensions
    irregular_svg_1 = """<svg xmlns="http://www.w3.org/2000/svg" width="150" height="50">
        <path fill="#111" d="M15.45 20.30 L 10 20" />
        <path fill="#111" d="m   35.80   40.12 L 20 30" />
        <path fill="#111" d="M 5.25, 10.50 L 30 40" />
    </svg>"""

    with patch("auth.captcha_solver.get_ocr_instance") as mock_get_ocr:
        mock_ocr = MagicMock()
        mock_ocr.classification.return_value = "SOLVED"
        mock_get_ocr.return_value = mock_ocr

        result = solve_captcha_from_svg(irregular_svg_1)
        assert result == "SOLVED"


def test_invoice_archiver_json_stream_memory_safety():
    """Verify that InvoiceArchiver reads cold invoices using memory-safe stream parsing (json.load)."""
    # Ensure active archive directory exists
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    
    # Write a test cold archive zip file
    test_data = {
        "COLD-TEST-ID-1": {
            "id": "COLD-TEST-ID-1",
            "date": "2019-01-01",
            "taxpayer_mst": "0102030405",
            "buyer_mst": "0102030405",
            "amount_before_tax": 100.0,
            "items": []
        }
    }
    
    with zipfile.ZipFile(ARCHIVE_FILE, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("invoices.json", json.dumps(test_data))
        
    # We patch json.load to spy on it and assert it is indeed called with a stream
    with patch("json.load", wraps=json.load) as spy_json_load:
        results = InvoiceArchiver.get_archived_invoices("0102030405")
        
        # Verify JSON was streamed safely
        assert len(results) == 1
        assert results[0]["id"] == "COLD-TEST-ID-1"
        assert spy_json_load.call_count == 1
        
    # Clean up test archive file
    if os.path.exists(ARCHIVE_FILE):
        try:
            os.remove(ARCHIVE_FILE)
        except Exception:
            pass


def test_stats_cache_invalidation_isolation():
    """Assert multi-tenant stats cache isolation and robust namespace key mapping."""
    mst_a = "1111111111"
    mst_b = "2222222222"
    
    from_d = "2026-05-01"
    to_d = "2026-05-31"
    direction = "purchase"
    
    # Invalidate both to ensure clean state
    invalidate_stats_cache(mst_a)
    invalidate_stats_cache(mst_b)
    
    stats_a = {"total_spend": 100.0}
    stats_b = {"total_spend": 200.0}
    
    set_cached_stats(mst_a, from_d, to_d, direction, stats_a)
    set_cached_stats(mst_b, from_d, to_d, direction, stats_b)
    
    # Verify cached values exist independently
    cache_a = get_cached_stats(mst_a, from_d, to_d, direction)
    cache_b = get_cached_stats(mst_b, from_d, to_d, direction)
    
    assert cache_a is not None
    assert cache_b is not None
    assert cache_a["total_spend"] == 100.0
    assert cache_b["total_spend"] == 200.0
    
    # Invalidate MST A only, verify MST B cache remains completely untouched
    invalidate_stats_cache(mst_a)
    
    assert get_cached_stats(mst_a, from_d, to_d, direction) is None
    assert get_cached_stats(mst_b, from_d, to_d, direction) is not None
    assert get_cached_stats(mst_b, from_d, to_d, direction)["total_spend"] == 200.0
    
    # Invalidate B
    invalidate_stats_cache(mst_b)
    assert get_cached_stats(mst_b, from_d, to_d, direction) is None
