# Epic Map - Version 19.0.0: Enterprise Tax Compliance & Dynamic Multi-Tenant Audit Oracle

## Feature Outcome
A fully compliant enterprise tax hub supporting related-party transaction tracking (Decree 132), foreign contractor withholding declarations (Circular 103), and dynamic CIT preferred rates, tax holidays, and R&D funds (Circular 78).

---

## Epics

### Epic 1: Decree 132 Related-Party & EBITDA Cap
- **Outcome**: Persist vendor relationship codes (A-L), compute 30% EBITDA cap on net interest expense deductions, and output disclosure details.
- **Complexity**: Medium

### Epic 2: Circular 103 FCT Withholding Auditor
- **Outcome**: Scan line-item service expenses, calculate FCT VAT/CIT splits, and export Form 01/NTNN in Excel.
- **Complexity**: High

### Epic 3: Circular 78 CIT Preferential Rates & Tax Holidays
- **Outcome**: Dynamic modulations for custom corporate preferential rates, tax exemption/reduction holidays, and science & technology development (R&D) fund shielding.
- **Complexity**: Medium

---

## Story Queue

| Story ID | Title | Epic | Status | Dependencies |
| --- | --- | --- | --- | --- |
| `US-191` | Database Schema & Catalog Management | Epic 1 | Todo | None |
| `US-192` | Core EBITDA interest cap & Form 01/132 disclosures | Epic 1 | Todo | `US-191` |
| `US-193` | FCT Classifier & Line-item calculations | Epic 2 | Todo | `US-191` |
| `US-194` | FCT Form 01/NTNN Excel Exporter | Epic 2 | Todo | `US-193` |
| `US-195` | Preferred CIT Rates, Tax Holidays & R&D Modeler | Epic 3 | Todo | `US-192` |
| `US-196` | End-to-End Integration & Suite Verification | Epic 4 | Todo | All |

---

## Current Story to Prepare: `US-191`
- **Objective**: Extend database model for `Partner` to include Decree 132 relationship code column (`decree_132_relationship`), perform migrations/initializations, and expose CRUD api endpoints for relationship assignment in `routes.py`.
