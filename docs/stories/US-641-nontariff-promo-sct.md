# Spec: US-641 — Inland to Non-Tariff Area SCT Auditor & Promotion Price Calculator (Law 66)

## Status

planned

## Lane

normal

## Product Contract

The system audits inland sales into non-tariff zones (taxable under SCT, excluding cars <24 seats) and computes promotion SCT base prices using equivalent/identical market values under the Special Consumption Tax Law No. 66/2025/QH15.

## Acceptance Criteria

- [ ] Create `nontariff_sct_logs` and `promotion_sct_logs` tables in tenant databases.
- [ ] Audit transactions sold into non-tariff areas. Apply SCT (default 10%) unless the item is classified as a passenger car with < 24 seats.
- [ ] Determine correct SCT base price for promotional goods using equivalent or identical market values instead of promotional price (e.g. 0 VND).
- [ ] Log all calculations and warnings in the tenant database.

## Validation

- `tests/test_v52_features.py::test_nontariff_sct_auditing`
- `tests/test_v52_features.py::test_promotion_sct_calculation`
