# Intent: Accounting-Grade Ultra-Lean Compliance Studio [GDT-ACC-01]

## Problem Statement [PRB-ACCOUNTING-1]
Vietnamese chief accountants and tax auditors need an instant, single-pass compliance verification engine that validates e-invoices against Decree 123/2020/NĐ-CP, Circular 78/2021/TT-BTC, CIT Law 149/2024, and FCT Circular 103/2014 without sluggish multi-query database latency or bloated UI components.

## Expected Outcome [OUT-ACCOUNTING-1]
An ultra-lean Accounting Compliance Fast-Audit Studio integrating:
1. **Single-Pass Accounting Aggregation**: Instant VAT input/output deductible breakdown, non-deductible cash payments >20M VND, FCT withholding tax, and aging debt buckets.
2. **Lieflat Charts Visual Dashboard**: High-taste visual accounting charts (Waterfall for VAT, Dumbbell Queue for Aging, Candlestick for monthly tax range).
3. **REST API Endpoint (`/api/accounting/fast-summary`)**: Returns standardized accounting compliance JSON payload under 5ms.
4. **100% TDD Pass Rate & Telemetry**: Full pytest coverage in `tests/test_v84_accounting_lean.py` and recorded Harness trace.
