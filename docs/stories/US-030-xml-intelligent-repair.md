# US-030: Tự Động Sửa Sai & Hoàn Thiện Metadata Bằng AI (XML Intelligent Data Repair)

## Status

completed

## Lane

normal

## Product Contract

The application will leverage offline local LLM models (e.g., Google Gemma-4 via Ollama, or fallback APIs) to automatically repair incomplete, abbreviated, or faulty invoice metadata. This includes:
1. **Chuẩn hóa tên công ty (Standardize Partner Names)**: Expand abbreviations like "CP", "TNHH", "DV", "TM" into complete Vietnamese company names (e.g., "Công ty Cổ phần", "Công ty Trách nhiệm Hữu hạn").
2. **Chuẩn hóa địa chỉ (Standardize Addresses)**: Standardize abbreviated addresses (e.g., "HBT, HN" -> "Hai Bà Trưng, Hà Nội").
3. **Chuyển đổi số thành chữ (Text-to-Money Speller)**: Automatically spell out total invoice amount to Vietnamese text if missing or inconsistent (e.g., "1,500,000" -> "Một triệu năm trăm nghìn đồng chẵn").
4. **Khôi phục thông tin thiếu (Deduce Missing Info)**: Automatically deduce or recommend missing buyer details or tax rates based on historical records or context.

Users can view before/after suggestions and click "Chấp Nhận Gợi Ý AI" (Apply AI Suggestions) to update database fields dynamically.

## Relevant Product Docs

- `docs/ARCHITECTURE.md`
- `invoices/models.py`
- `invoices/ai_service.py`
- `invoices/routes.py`
- `docs/stories/backlog.md`
- `PROGRESS_TRACKER_INVOICE_WEBAPP.md`

## Acceptance Criteria

1. **AI Data Repair Engine**:
   - Implement the `AIDataRepairer` class or method inside `invoices/ai_service.py` that formats e-invoice metadata (buyer name, seller name, buyer address, seller address, payment method, spelling text) into a targeted prompt.
   - Instruct the LLM to output a JSON-structured payload containing standardizations for abbreviated or incomplete strings, plus spelled-out money text.
   - Establish robust Prompt Engineering with few-shot examples for Vietnamese addresses and company name abbreviations.
   - If AI is disabled or fails, provide a deterministic Python-based spelling fallback + standard abbreviations mapper (e.g., mapping "TNHH" -> "Trách nhiệm Hữu hạn").

2. **API Endpoint `/api/ai/repair-metadata` (POST)**:
   - Request body takes `{"invoice_id": "seller_mst-symbol-number"}`.
   - Run AI or fallback standardizer to generate suggested updates.
   - Return structured JSON showing:
     - `invoice_id`
     - `before`: original dictionary of names/addresses/spelling.
     - `after`: suggested standardized dictionary of names/addresses/spelling.
     - `differences`: array of fields that would be modified.

3. **API Endpoint `/api/ai/apply-repair` (POST)**:
   - Request body takes `{"invoice_id": "seller_mst-symbol-number", "fields": [...]}` where `fields` lists which suggestions to apply.
   - Persist these standardized values to the database.
   - Secure both API endpoints using Flask login validation.

4. **Frontend Integration inside Drawer**:
   - In the Invoice Details Offcanvas drawer, add a clean glassmorphic section called "Tối ưu hóa dữ liệu AI" (AI Metadata Optimization).
   - Display a "Đề xuất sửa đổi" (Review Suggestions) button that triggers a dialog displaying before/after diffs side-by-side with HSL visual differences.
   - Include checkboxes allowing the user to select which optimizations to apply and an "Áp dụng" (Apply) button that saves the changes to SQLite via AJAX.

## Design Notes

### 1. AI Prompt Format
The system prompt should enforce JSON output structure:
```json
{
  "seller_name": "Công ty Cổ phần...",
  "buyer_name": "Công ty Trách nhiệm Hữu hạn...",
  "buyer_address": "...",
  "amount_in_words": "..."
}
```

### 2. Standard Regex Fallbacks
```python
def spell_money_vietnamese(amount: float) -> str:
    # Deterministic Vietnamese money spelling implementation
    ...
```

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Write `tests/test_data_repair.py` verifying Vietnamese money spelling converter and abbreviation expansion fallbacks. |
| Integration | Call `/api/ai/repair-metadata` and `/api/ai/apply-repair` routes with a logged-in client to assert DB state transitions. |

## Harness Delta

- Update `docs/stories/backlog.md` and `docs/TEST_MATRIX.md` to map US-030.
- Update `PROGRESS_TRACKER_INVOICE_WEBAPP.md` with new checkmarks.

## Evidence

Completed and successfully validated the XML Intelligent Data Repair story with a 100% passing test suite `tests/test_data_repair.py` (6/6 tests passing).

```powershell
======================== 6 passed, 5 warnings in 5.24s ========================
Exit code: 0
```

### Test Coverage Results
- `test_spell_money_vietnamese`: Validated zero value spelling (`"Không đồng"`), tens (`"Một trăm mười lăm đồng chẵn"`), ones (`"Một trăm hai mươi mốt đồng chẵn"`), and scale words (`"Mười ba triệu năm trăm ba mươi nghìn đồng chẵn"`, `"Một tỷ không trăm linh hai triệu không trăm linh ba nghìn không trăm linh năm đồng chẵn"`).
- `test_expand_abbreviations`: Validated regex mappings expanding abbreviations like `TNHH`, `CP`, `MTV`, `TM`, `DV`, `HN`, `HCM` into complete capitalized corporate names and address strings.
- `test_ai_data_repairer_ollama_success`: Verified AIDataRepairer connects successfully, formats prompts, handles response parsing and updates `amount_in_words`.
- `test_ai_data_repairer_fallback_on_error`: Checked graceful failover to deterministic regular expression rules when the LLM service is unavailable.
- `test_route_repair_metadata_unauthorized`: Ensured authorization guard blocks unauthorized route calls.
- `test_route_repair_metadata_and_apply_flow`: Verified end-to-end SQLite persistence flow using AJAX data-binding payload through the Flask app context.
