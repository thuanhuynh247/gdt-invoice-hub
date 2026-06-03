# 0006 Chatbot Gemma-4 Regulation RAG Upgrade

Date: 2026-05-27

## Status

Accepted

## Context

The meInvoice local chatbot (AIChatAgent) needs to advise accountants on the newest Vietnamese tax regulations. Specifically:
1. **VAT Law 48/2024/QH15** (effective July 1, 2025) which outlines significant changes to digital provider withholding, tax refund conditions, and deduction thresholds.
2. **VAT Law 149/2025/QH15** (passed December 11, 2025, effective January 1, 2026) which drastically raises the annual tax-free revenue threshold for household/individual businesses from 200 million VND to 500 million VND and restores commercial raw agricultural exemptions.

We need a lightweight, highly accurate way to retrieve these regulations locally and inject them into the local Gemma-4 prompt context (RAG) when users query about "luật mới", "nông sản", "500 triệu", etc.

## Decision

We decide to:
1. Extend the in-memory `TAX_REGULATIONS` list inside `invoices/ai_service.py` with structured, rich Vietnamese law summaries for Law 48 and Law 149.
2. Optimize the keyword-based router (`get_tax_rag_context`) to search for terms like "luật 48", "luật 149", "500 triệu", "nông sản", "nhà thầu nước ngoài", "thương mại điện tử", "sàn giao dịch", and return the new legal context.
3. Update the system prompt to guide Gemma-4 (Senior Tax Compliance Consultant persona) to highlight the distinct effective dates and explain how Law 149 amends Law 48 (e.g. replacing the 200M threshold with 500M starting Jan 1, 2026).
4. Run regression unit/integration testing on the matching engine to ensure correctness.

## Alternatives Considered

1. **Embedding Database (e.g. Chroma/Faiss)**: Considered too heavy and complex for a purely local database persistence environment without additional system binary dependencies, whereas keyword-based dictionary RAG context in Python is extremely fast, 100% reliable for specific tax articles, and easily testable.

## Consequences

Positive:
- Extremely fast retrieval (0ms latency).
- Easy to audit exact matched regulatory text.
- Standardizes chatbot behavior across platforms.

Tradeoffs:
- Requires manual updates to the `TAX_REGULATIONS` list when laws change (mitigated by direct spec story tracking).

## Follow-Up

- Add unit and integration tests to ensure that tax inquiries pull correct regulations.
- Verify decision with `scripts\validate.bat`.
