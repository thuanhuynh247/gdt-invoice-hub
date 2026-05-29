# Overview

## Current Behavior
Currently, the invoice auditing system checks invoices against six static, predefined compliance rules:
1. **Duplicate check**: Matches seller MST, symbol, and invoice number.
2. **Tax mismatch**: Computes item prices and tax rates against declared tax amount.
3. **High-risk MST**: Cross-references seller MST against a static list of blacklisted tax codes.
4. **Digital signature**: Checks if the signature field is present and valid in the XML.
5. **Late signing**: Compares the difference in days between the invoice date and signing date.
6. **Non-cash compliance**: Flags cash payments for totals exceeding 5,000,000 VND.

These rules do not check the semantic content of the items, invoice line item descriptions, or whether the purchase aligns with standard business expense deduction rules.

## Target Behavior
The system will integrate an AI Compliance Auditor utilizing a local Large Language Model (e.g., Llama-3, Qwen-2.5 via Ollama) or a public LLM API (Gemini/OpenAI) to analyze invoice line items.
1. **Expense Deductibility Audit**: The AI evaluates invoice descriptions to identify personal, non-business related purchases (e.g., luxury retail, gaming consoles, personal cosmetics, spa vouchers) that are potentially miscategorized as deductible business expenses (like "office materials", "business consultancy", or "administrative supplies").
2. **Price Anomaly Detection**: The AI checks line item unit prices against a historical average of similar items in the local database or flags unit prices that appear abnormally inflated for the specified descriptions.
3. **Structured Warning Output**: AI audit results are persisted in the database as warnings and displayed alongside the static warnings in the offcanvas details panel and invoice viewer modal.

## Affected Users
- **Accountants / Administrators**: View AI audit warnings to reject fraudulent or non-compliant invoices before submitting VAT declarations.

## Affected Product Docs
- `docs/product/compliance.md` (new document defining auditing policies)

## Non-Goals
- Real-time automatic rejection of invoices (AI warnings are purely advisory).
- Auto-adjustment of invoice fields by AI without user confirmation.
