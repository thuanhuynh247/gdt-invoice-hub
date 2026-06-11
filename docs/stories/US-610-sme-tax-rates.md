# Spec: US-610 — Revenue-Scaled CIT Classifier & RE Loss Offset Engine (Law 67, Article 10)

## Status

planned

## Lane

normal

## Product Contract

The system implements the progressive Corporate Income Tax (CIT) rate classifier for small and medium enterprises (SMEs) and calculates the offsetting of losses from real estate transfers against income from general production/business operations under the CIT Law 67/2025/QH15.

## Acceptance Criteria

- [ ] Create `sme_cit_classifications` and `re_loss_offset_logs` tables in tenant databases.
- [ ] Determine the CIT rate based on annual revenue thresholds (15% for revenue <3B, 17% for 3B-50B, 20% standard rate).
- [ ] Implement the offsetting rule: permit offsetting real estate transfer losses directly against main production income in the same tax period.
- [ ] Log classification results and computed offsets in the tenant database ledger.

## Validation

- `tests/test_v49_features.py::test_sme_cit_classification`
