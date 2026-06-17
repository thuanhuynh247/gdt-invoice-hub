# Discovery - Version 18.0.0: Enterprise IFRS Compliance & Global Tax Optimization

## Technical Constraints & Facts

1. **Backend Stack**:
   - **Language**: Python (Flask application)
   - **Database**: SQLite with SQLAlchemy (`invoices/models.py`)
   - **IFRS Logic**: Calculations are housed in `invoices/ifrs_engine.py`
   - **HTTP Routing**: Implemented in `invoices/routes.py`

2. **Compliance Rules (Pillars)**:
   - **Pillar 1 (IAS 12 Deferred Tax)**:
     - Compare Asset/Liability Carrying Value vs. Tax Base.
     - Tax rate is statutory (20% standard).
     - Calculate Net DTA / Net DTL and output balance sheet adjusters.
   - **Pillar 2 (IFRS 16 Lease Amortization)**:
     - Discount future rents to Right-of-Use asset present value.
     - Divide rent payment into interest expense and lease liability reduction.
     - Export month-by-month schedules to PDF and CSV formats.
   - **Pillar 3 (OECD Pillar Two GloBE)**:
     - Aggregate covered taxes and accounting profit per jurisdiction.
     - Minimum tax rate threshold is 15%.
     - Exclude substance-based income (SBIE) - 8% tangible assets and payroll.

3. **Existing Test Suite**:
   - `tests/test_ifrs_engine.py` contains assertions verifying DTA/DTL calculations, lease amortization tables, and GloBE ETR results.

4. **Harness Platform**:
   - Sole orchestrator CLI is `scripts/harness`.
   - Run tests through `harness validate --cmd "pytest"`.

## Structural Discovery & Integration Points

- **`invoices/ifrs_engine.py`**:
  - The primary class is `IFRSEngine` which exports methods for IAS 12 temporary differences, IFRS 16 lease liability tracking, and OECD Pillar Two estimation.
- **`invoices/routes.py`**:
  - Expose API endpoints for IFRS reports.
  - Implement cross-tenant router to merge stats for multi-entity consolidation.
