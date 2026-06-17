# US-681: LF Exemption Auditor

## Description
As an auditor, I want to automatically screen business locations and branches for license fee exemptions, specifically for low-revenue households, agricultural cooperatives, and newly established enterprises.

## Acceptance Criteria
- Set license fee to 0 and mark `is_exempt = True` if annual revenue is ≤ 100 Million VND.
- Set license fee to 0 and mark `is_exempt = True` if the business entity was established in the current calendar year (first year of operation).
- Set license fee to 0 and mark `is_exempt = True` if the entity is an agricultural cooperative.
- Save exemptions and audit results in the multitenant SQLite database.
