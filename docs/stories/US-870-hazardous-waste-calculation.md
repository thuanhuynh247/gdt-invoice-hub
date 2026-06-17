# Story US-870: Core Hazardous Waste Disposal & Licensing Engine

## Business Need
Under Decree No. 08/2022/NĐ-CP and Circular 02/2022/TT-BTNMT, companies generating or treating hazardous waste must track their disposal volumes and pay corresponding licensing and disposal fees.

## Technical Requirements
- Input parameters: waste category (`category_a` or `category_b`), weight in kilograms (`weight_kg`), and license application flag (`apply_license`).
- Calculations:
  - Base licensing fee: **5,000,000 VND** if `apply_license = true`.
  - Disposal surcharge:
    - Category A (standard chemical/organic/oily waste): **2,000 VND / kg**.
    - Category B (heavy metal contaminated, infectious, clinical waste, asbestos, mercury): **5,000 VND / kg**.
  - Total Fee = Licensing Fee + Disposal Fee.

## Acceptance Criteria
- Accurate calculation of both base licensing fee and category disposal fees.
- Reject invalid waste category types or negative weights.
