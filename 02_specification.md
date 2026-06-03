# Specification: Invoice Download Webapp
**Project Code**: INVOICE-WEBAPP-PLAN-A  
**Version**: 1.0  
**Date**: 2026-05-19  
**Status**: ✅ APPROVED

---

## 📋 Executive Summary

Build a local web application that simplifies downloading invoices from Vietnam's government electronic invoice system (gdt.gov.vn). The application eliminates manual logins and repetitive file exports, allowing accounting professionals to batch-download invoices and generate Excel reports for a date range with a single click.

**Target User**: Accounting/Finance professionals at small-to-medium Vietnamese companies (like Vinatex Phú Hưng)  
**Use Case**: Monthly/quarterly invoice reconciliation and reporting  
**Problem Solved**: Current process requires manual login to gdt.gov.vn, tedious month-by-month exports, manual Excel compilation  
**Time Saved**: 30-60 min/month per user → 2-3 minutes automated

---

## 🎯 Core Features (MVP)

### Feature 1: User Authentication
**What**: Users log into their gdt.gov.vn account through the webapp  
**Why**: Eliminate need to login separately to gdt.gov.vn  
**Acceptance Criteria**:
- [ ] User enters username and password in webapp login form
- [ ] Webapp handles Captcha verification (either auto or manual)
- [ ] Session is stored locally for subsequent requests
- [ ] Login attempt with wrong credentials shows error message
- [ ] Session expires after inactivity (30 minutes)
- [ ] User can logout explicitly
- [ ] No credentials stored in browser history or code

### Feature 2: Invoice Search & Display
**What**: User enters date range, webapp shows all invoices for that period  
**Why**: Reduce manual checking of gdt.gov.vn each month  
**Acceptance Criteria**:
- [ ] User selects "From Date" and "To Date" with date picker
- [ ] Date format enforced (YYYY-MM-DD)
- [ ] Submit button triggers invoice fetch from gdt.gov.vn
- [ ] Results show in table: ID, Date, Amount, Status, Issuer
- [ ] Results show total count ("Tổng: 45 hóa đơn")
- [ ] Empty result shows "Không có hóa đơn" message
- [ ] Loading indicator shows while fetching (spinner)
- [ ] Error shows if gdt.gov.vn connection fails
- [ ] Results paginatable if >20 invoices

### Feature 3: Single Invoice Download
**What**: User can download individual invoice as XML file  
**Why**: Allows selective invoice retrieval without batch export  
**Acceptance Criteria**:
- [ ] Each invoice row has "Download XML" button
- [ ] Click triggers file download (Content-Disposition: attachment)
- [ ] File named consistently (invoice_YYYYMMDD_ID.xml)
- [ ] File saved to user's Downloads folder
- [ ] Toast notification shows "Downloaded successfully"
- [ ] Error if download fails shows "Lỗi: ..."

### Feature 4: Batch Excel Export
**What**: Export all invoices from date range to single Excel file  
**Why**: Enable bulk invoice processing for accounting/reconciliation  
**Acceptance Criteria**:
- [ ] "Export to Excel" button visible in header
- [ ] Excel file contains columns: ID, Date, Amount, Status, Issuer, Details
- [ ] Excel file formatted professionally:
  - [ ] Headers bold and blue background
  - [ ] Column widths auto-adjusted to content
  - [ ] Numbers formatted as currency (₫)
  - [ ] Dates formatted as DD/MM/YYYY
  - [ ] Row count matches invoice count
- [ ] File named: invoices_YYYYMMDD_YYYYMMDD.xlsx
- [ ] File downloads immediately, no prompt
- [ ] Works with 0 results (empty Excel)
- [ ] Works with 1000+ invoices (performance <5s)

### Feature 5: Cancelled Invoices List
**What**: Show invoices that were cancelled/revoked  
**Why**: Separate cancelled invoices for accounting adjustments  
**Acceptance Criteria**:
- [ ] Option to toggle "Show Cancelled Only" filter
- [ ] Display cancelled invoices in different color (orange background)
- [ ] Can export cancelled invoices to separate Excel
- [ ] Shows cancellation date and reason (if available from API)

### Feature 6: Session Management
**What**: Keep user logged in across page refreshes, handle timeouts gracefully  
**Why**: Prevent re-login on every page refresh (usability)  
**Acceptance Criteria**:
- [ ] User stays logged in after page refresh (F5)
- [ ] Browser tab close = logout (session cleared)
- [ ] Inactivity 30 min = auto logout
- [ ] User notified 1 min before timeout ("Phiên hết hạn trong 1 phút")
- [ ] Logout button clears session completely
- [ ] Cannot access invoice page without login (redirect to login)

---

## 🎬 User Stories & Scenarios

### Story 1: Monthly Invoice Reconciliation (Happy Path)
```
As: Accounting Manager at Vinatex Phú Hưng
I want: Download all invoices from May 1-31, 2026
So that: I can reconcile with general ledger and run reports

SCENARIO:
1. Open http://localhost:5000
2. See login form
3. Enter username: user123, password: ****
4. Solve Captcha (system shows image, I enter code)
5. Click "Đăng nhập"
6. See invoice search page
7. Select date: 2026-05-01 to 2026-05-31
8. Click "Tìm kiếm"
9. See table with 45 invoices
10. Click "Xuất Excel"
11. File invoices_20260501_20260531.xlsx downloads
12. Open in Excel, see proper formatting
13. Copy data to reporting system
14. Done - saved 45 min vs manual process
```

### Story 2: Find Specific Invoice
```
As: Accountant
I want: Find invoice #INV-2026-001234 that customer disputed
So that: I can verify invoice details match customer complaint

SCENARIO:
1. Login as above
2. Enter narrow date range (just that day)
3. Click "Tìm kiếm"
4. Scan results table for invoice ID
5. Click "Download XML" for that invoice
6. Send XML to customer for verification
```

### Story 3: Check for Cancelled Invoices
```
As: Finance Officer
I want: See which invoices were cancelled this month
So that: I can track voided transactions in accounting system

SCENARIO:
1. Login
2. Enter date range for month
3. Click "Show Cancelled Only" toggle
4. See cancelled invoices highlighted in orange
5. Export cancelled invoices to separate Excel for audit trail
```

### Story 4: Session Timeout Recovery
```
As: User
I want: Receive warning before session expires
So that: I don't lose my work if I step away

SCENARIO:
1. Login and use invoice search
2. Walk away for 29 minutes
3. Return and click button
4. Toast shows "Phiên hết hạn, vui lòng đăng nhập lại"
5. Redirected to login page
6. Login again, previous search data retained
```

---

## 🔄 Non-Functional Requirements

### Performance
- Page load time: <3 seconds
- Invoice search: <10 seconds (gdt.gov.vn latency acceptable)
- Excel export: <5 seconds for 1000 invoices
- Webapp footprint: <100MB on disk

### Security
- HTTPS-ready (localhost uses HTTP for dev, production uses HTTPS)
- No credentials stored in cookies (session tokens only)
- CSRF protection on forms (Flask-WTF if using forms)
- Input validation on all user inputs
- SQL injection prevention (if using database later)
- Error messages don't expose system details

### Usability
- Mobile-friendly (responsive design, not mobile app)
- Font size readable (14px+ for text)
- Buttons large enough to click (44px+ minimum)
- Color contrast WCAG AA compliant
- Vietnamese language throughout (no English except logo)
- Dark mode optional (nice-to-have, not MVP)

### Reliability
- Graceful error handling (never white screen of death)
- Automatic retry on network timeout
- Session recovery if gdt.gov.vn temporarily down
- Logging of all errors for debugging
- 99% uptime expected (local app, not cloud)

### Maintainability
- Code documented (docstrings, comments)
- API documented (Postman-ready)
- Architecture simple (no microservices)
- Deployable on any machine with Python 3.10+
- Upgrade path for future features

---

## 📊 Data Model Overview

### Entities
1. **Invoice**
   - Fields: id, date, amount, status, issuer, description
   - Source: gdt.gov.vn API
   - Storage: In-memory (not persisted)

2. **CancelledInvoice**
   - Fields: id, date, amount, cancellation_date, cancellation_reason
   - Source: gdt.gov.vn API
   - Storage: In-memory

3. **Session**
   - Fields: user_id, token, expires_at, login_time
   - Storage: Flask session (browser cookie)
   - Lifetime: 30 minutes

---

## 🔗 References & Research

- **gdt.gov.vn**: Vietnam electronic invoice system (https://hoadondientu.gdt.gov.vn/)
- **HTTP**: Request/response protocol for API calls
- **XML/JSON**: Response formats from gdt.gov.vn
- **Excel Format**: XLSX standard for professional formatting
- **Captcha**: Browser automation handling or manual entry

---

## ❌ Out of Scope (Not MVP)

- ❌ User registration (login only for existing gdt.gov.vn users)
- ❌ Multi-user accounts (single user per browser session)
- ❌ Cloud backup (local storage only)
- ❌ Mobile app (responsive web only)
- ❌ Recurring automation (manual trigger only)
- ❌ Invoice PDF export (XML + Excel only)
- ❌ Database persistence (in-memory only)
- ❌ Authentication from other providers
- ❌ Batch upload to accounting systems
- ❌ Invoice modification/creation

---

## 📋 Acceptance Checklist

**Specification is DONE when**:
- [ ] All 6 core features defined with acceptance criteria
- [ ] All 4 user stories described with scenarios
- [ ] All non-functional requirements (performance, security, UX) specified
- [ ] Data model identified
- [ ] References documented
- [ ] Out of scope clearly marked
- [ ] No ambiguities remain
- [ ] Developer can build without asking clarification

**Sign-Off**:
- [ ] Product Owner (user) approves spec
- [ ] Technical Lead reviews for feasibility
- [ ] QA confirms acceptance criteria testable

---

## 🔄 Clarifications (From /speckit.clarify)

### Q1: What if gdt.gov.vn is down?
**A**: Show error "Không thể kết nối đến gdt.gov.vn. Vui lòng thử lại sau." with retry button. Don't crash.

### Q2: Can user search same invoice multiple times?
**A**: Yes, no limit on searches. Session might expire but that's a feature (inactivity protection).

### Q3: What about invoices issued in future dates?
**A**: gdt.gov.vn won't have them. System validates date range (from ≤ to, both in past). If user enters future date, show "Ngày không hợp lệ" error.

### Q4: Can user download invoice while another download in progress?
**A**: Yes, but show progress indicator for each. No weird async conflicts expected at small scale.

### Q5: Excel export — should data be summary only or line-by-line?
**A**: Summary only (1 row = 1 invoice). Line-item detail can be Phase 2 enhancement.

---

## 📈 Future Enhancements (Post-MVP)

1. **Phase 2**: Invoice details (line items, tax breakdown)
2. **Phase 3**: Recurring scheduled exports (email daily/weekly)
3. **Phase 4**: Database persistence (history of searches)
4. **Phase 5**: Multi-user support with user accounts
5. **Phase 6**: PDF export and digital signing
6. **Phase 7**: Integration with accounting software (QuickBooks, SAP)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-05-19 | Initial specification |

---

**Approved By**: Huỳnh Anh Thuận  
**Date Approved**: 2026-05-19  
**Next Step**: `/speckit.clarify` or proceed to `/speckit.plan`
