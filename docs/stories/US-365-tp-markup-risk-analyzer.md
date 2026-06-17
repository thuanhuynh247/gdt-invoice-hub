# Story Specification: US-365 — Transfer Pricing Markup Risk Engine

## 📋 Context & Business Value
Tax audits frequently target transfer pricing policies. Companies need an analysis engine that evaluates their transaction markup levels (EBIT Margin, Gross Margin) against industry standard benchmark ranges (e.g. Interquartile Range) to flag high-risk anomalies.

---

## 🎯 Acceptance Criteria
- **Transfer Pricing Markup Risk Engine**:
  - Retrieve pricing and cost data from transactions with related parties.
  - Calculate margin ratios (Gross Profit margin, Net Operating profit margin).
  - Compare calculated margins against industry benchmark ranges (lower quartile, median, upper quartile).
  - Flag margins below the interquartile range (lower quartile) as "High Risk of Underpricing" (to avoid tax profit shifting).
  - Generate an advisory report with recommended adjustments to reach the median range.

---

## 🛠️ Verification & Test Plan
- Run unit test verifying transfer pricing markup comparisons and risk warnings:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\pytest.exe tests/test_v24_transfer_pricing.py -k test_markup_risk_engine"
  ```
