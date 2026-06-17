# Spec: US-451 — Interactive Tax Compliance Calendar & Deadline Dashboard UI

## Status
implemented

## Lane
high_risk

## Product Contract

The system shall provide an **Interactive Tax Compliance Calendar Dashboard** on a new `/v33-compliance` page. The UI displays a visual yearly tax calendar with color-coded deadline cards for all major Vietnamese tax obligations (VAT, CIT, PIT, FCT, Social Insurance). Users can interact with the CIT Quarterly Declaration panel to compute estimated quarterly CIT and generate Form 01A/TNDN XML.

## Acceptance Criteria

- [x] A new page `/v33-compliance` renders `templates/v33_compliance.html` with premium glassmorphism design.
- [x] The page contains a **Tax Compliance Calendar** section displaying monthly deadline cards with status indicators (overdue/upcoming/filed).
- [x] A **CIT Quarterly Declaration** interactive panel with input fields for quarter, year, revenue, COGS, and operating expenses.
- [x] CIT calculation results displayed in a structured card with breakdown items.
- [x] A "Generate Form 01A/TNDN XML" button that calls the backend and displays the raw XML output.
- [x] An **AI Swarm** chat panel for CIT optimization advisory (multi-agent discussion).
- [x] Responsive design with smooth animations, dark mode compatible.
- [x] Navigation link added to the main compliance navigation.

## Design Notes

- **Calendar Cards**: Each month shows relevant deadlines with pill badges (VAT-20, CIT-Q, PIT-Y, etc.).
- **Status Colors**: Red = overdue, Amber = upcoming (<7 days), Green = filed/completed.
- **CIT Panel**: Glassmorphic card with inline calculation preview and XML viewer.
- **Swarm Panel**: Reuses existing swarm chat pattern from v28-v32 compliance pages.
