# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

## Before exploring, read these

- **`CONTEXT.md`** at the repo root — defines ubiquitous domain language, core entities, system architecture, and UI/UX conventions for Webapp XML.
- **`docs/decisions/`** — read Architecture Decision Records (ADRs) that touch the area you are about to work in.
- **`docs/ARCHITECTURE.md`** — system layering, dependency rules, and boundary parsing.
- **`docs/GLOSSARY.md`** — Harness and development lifecycle terms.

If any of these files don't exist, **proceed silently**. Don't flag their absence; don't suggest creating them upfront. The `/domain-modeling` skill (reached via `/grill-with-docs` and `/improve-codebase-architecture`) creates or updates them lazily when terms or decisions actually get resolved.

## File structure

Single-context repo layout:

```
/
├── CONTEXT.md                         ← Core ubiquitous glossary and domain model
├── docs/
│   ├── ARCHITECTURE.md                ← System layering & parse-first boundaries
│   ├── GLOSSARY.md                    ← Harness & agent terminology
│   └── decisions/                     ← Architecture Decision Records (ADRs)
│       ├── 0001-harness-first-development.md
│       ├── 0004-sqlite-durable-layer.md
│       └── ...
└── invoices/                          ← Application domain, routes, and services
```

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `CONTEXT.md`. Don't drift to synonyms the glossary explicitly avoids (e.g. use `e-invoice` or `HĐĐT` instead of ambiguous generic `bill`).

If the concept you need isn't in the glossary yet, that's a signal — either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/domain-modeling`).

## Flag ADR conflicts

If your output contradicts an existing ADR in `docs/decisions/`, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0004 (sqlite-durable-layer) — but worth reopening because…_
