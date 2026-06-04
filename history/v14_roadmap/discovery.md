# Discovery - Version 14.0.0: AI Tax Audit Simulation, Automated Transfer Pricing Compliance & Multi-Currency Treasury Management Hub

## Technical Constraints & Facts

1. **Codebase Inclusions**:
   - `invoices/audit_service.py` conducts GDT checklist verification and exports DOCX mitigation templates.
   - `invoices/related_party_service.py` scans partners directory to flag entity relations.
   - `invoices/exchange_service.py` houses Vietcombank (VCB) rate extraction and translation logic.
   - `invoices/fct_service.py` computes VAT and CIT FCT withholding splits (Circular 103/2014/TT-BTC).
2. **Key Constraints**:
   - Related party identification relies on manual flags and transaction amount thresholds (e.g., EBITDA interest cap checks).
   - VCB rates fallback to the nearest historical record if transaction date rate is missing.
3. **Existing Tests**:
   - `tests/test_fct_auditor.py` verifies VAT and CIT FCT calculations and worksheets.
   - `tests/test_mitigation.py` asserts generated DOCX content format.

---

## Structural Discovery & Integration Points
- All business operations are modularized within separate service files under the `invoices/` directory.
- APIs are declared via blueprints inside `invoices/routes.py` to maintain routing modularity.
