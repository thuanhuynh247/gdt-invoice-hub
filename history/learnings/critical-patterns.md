# Critical Patterns & Reusable Lessons

Welcome to the central repository of durable patterns and critical lessons extracted from our engineering iterations. Always review this file before planning or starting execution on new features.

---

## [20260529] Premium HSL-based SVG Charting & Custom Forms CRO
**Category:** pattern
**Feature:** webapp_audit_refinement
**Tags:** [ui-ux, responsive, glassmorphism]

To deliver stunning dashboards that switch themes seamlessly without visual flickers or external script conflicts:
- Use inline SVGs populated with HSL gradient fills (`url(#gradient-id)`) instead of heavy JS chart libraries.
- Define theme properties in `static/css/style.css` using dynamic HSL CSS custom properties (`--bg-card`, `--accent-primary`).
- Utilize `.custom-input` with transition-based focus shadows (`box-shadow: 0 0 12px var(--primary-glow)`) to maximize form completion rates (CRO).

**Full entry:** [20260529-webapp-audit-refinement.md](file:///d:/LearnAnyThing/Webapp%20XML/history/learnings/20260529-webapp-audit-refinement.md)

---

## [20260529] Robust Coordinate SVG Regex Extraction
**Category:** pattern
**Feature:** webapp_audit_refinement
**Tags:** [regex-parsing, robust-code]

When interpreting dynamically generated coordinates or letters in SVG inputs (such as tax-authority CAPTCHA nodes):
- Never rely on strict split methods (`d.split(",")` or `d.split(" ")`) as layout engines vary in spacing, relative prefixes, and coordinate precision.
- Always use high-performance, robust regular expressions (`re.search(r'[Mm]\s*(-?\d+\.?\d*)', d)`) to parse float/integer coordinates from path structures safely.

**Full entry:** [20260529-webapp-audit-refinement.md](file:///d:/LearnAnyThing/Webapp%20XML/history/learnings/20260529-webapp-audit-refinement.md)

---

## [20260529] Stream-based JSON ZIP Decompression & Cold Storage
**Category:** pattern
**Feature:** webapp_audit_refinement
**Tags:** [memory-safety, streaming]

When reading cold storage archives, database backups, or compressed logs packaged inside ZIP streams:
- Never call `.read().decode()` as loading entire file payloads into memory poses severe Out-Of-Memory (OOM) risks under multi-tenant production stress.
- Always pass the raw ZIP stream reference directly to the parser (`json.load(f)`) to achieve memory-safe sequential loading.

**Full entry:** [20260529-webapp-audit-refinement.md](file:///d:/LearnAnyThing/Webapp%20XML/history/learnings/20260529-webapp-audit-refinement.md)

---

## [20260601] Stateful API Binding for Contextual AI Agents & Network Mocking
**Category:** pattern
**Feature:** tax_ai_invoice_chat
**Tags:** [ai-context, testing, standard-chat]

When designing conversational AI agents that interact with specific repository resources (such as specific invoices):
- Do not let the client submit raw, lengthy prompt contexts. Instead, pass resource identifiers (`invoice_id` foreign key) and bind them to the database model (`AIChatSession.invoice_id`). This secures the transaction and keeps token costs low.
- For robust, high-fidelity API testing, mock the network transport level (`requests.post`) instead of internal methods. This ensures that every line of system prompt composition, JSON serialization, and response handling is thoroughly covered by tests.

**Full entry:** [20260601-tax-ai-invoice-chat.md](file:///d:/LearnAnyThing/Webapp%20XML/history/learnings/20260601-tax-ai-invoice-chat.md)

---

## [20260602] Smart SQLite CP1258 Decoding Factory & Mock Test Isolation
**Category:** pattern
**Feature:** harness_onboarding_uat
**Tags:** [sqlite, windows, encoding, testing]

To prevent application crashes on Windows systems when reading or indexing database logs with Vietnamese characters:
- Always use a multi-encoding fallback `decode_smart` as `conn.text_factory` on the SQLite connection.
- Isolate external dependency tests behind mock endpoints when `GDT_USE_MOCK=true` to achieve offline reliability.

**Full entry:** [20260602-harness-onboarding-uat.md](file:///d:/LearnAnyThing/Webapp%20XML/history/learnings/20260602-harness-onboarding-uat.md)

---

## [20260603] P2P Mailroom Architecture for Cooperative AI Swarms & ISO 20022 Bank Matching
**Category:** pattern
**Feature:** v20_roadmap
**Tags:** [ai-swarm, telemetry, bank-matching, iso-20022]

To implement decoupled multi-agent collaboration and high-precision bank transaction matching:
- Utilize a database-backed inbox/outbox table (`AgentMessage`) with stringified JSON payloads to enable asynchronous peer-to-peer message exchanges between specialized agents.
- Map and normalize disparate commercial bank statements into a unified `BankLedger` schema first, then execute a rule-based matching engine with configurable confidence weights (for MST matching, text similarity, and numerical tolerances).
- Automatically flag transactions over 20M VND that lack a matching bank record to comply with non-cash payment rules under Vietnamese VAT law.

**Full entry:** [20260603-v20_roadmap.md](file:///d:/LearnAnyThing/Webapp%20XML/history/learnings/20260603-v20_roadmap.md)

---

## [20260604] Graph-Based Circular Invoicing Detection & Sequential Merkle Ledgers
**Category:** pattern
**Feature:** v21_roadmap
**Tags:** [graph-analytics, fraud-detection, cryptography, merkle-tree]

To identify systemic VAT fraud rings and guarantee tax ledger integrity:
- Represent buyer-seller transactions as a directed network graph, and run cycle-detection algorithms with a depth limit (e.g., depth $\le 5$) to detect circular cost-shielding rings while avoiding exponential scaling.
- Apply HITS (Hubs and Authorities) scoring on transaction networks to flag central invoice-selling nodes (high Hubs) and tax-sink shell companies (high Authorities).
- Construct an immutable transaction ledger using sequential SHA-256 Merkle tree hashing, and leverage Zero-Knowledge Proofs (ZKP) to prove tax rate compliance without leaking actual transaction numbers.

**Full entry:** [20260604-v21_roadmap.md](file:///d:/LearnAnyThing/Webapp%20XML/history/learnings/20260604-v21_roadmap.md)

---

## [20260604] Unified E-Commerce Normalization & Statutory Penalty Simulation
**Category:** pattern
**Feature:** v22_roadmap
**Tags:** [ecommerce-reconciliation, tax-penalties, pit-finalization, decree-125]

To handle multi-platform e-commerce audits and statutory penalty predictions:
- Map platform-specific keys (e.g. Lazada's `gross_revenue` vs Shopee's item price) into a standardized transaction ledger to isolate normalization from downstream matching algorithms.
- Run late-payment penalty simulation beginning the 0.03% daily interest accrual precisely on `due_date + 1` pursuant to Decree 125/2020/NĐ-CP.
- Implement progressive PIT tier calculations using a lookup table of boundaries, and compile Form 05/QTT-TNCN XML returns conforming to GDT's HTKK layout structure.

**Full entry:** [20260604-v22_roadmap.md](file:///d:/LearnAnyThing/Webapp%20XML/history/learnings/20260604-v22_roadmap.md)

---

## [20260605] Secure API Gateway, Webhook Retry & Resilient Tax RAG
**Category:** pattern
**Feature:** v23_roadmap
**Tags:** [hmac-signatures, webhooks-backoff, local-rag, circular-80]

To build secure integration channels and resilient offline tax regulations RAG:
- Authorize API requests via HMAC-SHA256 request signing over a `timestamp + "." + query_string_or_body` payload, rejecting requests with timestamp deviation > 300 seconds.
- Execute exponential retry backoffs for webhooks (delay = $2^{retry} \times 10$ seconds) capped at 3 retries before marking as degraded.
- Embed fallback regex and keyword lookups in RAG interfaces to return local tax decree answers if the Ollama service is unreachable.
- Enforce non-cash payment rules by cross-matching customs imports and domestic VAT invoices with bank transaction ledgers for any refund claim > 20M VND.

**Full entry:** [20260605-v23_roadmap.md](file:///d:/LearnAnyThing/Webapp%20XML/history/learnings/20260605-v23_roadmap.md)




