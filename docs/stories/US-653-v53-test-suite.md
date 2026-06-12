# Spec: US-653 — End-to-End V53 Verification Test Suite

## Status

planned

## Lane

normal

## Product Contract

Verifies correct Environmental Protection (EP) Tax rates, biodegradable certifications, coal usage exceptions, dashboard view rendering, and REST JSON API endpoints using pytest.

## Acceptance Criteria

- [ ] Execute pytest testing all calculation functions in `invoices/v53_service.py`.
- [ ] Test biodegradable plastic bag exemptions (100% discount).
- [ ] Test coal electricity-generation and export exemptions (100% discount).
- [ ] Test fuel transit and temporary import re-export exemptions.
- [ ] Test HTTP client status codes, view rendering, and REST response shapes.

## Validation

- Pytest runs and all tests pass.
