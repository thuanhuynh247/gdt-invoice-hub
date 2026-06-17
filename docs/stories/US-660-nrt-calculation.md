# Spec: US-660 — Core Natural Resources Tax Calculation Engine

## Status

completed

## Lane

normal

## Product Contract

Classify and calculate Natural Resources Tax (NRT) on minerals, water, timber, and marine products using ad-valorem percentage rates under Luật Thuế tài nguyên 45/2009/QH12.

## Acceptance Criteria

- [x] Calculate metallic ore NRT: Iron 12%, Copper 13%, Gold 15%, Tin 20%.
- [x] Calculate non-metallic mineral NRT: Granite 8%, Sand 7%, Marble 9%, Limestone 5%.
- [x] Calculate water resource NRT: Surface water 2% default, Groundwater 4% default.
- [x] Calculate timber NRT: Natural forest hardwood 25% default, Plantation 3% default.
- [x] Calculate marine product NRT: Aquatic products 2% default, Pearls/Coral 8% default.
- [x] Formula: `NRT = Quantity × Unit Price × Tax Rate (%)`.
- [x] Log all calculations to tenant-specific SQLite tables.

## Validation

- `tests/test_v54_features.py::test_mineral_nrt`
- `tests/test_v54_features.py::test_water_nrt`
- `tests/test_v54_features.py::test_timber_nrt`
- `tests/test_v54_features.py::test_marine_nrt`
