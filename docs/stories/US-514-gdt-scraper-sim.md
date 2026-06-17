# Spec: US-514 — Live GDT High-Risk Supplier Scraper Simulator & Offcanvas Auditor

## Status

completed

## Lane

normal

## Product Contract

The system integrates an Offcanvas drawer containing detailed audit risks for a selected supplier, featuring a button to trigger a live mock GDT portal check that updates MST status and catalog cache in real-time.

## Acceptance Criteria

- [x] Click events on supplier nodes in the SVG network graph open a detailed sidebar drawer.
- [x] Renders comprehensive metrics: total trade volume, late signing risk, cash ratio, blacklist flags.
- [x] "GDT Check" button fetches GDT portal status using simulated scrapers and updates partner table (`mst_status`, `mst_last_checked`).
- [x] Visual notification/toast shown in UI indicating updated business registration.

## Validation

- `tests/test_v39_features.py::test_live_gdt_scraper_check`