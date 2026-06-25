---
id: PRD-AUTH-E1-S2
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
moscow: should
size: S
horizon: now
metrics:
  - "Captcha solve success rate (>90%)"
acceptance_criteria:
  - "Run a background daemon thread that pre-fetches and pre-solves up to 2 GDT CAPTCHAs."
  - "Ensure cached CAPTCHAs expire after 120 seconds to prevent stale tokens."
  - "Retrieve pre-solved CAPTCHAs instantly from the queue on query initiation."
---

# CAPTCHA Caching & Prefetch Queue — Story PRD-AUTH-E1-S2

## User Story

**As a** General Accountant  
**I want** GDT login Captchas to be fetched and solved in the background before I initiate a query  
**so that** I don't experience network latency or delays during login attempts.

## Acceptance Criteria

- A background daemon thread checks the prefetch queue length and maintains up to 2 pre-fetched and pre-solved CAPTCHAs.
- Cached CAPTCHAs expire after 120 seconds to prevent GDT token staleness.
- The system instantly retrieves a pre-solved CAPTCHA from the queue, falling back to synchronous fetch if empty.
