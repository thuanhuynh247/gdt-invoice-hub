# Spec: US-493 — Fixed Asset Registry & Depreciation Engine (TT45/2013)

## Status
completed

## Lane
normal

## Product Contract

The system provides a **Fixed Asset Registry** and **Depreciation Engine** supporting Thông tư 45/2013/TT-BTC. Users can register fixed assets with acquisition details, choose depreciation methods (straight-line, declining balance, production-based), and the engine auto-computes monthly/annual depreciation schedules. A glassmorphic Asset Management sub-page displays the registry with search/filter and depreciation timeline visualization.

## Acceptance Criteria

- [x] Database models `FixedAsset` and `DepreciationEntry` are created with auto-migration.
- [x] API endpoint `POST /api/assets` creates a new fixed asset record.
- [x] API endpoint `GET /api/assets` returns paginated asset registry with search/filter.
- [x] API endpoint `GET /api/assets/<id>/depreciation-schedule` returns full depreciation schedule.
- [x] Straight-line depreciation formula: Monthly = (Cost - Residual) / Useful Life (months).
- [x] Declining balance with acceleration factor (1.5× for ≤4yr, 2.0× for >4yr).
- [x] Production-based depreciation: Monthly = (Cost - Residual) / Total Output × Actual Output.
- [x] API endpoint `POST /api/assets/<id>/dispose` records disposal with gain/loss calculation.
- [x] SVG timeline chart showing depreciation curve and net book value over time.

## Validation

- `tests/test_v37_features.py::test_asset_registry_crud`
- `tests/test_v37_features.py::test_straight_line_depreciation`
- `tests/test_v37_features.py::test_declining_balance_depreciation`
- `tests/test_v37_features.py::test_asset_disposal_gain_loss`
