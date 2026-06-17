# US-712: Interactive Version 59 Compliance Hub UI and API

## Story
**As a** finance manager,
**I want** an interactive web dashboard at `/v59-compliance-hub`,
**So that** I can calculate NALUT, view baselines, and review audit logs.

## Acceptance Criteria
- Web page renders at `/v59-compliance-hub`.
- REST API POST `/api/v59/calculate` accepts land details.
- REST API GET `/api/v59/compliance-data` returns baselines.
- Navigation dropdown includes V59 link.
