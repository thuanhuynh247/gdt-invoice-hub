# Discovery - Version 15.0.0: Automated Corporate Income Tax (CIT) Finalization, Visual Scenario Modeler & Intelligent XML Schema Expansion

## Technical Constraints & Facts

1. **Codebase Inclusions**:
   - `invoices/cit_finalizer.py` calculates taxable income adjustments and builds the Form 03/TNDN XML.
   - `invoices/schema_extension.py` parses arbitrary tags from XML files and manages JSON attributes.
   - `invoices/approval_service.py` tracks multi-user approval histories and digital signatures.
   - `invoices/blockchain_ledger.py` handles cryptographic anchoring, generating sequential block hashes.
2. **Key Constraints**:
   - Form 03/TNDN output must comply with GDT's XML layout validator rules.
   - Ledger records use a Merkle-like sequential hashing technique to guarantee non-repudiation.
3. **Existing Tests**:
   - `tests/test_cit.py` checks final tax liability computations under various R&D credit scenarios.

---

## Structural Discovery & Integration Points
- All business operations are modularized within separate service files under the `invoices/` directory.
- APIs are declared via blueprints inside `invoices/routes.py` to maintain routing modularity.
