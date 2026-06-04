# Discovery - Version 17.0.0: Statutory Accounting, Corporate Banking Reconciliation & Multi-Channel E-Commerce Tax Sync

## Technical Constraints & Facts

1. **Codebase Inclusions**:
   - `invoices/accounting_service.py` builds financial statement models (BCTC) and audits trial balances.
   - `invoices/budget_service.py` generates Form 711/MB payment slips and VietQR codes.
   - `invoices/bank_reconcile_service.py` normalizes bank logs and matches records to invoices.
   - `invoices/ecommerce_service.py` mocks portal integration and matches marketplace transactions.
2. **Key Constraints**:
   - Financial statement codes map strictly to Circular 200/2014/TT-BTC guidelines.
   - E-commerce transactions require deducting commissions, voucher offsets, and shipping fees to match declared revenue.
3. **Existing Tests**:
   - `tests/test_v17_features.py` asserts BCTC compilations, bank matches, and e-commerce sync discrepancies.

---

## Structural Discovery & Integration Points
- All business operations are modularized within separate service files under the `invoices/` directory.
- APIs are declared via blueprints inside `invoices/routes.py` to maintain routing modularity.
