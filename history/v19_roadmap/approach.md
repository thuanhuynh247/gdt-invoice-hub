# Approach - Version 19.0.0: Enterprise Tax Compliance & Dynamic Multi-Tenant Audit Oracle

## Recommended Approach

### 1. Database Schema Extensions (`invoices/models.py`)
- We will add a `decree_132_relationship` column (`db.Column(db.String(10), nullable=True)`) directly to the `Partner` model to persist the related-party relationship code (letters A through L).
- Expose helper routes under `invoices/routes.py` to get/set related-party relationship codes for partners, allowing the UI to manage the catalog.

### 2. Decree 132 Related-Party & Transfer Pricing Engine (`invoices/cit_service.py`)
- Modify `finalize_cit` to compute:
  - `EBITDA = Net Operating Profit + Net Interest Expense + Depreciation`
  - Where `Net Interest Expense = Interest Expense (635) - Interest Income (515/deposit interest)`
  - Flag any net interest expense exceeding the 30% EBITDA cap.
  - Compile transfer pricing disclosures for **Form 01/132-NĐ-CP** by scanning purchase/sales transactions with partners who have a non-null relationship code.

### 3. FCT Withholding Auditor & Circular 103 Rules (`invoices/routes.py` & new utility)
- Implement `/api/reports/fct-declaration` to scan and aggregate FCT-applicable invoices.
- **FCT Identification Rules**: Sellers with MST starting with `900`, or empty MST combined with foreign contractor keywords (e.g. Google, Zoom, AWS, Microsoft, Facebook).
- **Line-item level splitting**:
  - **SaaS/Software License**: VAT: 0%, CIT: 5%
  - **Online Advertising & Hosting Services (e.g. Google Ads, AWS)**: VAT: 5%, CIT: 5%
  - **Royalties**: VAT: 0%, CIT: 10%
  - **Default services**: VAT: 5%, CIT: 5%
- Generate the **Form 01/NTNN** Excel export matching the file structure verified by `test_fct_auditor.py`.

### 4. CIT Scenario Modeler with Tax Holidays & R&D Fund
- Update `simulate_cit_scenario` in `cit_service.py` to incorporate:
  - Preferred CIT rates (10%, 15% instead of standard 20%).
  - Tax Holiday schedules: N years of 100% tax exemption, M years of 50% tax reduction.
  - Science & Technology (R&D) fund deduction (up to 10% of taxable income).

## Risk Map & Mitigation Strategies

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Database synchronization conflicts | Medium | Write raw DDL updates or ensure the SQLite db is initialized/updated dynamically during tests. |
| Inaccurate FCT classification | High | Implement a fallback classifier with regex checking on line item names and seller names (e.g., matches "Zoom Pro" for SaaS, "Google Ads" for services). |
| Performance overhead on large invoice tables | Low | Implement indexed queries on `seller_mst` and `taxpayer_mst`. |

## Reusable Learnings (from `critical-patterns.md`)
- **Smart SQLite Text Factory**: Always apply `decode_smart` as `conn.text_factory` on the SQLite connection.
- **HSL styling in UI**: Maintain clean CSS styles with CSS variables to avoid presentation breakage.
