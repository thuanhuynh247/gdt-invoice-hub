# Story Specification: US-395 — Smart Treasury & VAT Forecast Scenario Sandbox UI

## 📋 Context & Business Value
Financial officers need to forecast tax payment dates and simulate cash reserves. This story implements a cash flow and tax sandbox dashboard where users can interactively forecast VAT/CIT and cash projections.

---

## 🎯 Acceptance Criteria
- **Scenario Simulation Engine**:
  - Predict VAT/CIT liabilities and cash flow over a 60-day horizon by combining upcoming contract milestones and actual unpaid invoice records.
  - Implement sliders allowing the user to simulate payment delay factors (e.g. customers paying 10 days late) or tax discount packages (e.g., 30% CIT reduction).
- **Interactive Sandbox View**:
  - Provide a dashboard visualization (a grid layout with metrics and simulated values).
  - Export a compiled forecast PDF report.

---

## 🛠️ Verification & Test Plan
- Run tests:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\python -m pytest tests/test_v27_features.py -k test_treasury_forecast_sandbox"
  ```
