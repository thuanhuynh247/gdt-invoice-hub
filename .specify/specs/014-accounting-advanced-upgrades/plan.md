# Plan: Advanced Accounting Upgrades & Lieflat Report Generator [GDT-ACC-03]

## Files That Change

- **[MODIFY] [core.py](file:///d:/LearnAnyThing/Webapp%20XML/invoices/routes/core.py)**: Register `POST /api/accounting/tp-audit` and `GET /api/accounting/report-html`.
- **[MODIFY] [tax_compliance_hub.html](file:///d:/LearnAnyThing/Webapp%20XML/templates/tax_compliance_hub.html)**: Add TP Audit modal trigger & Lieflat HTML report download button.
- **[NEW] [test_v86_accounting_advanced.py](file:///d:/LearnAnyThing/Webapp%20XML/tests/test_v86_accounting_advanced.py)**: Automated pytest verification suite.

## Verification Protocol
- `python -m pytest tests/test_v86_accounting_advanced.py tests/test_v85_accounting_cockpit.py tests/test_v84_accounting_lean.py -v` exit code 0.
- Record Telemetry Trace #10 in `harness.db`.
