# Approach - Version 15.0.0: Automated Corporate Income Tax (CIT) Finalization, Visual Scenario Modeler & Intelligent XML Schema Expansion

## Recommended Approach

### 1. Architectural Strategy
- Ensure service modules are self-contained and expose clear functional APIs.
- Avoid introducing circular dependencies on invoice routers.
- Maintain transactional consistency when reading from SQLite database paths.

### 2. Integration Design & Patterns
1. **CIT Finalization Model**:
   - Aggregate income, add back non-deductible expenses (from US-152), and subtract tax incentives.
   - Check interest expense limits (30% EBITDA) to generate final tax liability.
2. **Schema Extension Parser**:
   - Use standard `xml.etree.ElementTree` to parse custom tags defined in configuration profiles, storing matches in the metadata JSON column.
3. **Blockchain Verification Loop**:
   - Recalculate block hashes sequentially on request to verify audit trail integrity and raise alarms on mismatches.

---

## Risk Map & Mitigation Strategies

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Dynamic data parsing exceptions | Medium | Add structured validation constraints and catch exceptions gracefully. |
| Performance bottlenecks during batch processing | High | Execute large data imports inside background threads or scheduled queues. |
| Inaccurate tax computation | Critical | Cross-verify results with official Ministry of Finance calculators and write extensive tests. |
