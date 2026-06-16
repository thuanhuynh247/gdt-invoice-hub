# Story US-851: E-Waste Recycling Exemption & Small Importer Auditor

## Business Need
Under Decree No. 08/2022/NĐ-CP, small manufacturers and importers or goods manufactured/imported directly for export are exempt from VEPF recycling fees to protect small businesses and avoid export double-taxation.

## Technical Requirements
- Implement checking logic for EPR exemptions.
- Exemption criteria:
  1. Export: If the goods are marked for export (`is_export = true`), they qualify for a **100% exemption**.
  2. Small scale: If the business's net revenue from the preceding fiscal year is `< 30,000,000,000 VND` or total import value is `< 3,000,000,000 VND`, they qualify for a **100% exemption**.

## Acceptance Criteria
- Calculate correct net fee after exemptions (should be zero if exempt).
- Audit trace must document the exact exemption rules applied (e.g. `export_exemption`, `small_scale_revenue_exemption`, `small_scale_import_exemption`).
