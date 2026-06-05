# Epic Map - Version 16.0.0: Vietnamese E-Invoice Customs & Import-Export Duty Audit Hub, PIT & Social Insurance Audit Engine, and Secure E-Invoice Archiving & TSA Cryptographic Vault

## Feature Outcome
Establish a compliant, automated, and secure enterprise financial tax compliance and auditing workspace.

---

## Epics

### Customs Audit Hub (E79)
- **Outcome**: Parse Customs XML files and match import VAT declarations to domestic invoices.
- **Complexity**: Medium

### PIT & Social Insurance (E80)
- **Outcome**: Verify payroll compliance and compile annual PIT declarations (Form 05/QTT-TNCN).
- **Complexity**: Medium

### Compliance Vault (E81)
- **Outcome**: Secure invoice archives under Decree 123 using AES-256 and validate long-term digital signatures.
- **Complexity**: High

---

## Story Queue

| Story ID | Title | Epic | Status | Dependencies |
| --- | --- | --- | --- | --- |
| `US-190` | Customs XML Parser & Import-Export Duty Calculator | E79 | ✅ Completed | None |
| `US-191` | Customs-to-Invoice Matcher & Discrepancy Detector | E79 | ✅ Completed | None |
| `US-192` | Payroll & Labor Contract Compliance Audit Engine | E80 | ✅ Completed | None |
| `US-193` | Automated PIT Finalizer & Form 05/QTT-TNCN Scaffolder | E80 | ✅ Completed | None |
| `US-194` | Decree 123 Compliant Digital Vault & XML Archiver | E81 | ✅ Completed | None |
| `US-195` | Long-Term Signature & TSA Validator | E81 | ✅ Completed | None |

---

## Current Story to Prepare: `US-190`
- **Objective**: Implement core mechanisms for Customs XML Parser & Import-Export Duty Calculator.
