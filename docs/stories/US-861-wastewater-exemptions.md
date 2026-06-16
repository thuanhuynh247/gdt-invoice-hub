# Story US-861: Wastewater Exemption Auditor

## Business Need
Decree No. 53/2020/NĐ-CP provides exemptions for non-polluting water loops (e.g. cooling water) and discharges that flow directly into centralized wastewater treatment facilities (which already pay treatment fees) to avoid double taxation.

## Technical Requirements
- Support exemption flags:
  - `cooling_water` (only cooling loops, not contacting pollutants) → **100% exempt**.
  - `municipal_treatment_inflow` (flows into municipal or industrial zone sewers) → **100% exempt**.
  - Surcharges must reduce to zero when these flags are set to true.

## Acceptance Criteria
- Zero fee computed for cooling water or municipal treatment inflows.
- Exemption type logged in calculation history for auditing.
