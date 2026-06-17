# Spec: US-494 — AI Invoice-to-Asset Linker & CIT Depreciation Validator

## Status
completed

## Lane
normal

## Product Contract

The system provides an **AI Invoice-to-Asset Auto-Linker** that scans the invoice pool for purchases ≥ 30M VND with asset-related keywords (máy tính, xe, máy móc, thiết bị, bất động sản) and suggests fixed asset creation. Includes a **CIT Depreciation Validator** that cross-checks depreciation parameters against Thông tư 45 Appendix 1 maximum useful life limits and flags non-compliant deductions.

## Acceptance Criteria

- [x] API endpoint `POST /api/assets/auto-detect` scans invoices and returns asset candidates with confidence scores.
- [x] Keyword matching + AI classification (Ollama/Gemini) for asset candidate detection.
- [x] Threshold: invoices with `tong_tien_thanh_toan >= 30,000,000 VND`.
- [x] Suggests asset metadata (name, category, useful life) from invoice description.
- [x] CIT Depreciation Validator checks useful_life_months against TT45 Appendix 1 limits.
- [x] Flags assets where depreciation exceeds allowable CIT deduction amount.
- [x] Validation report API: `GET /api/assets/depreciation-validation` returns compliance status.

## Validation

- `tests/test_v37_features.py::test_ai_asset_detection_threshold`
- `tests/test_v37_features.py::test_ai_asset_classification_keywords`
- `tests/test_v37_features.py::test_depreciation_tt45_limit_validation`
