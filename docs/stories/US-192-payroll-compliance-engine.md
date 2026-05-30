# US-192 Payroll & Labor Contract Compliance Audit Engine

## Status

planned

## Lane

normal

## Product Contract

The application must support uploading corporate Excel payroll sheets, parsing them, and auditing them against labor contract templates to verify PIT withholding, social insurance contributions, and tax-exempt allowances.

## Relevant Product Docs

- `docs/product/v16_roadmap.md`

## Acceptance Criteria

- [ ] Support importing Excel payroll files and mapping payroll columns (salary, allowances, deductions).
- [ ] Implement payroll audit logic to verify employee & employer social insurance contributions against statutory rates.
- [ ] Implement allowance checks to flag welfare, lunch, and telephone allowances exceeding statutory tax-exempt thresholds.
- [ ] Display an audit summary dashboard showing high-risk items, wrong calculations, or missing contracts.
- [ ] Expose API endpoint `POST /api/pit/payroll-audit` to execute payroll checks.
- [ ] Write unit tests verifying payroll Excel parsing, insurance calculation, and allowance check compliance.

## Design Notes

- **Module**: `invoices/payroll_auditor.py`
- **Data model**: Supports mapping of custom Excel files using column profiles.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | `pytest tests/test_v16_payroll_auditor.py` checking social insurance calculation math and allowance limit alerts |
| Integration | Uploading a payroll sheet with wrong calculations returns explicit validation error codes |
