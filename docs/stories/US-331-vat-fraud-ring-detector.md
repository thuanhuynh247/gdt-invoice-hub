# Story Specification: US-331 — VAT Fraud Ring Network Detector

## 📋 Context & Business Value
To automatically flag circular VAT invoicing structures, the system performs graph analytics, checking for supplier-buyer transaction loops (cycles of length <= 5) and calculating HITS hub/authority score anomalies.

---

## 🎯 Acceptance Criteria
- **Analytics Logic**:
  - Implement cycle detection up to depth 5.
  - Calculate Hub and Authority scores to find suspicious transaction hubs.
- **API Endpoint**:
  - `GET /api/fraud/alerts` returning list of detected loops and outlier scores.

---

## 🛠️ Verification & Test Plan
- Run unit test verifying fraud loop detection:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\pytest.exe tests/test_graph_fraud.py -k test_fraud_loop_detection"
  ```
