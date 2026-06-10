# Spec: US-505 — End-to-End V38 Validation Test Suite

## Status
completed

## Lane
normal

## Product Contract
Comprehensive test suite verifying electronic delivery notes parser, timeline calculations, logistics allocator, and cost-base adjuster.

## Acceptance Criteria
- [x] Pytest suite verifying XML parsing of PXK documents.
- [x] Pytest suite verifying allocation algorithms and VAS 02 adjustments.
- [x] Verify test suite integration under validate command.

## Validation
- `python scripts/harness_win.py validate --cmd "venv\Scripts\python.exe -m pytest tests/test_v38_features.py"`
