# Business Context & Architectural Decisions: Version 17.0.0

This document records the architectural and business decisions locked for the design phase of **Version 17.0.0** of the GDT Invoice Hub.

---

## 🔒 Decisions Log

### 1. Decision D17-1: VAS General Ledger Aggregation Rule
- **Decision**: The system will map transactions based on standard VAS accounts guidelines (Circular 200/2014/TT-BTC). Cash balances map Cash-on-hand (`111`) and Cash-in-bank (`112`) accounts.
- **Rationale**: Keeps Balance Sheet compilation compliant with standard Vietnamese corporate audit audits.

### 2. Decision D17-2: GDT Tax Payment Code Mappings (Form 711/MB)
- **Decision**: The system will support Chapter Codes `152` and `552` (Enterprise Chapters) and map taxes to Sub-Chapter codes:
  - Domestic VAT: `1701`
  - Corporate Income Tax (CIT): `1052`
  - Personal Income Tax (PIT): `1001`
  - Import Duty: `1901`
- **Rationale**: Avoids manual entry errors that cause misclassified payments at GDT treasury terminals.

### 3. Decision D17-3: Non-Cash VAT Deduction Threshold (US-203)
- **Decision**: Invoices valued above 20,000,000 VND will trigger a compliance warning if bank reconciliation does not find a corporate bank transfer.
- **Rationale**: Complies with Article 15 of Circular 219/2013/TT-BTC stating input VAT is not deductible for transactions ≥ 20M VND without bank clearing.

### 4. Decision D17-4: E-Commerce Settlement Mapping (US-204, US-205)
- **Decision**: Aggregates retail sales without tax codes under a daily consolidated output invoice matching Shopee/TikTok daily payout logs.
- **Rationale**: Complies with Decree 123/2020/NĐ-CP on retail invoices, while preserving computational efficiency without generating individual buyer XMLs for small purchases.
