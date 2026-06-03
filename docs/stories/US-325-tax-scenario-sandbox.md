# Story Specification: US-325 — Tax Scenario Simulation Sandbox

## 📋 Context & Business Value
To optimize corporate structures and evaluate tax risks before transaction closing, financial users require a modeling sandbox to simulate tax holidays, related-party pricing changes, and potential M&A scenarios.

---

## 🎯 Acceptance Criteria
- **Scenario Simulation**: Support custom adjustments for tax rate parameters, transfer pricing adjustments, and tax incentive windows.
- **Reporting Output**: Compute comparative tables showing original vs. simulated tax burdens (VAT, CIT, FCT).
- **API Endpoint**:
  - `POST /api/predictive/simulate-scenario` to execute scenario calculations.

---

## 🛠️ Verification & Test Plan
- Run unit test verifying tax sandbox parameters and calculations:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\pytest.exe tests/test_predictive_forecasting.py -k test_scenario_sandbox"
  ```
