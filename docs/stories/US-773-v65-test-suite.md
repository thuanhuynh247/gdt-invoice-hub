# US-773: End-to-End V65 Verification Test Suite

## Story
**As a** QA engineer,
**I want** an automated test suite verifying EPR calculation logic and routes,
**So that** I can prevent regressions.

## Acceptance Criteria
- Verify calculations of EPR contributions using the formula F = R * V * Fs for packaging, batteries, oil, appliances.
- Verify 100% exemptions (revenue thresholds, import thresholds, closed-loop recycling, export-only) are correctly handled.
- Verify Flask REST endpoints return correct status codes and JSON payloads.
