# Spec: US-583 — End-to-End V46 Verification Test Suite

## Status

completed

## Lane

normal

## Product Contract

An isolated automated test suite verifying error notices processing, conversion duplicate claims auditing, and dashboard API responses.

## Acceptance Criteria

- [x] Write a pytest suite in `tests/test_v46_features.py`.
- [x] Test the database schema initialization in tenant databases.
- [x] Test Form 04/SS status tracking and submission deadline warning triggers.
- [x] Test legacy converted bill duplicate matching rules.
- [x] Test API endpoints `/api/v46/compliance-data` and simulation routes.

## Validation

- `tests/test_v46_features.py`
