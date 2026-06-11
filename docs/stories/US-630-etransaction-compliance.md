# Spec: US-630 — E-Transaction Auditing & Digital Signature Integrity Engine (Law 108)

## Status

planned

## Lane

normal

## Product Contract

The system audits the integrity of digital signatures on XML invoices, verifies certificate expiration status, and flags transmission delays between signing and GDT reception to meet compliance requirements under the Tax Administration Law 108/2025/QH15.

## Acceptance Criteria

- [ ] Create `etransaction_signature_audit` and `transmission_delay_logs` tables in tenant databases.
- [ ] Verify digital certificate validity range relative to invoice date. Flag `SIGNATURE_EXPIRED` warnings.
- [ ] Compute signing-to-reception delays and flag a `LATE_TRANSMISSION` warning if it exceeds 24 hours.
- [ ] Log signature status, timestamps, and compliance flags in the tenant database ledger.

## Validation

- `tests/test_v51_features.py::test_etransaction_signature_integrity`
