# Spec: US-563 — End-to-End V44 Verification Test Suite

## Status

planned

## Lane

normal

## Product Contract

The system provides a comprehensive verification suite to test all components of Version 44 compliance hub, including the Decree 123 adjustment reconciler, the Sci-Tech fund simulation calculations, welfare limit audits, API routing, and multi-tenant database isolation.

## Acceptance Criteria

- [ ] Implement robust tests inside `tests/test_v44_features.py`.
- [ ] Test Decree 123 VAT Adjustment rules: original invoice linking, amount ceiling validation, taxpayer MST matching, and mismatch flag assertions.
- [ ] Test Circular 67 Science & Tech Fund calculations: tax-deductible ceiling, qualified spending timeline, CIT clawback amount, and daily late payment interest (lãi chậm nộp).
- [ ] Test all three REST endpoints with mock sessions and isolated multi-tenant database paths.

## Validation

- Pytest execution passing 100% of tests.
