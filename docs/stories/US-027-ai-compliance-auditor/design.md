# Design

## Domain Model
- **AIComplianceAuditor**: Core service that maps an Invoice and its LineItems into a structured prompt, submits it to the LLM, and parses the structured JSON warning response.
- **Anomalies**:
  - `personal_purchase_risk`: Boolean flag + explanation.
  - `price_inflation_risk`: Boolean flag + explanation.

## Application Flow
1. **Invoice Imported**: The XML is parsed and saved to SQLite.
2. **AI Audit Trigger**:
   - If AI audit is enabled in Settings, call `AIComplianceAuditor.audit_invoice(invoice)`.
   - LLM processes item descriptions and returns JSON:
     ```json
     {
       "anomalies": [
         {"type": "personal_purchase", "description": "Flagged item 'iPhone 15 Pro Max' - High risk of personal use disguise."},
         {"type": "price_inflation", "description": "Unit price of 'Office chair' (15,000,000 VND) is 300% higher than historical average."}
       ]
     }
     ```
3. **Save Results**: Insert anomalies into the database.

## Interface Contract
- **POST `/api/invoices/local/<invoice_id>/ai-audit`**: Trigger AI audit manually.
  - Response:
    ```json
    {
      "status": "success",
      "ai_warnings": [
        "Cảnh báo AI: Mặt hàng 'Son môi Chanel' có nguy cơ cao là chi phí cá nhân không được khấu trừ thuế."
      ]
    }
    ```
- **GET `/api/settings`**: Expose LLM configurations.

## Data Model
- Add table `ai_audit_results`:
  - `id` (INTEGER, Primary Key)
  - `invoice_id` (VARCHAR, Foreign Key to `invoices.id`)
  - `warning_type` (VARCHAR) - e.g., 'personal_purchase', 'price_inflation'
  - `message` (TEXT)
  - `created_at` (TIMESTAMP)

## UI / Platform Impact
- **Invoices Dashboard**:
  - Add an AI Audit status column / purple warning badge in the table list.
- **Offcanvas Drawer**:
  - Render an "AI Auditing Results" section with a distinctive robot icon and deep purple alert box.
- **Settings Page**:
  - Add "AI Auditor Settings" sub-section with toggle, API Keys, and Ollama endpoint inputs.

## Observability
- Log LLM execution latency, prompt token count, and parse errors.
- Audit logs: record when settings changes occur.

## Alternatives Considered
1. **Single column string array on `Invoice`**: Storing warnings as JSON string array directly in `Invoice.warnings`.
   - *Verdict*: Kept for simple display, but a separate table `ai_audit_results` is cleaner for structured database filtering.
