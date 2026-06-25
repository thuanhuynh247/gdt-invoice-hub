---
id: PRD-DOWNLOAD-E1-S1
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
size: M
horizon: now
metrics:
  - "Invoice download success rate"
acceptance_criteria:
  - "Retrieve XML and PDF invoice files from GDT APIs in bulk."
  - "Store all downloaded files securely in a configurable local folder structure."
  - "Handle API rate limits and network retries gracefully."
---

# Bulk XML & PDF Invoice Downloader — Story PRD-DOWNLOAD-E1-S1

## User Story

**As a** General Accountant  
**I want** to specify a date range and download all matching XML and PDF invoices at once  
**so that** I don't have to download them individually from the GDT portal interface.

## Acceptance Criteria

- The application fetches XML and PDF invoices from GDT APIs in bulk based on query parameters.
- Downloaded files are saved to a configurable local directory.
- The downloader throttles requests and retries on failure to handle GDT portal rate-limiting gracefully.
