# US-763: End-to-End V64 Verification Test Suite

## Story
**As a** QA engineer,
**I want** an automated test suite verifying solid waste calculation logic and routes,
**So that** I can prevent regressions.

## Acceptance Criteria
- Verify calculations of solid waste fees based on classes (hazardous waste, ordinary industry, construction, other) are correct.
- Verify 100% exemptions (on-site self-recycling, agricultural byproducts, rural households) are correctly handled.
- Verify Flask REST endpoints return correct status codes and JSON payloads.
