---
id: PRD-COMPLIANCE-E1-S2
type: story
epic: PRD-COMPLIANCE-E1
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
size: S
horizon: now
metrics:
  - "Visual range accuracy"
acceptance_criteria:
  - "Render an SVG-based linear scale showing the sector's arm's length range (p35 to p75) and median (p50)."
  - "Mark the company's actual markup position clearly on the scale."
  - "Color code compliance zones: Green for compliant range, Red for under-priced risk, Yellow/Orange for high-priced risk."
---

# Arm's Length Range Visualizer — Story PRD-COMPLIANCE-E1-S2

## User Story | Câu chuyện người dùng

**As a** Chief Financial Officer  
**I want** to see a visual chart of our company's markup position relative to the arm's length range  
**so that** I can intuitively understand our compliance margin and risk level.

## Acceptance Criteria | Tiêu chí chấp nhận

* Dynamic SVG rendering of the scale.
* Zone highlights corresponding to the sector range.
* Precise marking of the company's current position.
