# Spec: US-550 — IAS 12 Deferred Tax Automation Ledger & Temporary Difference Engine

## Status

planned

## Lane

normal

## Product Contract

The system ingests asset and liability carrying amounts (IFRS) and tax bases (VAS) from the tenant database's deferred tax ledger, calculates temporary differences, and computes and saves deferred tax assets (DTA) and deferred tax liabilities (DTL) under IAS 12 rules.

## Acceptance Criteria

- [ ] Create/ensure `ifrs_deferred_tax_ledger` table inside isolated tenant database.
- [ ] Implement temporary difference calculation logic:
  - Asset: Carrying > Tax Base -> DTL; Carrying < Tax Base -> DTA.
  - Liability: Carrying > Tax Base -> DTA; Carrying < Tax Base -> DTL.
- [ ] Save calculated DTA/DTL values back to the ledger and return them to the caller.

## Validation

- `tests/test_v43_features.py::test_ias12_deferred_tax_calculation`
