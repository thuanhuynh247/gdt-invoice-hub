# Story US-881: Noise & Vibration Exemption Auditor

## Business Need
Certain activities, such as public transport/infrastructure works, disaster relief, and cultural traditional festivals, are exempt from environmental noise and vibration penalties due to their public interest.

## Technical Requirements
- Support exemption flags:
  - `public_infrastructure` (direct public construction works) → **100% exempt**.
  - `emergency_relief` (warning sirens, emergency vehicles, disaster relief) → **100% exempt**.
  - `traditional_festival` (cultural or religious events lasting <= 3 days) → **100% exempt**.
- If any exemption flag is true, set the total noise/vibration surcharge to zero.

## Acceptance Criteria
- Verify that setting any valid exemption flag results in a zero surcharge.
- Exemption type must be logged in calculation audits.
