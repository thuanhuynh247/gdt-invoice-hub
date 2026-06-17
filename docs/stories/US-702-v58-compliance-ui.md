# US-702: Interactive Version 58 Compliance Hub UI and API

## Story
**As a** finance manager,
**I want** an interactive web dashboard at `/v58-compliance-hub`,
**So that** I can calculate NRT, view baselines, and review audit logs.

## Acceptance Criteria
- Web page renders at `/v58-compliance-hub` with NRT calculator.
- REST API POST `/api/v58/calculate` accepts resource details.
- REST API GET `/api/v58/compliance-data` returns baselines and history.
- Navigation dropdown includes V58 link.
