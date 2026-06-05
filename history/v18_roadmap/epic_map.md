# Epic Map - Version 18.0.0: Enterprise IFRS Compliance & Global Tax Optimization

## Feature Outcome
A standard international accounting alignment hub that translates Vietnamese Accounting Standards (VAS) carrying amounts to IFRS compliance, handles right-of-use (ROU) assets and liabilities under IFRS 16, and calculates covered taxes and substance-based exclusions for OECD Pillar Two top-up estimations.

---

## Epics

### Epic 1: IAS 12 Deferred Tax Ledger
- **Outcome**: Automate carrying amount comparisons, loss carry-forwards valuations, and deferred tax balance calculations mapped to adjusting entries.
- **Complexity**: Medium

### Epic 2: IFRS 16 Leases Amortization
- **Outcome**: Construct discounted cash flow calculator for Right-of-Use asset value and amortization schedules separating interest and principal repayments.
- **Complexity**: Medium

### Epic 3: OECD Pillar Two Global Minimum Tax
- **Outcome**: Perform jurisdictionalEffective Tax Rate (ETR) computations and apply Substance-Based Income Exclusions (SBIE) to assess global top-up liabilities.
- **Complexity**: High

---

## Story Queue

| Story ID | Title | Epic | Status | Dependencies |
| --- | --- | --- | --- | --- |
| `US-300` | IAS 12 Deferred Tax Temporary Difference Engine | Epic 1 | ✅ Completed | None |
| `US-301` | Deferred Tax Balance Sheet Integration | Epic 1 | ✅ Completed | `US-300` |
| `US-302` | IFRS 16 Lease Present Value Calculator | Epic 2 | ✅ Completed | None |
| `US-303` | Lease Liability Amortization Schedule | Epic 2 | ✅ Completed | `US-302` |
| `US-304` | Cross-Tenant Consolidation Router | Epic 3 | ✅ Completed | None |
| `US-305` | OECD Pillar Two GloBE Top-up Tax Estimator | Epic 3 | ✅ Completed | `US-304` |

---

## Current Story to Prepare: `US-300`
- **Objective**: Implement the temporary difference calculator comparing carrying values and tax bases to recognize deferred tax assets and liabilities.
