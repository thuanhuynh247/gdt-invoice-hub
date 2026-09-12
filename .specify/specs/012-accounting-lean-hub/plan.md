# Plan: Accounting-Grade Ultra-Lean Compliance Studio [GDT-ACC-01]

## Files That Change

- **[MODIFY] [service.py](file:///d:/LearnAnyThing/Webapp%20XML/invoices/service.py)**: Add `get_accounting_compliance_summary()` single-pass SQL query.
- **[MODIFY] [core.py](file:///d:/LearnAnyThing/Webapp%20XML/invoices/routes/core.py)**: Add `/api/accounting/fast-summary` GET endpoint.
- **[MODIFY] [tax_compliance_hub.html](file:///d:/LearnAnyThing/Webapp%20XML/templates/tax_compliance_hub.html)**: Add Accounting Fast-Audit Studio Card & JS handler `fetchAccountingSummary()`.
- **[NEW] [test_v84_accounting_lean.py](file:///d:/LearnAnyThing/Webapp%20XML/tests/test_v84_accounting_lean.py)**: Automated pytest verification suite.

## Verification Protocol (Binary Proof of Correctness)
- `python -m pytest tests/test_v84_accounting_lean.py -v` exit code 0.
- Telemetry trace logged in `harness.db`.
