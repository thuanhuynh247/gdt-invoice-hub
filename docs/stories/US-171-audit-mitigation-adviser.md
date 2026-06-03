# US-171 Audit Mitigation Adviser

## Status

implemented

## Lane

normal

## Product Contract

The application must provide legal citations for simulated audit warning flags and auto-generate standard Vietnamese explanation letter templates (công văn giải trình) exportable to DOCX and PDF.

## Relevant Product Docs

- `docs/product/v14_roadmap.md`
- Circular 96/2015/TT-BTC (CIT deductibility criteria)
- Circular 219/2013/TT-BTC (VAT deductibility rules)

## Acceptance Criteria

- [x] Match warning badges to relevant Vietnamese tax regulations (Circulars, Decrees).
- [x] Provide explanation suggestions in the audit details panel.
- [x] Implement a "Draft Explanation Letter" generator producing formatted Vietnamese templates.
- [x] Support exporting generated response drafts to DOCX or PDF format.
- [x] Write integration tests verifying generated document content contains key invoice details.

## Design Notes

- **Module**: `invoices/mitigation_service.py` using python-docx/reportlab.
- **Template language**: Vietnamese formal tax letter format.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | `pytest tests/test_v14_mitigation_adviser.py` checking legal lookup logic |
| Integration | API endpoint `/api/audit/mitigation/letter` generates non-empty DOCX stream |
