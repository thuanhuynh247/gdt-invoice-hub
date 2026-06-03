# Trợ lý AI Hóa đơn Chuyên sâu (Single-Invoice AI Chat) - Context

**Feature slug:** tax_ai_invoice_chat
**Date:** 2026-06-01
**Exploring session:** complete
**Scope:** Standard
**Domain types:** SEE | CALL | ORGANIZE

## Feature Boundary

This feature enables users to chat with the AI assistant about a specific invoice directly from the invoice details drawer, automatically maintaining the invoice's metadata, line items, and risk warnings as active context throughout the chat session.

## Locked Decisions

These are fixed. Planning must implement them exactly.

- **D1:** Triggering single-invoice chat from the Invoice Details Drawer.
  - A new button labeled "Hỏi Trợ lý AI" (`btnChatAboutInvoice`) is added to the AI section of the invoice details drawer (`invoiceDetailsDrawer` in `templates/invoices.html`). 
  - Clicking this button will open/focus the main floating chatbot panel (`#aiChatCard`). 
  - The client will check if a chat session specifically associated with this `invoice_id` already exists. If yes, it will select and load that session. If no, it will call the POST `/api/ai/chat/sessions` endpoint to automatically create a new session (titled `Hỏi về HĐ [Số hóa đơn]`) linked to this `invoice_id`.
- **D2:** Session association at the Database level.
  - Add an `invoice_id` column to the `AIChatSession` table (db.String(100), nullable=True, FK to `invoice.id` with cascade delete) in `invoices/models.py`.
  - Update POST `/api/ai/chat/sessions` in `invoices/routes.py` to optionally accept `invoice_id` in the request body and save it.
- **D3:** Automatic Context Injection in AIChatAgent.
  - In `invoices/ai_service.py`, if the session has an associated `invoice_id`, the system will load the invoice, its related line items, and any AI audit results.
  - This details context (metadata, lines, audit warnings) will be formatted and injected as a system prompt prefix, ensuring the AI has full visibility of the invoice data in every message turn.

## Specific Ideas And References

- The user wants a clean integration without cluttering the compact details drawer (Option B selected).
- Chat sessions should display their custom titles indicating the specific invoice number for traceability.

## Existing Code Context

### Reusable Assets

- `invoices/ai_service.py` - Contains `AIChatAgent` ask() function, intent classification, and tax regulation RAG search (`get_tax_rag_context()`).
- `static/js/main.js` - Contains `initAiChatbot()` for handling session selections, message sending, and typing indicators.

### Established Patterns

- Asynchronous backend API interactions are routed through the `apiCall(url, options)` utility function in `main.js`.
- Session creation returns a dual-compatibility dictionary (both raw dict and nested under the `session` key).

### Integration Points

- `invoices/models.py` - `AIChatSession` schema update.
- `invoices/routes.py` - `/api/ai/chat/sessions` routes for querying and creating sessions.
- `templates/invoices.html` - The Offcanvas drawer `#invoiceDetailsDrawer` (specifically under the `#detAiAuditBox` header) and the chatbot floating container `#aiChatCard`.

## Canonical References

- `docs/ARCHITECTURE.md` - System architecture description.
- Circular 219/2013/TT-BTC, Decree 123/2020/NĐ-CP - Primary tax regulation bases indexed in FTS5.

## Outstanding Questions

### Resolve Before Planning

*None. Decisions locked.*

### Deferred To Planning

- [ ] Schema migration: Verify SQLite automatic column addition behavior on first start or write a migration query for existing local DB.
- [ ] UI feedback: Determine how to visually indicate that a session is linked to an invoice in the chat window (e.g. badge or helper text).

## Deferred Ideas

- Direct document uploading inside the chat box - Deferred to keep scope standard.
