# Brainstorming Version 39: VAS 17 Deferred Tax, Cash-Flow Stress Sandbox & Supplier Risk Network

This document outlines the conceptual designs, aesthetics, and technical components for **Version 39.0.0** of the GDT Invoice Hub.

---

## 1. Core Technical & Compliance Pillars

### Pillar A: Vietnamese Deferred Income Tax (VAS 17) Engine (US-510 & US-511)
Under **VAS 17 (Vietnamese Accounting Standard 17 - Corporate Income Tax)**:
- Differences between Accounting Profit (Lợi nhuận kế toán) and Taxable Income (Thu nhập tính thuế) are classified into temporary differences (chênh lệch tạm thời) and permanent differences (chênh lệch vĩnh viễn).
- Temporary differences (taxable or deductible) give rise to **Deferred Tax Liabilities (Thuế thu nhập hoãn lại phải trả)** and **Deferred Tax Assets (Tài sản thuế thu nhập hoãn lại)**.
- Sources of differences include:
  1. *Fixed Asset Depreciation*: Accounting useful lives differ from Thông tư 45/2013/TT-BTC tax maximum limits.
  2. *Provisions*: Provision for bad debts (dự phòng nợ phải thu khó đòi) or inventory obsolescence (dự phòng giảm giá hàng tồn kho) disallowed for tax purposes in the current period until realized.
  3. *Accrued Expenses*: Expenses accrued but not yet invoiced.
- The Engine will calculate temporary differences, calculate net deferred tax asset/liability positions using the current corporate tax rate (20%), and suggest double-entry ledger entries.

### Pillar B: Cash-Flow Sensitivity Sandbox & Runaway Monitor (US-512)
- Simulates corporate treasury liquidity under varying operational conditions:
  - **A/R Collection Period (Days Sales Outstanding - DSO)**: 15 to 90 days.
  - **A/P Payment Period (Days Payable Outstanding - DPO)**: 15 to 90 days.
- Calculations:
  - **Net Monthly Burn Rate**: Difference between cash inflows (realized collections) and outflows (supplier payments, wages, taxes, depreciation).
  - **Cash Runway (Months)**: Current cash balance / net monthly burn rate.
- Interactive Dashboard: Dynamic charts representing runway duration, alerting users when runway drops below critical limits (3 months).

### Pillar C: Supplier Multi-Dimensional Risk Scorecard & Network Graph (US-513 & US-514)
- Aggregates invoice and compliance signals to score supplier reliability:
  - Blacklist status (matching against GDT list of high-risk taxpayers).
  - Transaction volumes and invoice frequency anomalies.
  - Signing delays (late signing risk).
  - Payment method patterns (excessive cash use).
- Renders an interactive SVG-based Supplier Transaction network graph, mapping relative transaction weights and highlighting high-risk nodes in amber/red.
- Implements a simulated GDT database scraper checking real-time status of business partners.

---

## 2. Design Options & Aesthetics

To wow the user at first glance, the interface at `/v39-deferred-tax-and-risk` will implement a premium layout:

### Option 1: Bento Grid Command Center (Selected)
- **Grid Layout**: A unified bento grid containing:
  - *Deferred Tax Ledger & VAS 17 Calculator* (Top left card - detailed table with temporary differences, permanent differences, deferred tax assets, and journal entry suggestions).
  - *Cash Runway Gauge & Stress Modeler* (Top right card - interactive circular SVG progress gauge showing runway months, paired with A/R and A/P range sliders).
  - *Supplier Risk Network Graph* (Bottom wide card - custom interactive SVG network graph representing suppliers as nodes with size indicating transaction volume and color indicating risk score).
- **Aesthetic Theme**: Dark Emerald & Glassmorphic Slate.
  - Background: Solid dark background (`#0B0F19`) with blurred overlay elements.
  - Panels: Glassmorphism panels with thin borders (`rgba(255, 255, 255, 0.05)`), background blur (`backdrop-filter: blur(16px)`), and rich gradients.
  - Typography: Outfit/Inter google fonts, clear contrast.
  - Micro-animations: Hover expansions on graph nodes, slider adjustments that trigger fluid animation updates on the SVG gauge.

### Option 2: Split-Pane Wizard Layout
- A vertical split layout with controls on the left panel (sliders, forms, settings) and a large results dashboard on the right.
- While functional, it feels less cohesive than a Bento Grid.

### Option 3: Tabbed Ledger Layout
- Uses separate tabs for VAS 17, Cash Flow, and Supplier Risk.
- Not selected because it hides data behind tabs, preventing the user from seeing all three premium compliance features at once.

---

## 3. Concept-to-Mechanic Translation
- **Cash Flow Simulation**: Dragging A/R or A/P sliders will fire an AJAX request to the backend simulation endpoint, immediately re-drawing the circular SVG Runway Gauge and animating the text counter.
- **Supplier Risk Details**: Clicking on any node in the SVG Supplier Network will open an Offcanvas drawer containing the multi-dimensional risk audit metrics for that specific supplier, along with the option to trigger a "GDT Status Scraper Check".
- **VAS 17 Entry Builder**: A toggle allows users to switch between "Straight-Line Accounting" and "TT45 Tax Depreciation" to visualize temporary differences instantly.

---

## 4. Review of Existing Systems
- We will integrate the VAS 17 engine with the existing `FixedAsset` model from V37.
- We will integrate the Supplier Risk scorecard with the MST verification caching from US-019 and GDT scraper helpers.
- Test suites will be added under `tests/test_v39_features.py` to achieve 100% green coverage.
