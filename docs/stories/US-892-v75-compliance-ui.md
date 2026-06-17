# Story US-892: Interactive Version 75 Compliance Hub UI and API

## Business Need
Users require a web dashboard under `/v75-compliance-hub` to calculate single-use plastics levies interactively, view history logs, and review consensus discussions.

## Technical Requirements
- Create Flask page route `/v75-compliance-hub`.
- Expose REST endpoints:
  - `POST /api/v75/calculate`: calculate plastic levies.
  - `GET /api/v75/compliance-data`: fetch sample metrics, history log, and agent consensus transcripts.
- Webpage must follow the premium glassmorphism styling, clean inputs, and table logs.

## Acceptance Criteria
- `/v75-compliance-hub` returns 200 OK.
- Calculate button triggers calculation and displays results dynamically.
- Consensus panel updates with simulated discussion on single-use plastics and ocean pollution levies.
