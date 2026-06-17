# Spec: US-484 — AI Swarm CIT Finalization Advisory Consensus Chat

## Status
completed

## Lane
normal

## Product Contract

The dashboard page features an **AI Swarm CIT Advisor Console** where multiple tax advisors (CIT Specialist, CFO, Tax Auditor, Legal Adviser) debate tax optimization strategies for non-deductible items and loss absorption schedules, outputting a downloadable memo.

## Acceptance Criteria

- [x] API endpoint `/api/cit/swarm-chat` simulates a consensus debate between at least 3 advisor agent personas.
- [x] Swarm chat UI timeline matches the glassmorphic styling.
- [x] Provides a button to download the debate output as a print-ready CIT Advisory Memo in Markdown.
