---
id: VISION
type: vision
status: draft
lang: en
owner: PO-Lead
version: 3.0.0
created: "2026-06-08"
updated: "2026-06-08"
personas:
  - "Chief Financial Officer"
  - "Tax Compliance Auditor"
  - "General Accountant"
---

# Vision — Invoice Download Webapp | Tầm nhìn

## Problem Narrative | Câu chuyện vấn đề

Vietnamese businesses struggle to retrieve, validate, and manage e-invoices directly from the General Department of Taxation (GDT) portal due to:
1. Frequent portal downtime and API changes.
2. Complex Captchas blocking bulk downloads.
3. Lack of automated compliance screening for invalid signatures, fake suppliers, or risk signs.
4. Difficulty calculating complex related-party transactions and transfer pricing ranges (Decree 132/2020/NĐ-CP).

This webapp provides a single, local, robust bridge to fetch all electronic invoices, analyze their tax compliance, flag risks, and perform transfer pricing modeling securely on-premise.

## Personas | Nhóm người dùng

* **Chief Financial Officer (CFO)**: Uses dashboards to track corporate tax compliance risk and prepare dossiers for inspection.
* **Tax Compliance Auditor**: Evaluates related-party transactions and verifies compliance signatures.
* **General Accountant**: Manages portal authentication, fetches XMLs, and exports structured reports.

## Value Proposition | Đề xuất giá trị

A local-first, zero-dependency portal integrating invoice collection, Decree 123 XML compliance verification, related-party transaction discovery, and transfer pricing risk simulation.

## North-Star | Sao Bắc Đẩu

Provide 100% accurate, real-time invoice retrieval and compliance screening to eliminate tax audit surprises.

## 1–3 Year Direction | Hướng đi 1–3 năm

Automate compliance with tax intelligence, support electronic contract reconciliation, and expand swarm-simulation capabilities for custom auditing scenarios.
