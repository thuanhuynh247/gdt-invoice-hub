# US-743: End-to-End V62 Verification Test Suite

## Story
**As a** quality assurance engineer,
**I want** to execute automated tests verifying calculations, exemptions, and API responses,
**So that** I can prevent regression issues in the emissions fee engine.

## Acceptance Criteria
- Verify calculations of fixed and variable fees for pollutants (dust, SOx, NOx, CO) are correct.
- Verify exemption rules and zero-emission status are correctly handled.
- Verify Flask REST endpoints return correct status codes and JSON payloads.
