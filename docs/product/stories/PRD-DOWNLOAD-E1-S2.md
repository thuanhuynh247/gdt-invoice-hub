---
id: PRD-DOWNLOAD-E1-S2
type: story
epic: PRD-DOWNLOAD-E1
status: approved
lang: en
owner: Dev-Lead
version: 1.0.0
created: "2026-06-08"
updated: "2026-06-08"
personas:
  - "General Accountant"
scope: core-value
moscow: must
size: S
horizon: now
metrics:
  - "Invoice download success rate"
acceptance_criteria:
  - "Compile key metadata from downloaded invoices into a single Excel file."
  - "Apply professional formatting and styling to the generated spreadsheet."
  - "Complete generation in less than 2 seconds after fetching is complete."
---

# Excel Compilation & Formatting — Story PRD-DOWNLOAD-E1-S2

## User Story

**As a** General Accountant  
**I want** downloaded invoice details to be automatically summarized in a styled Excel sheet  
**so that** I can import them directly into my ERP system or perform manual audits.

## Acceptance Criteria

- The application compiles downloaded invoice metadata (buyer, seller, amount, tax, date) into an Excel spreadsheet.
- The spreadsheet uses professional columns and layout formatting (via openpyxl).
- Export operations execute and save the spreadsheet in under 2 seconds.
