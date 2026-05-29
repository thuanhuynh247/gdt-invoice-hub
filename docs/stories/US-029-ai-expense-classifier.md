# US-029: Công Cụ Tự Động Phân Loại Chi Phí Bằng AI (Intelligent Expense Auto-Classifier)

## Status

completed

## Lane

normal

## Product Contract

The application will leverage offline local LLM models (e.g., Google Gemma-4 via Ollama, or fallback APIs) to automatically categorize individual invoice line items into standardized accounting expense classes. This helps accountant users group free-form business purchase descriptions (e.g., "Giấy in Double A A4 70gsm", "Dell Latitude 7420 Core i7") into structured categories for immediate tax deductions, profit-and-loss reports, and internal spend audits.

The 8 standard expense categories defined are:
1. **Văn phòng phẩm & Thiết bị văn phòng (Office Supplies & Stationery)**
2. **Thiết bị công nghệ & Phần mềm (IT Equipment & Software)**
3. **Chi phí tiếp khách & Hội nghị (Entertainment & Meetings)**
4. **Quảng cáo, Tiếp thị & Sự kiện (Marketing, Advertising & Events)**
5. **Vận chuyển, Giao hàng & Logistics (Shipping, Logistics & Postage)**
6. **Chi phí dịch vụ công cộng & Tiện ích (Utilities, Electricity & Water)**
7. **Sửa chữa, Bảo trì & Nâng cấp (Repairs & Maintenance)**
8. **Chi phí khác & Vật tư dùng chung (Other Miscellaneous Expenses)**

## Relevant Product Docs

- `docs/ARCHITECTURE.md`
- `invoices/models.py`
- `invoices/ai_service.py`
- `invoices/routes.py`
- `PROGRESS_TRACKER_INVOICE_WEBAPP.md`
- `docs/stories/backlog.md`

## Acceptance Criteria

1. **Persistent Category Storage (Database Schema Update)**:
   - Upgrade the `LineItem` table in SQLite with an `expense_category` column (String, nullable).
   - Gracefully perform automatic migration on startup in `app.py` by running `ALTER TABLE line_item ADD COLUMN expense_category VARCHAR(100) NULL` if the column doesn't exist.
2. **AI Expense Auto-Classifier Engine**:
   - Implement the `AIExpenseClassifier` service inside `invoices/ai_service.py` that accepts a list of line items, packages them into an optimized prompt, and issues a structured JSON request to Ollama / Gemini.
   - Establish robust Prompt Engineering with few-shot examples to map arbitrary Vietnamese descriptions to exactly one of the 8 canonical categories.
   - If the AI is disabled or fails, fallback to simple exact/substring matching keywords (e.g., "giấy", "bút" -> Category 1; "máy tính", "phần mềm" -> Category 2) for maximum robustness.
3. **API Endpoint `/api/ai/classify-items`**:
   - Define a `POST` route to categorize a given list of line item descriptions or to automatically scan and categorize all uncategorized line items in the SQLite database.
   - Ensure secure sessions: the API must be protected by the login validation wrapper.
   - Return structured JSON with categorized mappings.
4. **Intuitive Frontend Integrations & Controls**:
   - Add a "Tự Động Phân Loại Bằng AI" button in the Invoice Details drawer/modal.
   - Display visual tags/badges with tailored HSL color indicators next to each line item inside the invoice detail drawer showing its classified category.
   - Support manually editing the category via a dropdown selector to override AI suggestions if necessary.

## Design Notes

### 1. Database Table Upgrade (`invoices/models.py`)

Add the column to `LineItem`:
```python
class LineItem(db.Model):
    # ...
    expense_category = db.Column(db.String(100), nullable=True)
```

Include it in `to_dict()`:
```python
"expense_category": self.expense_category or "Chưa phân loại"
```

### 2. Live Startup Migration (`app.py`)

```python
res_item = db.session.execute(db.text("PRAGMA table_info(line_item);")).fetchall()
columns_item = [r[1] for r in res_item]
if "expense_category" not in columns_item:
    db.session.execute(db.text("ALTER TABLE line_item ADD COLUMN expense_category VARCHAR(100) NULL;"))
    db.session.commit()
```

### 3. API Payload (`/api/ai/classify-items`)

*Request payload*:
```json
{
  "invoice_id": "seller_mst-symbol-number"
}
```

*Response payload*:
```json
{
  "success": true,
  "classified_items": [
    {
      "item_id": 142,
      "item_name": "Mực máy in HP LaserJet",
      "category": "Văn phòng phẩm & Thiết bị văn phòng"
    }
  ]
}
```

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | Write `tests/test_expense_classifier.py` verifying system prompt composition, fallback keyword match functions, and database schema updates. |
| Integration | Call the `/api/ai/classify-items` route with active sessions and assert correct JSON responses and database changes. |

## Harness Delta

- Update `docs/stories/backlog.md` and `docs/TEST_MATRIX.md` to map US-029.
- Log task progress under `PROGRESS_TRACKER_INVOICE_WEBAPP.md`.

## Evidence

- The pytest suite has been implemented successfully under [test_expense_classifier.py](file:///d:/LearnAnyThing/Webapp%20XML/tests/test_expense_classifier.py) and passes with 100% success rate (5/5 tests passing).
- Run evidence command:
  ```powershell
  venv/Scripts/python.exe -m pytest tests/test_expense_classifier.py
  ```
  Output:
  `5 passed, 9 warnings in 5.18s`
- Visual custom HSL category badges and manual drop-down edit modal implemented beautifully inside the offcanvas drawer in `static/js/main.js` and `templates/invoices.html` according to premium Supabase design aesthetics.
