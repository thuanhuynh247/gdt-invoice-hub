# Story Specification: US-330 — Taxpayer Network Graph Generator

## 📋 Context & Business Value
To detect systematic supplier-buyer collusion or shell invoicing networks, the application builds directed taxpayer network maps (with nodes as business entities and edges representing invoices/transaction volumes).

---

## 🎯 Acceptance Criteria
- **Graph Assembly**: Construct graph representation with nodes for taxpayers and partners, and edges representing invoices.
- **API Endpoint**:
  - `GET /api/fraud/network` returning transaction nodes and edges.

---

## 🛠️ Verification & Test Plan
- Run unit test verifying graph generation from db invoices:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\pytest.exe tests/test_graph_fraud.py -k test_graph_generation"
  ```
