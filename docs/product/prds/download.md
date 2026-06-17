---
id: PRD-DOWNLOAD
type: prd
brd_goals:
  - BRD-G5
status: draft
lang: en
owner: Dev-Lead
version: 3.0.0
created: "2026-06-08"
updated: "2026-06-08"
personas:
  - "General Accountant"
scope: in
moscow: must
horizon: now
metrics:
  - "Invoice download success rate"
risks:
  - description: "GDT Portal download APIs throttle or block concurrent requests."
    impact: med
    likelihood: med
    mitigation: "Implement request throttling and exponential backoff."
    status: open
competitive_parity: {}
---

# Invoice Download & Excel Export — PRD PRD-DOWNLOAD

## Overview & Problem | Tổng quan và Vấn đề

Downloading XML and PDF invoices individually from the government portal is tedious. Accountants need a tool to bulk download XML/PDF invoices and compile them into a unified Excel report.

## Personas | Nhóm người dùng

* General Accountant

## Functional Requirements (MoSCoW) | Yêu cầu chức năng (MoSCoW)

### Must | Bắt buộc

* Fetch XML and PDF invoice files from GDT APIs.
* Store downloaded files in a local directory.
* Generate a unified Excel spreadsheet of downloaded invoices with custom styling and formatting.

### Should | Nên có

* Show a progress bar during download operations.

### Could | Có thể có

* Download email-based invoices.

### Won't (this round) | Không (lần này)

* Cloud storage sync.

## Non-Functional Requirements | Yêu cầu phi chức năng

* Excel generation must complete within 2 seconds of fetch completion.
* Strictly run on-premise without uploading invoice data to external servers.
