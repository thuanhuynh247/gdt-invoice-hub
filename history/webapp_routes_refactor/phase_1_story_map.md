# Story Map: Phase 1 - Verification & Modular Setup

## Dependency Diagram

```
Entry (monolithic state) -> Story 1.1 (Verify Baseline) -> Story 1.2 (Isolate Workers) -> Story 1.3 (Setup Package Skeleton) -> Exit (Phase 1 Complete)
```

## Story Table

| Story | Outcome | Contributes To | Creates | Done |
|---|---|---|---|---|
| **US-1.1** | Confirm existing tests pass successfully. | Ensures no existing regressions. | Test baseline report | [ ] |
| **US-1.2** | Workers started through `invoices/workers.py` instead of directly inside `app.py`. | Cleaner application initialization. | `invoices/workers.py` | [ ] |
| **US-1.3** | Package `invoices/routes/` is created, and app runs without circular import errors. | Modular layout ready. | `invoices/routes/` folder & `invoices/routes/__init__.py` | [ ] |

## Story-to-Bead Mapping

- **US-1.1:** US-840
- **US-1.2:** US-841
- **US-1.3:** US-842

