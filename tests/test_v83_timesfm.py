"""Tests for Google TimesFM Time-Series Foundation Model Engine & API Endpoints (US-350, US-351)."""

from __future__ import annotations
import pytest
from invoices.timesfm_engine import (
    TimesFMPatchDecoder,
    evaluate_supplier_risk_index,
    forecast_supplier_taxes_timesfm
)

def test_timesfm_patch_decoder_unit():
    """Verify patch extraction and quantile forecasting logic in TimesFMPatchDecoder."""
    engine = TimesFMPatchDecoder(patch_len=4, horizon_len=6)
    history = [100.0, 105.0, 110.0, 115.0, 120.0, 125.0, 130.0, 135.0, 140.0]
    
    patches = engine._patchify(history)
    assert len(patches) > 0
    assert patches[0].shape == (4,)
    
    forecasts = engine.predict_quantiles(history, horizon=6)
    assert len(forecasts) == 6
    for f in forecasts:
        assert "horizon_month" in f
        assert f["p10"] <= f["p50"] <= f["p90"]
        assert f["point_forecast"] == f["p50"]

def test_supplier_risk_index_unit():
    """Verify Supplier Risk Index (SRI) calculations and anomaly detection."""
    # Normal stable series
    history_normal = [10.0, 10.5, 10.2, 10.8, 10.1, 10.4]
    risk_normal = evaluate_supplier_risk_index("MST_STABLE", history_normal)
    assert risk_normal["risk_level"] in ["LOW", "MEDIUM"]
    assert risk_normal["risk_score"] < 50.0

    # Volatile/Spike series
    history_volatile = [10.0, 12.0, 100.0, 11.0, 150.0, 12.0, 200.0]
    risk_volatile = evaluate_supplier_risk_index("MST_VOLATILE", history_volatile)
    assert risk_volatile["risk_score"] > 30.0
    assert len(risk_volatile["anomalies"]) > 0

def test_forecast_supplier_taxes_timesfm_synthetic():
    """Verify end-to-end forecasting wrapper produces valid JSON structure."""
    result = forecast_supplier_taxes_timesfm(buyer_mst="0109998887", seller_mst="0101112223", horizon=12)
    assert result["status"] == "success"
    assert "forecast" in result
    assert len(result["forecast"]) == 12
    assert "risk_index" in result
    assert "metrics" in result
    assert result["metrics"]["wape"] >= 0.0

def test_timesfm_flask_api_routes(client):
    """Verify TimesFM REST API endpoints integration in Flask app."""
    with client.session_transaction() as sess:
        sess["username"] = "admin"
        sess["role"] = "admin"
        sess["logged_in"] = True
        sess["taxpayer_mst"] = "0109998887"
        sess["active_taxpayer_mst"] = "0109998887"

    # 1. GET suppliers
    res1 = client.get("/api/ai/timesfm/suppliers")
    assert res1.status_code == 200
    data1 = res1.get_json()
    assert data1["status"] == "success"
    assert isinstance(data1["suppliers"], list)

    # 2. POST forecast
    res2 = client.post("/api/ai/timesfm/forecast", json={
        "seller_mst": "0101112223",
        "horizon": 6
    })
    assert res2.status_code == 200
    data2 = res2.get_json()
    assert data2["status"] == "success"
    assert len(data2["forecast"]) == 6

    # 3. POST scenario simulation
    res3 = client.post("/api/ai/timesfm/scenario", json={
        "seller_mst": "0101112223",
        "horizon": 6,
        "price_shift": 10.0,
        "volume_shift": 5.0,
        "tax_rate_delta": 2.0
    })
    assert res3.status_code == 200
    data3 = res3.get_json()
    assert data3["status"] == "success"
    assert "simulation" in data3
    assert len(data3["simulation"]) == 6
    assert data3["simulation"][0]["simulated_p50"] > data3["simulation"][0]["base_p50"]
