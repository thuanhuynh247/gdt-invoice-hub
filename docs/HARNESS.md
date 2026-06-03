# Harness

The project goal is to provide a reusable operating harness that lets humans and
agents turn a future product spec into safe, validated work.

The app is what users touch. The harness is what agents touch.

## Mental Model

```text
------------------+
| Human intent    |
+------------------+
         |
         v
+------------------+
| Feature intake   |
+------------------+
         |
         v
+------------------+
| Story packet     |
+------------------+
         |
         v
+------------------+
| Agent work loop  |
+------------------+
         |
         v
+------------------+
| Product delta    |
+------------------+
         |
         v
+------------------+
| Validation proof |
+------------------+
         |
         v
+------------------+
| Harness delta    |
+------------------+
         |
         v
+------------------+
| Next intent      |
+------------------+
```

Every task has two possible outputs:

1. Product delta: app code, tests, API shape, data model, or product docs.
2. Harness delta: docs, templates, validation expectations, backlog items, or
   decision records that make the next task easier.

## Harness v2.0 (Hermes-Inspired Edition)

Harness v2.0 introduces a state-of-the-art multi-agent operating environment designed for autonomous collaboration, self-improving workflows, and secure execution sandboxes.

### Key Components

1. **Multi-Agent Kanban Board**
   * Durable task coordination layer managed via the `br` (Beads CLI) and `bv` (Beads Viewer) engines.
   * Tracks task dependencies, blockages, run histories, and priorities.
   * Enables "fleet farming" where specialized agents (e.g. implementing agents, quality gatekeepers) collaborate.

2. **Orchestrator v3 Background Processing**
   * Coordinates background task delegation asynchronously to prevent blocking the main developer conversation.
   * Employs "Doer" (functional developer) and "Reviewer" (auditor/linter/tester) patterns.
   * Uses "Hindsight" semantic search log access (via `cass` / `cm` toolsets) to maintain a shared memory loop.

3. **Self-Improving Reflection Loops**
   * Automatically captures developer friction, compiler errors, and audit failures.
   * Feeds back into project guidelines by dynamically proposing updates to skill runbooks (`SKILL.md` documents) or `AGENTS.md`.

4. **YOLO Mode & Execution Sandboxing**
   * Bypasses interactive confirmation gates using the `--yolo` flag for automated pipeline environments.
   * Establaces strict sandbox isolation profiles:
     - `local`: Direct command execution (for read-only queries, code formatting, lints).
     - `containerized`: Docker/Singularity for compiling or testing untrusted payloads.
     - `cloud`/`remote`: Modal, Daytona, and SSH execution backends to control the blast radius.

## Source Hierarchy

```text
User-provided spec or prompt
  input material for first buildout or future changes

docs/product/*
  current product contract derived from accepted input

docs/stories/*
  story-sized work packets and historical evidence

docs/TEST_MATRIX.md
  behavior-to-proof control panel

docs/decisions/*
  why the contract changed
```

Before implementation, product docs describe intent. After implementation,
product docs plus executable tests become the living contract.

## Spec Lifecycle

Harness v2.0 starts without a tracked project spec. When the human provides a
specification, treat it as input material, not as a permanent operating manual.
Use it to populate product docs, story packets, architecture decisions, and
validation expectations during the first buildout.

After the specification has been decomposed, do not keep extending it as the
living product plan. Ongoing work should update the smaller product docs,
stories, test matrix, and decision records.

Ongoing work should enter the harness as one of these input types:

- New spec: a project specification that needs to become product docs and
  initial story candidates.
- Spec slice: a selected behavior from the provided spec.
- Change request: a bounded behavior change, bug fix, or product refinement.
- New initiative: a larger product area that needs multiple stories.
- Maintenance request: dependency, architecture, performance, security, or
  operational work.
- Harness improvement: a process, template, proof, or agent-instruction change.

The spec-to-work loop is:

```text
human intent or supplied spec
  -> classify input type
  -> update or create product contract
  -> create story packet or initiative notes when needed
  -> define validation proof
  -> implement or document the blocker
  -> update product docs, stories, test matrix, and decisions
  -> capture harness friction
```

Large product areas should use scoped initiative notes instead of a second
monolithic specification. An initiative should explain the goal, affected
product docs, candidate stories, validation shape, open decisions, and exit
criteria. If initiative work becomes a repeated pattern, add a template or
proposal to `docs/HARNESS_BACKLOG.md`.

## Growth Rule

The harness grows from friction.

When an agent is confused, repeats manual reasoning, needs a new validation
command, discovers a missing rule, or sees a recurring failure pattern, it must
either improve the harness directly or add a proposal to `HARNESS_BACKLOG.md`.

## Future Validation Ladder

No validation scripts exist yet. When implementation begins, the expected ladder
is:

```text
validate:quick
  format, lint, typecheck, unit tests, architecture check

test:integration
  backend, database, provider, or service checks as the stack requires

test:e2e
  user-visible end-to-end flows

test:platform
  shell, mobile, desktop, or deployment smoke checks as the stack requires

test:release
  full suite, log checks, and performance smoke
```

Agents must not claim these commands pass until they exist and have been run.
