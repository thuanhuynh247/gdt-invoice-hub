# Specification: Accounting-Grade Ultra-Lean Compliance Studio [GDT-ACC-01]

## Functional Requirements

### [FR-ACCOUNTING-1] Single-Pass Accounting Summary Engine (`invoices/service.py`)
- Maps to `[PRB-ACCOUNTING-1]`.
- Function: `get_accounting_compliance_summary(taxpayer_mst: str) -> dict`
- Computes in a single SQL query:
  - `sales_revenue`: Total sales amount before tax.
  - `sales_vat`: Total output VAT.
  - `purchase_expense`: Total purchase amount before tax.
  - `purchase_vat`: Total input VAT.
  - `deductible_input_vat`: Input VAT for bank-paid invoices or invoices <= 20,000,000 VND.
  - `non_deductible_cash_vat`: Input VAT flagged non-deductible (cash payment > 20,000,000 VND).
  - `estimated_net_vat_payable`: `max(0, sales_vat - deductible_input_vat)`.
  - `aging_summary`: Debt breakdown by 1-30d, 31-60d, 61-90d, >90d buckets.

### [FR-ACCOUNTING-2] REST API Endpoint (`invoices/routes/core.py`)
- Endpoint: `GET /api/accounting/fast-summary`
- Roles: `admin`, `auditor`
- Returns JSON payload:
```json
{
  "status": "success",
  "taxpayer_mst": "0109998887",
  "accounting_summary": {
    "sales_revenue": 1500000000.0,
    "sales_vat": 150000000.0,
    "purchase_expense": 1000000000.0,
    "purchase_vat": 100000000.0,
    "deductible_input_vat": 95000000.0,
    "non_deductible_cash_vat": 5000000.0,
    "estimated_net_vat_payable": 55000000.0,
    "aging": {
      "1_30": 200000000.0,
      "31_60": 50000000.0,
      "61_90": 10000000.0,
      "over_90": 0.0
    }
  },
  "query_latency_ms": 1.2
}
```

### [FR-ACCOUNTING-3] UI Integration & Lieflat Visual Component (`templates/tax_compliance_hub.html`)
- Injects **Accounting Compliance Fast-Audit Studio Card** into `templates/tax_compliance_hub.html`.
- Displays instant KPI pills for Deductible VAT, Non-Deductible Risk, and Payable Net VAT.
- Interactive toggle for Lieflat F9 Waterfall vs Dumbbell Queue visualizations.
