# US-027: AI-Powered Compliance Auditor

## Status

implemented

## Lane

high-risk

## Product Contract

The application must integrate an AI Compliance Auditor utilizing a Large Language Model (local Ollama or public OpenAI/Gemini APIs) to semantically audit invoice line item descriptions for tax-deductibility (identifying personal/non-deductible items disguised as business expenses) and price inflation anomalies, persisting warnings in the database.

## High-Risk Story Folder

This is classified as a High-Risk story. The detailed story specifications are located in:
- [Execution Plan (execplan.md)](file:///d:/LearnAnyThing/Webapp%20XML/docs/stories/US-027-ai-compliance-auditor/execplan.md)
- [Overview (overview.md)](file:///d:/LearnAnyThing/Webapp%20XML/docs/stories/US-027-ai-compliance-auditor/overview.md)
- [Design (design.md)](file:///d:/LearnAnyThing/Webapp%20XML/docs/stories/US-027-ai-compliance-auditor/design.md)
- [Validation (validation.md)](file:///d:/LearnAnyThing/Webapp%20XML/docs/stories/US-027-ai-compliance-auditor/validation.md)

## Relevant Product Docs

- [02_specification.md](file:///d:/LearnAnyThing/Webapp%20XML/02_specification.md)
- [docs/ARCHITECTURE.md](file:///d:/LearnAnyThing/Webapp%20XML/docs/ARCHITECTURE.md)

## Acceptance Criteria

- [x] Implement settings support for selecting AI providers (Ollama, Gemini, OpenAI), API keys, models, and custom prompts.
- [x] Build `AIComplianceAuditor` service with specialized prompt engineering to query the selected LLM.
- [x] Run AI audits asynchronously or triggered manually, parsing structured JSON outputs.
- [x] Detect non-deductible personal expense disguise attempts (e.g., premium items, consumer retail goods).
- [x] Detect price inflation anomalies based on dynamic historical average unit price calculations.
- [x] Persist AI-generated warnings in the SQLite database and render them with distinctive UI badges in the Invoice details offcanvas and preview modal.

## Design Notes

- **AI Service**: `invoices/ai_service.py` implements the prompt construction, model selection, error handling, and mock integration support.
- **Persistence**: Relational SQLite table `ai_audit_results` tracks anomalies per invoice.
- **Frontend integration**: Interactive Offcanvas drawer and preview modal display purple badges for AI warnings.

## Validation

See details in [Validation Specifications](file:///d:/LearnAnyThing/Webapp%20XML/docs/stories/US-027-ai-compliance-auditor/validation.md) and executed test suite `tests/test_ai_auditor.py`.

## Evidence

Completed and validated with all 80 tests passing:
- `tests/test_ai_auditor.py::test_ai_settings_saving_and_loading`
- `tests/test_ai_auditor.py::test_historical_average_price_calculation`
- `tests/test_ai_auditor.py::test_audit_invoice_disabled_does_nothing`
- `tests/test_ai_auditor.py::test_audit_invoice_ollama_success`
- `tests/test_ai_auditor.py::test_audit_invoice_gemini_success`
- `tests/test_ai_auditor.py::test_api_manual_ai_audit`
- `tests/test_ai_auditor.py::test_invoice_details_returns_ai_warnings_and_status`
