# Discovery - Version 12.0.0: Smart Cash Flow Forecasting, AI Tax Optimization & Cross-Tenant Consolidated Analytics

## Technical Constraints & Facts

1. **Codebase Inclusions**:
   - `invoices/cashflow_service.py` houses cash flow projections and what-if scenario logic.
   - `invoices/cit_service.py` implements statutory rules (Circular 96/2015/TT-BTC) for passenger cars (>1.6B VND limit) and cash invoice threshold (>20M VND).
   - `invoices/routes.py` registers endpoints `/api/finance/cashflow`, `/api/finance/simulate`, `/api/cit/audit`, and `/api/tenant/consolidate`.
2. **Key Constraints**:
   - Multi-tenant dashboard checks permissions via `TenantRoutingSession` or tenant group roles.
   - Scenario adjustments are kept stateless in-memory or in the session context.
3. **Existing Tests**:
   - `tests/test_v12_cashflow.py` verifies projection timelines and payment delay simulation offsets.

---

## Structural Discovery & Integration Points
- All business operations are modularized within separate service files under the `invoices/` directory.
- APIs are declared via blueprints inside `invoices/routes.py` to maintain routing modularity.
