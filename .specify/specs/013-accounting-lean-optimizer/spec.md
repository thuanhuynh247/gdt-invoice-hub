# Specification: Accounting-Grade Lean Cockpit [GDT-ACC-02]

## Functional Requirements

### [FR-ACC-COCKPIT-1] Single-Pass Accounting Cockpit Service (`invoices/service.py`)
- Maps to `[PRB-ACC-LEAN-1]`.
- Function: `get_lean_accounting_cockpit(taxpayer_mst: str) -> dict`
- Single-pass SQL aggregation returning:
  - `output_vat`: Total sales VAT collected.
  - `input_vat_total`: Total purchase VAT.
  - `input_vat_deductible`: Eligible input VAT (paid via bank or $\le 20.000.000$ VND).
  - `input_vat_disallowed_cash`: Non-deductible input VAT for cash payments $\ge 20.000.000$ VND.
  - `input_vat_disallowed_blacklisted`: Input VAT from blacklisted supplier MSTs.
  - `net_vat_payable`: `max(0, output_vat - input_vat_deductible)`.
  - `aging_receivables`: `{"1_30": float, "31_60": float, "61_90": float, "over_90": float}`
  - `aging_payables`: `{"1_30": float, "31_60": float, "61_90": float, "over_90": float}`
  - `htkk_ready`: boolean (`True` if zero unverified XML signatures exist).

### [FR-ACC-COCKPIT-2] REST API Endpoint (`invoices/routes/core.py`)
- Endpoint: `GET /api/accounting/cockpit`
- Request Parameters: `taxpayer_mst` (optional in session).
- Response JSON Schema:
```json
{
  "status": "success",
  "taxpayer_mst": "0109998887",
  "cockpit": {
    "output_vat": 150000000.0,
    "input_vat_total": 100000000.0,
    "input_vat_deductible": 95000000.0,
    "input_vat_disallowed_cash": 5000000.0,
    "input_vat_disallowed_blacklisted": 0.0,
    "net_vat_payable": 55000000.0,
    "aging_receivables": {"1_30": 120000000.0, "31_60": 30000000.0, "61_90": 0.0, "over_90": 0.0},
    "aging_payables": {"1_30": 80000000.0, "31_60": 20000000.0, "61_90": 0.0, "over_90": 0.0},
    "htkk_ready": true
  },
  "query_latency_ms": 1.15
}
```

### [FR-ACC-COCKPIT-3] Wise Fintech Bento UI & Lieflat Charts Integration (`templates/tax_compliance_hub.html`)
- Render **Accounting Cockpit Studio Card** on `tax_compliance_hub.html`.
- Display Lieflat F9 Waterfall chart comparing Output VAT ➔ Deductible Input VAT ➔ Net Payable.
- Display Lieflat F12 Dumbbell Queue for Receivables vs Payables Aging comparison.
- Provide 1-Click Fast Audit Buttons & quick filters for Accountants.
