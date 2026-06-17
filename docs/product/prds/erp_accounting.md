---
id: PRD-ERP
type: prd
brd_goals:
  - BRD-G6
status: draft
lang: en
owner: Dev-Lead
version: 3.0.0
created: "2026-06-08"
updated: "2026-06-08"
personas:
  - "General Accountant"
  - "Tax Compliance Auditor"
scope: in
moscow: must
horizon: now
metrics:
  - "Bank feed reconciliation accuracy (100%)"
  - "OCR processing throughput per invoice (< 500ms)"
  - "E-commerce revenue matching speed"
risks:
  - description: "Bank feed ingestion formats are highly variable."
    impact: high
    likelihood: med
    mitigation: "Create a flexible bank-feed normalizer service and adapter layer."
    status: open
competitive_parity: {}
---

# Enterprise ERP & Advanced Tax Accounting Suite — PRD PRD-ERP

## Overview & Problem | Tổng quan và Vấn đề

Managing multiple transactional streams (e-commerce orders, bank statements, physical paper invoices, delivery notes, and customs declarations) and reconciling them for tax compliance is extremely labor-intensive. General accountants need automated tools to ingest, parse, verify, and cross-match these data streams to ensure they comply with Decree 123 regulations and match the general ledger.

## Personas | Nhóm người dùng

* **General Accountant**: Performs daily bookkeeping, uploads bank statements, matches receipts, and runs reconciliations.
* **Tax Compliance Auditor**: Audits delivery notes, import VAT, and verfies digital signatures or Merkle ledger proofs for immutable logging.

## Functional Requirements (MoSCoW) | Yêu cầu chức năng (MoSCoW)

### Must | Bắt buộc

* **Bank Feed Ingestion & Reconciliation**: Parse Excel/CSV bank statements (Vietcombank, Techcombank, etc.) and match them with GDT electronic invoices.
* **E-Commerce Sync**: Synchronize transaction records from Shopee, Lazada, and TikTok Shop, normalizing order statuses and matching revenue to invoices.
* **OCR Physical Invoice Parsing**: Import physical/scanned PDF/image invoices, run OCR text extraction, and generate XML files conforming to GDT schemas.
* **Statutory Reports (BCTC) Scaffolder**: Generate statutory financial templates and audit ledger integrity indicators.
* **ZKP / Cryptographic Ledgers**: Create a Merkle ledger system and ZK proofs for immutable compliance verification.
* **Foreign Contractor Tax (FCT) Classifier**: Screen and classify contractor invoices and automatically generate Form 01/NTNN.
* **Decree 123 Compliance & Repair**: Audit GDT electronic invoices for syntax errors and apply auto-repair models (such as correcting invalid decimal characters or encoding mismatches).
* **Social Insurance & Customs Sync**: Reconcile delivery notes, customs declarations (import VAT), and social insurance payments with corresponding tax returns.

### Should | Nên có

* Interactive VietQR payment wizard to pay taxes and fees from the compliance hub.
* Anomaly and fraud detection rules for input VAT rings.

### Could | Có thể có

* Multi-currency treasury hedges for import/export VAT mitigation.

### Won't (this round) | Không (lần này)

* Cloud ERP database synchronization (local SQLite storage only).

## Non-Functional Requirements | Yêu cầu phi chức năng

* Ledger auditing and integrity verification must execute in under 1 second.
* ZK compliance proofs must compile in under 3 seconds per batch.
* Decree 123 auto-repair suite must achieve a 100% success rate on schema corrections.
