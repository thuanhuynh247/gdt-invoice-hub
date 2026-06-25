# Implementation Plan: Invoice Download Webapp
**Project Code**: INVOICE-WEBAPP-PLAN-A  
**Version**: 1.0  
**Date**: 2026-05-19  
**Status**: ✅ READY FOR EXECUTION

---

## 🏗️ Architecture Overview

### Technology Stack
```
Frontend:        HTML5 + Vanilla JavaScript + Bootstrap 5 CSS
Backend:         Python 3.10+ + Flask 2.3+
Data Processing: openpyxl (Excel), lxml (XML parsing)
Automation:      Selenium 4+ (browser automation for Captcha)
Deployment:      Local (localhost:5000)
Database:        None (in-memory sessions only)
External APIs:   gdt.gov.vn (Vietnamese government invoice system)
```

### Why These Choices?
1. **Flask**: Lightweight, minimal learning curve, mature, perfect for beginners
2. **Vanilla JS**: No framework bloat; teaches core web concepts
3. **Bootstrap 5**: Professional UI, responsive, minimal CSS writing
4. **openpyxl**: Only production-grade Excel library for Python
5. **Selenium**: Only reliable way to handle dynamic Captcha on gdt.gov.vn
6. **No database**: Simplifies deployment, data is fetch-on-demand

---

## 📂 Project Folder Structure

```
invoice-webapp/
├── .env.example              # Credentials template
├── .gitignore                # Git config
├── app.py                    # Main Flask app
├── config.py                 # Configuration (debug, secret key)
├── requirements.txt          # Python dependencies
├── README.md                 # User documentation
├── API_SPEC.md              # API endpoint documentation
├── 
├── auth/                     # Authentication module
│   ├── __init__.py
│   ├── login.py             # Login route, session management
│   └── captcha.py           # Captcha handling (Selenium)
│
├── invoices/                # Invoice module
│   ├── __init__.py
│   ├── routes.py            # Invoice search, download routes
│   ├── service.py           # gdt.gov.vn API calls
│   └── parser.py            # XML/JSON parsing
│
├── export/                  # Excel export module
│   ├── __init__.py
│   ├── excel.py             # Excel generation (openpyxl)
│   └── formatter.py         # Cell styling, formatting
│
├── templates/               # HTML templates
│   ├── base.html            # Base layout
│   ├── login.html           # Login page
│   └── invoices.html        # Invoice list page
│
├── static/                  # CSS, JS, images
│   ├── css/
│   │   └── style.css        # Custom styles
│   ├── js/
│   │   └── main.js          # JavaScript for frontend
│   └── images/
│       └── logo.png         # Company logo
│
├── tests/                   # Unit and integration tests
│   ├── __init__.py
│   ├── test_auth.py         # Auth tests
│   ├── test_invoices.py     # Invoice tests
│   ├── test_excel.py        # Excel generation tests
│   └── test_parsing.py      # Parser tests
│
└── docs/                    # Documentation
    ├── API_SPEC.md
    ├── ARCHITECTURE.md
    └── TROUBLESHOOTING.md
```

---

## 🔄 Request Flow Diagram

```
User Browser
    │
    ├─ GET /
    │   └─> templates/login.html
    │
    ├─ POST /api/auth/login
    │   ├─> auth/login.py
    │   ├─> auth/captcha.py (Selenium to solve/verify)
    │   ├─> Call gdt.gov.vn POST /login
    │   ├─> Store session cookie
    │   └─> Return {status: "success"}
    │
    ├─ GET /invoices
    │   └─> templates/invoices.html
    │
    ├─ GET /api/invoices?from=2026-05-01&to=2026-05-31
    │   ├─> invoices/routes.py
    │   ├─> invoices/service.py
    │   ├─> Call gdt.gov.vn GET /api/invoices
    │   ├─> invoices/parser.py (parse XML/JSON)
    │   └─> Return [{id, date, amount, ...}]
    │
    ├─ GET /api/export-excel
    │   ├─> invoices/routes.py
    │   ├─> export/excel.py
    │   ├─> export/formatter.py
    │   └─> Return Excel file (binary)
    │
    └─ GET /api/auth/logout
        ├─> Clear session cookie
        └─> Redirect to login
```

---

## 🗂️ Module Responsibilities

### `auth/login.py` - Authentication
```python
- POST /api/auth/login(username, password, captcha_answer)
  - Validate inputs (not empty)
  - Call gdt.gov.vn POST /login with credentials
  - Capture session cookies
  - Store in flask.session (encrypted browser cookie)
  - Return {status: "success", expires_at: timestamp}
  
- GET /api/session-status()
  - Return {logged_in: bool, expires_in: seconds}
  
- POST /api/auth/logout()
  - Clear flask.session
  - Return {status: "logged out"}
```

### `auth/captcha.py` - Captcha Handling
```python
- get_captcha_image() -> bytes
  - Fetch Captcha image from gdt.gov.vn
  - Return as base64 for frontend to display
  
- verify_captcha(user_answer) -> bool
  - Option 1: Use Selenium to automate Captcha solving
  - Option 2: Accept manual user entry (simpler)
  - Validate against session
```

### `invoices/service.py` - gdt.gov.vn Integration
```python
- fetch_invoices(date_from, date_to, session) -> list[dict]
  - Call gdt.gov.vn GET /api/invoices with session cookie
  - Handle authentication errors (401 -> logout)
  - Return parsed invoice list
  
- fetch_invoice_detail(invoice_id, session) -> dict
  - Get single invoice details
  
- download_invoice_xml(invoice_id, session) -> bytes
  - Fetch XML file from gdt.gov.vn
  - Return binary XML content
```

### `invoices/parser.py` - Data Parsing
```python
- parse_invoice_list_json(response) -> list[dict]
  - Parse gdt.gov.vn JSON response
  - Extract: id, date, amount, status, issuer
  - Handle missing fields (use defaults)
  
- parse_invoice_list_xml(response) -> list[dict]
  - Parse if gdt.gov.vn returns XML
  - Same field extraction
  
- validate_date_range(from_date, to_date) -> bool
  - Both dates valid format (YYYY-MM-DD)
  - from_date <= to_date
  - Both in past (no future invoices)
```

### `export/excel.py` - Excel Generation
```python
- generate_excel(invoices: list[dict]) -> bytes
  - Create workbook (openpyxl)
  - Add header row: ID, Date, Amount, Status, Issuer
  - Add data rows (1 invoice per row)
  - Apply formatting (headers bold+blue, auto-width)
  - Format numbers as currency (₫)
  - Format dates as DD/MM/YYYY
  - Return as binary content
  
- save_excel_file(invoices: list[dict], filename: str) -> str
  - Generate + save to disk
  - Return file path
```

### `export/formatter.py` - Cell Styling
```python
- format_header_row(ws) -> None
  - Bold font, blue background, white text
  
- format_currency_column(ws, column) -> None
  - Format as "₫ 1,234,567"
  
- format_date_column(ws, column) -> None
  - Format as "DD/MM/YYYY"
  
- auto_adjust_column_widths(ws) -> None
  - Width = max(content length, header length)
```

---

## 🌐 API Endpoints (Backend)

### Authentication Endpoints
```
POST /api/auth/login
├─ Input: {username, password, captcha_answer}
├─ Output: {status, message, expires_at}
├─ Errors: 400 (invalid input), 401 (bad credentials), 500 (gdt.gov.vn down)
└─ Side effects: Flask session cookie set

GET /api/session-status
├─ Input: None (session from cookie)
├─ Output: {logged_in: bool, expires_in: seconds}
└─ Errors: None (always returns something)

POST /api/auth/logout
├─ Input: None
├─ Output: {status: "logged out"}
└─ Side effects: Flask session cleared
```

### Invoice Endpoints
```
GET /api/invoices?from=2026-05-01&to=2026-05-31
├─ Input: Query params (from_date, to_date)
├─ Output: {total_count, invoices: [{id, date, amount, status, issuer}]}
├─ Errors: 400 (invalid date), 401 (not logged in), 504 (gdt.gov.vn timeout)
└─ Performance: Expected <10s (gdt.gov.vn latency)

GET /api/invoices/{id}/download?format=xml
├─ Input: invoice_id
├─ Output: XML file (binary)
├─ Errors: 404 (not found), 401 (not logged in)
└─ Content-Disposition: attachment

GET /api/export-excel?from=2026-05-01&to=2026-05-31
├─ Input: Query params (from_date, to_date)
├─ Output: Excel file (binary)
├─ Errors: 400 (invalid date), 401 (not logged in)
└─ Content-Disposition: attachment
```

---

## 🔐 Security Architecture

### Session Management
```python
# Flask configuration
app.config['SESSION_COOKIE_HTTPONLY'] = True  # No JS access
app.config['SESSION_COOKIE_SECURE'] = True    # HTTPS only (prod)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
app.config['SESSION_REFRESH_EACH_REQUEST'] = True
```

### Credential Handling
```
✗ NEVER store in code
✗ NEVER log credentials
✗ NEVER show in error messages

✓ Always use .env file
✓ Always use flask.session (encrypted)
✓ Always validate inputs before API call
```

### Error Messages
```
✗ BAD: "Invalid username 'user123' for gdt.gov.vn"
✓ GOOD: "Thông tin đăng nhập không đúng"

✗ BAD: "Connection timeout to https://gdt.gov.vn at 192.168.1.1"
✓ GOOD: "Không thể kết nối. Vui lòng thử lại sau 5 phút"
```

---

## 📊 Data Flow (Specific to Core Workflows)

### Workflow 1: Login
```
User enters username/password
    ↓
Frontend validates (not empty)
    ↓
POST /api/auth/login
    ↓
Backend calls gdt.gov.vn with credentials
    ↓
gdt.gov.vn returns session cookie
    ↓
Backend stores in flask.session
    ↓
Return {status: "success"}
    ↓
Frontend redirects to /invoices page
    ↓
User can now search
```

### Workflow 2: Search Invoices
```
User selects date range (2026-05-01 to 2026-05-31)
    ↓
Frontend validates (from ≤ to, both valid format)
    ↓
GET /api/invoices?from=2026-05-01&to=2026-05-31
    ↓
Backend retrieves session cookie
    ↓
Call gdt.gov.vn API with session
    ↓
Parse response (XML or JSON)
    ↓
Return list of invoices [{id, date, amount, ...}]
    ↓
Frontend renders table
    ↓
User sees results
```

### Workflow 3: Export to Excel
```
User clicks "Xuất Excel" button
    ↓
GET /api/export-excel?from=2026-05-01&to=2026-05-31
    ↓
Backend fetches invoices (same as workflow 2)
    ↓
Create Excel workbook (openpyxl)
    ↓
Add headers + data rows
    ↓
Apply formatting (bold, colors, currency)
    ↓
Generate binary file
    ↓
Return with Content-Disposition: attachment
    ↓
Browser downloads file
    ↓
User opens in Excel
```

---

## 🧪 Testing Strategy

### Unit Tests (per module)
```python
test_auth.py:
  - test_login_success()
  - test_login_invalid_credentials()
  - test_login_captcha_mismatch()
  - test_session_expired()
  - test_logout()

test_invoices.py:
  - test_fetch_invoices_success()
  - test_fetch_invoices_invalid_date()
  - test_fetch_invoices_empty_result()
  - test_download_invoice_success()
  - test_download_invoice_not_found()

test_excel.py:
  - test_generate_excel_valid()
  - test_generate_excel_formatting()
  - test_generate_excel_currency_format()
  - test_generate_excel_large_dataset()

test_parsing.py:
  - test_parse_json_response()
  - test_parse_malformed_json()
  - test_parse_xml_response()
```

### Integration Tests
```python
- test_full_login_to_export_flow()
- test_session_timeout_redirect()
- test_concurrent_requests()
```

### Manual Testing Checklist
```
[ ] Login with valid credentials
[ ] Login with invalid credentials
[ ] Search date range with 0 results
[ ] Search date range with 1000+ results
[ ] Download single invoice
[ ] Export to Excel
[ ] Check Excel formatting (colors, fonts, numbers)
[ ] Session timeout after 30 min
[ ] Logout button works
[ ] Navigate back button doesn't break state
```

---

## 🚀 Deployment & Running

### Local Development
```bash
# 1. Clone/download project
cd invoice-webapp

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Mac/Linux
# or
venv\Scripts\activate     # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file
cp .env.example .env
# Edit .env with YOUR gdt.gov.vn credentials

# 5. Run Flask
python app.py

# 6. Open browser
http://localhost:5000
```

### Production Deployment (Future)
```
- Use gunicorn (production WSGI server)
- Use nginx (reverse proxy)
- Use systemd service (auto-restart)
- Use HTTPS (Let's Encrypt SSL cert)
- Deploy on VPS or Heroku
```

---

## ⚠️ Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| gdt.gov.vn API changes | Medium | High | Monitor API, keep docs updated, have fallback |
| Captcha solving fails | Low | High | Allow manual Captcha entry as backup |
| Session timeout bugs | Low | Medium | Extensive session testing, clear UX on timeout |
| Excel generation slow | Low | Medium | Cache generated files, add progress indicator |
| Credential leak | Very Low | Critical | .env in .gitignore, code review, no logging |

---

## 📅 Phase Sequencing

| Phase | Duration | Dependency | Output |
|-------|----------|-----------|--------|
| 1: Setup | 1 day | None | Runnable Flask skeleton |
| 2: Learning | 3-5 days | Phase 1 | Python/Flask knowledge |
| 3: API Analysis | 5-7 days | Phase 2 | API_SPEC.md documented |
| 4: Backend | 7-10 days | Phase 3 | All routes working, tests passing |
| 5: Frontend | 3-5 days | Phase 4 | HTML/JS, fully responsive |
| 6: Testing | 3-5 days | Phase 5 | 70%+ coverage, all tests passing |
| 7: Documentation | 2 days | Phase 6 | README, API docs, troubleshooting |

**Critical Path**: Phase 3 (API analysis) blocks Phase 4 (backend)

---

## 🎯 Success Criteria

**This plan is GOOD when**:
- ✅ Architecture is clear, no tech surprises
- ✅ All routes mapped to Flask endpoints
- ✅ API contract defined (request/response)
- ✅ Security approach documented
- ✅ Testing strategy covers happy + error paths
- ✅ Deployment path (even if just local) documented
- ✅ Developer can start coding without questions

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-05-19 | Initial plan |

---

**Approved By**: Huỳnh Anh Thuận  
**Date Approved**: 2026-05-19  
**Next Step**: `/speckit.tasks` to break down into actionable tasks
