# Version 25.0.0: E-Invoice Corrections, GDT Status Syncing Agent, & Corporate Tax Optimization Modeler - Context

**Feature slug:** v25_roadmap
**Date:** 2026-06-05
**Exploring session:** completed
**Scope:** Deep
**Domain types:** SEE | CALL | RUN | READ | ORGANIZE

---

## 🌟 Feature Boundary

Version 25.0.0 introduces the **E-Invoice Corrections, GDT Status Syncing Agent, & Corporate Tax Optimization Modeler** suite. The feature boundary includes:
1. **GDT Portal Status Syncing (US-370, US-371)**: Agent queries transaction tokens to fetch approval statuses and GDT codes from the sandbox gateway. Dashboard UI supports filters, logs, and manual triggers.
2. **E-Invoice Correction & Replacement (US-372, US-373)**: Generates XML documents for correction/replacement linking back to target invoices. Scaffolds, signs, and transmits Form 04/SS-HĐĐT to report errors.
3. **Corporate Tax Optimization (US-374, US-375)**: Engine models deductible expenses, CIT incentives, and scheduling to project tax liabilities. Dashboard UI renders parameters and dynamic simulation graphs.

---

## 🔒 Locked Decisions

- **D25-1: E-Invoice Reference Mapping under Decree 123**
  - **Decision**: Correction and replacement invoices must include reference fields linking target invoice's GDT code, issue date, template code, and symbol. Reference validation must prevent matching non-existent or cancelled invoices.
- **D25-2: Form 04/SS-HĐĐT Schema & HSM Signing**
  - **Decision**: Form 04/SS XML must follow GDT's official schema format (`<TBao>` with `<DanhSachSaiSot>`). The document must be signed using standard HSM certificates (`sign_xml_invoice`) before gateway transmission.
- **D25-3: GDT Status Syncing Retry Schedule**
  - **Decision**: Status verification check interval should run every 5 seconds for pending records, marking them as `approved` if gateway issues `gdt_code` or `rejected` with errors if gateway rejects the signature or format.
- **D25-4: Tax Optimization CIT Limit Configurations**
  - **Decision**: Hardcode standard CIT rate at 20% and allow model parameters to test preferential rates (e.g. 10%, 15%), tax exemption holidays (e.g. 2 years free, 4 years 50% discount), and interest expense caps at 30% EBITDA.

---

## 🔍 Existing Code & Reusable Context

### 1. Reusable Assets
- `invoices/v24_compliance_service.py` — HSM signing, XML scaffolding, and GDT transmission mock.
- `invoices/models.py` — Database models for taxpayer, invoice, and partners.

### 2. Integration Seams
- `invoices/routes.py` — API routes mapping for compliance services.
- `templates/advanced_audit.html` — Layout UI mapping.

---

## 🚀 Handoff Note

Exploring phase is complete. The boundaries, architectural decisions, and integration guidelines for Version 25.0.0 are fully locked in `CONTEXT.md`.
