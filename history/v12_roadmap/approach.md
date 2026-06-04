# Approach - Version 12.0.0: Smart Cash Flow Forecasting, AI Tax Optimization & Cross-Tenant Consolidated Analytics

## Recommended Approach

### 1. Architectural Strategy
- Ensure service modules are self-contained and expose clear functional APIs.
- Avoid introducing circular dependencies on invoice routers.
- Maintain transactional consistency when reading from SQLite database paths.

### 2. Integration Design & Patterns
1. **Cash Flow Aggregator (`invoices/cashflow_service.py`)**:
   - Gather invoices with due date projections.
   - Subtract payables due, and factor in estimated monthly/quarterly VAT liabilities.
2. **CIT Audit Compliance Rules**:
   - Identify line-items containing key phrases (e.g. 'ô tô', 'xe con') to check passenger car limits.
   - Validate payment method attribute; mark invoices >= 20M VND with payment_method == 'Tiền mặt' as high risk.
3. **Multi-Entity Analytics Hub**:
   - Safely read invoices across different isolated SQLite databases.
   - Implement authorization checks ensuring only group administrators can query consolidated stats.

---

## Risk Map & Mitigation Strategies

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Dynamic data parsing exceptions | Medium | Add structured validation constraints and catch exceptions gracefully. |
| Performance bottlenecks during batch processing | High | Execute large data imports inside background threads or scheduled queues. |
| Inaccurate tax computation | Critical | Cross-verify results with official Ministry of Finance calculators and write extensive tests. |
