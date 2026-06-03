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


