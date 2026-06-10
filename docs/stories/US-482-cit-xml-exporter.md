# Spec: US-482 — Form 03/TNDN XML Exporter & GDT Schema Validator

## Status
planned

## Lane
normal

## Product Contract

The system generates a **Form 03/TNDN XML dossier** matching the official XML structure required by the General Department of Taxation (GDT) of Vietnam, containing the main declaration sheet and Phụ lục 03-1A and 03-2A.

## Acceptance Criteria

- [ ] API endpoint `/api/cit/export-xml` returns a structured GDT-compliant Form 03/TNDN XML file.
- [ ] Incorporates Phụ lục 03-1A (Business Results) and Phụ lục 03-2A (Loss Offset Schedule).
- [ ] Validates output tags (e.g. `<ct21>`, `<ct22>`, `<ct23>`, `<ct31>`, `<ct36>`) to match the schemas.
