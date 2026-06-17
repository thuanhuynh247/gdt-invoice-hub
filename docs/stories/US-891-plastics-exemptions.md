# Story US-891: Biodegradable Plastic Certification & Exemption Inspector

## Business Need
Decree No. 08/2022/NĐ-CP provides full exemptions from plastic levies for certified biodegradable plastics, packaging materials utilized directly for exports, and agricultural mulching films.

## Technical Requirements
- Support exemption flags:
  - `biodegradable_certified` (biodegradable plastic products complying with national standards) → **100% exempt**.
  - `export_packaging` (plastic items used directly to package export shipments) → **100% exempt**.
  - `agricultural_mulching` (plastic sheets used directly for agricultural mulching) → **100% exempt**.
- Surcharge must evaluate to zero if any valid exemption flag is true.

## Acceptance Criteria
- Set levy to 0 for certified biodegradable, export packaging, or agricultural films.
- Properly audit the exemption type in compliance logs.
