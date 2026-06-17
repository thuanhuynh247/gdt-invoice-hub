# Discovery - Version 16.0.0: Vietnamese E-Invoice Customs & Import-Export Duty Audit Hub, PIT & Social Insurance Audit Engine, and Secure E-Invoice Archiving & TSA Cryptographic Vault

## Technical Constraints & Facts

1. **Codebase Inclusions**:
   - `invoices/customs_service.py` parses customs XML templates and reconciles import taxes.
   - `invoices/pit_service.py` computes PIT progressive structures and exports Form 05/QTT-TNCN.
   - `invoices/archiver.py` manages encrypted digital vaults (Decree 123 compliant).
   - `invoices/signature_service.py` implements CRL/OCSP path checks and TSA token validation.
2. **Key Constraints**:
   - Payroll spreadsheets are parsed dynamically using cell coordinates mapping.
   - Long-term validation requires checking certificates that may have expired by verifying TSA timestamp records.
3. **Existing Tests**:
   - `tests/test_customs_reconciler.py` checks parser outputs, while `tests/test_signature_verification.py` checks validation logs.

---

## Structural Discovery & Integration Points
- All business operations are modularized within separate service files under the `invoices/` directory.
- APIs are declared via blueprints inside `invoices/routes.py` to maintain routing modularity.
