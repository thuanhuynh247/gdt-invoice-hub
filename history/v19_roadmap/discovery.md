# Discovery - Version 19.0.0: Enterprise Tax Compliance & Dynamic Multi-Tenant Audit Oracle

## Technical Constraints & Facts

1. **Backend Stack**:
   - **Language**: Python (Flask application)
   - **Database**: SQLite with SQLAlchemy (defined in `invoices/models.py`)
   - **CIT Logic**: Main calculations occur in `invoices/cit_service.py`
   - **HTTP Routing**: Implemented in `invoices/routes.py` (which is ~6.5k lines and defines routes like `/api/cit/finalize` and `/api/cit/simulate-scenario`)

2. **Compliance Rules (Pillars)**:
   - **Pillar 1 (Decree 132/2020/NĐ-CP Related Parties)**:
     - Automatically flag related party status for partners.
     - Support 12 relationship codes (A through L) in the supplier catalog.
     - Implement EBITDA-based net interest expense cap (30% of EBITDA).
     - Generate data for Form 01/132-NĐ-CP (related-party disclosures).
   - **Pillar 2 (Circular 103/2014/TT-BTC Foreign Contractor Tax)**:
     - Scan line items of invoices matching foreign contractor indicators (seller MST starts with `900` or is blank, and name matches known contractors).
     - Split FCT withholding tax into VAT and CIT based on service categories (Software/SaaS: 0% VAT + 5% CIT; Services: 5% VAT + 5% CIT; Royalty: 0% VAT + 10% CIT; Mixed goods & services).
     - Export to **Form 01/NTNN** in Excel format (`ToKhai_01NTNN_[YEAR]_[PERIOD].xlsx`).
   - **Pillar 3 (Circular 78/2014/TT-BTC Preferential CIT & Tax Holidays)**:
     - Dynamic scenario simulations of preferred corporate rates (10%, 15%, or standard 20%).
     - Custom multi-year Tax Holidays inputs (e.g. N years of 100% tax exemption, M years of 50% tax reduction).
     - R&D Fund allocations (up to 10% tax shield deduction from taxable income).

3. **Existing Test Suite**:
   - A pre-written test file `tests/test_fct_auditor.py` exists, asserting FCT contractor classification, tax calculation rules (Google Ads, Zoom, AWS), and Form 01/NTNN Excel file exports.

4. **Harness Platform**:
   - Sole orchestrator CLI is `scripts/harness`.
   - All tests/compile tasks must run inside `harness validate --cmd "<test-command>"`.

## Structural Discovery & Integration Points

- **`invoices/models.py`**:
  - Needs to support persisting related party status and Decree 132 relationship codes (A-L) for each `Partner` record.
  - Needs to allow querying partner classifications in FCT auditing.
- **`invoices/cit_service.py`**:
  - Needs an updated `finalize_cit` that parses related-party status, computes EBITDA using Net Operating Profit (and adjusting for Interest Income/Expense), applies the 30% cap, and formats the output for Form 01/132-NĐ-CP.
  - Needs an updated `simulate_cit_scenario` that supports custom preferred CIT rates, R&D fund allocations (0% to 10%), and tax holidays.
- **`invoices/routes.py`**:
  - Expose API endpoints for managing Related-Party codes.
  - Implement `/api/reports/fct-declaration` and `/api/reports/fct-declaration/export-excel` (as expected by `test_fct_auditor.py`).
  - Extend CIT simulation parameters.
