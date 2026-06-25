---
id: PRD-AUTH-E1-S1
type: story
epic: PRD-AUTH-E1
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
  - "Captcha solve success rate (>90%)"
acceptance_criteria:
  - "Validate credentials and submit POST request to GDT portal."
  - "Automatically solve GDT login Captcha using local OCR solver."
  - "Restore session state upon detecting expired GDT session."
---

# GDT Portal Authentication & Captcha Bypass — Story PRD-AUTH-E1-S1

## User Story

**As a** General Accountant  
**I want** the system to automatically handle authentication to the GDT portal and solve image Captchas  
**so that** I don't have to manually log in and solve Captchas every time I need to query invoices.

## Acceptance Criteria

- When the application starts a query session, it validates credentials and submits a POST request to GDT portal.
- The system automatically solves the GDT login Captcha using a local OCR solver.
- The system monitors session lifecycle and restores session state upon detecting an expired session.
