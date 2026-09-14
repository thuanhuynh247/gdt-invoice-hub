# Intent: Accounting-Grade Lean Cockpit [GDT-ACC-02]

## Problem Statement [PRB-ACC-LEAN-1]
Vietnamese chief accountants need an all-in-one, ultra-lean Accounting Cockpit to instantly audit VAT deductible status (Decree 123/2020 & Law 149/2024), detect non-deductible cash transactions $\ge 20.000.000$ VND, view aging debt distribution, and trigger 1-click HTKK XML exports without navigating across multiple fragmented screens.

## Expected Outcome [OUT-ACC-LEAN-1]
A high-performance Accounting Cockpit integrating:
1. **Single-Pass Accounting Cockpit Service (`get_lean_accounting_cockpit`)**: Sub-3ms execution time returning deductible VAT, disallowances, tax liability predictions, and 4-bucket aging.
2. **REST API Endpoint (`/api/accounting/cockpit`)**: Delivers structured JSON accounting payloads.
3. **Lieflat Interactive Visual Charts (`F9 Waterfall`, `F12 Dumbbell`, `F17 Candlestick`)**: Visualizing tax flows and aging debt queues directly inside Wise Fintech Bento cards.
4. **1-Click HTKK XML Export Link & Instant Quick Filter**: Filter invoices by tax status, payment method, and risk score in real-time.
5. **100% Automated Test Pass Rate & Telemetry Trace #9**: Validated via `tests/test_v85_accounting_cockpit.py` and logged in `harness.db`.
