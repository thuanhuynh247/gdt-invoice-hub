# Story Specification: US-315 — End-to-End Integration & Suite Verification

## 📋 Context & Business Value
To ensure the web application is stable, correct, and ready for production, all regulatory calculations, database migrations, API routes, and tenant-switching scenarios must be verified under a single unified test runner without regressions.

---

## 🎯 Acceptance Criteria

### 1. Fully Consolidated Suite Execution
- Run all 477 unit, integration, and E2E tests in the suite cleanly.
- Verify that there are zero failures or unexpected skips on the core tax computation paths.

### 2. Multi-Tenant Cross-Module Verification
- Confirm that Decree 132 related-party status, FCT auditing, and IFRS deferred tax/leases work correctly under multi-tenant profiles without leaking data between tenants.

---

## 🛠️ Verification & Test Plan
- Run the full suite using the Harness Windows validation wrapper:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\pytest.exe"
  ```
- Assert that all tests pass.
