# Compounding Learnings: GDT Hub Single-Invoice Contextual AI Chat (US-211)

**Feature Slug:** tax_ai_invoice_chat
**Date Completed:** 2026-06-01
**Author:** Antigravity (Advanced Agentic Coding Specialist)

## 1. Architectural Lessons & Takeaways

### A. Context Injection via SQLite RAG
- **Lesson:** Rather than passing verbose or large raw strings from the frontend, storing and linking contextual data via database keys (`invoice_id` foreign key) reduces security risks, makes state management stateless for frontend, and minimizes token usage in standard chat.
- **Pattern:** `AIChatAgent.ask(session_id)` dynamically resolves the invoice metadata and formats it cleanly inside the system prompt on the fly. This prevents client tampering and ensures consistent prompt structuring across different chat interfaces.

### B. High-Fidelity API Responses
- **Lesson:** Maintain dual-compatibility for JSON schemas (`created_session` vs `{ "session": created_session }`) when returning new resources. Old frontend logic might expect specific structures, while newer asynchronous fetch patterns could rely on cleaner nested objects.

---

## 2. Technical Decisions & Refinements

### A. Automatic Compliance Warning Generation
- During session creation, the backend pre-scans metadata to populate an intuitive contextual welcome message. 
- For instance, if payment method is "Tiền mặt" (Cash) and amount is $\ge 20,000,000$ VND, we automatically append a warning under Article 15 of Circular 219/2013/TT-BTC, informing the accountant that it is not eligible for VAT deduction.

### B. visual Indicators & Seamless Navigation
- **Badge Indicator:** Adding a clear badge `🧾 Số hóa đơn` in the header maintains spatial awareness so that the accountant is always aware they are conversing with specialized tax knowledge bound to that document.
- **Visual List Prefixing:** Prefixing all invoice-bound chat sessions with `🧾` in selection menus lets users instantly locate historical conversations and keeps general queries distinct.

---

## 3. Critical Patterns Promoted

1. **Self-Contained HTTP Mocking for Testing:**
   - Instead of mocking complex interior service methods (like `_call_llm`), mock the network transport level (`requests.post`). This exercises all actual code parsing, formatting, and edge cases, ensuring robust validation.
2. **Stateless Drawer to Chat Switching:**
   - Let the client handle layout state transition (`offcanvas.hide()` then `chatbot.show()`) while fetching session data immediately. This results in a fast, native-feeling user experience.
