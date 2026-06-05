# Epic Map - Version 21.0.0: Advanced VAT Fraud Detection & Cryptographic TSA Vault v2

## Feature Outcome
An ultra-secure, fraud-resistant tax compliance ledger utilizing network graph analytics, Merkle-tree cryptography, and Customs-to-VAT import reconciliation.

---

## Epics

### Epic E94: Graph Fraud Analyzer
- **Outcome**: Construct taxpayer transaction graphs and run Outlier and Cycle detection to identify circular invoicing loops.
- **Complexity**: High

### Epic E95: Cryptographic TSA Ledger
- **Outcome**: Cryptographic Merkle ledger recording sequential invoice hashes and validating data integrity.
- **Complexity**: High

### Epic E96: Customs VAT Reconciler
- **Outcome**: Ingestion of VNACCS/VCIS Customs XML declarations and reconciliation against actual paid import VAT.
- **Complexity**: Medium

---

## Story Queue

| Story ID | Title | Epic | Status | Dependencies |
| --- | --- | --- | --- | --- |
| `US-330` | Taxpayer Network Graph Generator | Epic E94 | ✅ Completed | None |
| `US-331` | VAT Fraud Ring Network Detector | Epic E94 | ✅ Completed | `US-330` |
| `US-332` | Immutable Cryptographic Merkle Ledger | Epic E95 | ✅ Completed | None |
| `US-333` | Zero-Knowledge Proof Tax Compliance | Epic E95 | ✅ Completed | `US-332` |
| `US-334` | Customs XML Declaration Parser | Epic E96 | ✅ Completed | None |
| `US-335` | Import VAT Reconciliation & Mitigation | Epic E96 | ✅ Completed | `US-334` |

---

## Current Story to Prepare: `US-330`
- **Objective**: Implement network builder returning buyer-seller nodes and transaction edges, and serialize graph to JSON for frontend rendering.
