# Version 27.0.0: Electronic Delivery Notes, Pre-Audit Risk Radar, & E-Contract Treasury Sandbox - Context

**Feature slug:** v27_roadmap
**Date:** 2026-06-05
**Exploring session:** completed
**Scope:** Deep
**Domain types:** SEE | CALL | RUN | READ | ORGANIZE

---

## 🌟 Feature Boundary

Version 27.0.0 introduces the **Electronic Delivery Notes (PXK) Sync & Reconciler, Pre-Audit Tax Risk Scorecard, and E-Contract Treasury Sandbox** suite. The feature boundary includes:
1. **Electronic Delivery Notes (US-390, US-391)**: Parse PXK XML conforming to Decree 123 regulations. Reconcile goods SKU lists, quantities, and dates against issued commercial invoices, exposing quantity variances or missing linkages.
2. **Pre-Audit Risk Scorecard (US-392, US-393)**: Engine calculates a weighted Tax Risk Index (0-100) along 5 dimensions (Related Party limits, blacklisted supplier list, delivery-to-invoice latency >10 days, cash transactions >= 20M VND, and high cancellation rates). Renders a responsive zero-dependency SVG radar chart on the dashboard UI.
3. **E-Contract Treasury Sandbox (US-394, US-395)**: Parser reads structured electronic contract details (XML/JSON format) containing payment milestones. Reconciles invoice and payment schedules with milestones. Simulates corporate cash flows and VAT/CIT obligations over a 60-day window with sliders.

---

## 🔒 Locked Decisions

- **D27-1: Electronic Delivery Note (PXK) Verification Code & Fields**
  - **Decision**: Parsed PXK models must map SKU-level variables (`MaHang`, `TenHang`, `DonViTinh`, `SoLuong`) and verify them against invoice lines. Variances between quantity delivered and quantity invoiced must raise a specific audit alert flag.
- **D27-2: Weighted Tax Risk Index Logic**
  - **Decision**: The overall score is calculated as: `RiskIndex = (RelatedPartyWeight * RPS) + (BlacklistWeight * BLS) + (LatencyWeight * LATS) + (CashWeight * CASH) + (CancelWeight * CANCEL)`, where weights sum to 1.0. If the index exceeds 70, a critical warning badge is displayed.
- **D27-3: SVG Radar Chart Scalability**
  - **Decision**: Visual representation of the risk scorecard must be drawn using clean, native inline SVG polygon elements on the `/v27-compliance` dashboard page, avoiding any external heavy charting libraries.
- **D27-4: Contract Milestone Cashflow Reconciliation**
  - **Decision**: Projection calculation aggregates all upcoming e-contract milestones and invoices due within 60 days, dynamically adjusting when users tweak sliders for delay settings.

---

## 🔍 Existing Code & Reusable Context

### 1. Reusable Assets
- `invoices/v26_service.py` — Structure of knowledge graph lookup and compliance calculations.
- `invoices/models.py` — Invoice and line item models.

### 2. Integration Seams
- `invoices/routes.py` — Register endpoints.
- `templates/v26_compliance.html` — Base layout to copy for `v27_compliance.html` theme setup.

---

## 🚀 Handoff Note

Exploring phase is complete. The boundaries, architectural decisions, and integration guidelines for Version 27.0.0 are fully locked in `CONTEXT.md`.
