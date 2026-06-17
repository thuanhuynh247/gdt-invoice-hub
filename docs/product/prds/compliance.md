---
id: PRD-COMPLIANCE
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
  - "Chief Financial Officer"
  - "Tax Compliance Auditor"
scope: in
moscow: must
horizon: now
metrics:
  - "Audit dossier export time (< 2s)"
  - "Risk scoring accuracy"
risks:
  - description: "Complex tax audit rules change with new decrees."
    impact: high
    likelihood: med
    mitigation: "Keep transfer pricing formulas and rules dynamic and configurable."
    status: open
competitive_parity: {}
---

# Tax Compliance & Transfer Pricing Audit — PRD PRD-COMPLIANCE

## Overview & Problem | Tổng quan và Vấn đề

Tax inspections under Decree 123 and Decree 132 (related-party transactions and transfer pricing) are highly complex. CFOs and tax compliance auditors need to run automated risk calculations and prepare documentation to defend their transfer pricing policies during audits.

## Personas | Nhóm người dùng

* **Chief Financial Officer (CFO)**: Evaluates high-level corporate tax risks and penalty projections.
* **Tax Compliance Auditor**: Generates audit dossiers, reviews margins, and analyzes transfer pricing ranges.

## Functional Requirements (MoSCoW) | Yêu cầu chức năng (MoSCoW)

### Must | Bắt buộc

* **Transfer Pricing Engine**: Determine compliance status (compliant, under-priced, high-priced risk) using arm's length ranges (e.g. p35 to p75).
* **Penalty Projections**: Project CIT underpayments, 10% underpayment penalties, and 0.03% daily interest.
* **Interactive SVG Visualizer**: Render arm's length ranges and company markup dynamically in an interactive diagram.
* **Audit Swarm & Dossier Exporter**: Swarm panel simulating joint coordinator, tax inspector, and transfer pricing advisor agents, and an export utility generating PDF or Markdown dossiers.

### Should | Nên có

* Direct download of PDF dossiers in the browser.

### Could | Có thể có

* Live sync of market markup database.

### Won't (this round) | Không (lần này)

* Automatic filing to GDT portals.

## Non-Functional Requirements | Yêu cầu phi chức năng

* Swarm agent simulation responses must render in real-time.
* Dossier exports must compile in under 2 seconds.
