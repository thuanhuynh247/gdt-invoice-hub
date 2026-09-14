# Plan: Accounting-Grade Lean Cockpit [GDT-ACC-02]

## Files That Change

- **[MODIFY] [service.py](file:///d:/LearnAnyThing/Webapp%20XML/invoices/service.py)**: Implement `get_lean_accounting_cockpit()` single-pass SQL query.
- **[MODIFY] [core.py](file:///d:/LearnAnyThing/Webapp%20XML/invoices/routes/core.py)**: Register `GET /api/accounting/cockpit` REST endpoint.
- **[MODIFY] [tax_compliance_hub.html](file:///d:/LearnAnyThing/Webapp%20XML/templates/tax_compliance_hub.html)**: Add Accounting Cockpit Studio Card & JS renderer `fetchAccountingCockpit()`.
- **[NEW] [test_v85_accounting_cockpit.py](file:///d:/LearnAnyThing/Webapp%20XML/tests/test_v85_accounting_cockpit.py)**: Automated pytest verification suite.

## Verification Protocol (Binary Proof of Correctness)
- Execute `python -m pytest tests/test_v85_accounting_cockpit.py tests/test_v84_accounting_lean.py tests/test_lean_webapp_optimizer.py -v`.
- Binary result: `0` exit code.
- Record Telemetry Trace #9 in `harness.db`.
