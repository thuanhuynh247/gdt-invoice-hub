# US-772: Interactive Version 65 Compliance Hub UI and API

## Story
**As a** system user,
**I want** an interactive dashboard and API for Version 65 EPR compliance,
**So that** I can run computations and view historical audits in real-time.

## Acceptance Criteria
- Create the `/v65-compliance-hub` endpoint rendering an interactive dashboard.
- Create `/api/v65/calculate` (POST) to compute EPR fees.
- Create `/api/v65/compliance-data` (GET) returning baseline comparisons, agent debate simulation, and history logs.
- Include the Version 65 compliance hub link in the main navigation.
