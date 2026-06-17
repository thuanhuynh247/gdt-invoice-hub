# US-722: Interactive Version 60 Compliance Hub UI and API

## Story
**As a** financial controller,
**I want** a web interface to calculate agricultural land tax and run audits,
**So that** I can manage my agricultural compliance obligations on demand.

## Acceptance Criteria
- Web interface at `/v60-compliance-hub` with user inputs for land grade, crop type, area, and exemption toggle.
- Expose REST API endpoint `/api/v60/calculate` (POST) to compute ALUT.
- Expose REST API endpoint `/api/v60/compliance-data` (GET) to get baseline tests and logs.
- Multi-agent debate panel showing advisory discussions.
