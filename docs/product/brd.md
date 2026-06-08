---
id: BRD
type: brd
status: draft
lang: en
owner: PO-Lead
version: 3.0.0
created: "2026-06-08"
updated: "2026-06-08"
goals:
  - id: BRD-G_AUTHENTICATION
    title: "Reliable GDT portal login and captcha solving"
    metrics:
      - "Captcha solve rate (>90%)"
    status: draft
    owner: Dev-Lead
  - id: BRD-G_COMPLIANCE
    title: "Automate tax audit preparation and risk scorecards"
    metrics:
      - "Audit dossier export time (<2s)"
      - "Risk scoring accuracy"
    status: draft
    owner: Dev-Lead
competitors:
  - id: COMP-EZINVOICE
    name: "EzInvoice Manager"
    url: "https://ezinvoice.example"
    threat: med
---

# Business Requirements Document | Tài liệu Yêu cầu Kinh doanh

## Problem / Opportunity | Vấn đề / Cơ hội

Vietnamese companies must reconcile hundreds of invoices monthly while complying with strict, evolving tax laws (Decree 123/2020/NĐ-CP, Decree 132/2020/NĐ-CP). Manual retrieval is slow and error-prone. There is a market opportunity for a secure, local utility that automates downloads and runs advanced tax audits on-premise.

## Business Goals | Mục tiêu kinh doanh

1. **BRD-G_AUTHENTICATION**: Log in to GDT portal and bypass Captcha challenges automatically.
2. **BRD-G_COMPLIANCE**: Automatically screen invoices for invalid signatures, related-party pricing, and tax risks.

## Success Metrics | Chỉ số thành công

* Captcha Solve Success Rate: Greater than 90%.
* Audit Prep Automation: Instant visualizer loading and dossier export under 2 seconds.

## Stakeholders | Bên liên quan

* CFO & Finance Directors
* External Tax Inspectors
* Internal Accountants

## Constraints | Ràng buộc

* MUST run entirely locally (localhost) with no external SaaS databases.
* Must handle GDT portal API changes dynamically.
