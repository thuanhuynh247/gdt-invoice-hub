# Approach - Version 16.0.0: Vietnamese E-Invoice Customs & Import-Export Duty Audit Hub, PIT & Social Insurance Audit Engine, and Secure E-Invoice Archiving & TSA Cryptographic Vault

## Recommended Approach

### 1. Architectural Strategy
- Ensure service modules are self-contained and expose clear functional APIs.
- Avoid introducing circular dependencies on invoice routers.
- Maintain transactional consistency when reading from SQLite database paths.

### 2. Integration Design & Patterns
1. **Customs Reconciler**:
   - Match by Customs Declaration number or vendor name across invoices database.
   - Flag discrepancies if domestic VAT invoice amount does not match customs import VAT.
2. **PIT Form Generation**:
   - Compute progressive tables (5% to 35%) and flat rates (20% for non-residents) automatically.
   - Populate HTKK-compliant XML templates.
3. **Long-Term Validation (LTV)**:
   - Extract signed attributes and verify against a Mock TSA Authority response if external network lookup fails.

---

## Risk Map & Mitigation Strategies

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Dynamic data parsing exceptions | Medium | Add structured validation constraints and catch exceptions gracefully. |
| Performance bottlenecks during batch processing | High | Execute large data imports inside background threads or scheduled queues. |
| Inaccurate tax computation | Critical | Cross-verify results with official Ministry of Finance calculators and write extensive tests. |
