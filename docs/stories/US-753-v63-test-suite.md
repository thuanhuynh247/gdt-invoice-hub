# US-753: End-to-End V63 Verification Test Suite

## Story
**As a** quality assurance engineer,
**I want** to execute automated tests verifying calculations, salvage reductions, exemptions, and API responses,
**So that** I can prevent regression issues in the mineral extraction fee engine.

## Acceptance Criteria
- Verify calculations of mineral extraction fees based on raw materials (crude oil, natural gas, associated gas, building stones, brick clay) are correct.
- Verify 60% rate application for salvage exploitation (khai thác tận thu) is correct.
- Verify 100% exemptions (household construction, disaster relief, environment reclamation) are correctly handled.
- Verify Flask REST endpoints return correct status codes and JSON payloads.
