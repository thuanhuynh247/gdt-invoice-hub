# Current Story Pack: US-330 - Taxpayer Network Graph Generator

## Context & Alignment
- **Epic**: Epic E94: Graph Fraud Analyzer
- **Story ID**: `US-330`
- **Objective**: Implement network builder returning buyer-seller nodes and transaction edges, and serialize graph to JSON for frontend rendering.

---

## 🚪 Entry State
- The application does not represent buyer-seller networks in a graph format.
- Invoices are queried as independent records rather than relational transaction flows.

---

## 🏁 Exit State
1. **Network Builder Implementation**:
   - Write `invoices/graph_service.py` to extract all unique business partners (sellers and buyers) as nodes, and their invoice transactions (aggregated by count and value) as directed edges.
2. **API Endpoint**:
   - `GET /api/analytics/network-graph` returns the graph nodes and edges in JSON format.
3. **Validation Tests**:
   - A new test suite `tests/test_graph_fraud.py` is written to verify graph generation correctness, Node counts, and directed Edge values.

---

## 📂 Files Likely Touched
- `invoices/graph_service.py` (New file)
- `invoices/routes.py`
- `tests/test_graph_fraud.py` (New test file)

---

## 🔍 Feasibility Assumptions & Risk Mitigations
- **Assumption 1**: Memory usage for the graph is small because the database runs in local/personal sandboxes.
  - *Mitigation*: Limit graph size or filter by transactions within the current year/quarter by default.

---

## 🧪 Verification Plan
- **Preflight & Compilation**:
  - Run compile check to verify syntax: `venv\Scripts\python.exe -m compileall invoices/routes.py`
- **Tests Execution**:
  - Run new unit tests: `venv\Scripts\python.exe -m pytest tests/test_graph_fraud.py -v`

---

## 🛑 Out of Scope
- Running HITS and page-rank algorithms for cycle detection (handled under `US-331`).
- Cryptographic hashing and ZKP validation checks.
