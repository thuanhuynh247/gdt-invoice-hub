# Version 39.0.0 Product Roadmap — VAS 17 Deferred Tax, Treasury Runway Simulator & Supplier Risk Graph Hub

This document defines the official product roadmap and development specifications for **Version 39.0.0** of the GDT Invoice Hub. It details the compliance requirements, technical architecture, and user experience components for implementing Vietnamese Deferred Income Tax accounting (VAS 17), interactive cash runway stress simulators, and multi-dimensional supplier risk network graphs.

---

## 🚀 1. Core Technical & Compliance Pillars

### Pillar A: Vietnamese Deferred Income Tax (VAS 17) Engine (US-510 & US-511)
Under **VAS 17 (Corporate Income Tax)**, differences between accounting profit (Lợi nhuận kế toán) and taxable income (Thu nhập tính thuế) are classified into:
- **Temporary Differences (Chênh lệch tạm thời)**: Arise from timing differences in recognition. These yield **Deferred Tax Assets (Tài sản thuế hoãn lại - TK 243)** and **Deferred Tax Liabilities (Thuế hoãn lại phải trả - TK 347)**.
  - *Depreciation*: Differences between accounting useful lives and the minimum ranges specified in **Circular 45/2013/TT-BTC**.
  - *Provisions*: Disallowed bad debt provisions (Circular 48/2019/TT-BTC) and inventory write-downs until actually realized.
  - *Accrued Expenses*: Operating costs accrued without invoice receipt by year-end.
- **Permanent Differences (Chênh lệch vĩnh viễn)**: Disallowed non-business expenses, penalties for late tax payments, and related-party interest caps.
- **Double-Entry Journal Generation**: Automatically maps accounting adjustments to ledger accounts `8212` (Deferred CIT expense), `243`, and `347`.

### Pillar B: Cash-Flow Sensitivity Sandbox & Runaway Monitor (US-512)
Simulates corporate treasury liquidity under variable transaction collection and payment patterns:
- **DSO (Days Sales Outstanding)** and **DPO (Days Payable Outstanding)** sliders range from 0 to 90 days.
- **Net Monthly Burn Rate**: Tracks cash inflow (A/R collection adjusted for DSO) against cash outflow (A/P payment adjusted for DPO, fixed OPEX, tax liabilities, depreciation).
- **Runway Months**: Computes total runway duration. Renders a premium, glassmorphic circular SVG progress gauge with color indicators (Red under 3 months, Amber under 6 months, Emerald green otherwise).

### Pillar C: Supplier Multi-Dimensional Risk Scorecard & Network Graph (US-513 & US-514)
Aggregates compliance audit markers from invoices and business partner directories:
- Checks blacklist status matching the GDT list of high-risk taxpayers.
- Flags anomalies in invoice signing delays, cash payment volumes, and abnormal transaction frequencies.
- Renders an interactive, zero-dependency SVG-based network graph:
  - Central node: The current business.
  - Outer nodes: Supplier partners scaled by transaction weight (total invoice amount) and colored by risk profile.
  - Integrated with an Offcanvas panel containing detailed risk scorecards and a mock "Live GDT Status Scraper Check".

---

## 📋 2. User Stories & Acceptance Criteria

| Story ID | Title | Status | Lane | Verification |
|---|---|---|---|---|
| **US-510** | VAS 17 Deferred Tax Calculation Engine | `completed` | normal | `test_vas17_deferred_tax_engine` |
| **US-511** | Journal Entry Generator & Advisory | `completed` | normal | `test_vas17_journal_entries` |
| **US-512** | Cash Runway Stress-Test Simulator | `completed` | normal | `test_cash_flow_stress_testing` |
| **US-513** | Supplier Risk SVG Network Graph | `completed` | normal | `test_supplier_network_graph` |
| **US-514** | GDT Scraper & Offcanvas Detail Drawer | `completed` | normal | `test_live_gdt_scraper_check` |
| **US-515** | End-to-End V39 Regression Suite | `completed` | normal | `test_api_routes_unauthorized` |

---

## 🛠️ 3. Verification & Validation

All tests for Version 39 features are implemented in `tests/test_v39_features.py` and are integrated into the global Pytest suite. To verify the implementation, run:

```bash
venv\Scripts\python.exe scripts/harness_win.py validate --cmd "venv\Scripts\python.exe -m pytest tests/test_v39_features.py"
```