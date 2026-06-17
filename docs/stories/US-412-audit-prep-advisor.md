# Story Specification: US-412 — AI Tax Audit Prep Advisor & Multi-Agent Swarm Collaboration Hub

## 📋 Context & Business Value
Preparing for a related-party audit requires coordinated input from specialists across Transfer Pricing, VAT, and Corporate Income Tax. This story introduces a simulated multi-agent swarm discussion panel that reviews the transaction compliance parameters and compiles a print-ready Transfer Pricing Audit Preparation Dossier.

---

## 🎯 Acceptance Criteria
- **AI Specialist Swarm Chat Panel**:
  - Simulate a collaborative chat between specialized agent roles:
    1. `JointAuditCoordinator` (Facilitator)
    2. `TransferPricingSpecialist` (Decree 132 & Arm's Length auditor)
    3. `CITSpecialist` (Deduction & adjustment auditor)
    4. `VATSpecialist` (Invoice validation auditor)
  - Generate conversational steps evaluating the taxpayer's risk profile and outlining evidence (e.g. Form 01/132, local benchmark studies, transaction contracts).
- **Printable Audit Prep Dossier Exporter**:
  - Automatically synthesize the swarm's findings into a structured, formal "Transfer Pricing Audit Preparation Dossier" in Markdown/HTML.
  - Detail margin calculations, compliance checks, risk zones, and a list of required documentation for tax inspection.

---

## 🛠️ Verification & Test Plan
- Run tests:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\python -m pytest tests/test_v30_features.py -k test_swarm_and_dossier"
  ```
