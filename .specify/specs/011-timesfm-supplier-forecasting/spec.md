# Specification: TimesFM Supplier Tax & Fee Time-Series Forecasting Engine

## Architectural Overview
Inspired by Google Research's **TimesFM** (`https://github.com/google-research/timesfm`), this module introduces a zero-shot Patch-Decoder Time Series Foundation Engine (`TimesFMPatchDecoder`) specifically tuned for supplier invoice time-series data.

```
Supplier Invoices (DuckDB / SQLite)
       │
       ▼
Monthly Aggregator (VAT, FCT/WHT, Revenue, Tax Count)
       │
       ▼
TimesFM Patch Tokenizer (Patch Size P, Stride S)
       │
       ▼
Patch-Decoder Transformer & Positional Projection
       │
       ▼
Multi-Horizon Quantile Head (P10, P50, P90) & Anomaly Evaluator
       │
       ▼
REST APIs (/api/ai/timesfm/*) ──► Wise Bento UI (Module 5)
```

## Functional Requirements
- `[FR-111-1]`: Aggregate historical invoice facts by Seller MST (NCC) into monthly time-series (`Y_t = [revenue, vat_input, fct_tax, total_payment]`).
- `[FR-111-2]`: Tokenize time-series context of length $L$ into patches of size $P \in \{3, 6\}$ months.
- `[FR-111-3]`: Perform autoregressive patch decoding over horizon $H \in [1, 12]$ months ahead.
- `[FR-111-4]`: Compute confidence intervals (P10, P25, P50, P75, P90, P95) to quantify downside/upside cash flow risk.
- `[FR-111-5]`: Calculate Supplier Risk Index (SRI) to flag potential ghost suppliers, sudden tax spikes, or invoicing anomalies.
- `[FR-111-6]`: Provide scenario simulation API for counterfactual adjustments (+/- price, VAT rate shift, volume shift).

## Data Contracts
### API Request: `POST /api/ai/timesfm/forecast`
```json
{
  "mst_supplier": "0101234567",
  "months_ahead": 6,
  "patch_size": 3
}
```

### API Response: `POST /api/ai/timesfm/forecast`
```json
{
  "status": "success",
  "mst_supplier": "0101234567",
  "supplier_name": "Công ty TNHH Cung Ứng Vinatex",
  "timesfm_metadata": {
    "patch_size": 3,
    "context_length": 12,
    "model": "TimesFM-PatchDecoder-v1.0",
    "zero_shot_confidence": 94.5
  },
  "supplier_risk_index": {
    "risk_score": 15.2,
    "risk_level": "Low",
    "anomaly_flag": false,
    "notes": "Chuỗi thời gian ổn định, không phát hiện bất thường."
  },
  "forecasts": [
    {
      "period": "2026-03",
      "predicted_vat_input": 15400000.0,
      "vat_p10": 13200000.0,
      "vat_p50": 15400000.0,
      "vat_p90": 17800000.0,
      "predicted_revenue": 154000000.0,
      "predicted_fct": 0.0
    }
  ]
}
```
