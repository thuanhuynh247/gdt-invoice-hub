# Specification: Advanced Accounting Upgrades & Lieflat Report Generator [GDT-ACC-03]

## Functional Requirements

### [FR-ACC-TP-1] Transfer Pricing & CIT Expense Audit Endpoint (`invoices/routes/core.py`)
- Endpoint: `POST /api/accounting/tp-audit`
- Payload: `{"taxpayer_mst": str, "consolidated_revenue": float, "ebitda": float, "net_interest_expense": float, "related_party_revenue": float}`
- Returns:
```json
{
  "status": "success",
  "taxpayer_mst": "0109998887",
  "tp_audit": {
    "is_interest_capped": false,
    "allowed_interest_limit": 300000000.0,
    "disallowed_interest_expense": 0.0,
    "tp_anomaly_risk_score": 15.0,
    "topup_tax_due": 0.0,
    "is_pillar2_subject": false
  }
}
```

### [FR-ACC-REPORT-1] Lieflat HTML Executive Tax Report Generator (`invoices/routes/core.py`)
- Endpoint: `GET /api/accounting/report-html`
- Returns: `text/html` single-file HTML document formatted according to Lieflat Report R04 (Financial Brief) with Mono/porcelain color palette.

### [FR-ACC-UI-1] Wise Fintech Hub UI Enhancements (`templates/tax_compliance_hub.html`)
- Adds **Giao Dịch Liên Kết & Khấu Trừ Lãi Vay 30% EBITDA** audit section.
- Adds **Xuất Báo Cáo Thuế Lieflat HTML (R04)** button.
