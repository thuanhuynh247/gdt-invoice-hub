# US-153 CIT Deduction Advisory Panel

## Status

implemented

## Lane

normal

## Product Contract

The application must provide an AI-powered advisory panel that presents actionable recommendations for resolving CIT non-deductible items. Each recommendation must cite the relevant legal circular and suggest concrete remediation steps (e.g., reclassifying expenses, requesting payment amendments).

## Relevant Product Docs

- `docs/product/v12_roadmap.md`
- Thông tư 96/2015/TT-BTC (Circular 96/2015)

## Acceptance Criteria

- [x] Display a structured list of flagged CIT items with legal citations (e.g., Điều 4, Thông tư 96/2015/TT-BTC).
- [x] Generate recommended adjustment actions per flagged item (reclassify, amend payment method, split invoices).
- [x] Provide one-click copy/download for advisory notes to include in CIT filing documentation.
- [x] Integrate with the existing RAG knowledge base to ground suggestions in current tax regulations.
- [x] Write tests verifying advisory content accuracy and legal citation correctness.

## Design Notes

- **UI panel**: New tab or modal within the tax auditing dashboard.
- **Knowledge base**: Extend existing `data/schemas/tax_knowledge/` with CIT-specific regulation excerpts.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Verify advisory generation produces correct citations and actions |
| Integration | Verify UI renders advisory panel with download/copy functionality |
