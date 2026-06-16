# Story US-882: Interactive Version 74 Compliance Hub UI and API

## Business Need
Users require a web dashboard under `/v74-compliance-hub` to calculate noise and vibration surcharges interactively, view history, and simulate stakeholder consensus.

## Technical Requirements
- Create Flask page route `/v74-compliance-hub`.
- Expose REST endpoints:
  - `POST /api/v74/calculate`: calculate noise and vibration surcharges.
  - `GET /api/v74/compliance-data`: fetch sample metrics, history log, and agent consensus transcripts.
- Webpage must follow the premium glassmorphism styling, clean inputs, and table logs.

## Acceptance Criteria
- `/v74-compliance-hub` returns 200 OK.
- Calculate button fires API call and renders results dynamically.
- Consensus panel updates with simulated discussion on noise and vibration regulations.
