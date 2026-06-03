# Version 21.0.0: Advanced VAT Fraud Detection & Cryptographic TSA Vault v2 - Context

**Feature slug:** v21_roadmap
**Date:** 2026-06-03
**Exploring session:** active
**Scope:** Deep
**Domain types:** SEE | CALL | RUN | READ | ORGANIZE

---

## 🌟 Feature Boundary

Version 21.0.0 introduces **Advanced VAT Fraud Detection & Cryptographic TSA Vault v2**, which adds graph analytics to scan for fraud patterns (fake invoices, shell rings) and zero-knowledge/Merkle-tree integrity protocols. The feature boundary includes:
1. **VAT Fraud Ring Network Detector**: Build directed buyer-seller network graphs, running cycle detection and authority scoring (HITS) to flag shell rings and circular transaction loops automatically.
2. **Cryptographic TSA Merkle Ledger**: Encrypt and hash local invoices sequentially using a Merkle tree structure, ensuring historical rows cannot be altered, and supporting Zero-Knowledge Proof (ZKP) verification.
3. **Customs VAT Reconciliation Engine**: Import VNACCS/VCIS Customs XML import declarations, reconciliation of tax bases, HS codes, exchange rate variations, and automated tax correction reports.

---

## 🔒 Locked Decisions

These decisions are locked to guide downstream planning:

- **D21-1: Graph-Based Cycle Detection Threshold**
  - **Decision**: Network graph scanning will identify supplier loops up to length 5. Loops must trigger an immediate, high-priority fraud risk warning in the risk audit panel.
  - **Rationale**: Circular invoicing (buying and selling between the same closed group) is a primary indicator of illegal invoice sales and fake VAT tax shielding.
- **D21-2: SHA-256 Merkle Root Chain Verification**
  - **Decision**: Every invoice transaction will record its transaction hash and the cumulative Merkle root in the database. Any data tampering will invalidate the verification chain.
  - **Rationale**: Guarantees data integrity for tax audits, preventing retroactive modifications of historical records.
- **D21-3: ISO 20022 and Customs XML Schema Compliance**
  - **Decision**: Customs XML files will be mapped matching HS codes, importing customs value, and tax rates against corresponding VAT input invoices.
  - **Rationale**: Directly aligns with Ministry of Finance audit procedures comparing Customs imports to domestic VAT declarations.

---

## 🔍 Existing Code & Reusable Context

Our quick scout has identified several high-value assets and integration seams inside the workspace:

### 1. Reusable Assets
- [test_reconciliation.py](file:///d:/LearnAnyThing/Webapp%20XML/tests/test_reconciliation.py) — Base Customs XML parser logic and invoice reconciler.
- [test_signature_verification.py](file:///d:/LearnAnyThing/Webapp%20XML/tests/test_signature_verification.py) — Signed digital vault checking logic, reusable for Merkle tree audits.

### 2. Integration Seams
- [routes.py](file:///d:/LearnAnyThing/Webapp%20XML/invoices/routes.py) — UI endpoints for fraud graphs, Merkle verification, and Customs discrepancy mitigation dashboards.

---

## 🚀 Handoff Note

Exploring phase is complete. The product boundaries, architectural decisions, and integration guidelines for Version 21.0.0 are fully locked in `CONTEXT.md`.
