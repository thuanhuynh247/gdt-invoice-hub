# US-732: Interactive Version 61 Compliance Hub UI and API

## Story
**As a** corporate developer,
**I want** a dashboard interface to calculate environmental wastewater fees and view logs,
**So that** we can integrate this reporting into our green finance disclosures.

## Acceptance Criteria
- Web dashboard at `/v61-compliance-hub` with inputs for domestic clean water fee and industrial variable pollutants.
- Expose REST API endpoint `/api/v61/calculate` (POST) to compute EPFW.
- Expose REST API endpoint `/api/v61/compliance-data` (GET) to get baseline tests and historical logs.
- Multi-agent debate panel showing advisor viewpoints.
