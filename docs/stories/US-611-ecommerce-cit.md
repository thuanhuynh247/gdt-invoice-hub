# Spec: US-611 — Digital Platform CIT Auditor & Green Exemption Scanner (Law 67, Articles 4 & 8)

## Status

planned

## Lane

normal

## Product Contract

The system audits e-commerce purchases from foreign digital providers without a permanent establishment to determine their CIT withholding liability, and scans transactions for green bond interest and carbon credit transfer CIT exemptions under Law 67/2025/QH15.

## Acceptance Criteria

- [ ] Create `digital_cit_audit_log` and `green_exemption_logs` tables in tenant databases.
- [ ] Evaluate digital platforms CIT withholding requirements (5% for service, 1% for trade component) on B2B purchases from foreign digital entities without permanent establishment.
- [ ] Exclude first-time carbon credit transfers and green bond interest/transfers from taxable CIT income.
- [ ] Save audited records and exemption indicators in the compliance database.

## Validation

- `tests/test_v49_features.py::test_ecommerce_cit_withholding_and_green_exemptions`
