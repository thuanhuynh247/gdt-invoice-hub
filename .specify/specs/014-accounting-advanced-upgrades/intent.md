# Intent: Advanced Accounting Upgrades & Lieflat Report Generator [GDT-ACC-03]

## Problem Statement [PRB-ACC-ADV-1]
Accountants and enterprise tax directors need automated Transfer Pricing interest expense audit (Decree 132/2020 30% EBITDA cap), OECD Pillar 2 Top-up Tax risk checks, and single-click Lieflat HTML report exports (Report R04 Financial Brief) to present to executive management and tax auditors.

## Expected Outcome [OUT-ACC-ADV-1]
An advanced accounting upgrade suite containing:
1. **Transfer Pricing & CIT Audit Endpoint (`POST /api/accounting/tp-audit`)**: Evaluates interest cap disallowance and related-party transaction risk.
2. **Lieflat HTML Tax Report Generator (`GET /api/accounting/report-html`)**: Renders single-file HTML executive tax report based on Lieflat Report R04 template.
3. **Wise Fintech UI Integration**: Adds Transfer Pricing audit triggers and 1-Click Lieflat HTML report download to `templates/tax_compliance_hub.html`.
4. **100% Automated Test Pass Rate & Telemetry Trace #10**: Validated in `tests/test_v86_accounting_advanced.py` and logged in `harness.db`.
