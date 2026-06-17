# Current Story Pack: US-300 - IAS 12 Deferred Tax Temporary Difference Engine

## Context & Alignment
- **Epic**: Epic 1: IAS 12 Deferred Tax Ledger
- **Story ID**: `US-300`
- **Objective**: Implement the temporary difference calculator comparing carrying values and tax bases under IFRS/VAS.

---

## 🚪 Entry State
- The `IFRSEngine` lacks temporary difference logic comparing assets and liabilities.
- There are no helper classes to audit Deferred Tax Assets/Liabilities on statutory records.

---

## 🏁 Exit State
1. **IAS 12 Calculations Engine**:
   - `IFRSEngine.calculate_temporary_differences` correctly identifies:
     - Deferred Tax Assets (DTA) when asset carrying < tax base, or liability carrying > tax base.
     - Deferred Tax Liabilities (DTL) when asset carrying > tax base, or liability carrying < tax base.
2. **Validation Tests**:
   - `tests/test_ifrs_engine.py` asserts DTA/DTL calculations and entries.

---

## 📂 Files Likely Touched
- `invoices/ifrs_engine.py`
- `tests/test_ifrs_engine.py`

---

## 🔍 Feasibility Assumptions & Risk Mitigations
- **Assumption**: A statutory CIT rate of 20% is applicable for standard calculations.
  - *Mitigation*: Fallback to standard 20% but support dynamic tax rate overrides.

---

## 🧪 Verification Plan
- **Preflight & Compilation**:
  - Run compile checks using Python standard tool.
- **Tests Execution**:
  - Run the test suite: `python scripts/harness_win.py validate --cmd "pytest tests/test_ifrs_engine.py"`

---

## 🛑 Out of Scope
- Balance sheet integration of adjusting entries (handled under `US-301`).
- IFRS 16 lease schedules (handled under `US-302` / `US-303`).

---

## 🧩 Bead Mapping
- **Bead US-300-1**: Implement standard IAS 12 DTA/DTL comparison model.
