# Story Backlog

This backlog lists the core epics and stories for the **Invoice Download Webapp** project, aligning the Spec-Kit tasks with the Harness v0 framework.

## Completed Epics & Stories

| Epic ID | Epic Title | Bounded Stories | Status | Proof / Test Suite |
| --- | --- | --- | --- | --- |
| **E01** | User Authentication | - US-001: Captcha SVGs fetching<br>- US-002: Credentials verification<br>- US-003: Explicit logout | **implemented** | `tests/test_auth.py` |
| **E02** | Invoice Search & Display | - US-004: Date picker inputs validation<br>- US-005: Fetch and normalize records | **implemented** | `tests/test_invoices.py`, `tests/test_parsing.py` |
| **E03** | Single Invoice Retrieval | - US-006: Stream live XML file attachment | **implemented** | `tests/test_invoices.py` |
| **E04** | Excel Export Engine | - US-007: Bulk workbook generation<br>- US-008: Header & cell formatting styling | **implemented** | `tests/test_excel.py` |
| **E05** | Cancellation Tracking | - US-009: Cancelled-only records filtering | **implemented** | `tests/test_invoices.py` |
| **E06** | Session Security | - US-010: Redirect unauthenticated page access<br>- US-011: Timeout session clearing | **implemented** | `tests/test_auth.py`, `tests/test_invoices.py` |
| **E07** | Detailed Invoice Line Items | - US-012: Extract line items from GDT XML<br>- US-013: API `/api/invoices/<id>/details`<br>- US-014: Offcanvas Drawer display | **implemented** | `tests/test_parsing.py`, `tests/test_stats.py` |
| **E08** | Analytics Dashboard | - US-021: API `/api/invoices/stats` aggregation<br>- US-022: Glassmorphism grid and distribution charts<br>- US-023: Counter count numbers animation | **implemented** | `tests/test_stats.py` |
| **E09** | Supabase UI Theme | - US-031: Premium Dark/Light theme & HSL custom properties | **implemented** | `tests/test_auth.py`, `tests/test_invoices.py` |
| **E10** | Partner Directory | - US-051: Extract unique business partners and totals | **implemented** | `tests/test_meinvoice.py` |
| **E11** | BC26 Reporting | - US-052: Compile invoice sequences for tax compliance forms | **implemented** | `tests/test_meinvoice.py` |
| **E12** | Red-Template e-Invoice | - US-053: Render red billing layout with number spelling conversions<br>- US-055: Red invoice and report print triggers | **implemented** | `tests/test_meinvoice.py` |
| **E13** | Local XML Repository | - US-061: Validate and import XML/ZIP to Local JSON DB<br>- US-064: Local store dynamic search, filtering, and sorting | **implemented** | `tests/test_meinvoice.py` |
| **E14** | Smart Auditing Panel | - US-062: 4 auditing check warnings (Duplicates, tax mismatch, high-risk MST, signature status)<br>- US-065: Integrate warning badges in Offcanvas drawer | **implemented** | `tests/test_meinvoice.py` |
| **E15** | Local Audited Excel | - US-066: Export audited local invoices to Excel sheet | **implemented** | `tests/test_meinvoice.py` |
| **E16** | Automation Optimizations | - US-071: SVG Noise filtering & character sorting CAPTCHA solver<br>- US-072: Swell memory rendering PNG for dddocr analysis<br>- US-073: Automatic login retries on CAPTCHA mismatch<br>- US-074: Conditional captcha UI inputs hide/show<br>- US-006 (Async): Async batch download background runner<br>- US-007 (Queue): Prefetching solved CAPTCHA queue worker daemon<br>- US-014: Automated Validation Runner & CI/CD Integration | **implemented** | `tests/test_captcha_solver.py`, `tests/test_captcha_queue.py`, `tests/test_async_download.py`, `scripts/validate.bat` |
| **E17** | Session Credentials & Refresh | - US-015: Symmetric encrypted credentials storage & transparent re-authentication | **implemented** | `tests/test_secure_credentials.py` |
| **E18** | MST Status Verification | - US-019: MST Status Verification & Caching | **implemented** | `tests/test_mst_service.py` |
| **E19** | Invoice Mutation & Duplicates | - US-020: Duplicate strategy selector and single-invoice edit/delete | **implemented** | `tests/test_meinvoice.py` |
| **E20** | SVG Charts & Late Signing Audit | - US-016: Zero-dependency interactive SVG charts & 5th smart audit warning for late signing | **implemented** | `tests/test_meinvoice.py` |
| **E21** | Invoice Preview Viewer Modal | - US-017: Red-layout interactive invoice preview modal with dedicated toolbar | **implemented** | `tests/test_meinvoice.py` |
| **E22** | Non-Cash Compliance Audit | - US-018: Extracted payment method & 6th compliance warning check for cash payments >= 5M VND | **implemented** | `tests/test_meinvoice.py` |
| **E23** | Scheduled Reports | - US-024: Recurring scheduled exports and email delivery | **implemented** | `tests/test_scheduler.py` |
| **E24** | Database Persistence | - US-025: Database persistence and SQLite migration | **implemented** | `tests/test_db_persistence.py` |
| **E25** | PDF Export | - US-026: PDF invoice export and printing | **implemented** | `tests/test_meinvoice.py::test_pdf_view_success` |
| **E26** | AI-Powered Compliance | - US-027: AI-Powered Compliance Auditor | **implemented** | `tests/test_ai_auditor.py` |
| **E27** | Google Gemma-4 Local AI Integration | - US-028: Local Gemma-4 Integration Plan | **implemented** | `tests/test_ai_auditor.py` |
| **E28** | AI Expense Auto-Classifier | - US-029: Automated AI Expense Classification and persistent category tagging | **implemented** | `tests/test_expense_classifier.py` |
| **E29** | XML Intelligent Data Repair | - US-030: Tự động sửa sai & Hoàn thiện Metadata bằng AI | **implemented** | `tests/test_data_repair.py` |
| **E30** | Period Billing Aggregates | - US-032: Bảng kê tổng hợp hóa đơn đầu vào theo tháng/quý theo người xuất | **implemented** | `tests/test_summary_by_seller.py` |
| **E31** | VAT Declaration & Tax Optimizer | - US-033: Dự Thảo Tờ Khai Thuế GTGT 01/GTGT & Tối Ưu Hóa Khấu Trừ Thuế Bằng AI | **implemented** | `tests/test_vat_declaration.py` |
| **E32** | Analytics Pro: Supplier Price Trends & VAT Forecast | - US-034: Phân Tích Xu Hướng Giá Nhà Cung Cấp & Dự Báo Thuế GTGT | **implemented** | `tests/test_analytics.py` |
| **E33** | Budget Monitor & Spending Alerts | - US-035: Giám Sát Ngân Sách & Cảnh Báo Chi Tiêu Theo Tháng | **implemented** | `tests/test_budget.py` |
| **E34** | Invoice Aging & Receivable Tracker | - US-036: Theo Dõi Tuổi Hóa Đơn & Kiểm Soát Công Nợ | **implemented** | `tests/test_aging.py` |
| **E35** | Cloud Sync Integration (Sprint 3.1) | - US-037: Google Drive & OneDrive Sync OAuth2 Flow<br>- US-038: AES-256 decrypted tokens storage | **implemented** | `tests/test_cloud_sync.py` |
| **E36** | ERP Connectors & Webhook Hub (Sprint 3.2) | - US-039: MISA XML/Excel and Odoo CSV Export templates<br>- US-040: Secure Webhook Dispatcher HMAC-SHA256 | **implemented** | `tests/test_erp_webhooks.py` |
| **E37** | Background AI Audit Scheduler (Sprint 4.1) | - US-041: 23:00 Background AI Worker & SMTP Email summary | **implemented** | `tests/test_tscore.py` |
| **E38** | Telegram Compliance Alert (Sprint 4.2) | - US-042: Telegram Bot API with quick response inline actions | **implemented** | `tests/test_tscore.py` |
| **E39** | Conversational NLP Assistant (Sprint 4.3) | - US-043: Text-to-SQL SELECT parser & Intent Classification | **implemented** | `tests/test_nlp_bot.py` |
| **E40** | System Performance & WAL (Sprint 5.0) | - US-044: SQLite WAL Mode enabling & Multi-tenant scalability | **implemented** | `tests/test_scaling.py` |
| **E41** | Multi-MST Profile Management (Sprint 1.1) | - US-045: TaxpayerProfile model & DB live schema migration | **implemented** | `tests/test_taxpayer_profile.py` |
| **E42** | OAuth2 Sandbox Testing Suite | - US-046: Mock OAuth2 Sandbox server & pytest automatic request interceptor | **implemented** | `tests/test_cloud_sync.py::test_sync_invoice_to_cloud_with_sandbox` |
| **E49** | Real-Time Sync | - US-053: Real-Time GDT Invoice Synchronization Agent | **implemented** | `tests/test_realtime_sync.py` |
| **E50** | Audit Mitigation | - US-054: AI Tax Optimization & Audit Mitigation Planner | **implemented** | `tests/test_v3_features.py` |
| **E51** | Cross-Border Tax | - US-055: Cross-Border E-Commerce & Multi-Currency VAT Auditor | **implemented** | `tests/test_fct_auditor.py` |

## Harness Growth Backlog

Future harness extensions and product enhancements are tracked in [docs/HARNESS_BACKLOG.md](file:///d:/LearnAnyThing/Webapp%20XML/docs/HARNESS_BACKLOG.md).

