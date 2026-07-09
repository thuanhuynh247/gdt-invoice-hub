# Technical Approach - Tax Chatbot Awesome Apps

**Feature slug:** tax_chatbot_awesome_apps
**Date:** 2026-06-27

## 1. Technical Path

We will implement the chatbot upgrades in a clean, modular fashion to ensure stability and compatibility with existing tests:

### A. Backend Calculations (`invoices/tax_audit_service.py`)
- Implement `calculate_pit_tax(income: float, dependents: int) -> dict` returning:
  - Personal deduction (11M VND)
  - Dependents deduction (4.4M VND per dependent)
  - Taxable income
  - Progressive tax breakdown across the 7 statutory brackets (5%, 10%, 15%, 20%, 25%, 30%, 35%)
  - Total PIT liability and net income
  - Legal basis reference: *Luật Thuế TNCN & Nghị quyết 954/2020/UBTVQH14*

### B. Tool Detection (`invoices/tax_advisor_service.py`)
- Add a PIT calculation trigger to `detect_and_run_tools(query)` matching keywords: "tính thuế tncn", "tính pit", "giảm trừ gia cảnh", "pit calculator".
- Extract income and dependents using regex parsing. Fallback to default of 30,000,000 VND and 1 dependent if not specified.
- Generate standard Wise-styled CSS cards inside `html_output` matching the layout of FCT and penalty cards.

### C. Chat API Enhancements (`invoices/routes/core.py`)
- In `api_tax_chat()`, capture:
  - Latency: Start a timer at the beginning of the request and record elapsed time using `time.perf_counter()`.
  - RAG Chunks Count: Track the number of citations retrieved from the SQLite regulation database.
  - Token Estimation: Compute a simple character-based word-token heuristic estimate for request & response.
- Return these metrics in the final JSON payload.

### D. Frontend Interface (`templates/tax_advisor.html`)
- Add a Wise glassmorphic status bar at the top of the chat panel.
- Incorporate CSS properties and class mappings for dynamic agent badges (e.g., custom gradients, micro-animations, and tooltips).
- Update the JavaScript message rendering system to parse metrics from the response and display them instantly.
- Dynamically parse and output tool HTML widgets inside assistant bubbles.

## 2. Risks & Mitigations

- **Risk:** Parsing numerical amounts from user queries might fail or match wrong numbers (e.g. taxpayer MST instead of money).
  - **Mitigation:** Use targeted regex matching words like "triệu", "tỷ", or "tr" and numbers accompanied by monetary symbols. If multiple numbers exist, prioritize the one near trigger words.
- **Risk:** Frontend injection vulnerabilities (XSS) from tool HTML output.
  - **Mitigation:** Only render trusted, server-generated widget HTML from the `/api/tax/chat` endpoint and clean it via standard elements insertion.

## 3. Proof Needs

- Unit/smoke tests verifying `calculate_pit_tax` behaves as expected.
- Hand-off validation to ensure `/api/tax/chat` responds with correct schema fields.
- Visual inspection via browser recording or DOM checks.

## 4. Files to Modify

- `invoices/tax_audit_service.py`
- `invoices/tax_advisor_service.py`
- `invoices/routes/core.py`
- `templates/tax_advisor.html`
