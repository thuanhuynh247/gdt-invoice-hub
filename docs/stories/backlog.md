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
| **E51** | Security Audit Ledger | - US-140: Immutable Security Audit Logger<br>- US-141: Audit Trail Viewer UI & Export | **implemented** | `tests/test_v11_audit_log.py`, `tests/test_v11_audit_trail_viewer.py` |
| **E52** | Sync Resiliency | - US-142: Resilient Sync Queue Manager<br>- US-143: CAPTCHA Solver Analytics Dashboard | **implemented** | `tests/test_v11_sync_resiliency.py`, `tests/test_captcha_analytics.py` |
| **E53** | Risk Analytics & PDF | - US-144: Tax Risk Scoreboard Dashboard<br>- US-145: Signed Compliance Report Exporter | **implemented** | `tests/test_v11_signed_report.py` |
| **E54** | Cash Flow Forecasting | - US-150: Smart Cashflow Predictor<br>- US-151: Interactive Scenario Simulator | **implemented** | `tests/test_v12_cashflow.py`, `tests/test_cashflow_oracle.py` |
| **E55** | AI CIT Deduction Auditor | - US-152: CIT Deduction Auditor Engine<br>- US-153: CIT Deduction Advisory Panel | **implemented** | `tests/test_cit.py` |
| **E56** | Consolidated Analytics | - US-154: Cross-Tenant Consolidated Dashboard<br>- US-155: Consolidated Executive Slide Exporter | **implemented** | `tests/test_consolidated.py` |
| **E57** | Smart Notification Engine | - US-160: Tax Deadline Alerter<br>- US-161: Anomaly Alert Engine | **implemented** | `tests/test_scheduler.py` |
| **E58** | Document Intelligence | - US-162: Photo Invoice OCR Pipeline<br>- US-163: Smart Document Classifier | **implemented** | `tests/test_ocr_pipeline.py`, `tests/test_expense_classifier.py` |
| **E59** | API Integration Gateway | - US-164: Versioned REST API Gateway<br>- US-165: Integration Marketplace Webhook Registry | **implemented** | `tests/test_webhook_hub.py` |
| **E60** | AI Tax Audit Simulation | - US-170: Tax Audit Simulation Engine<br>- US-171: Audit Mitigation Adviser | **implemented** | `tests/test_mitigation.py` |
| **E61** | Related Party & Transfer Pricing | - US-172: Related Party Transaction Detector<br>- US-173: Transfer Pricing Local File Scaffolder | **implemented** | `tests/test_v3_features.py` |
| **E62** | Foreign Contractor & Treasury | - US-174: Multi-Currency Treasury Reconciler<br>- US-175: Foreign Contractor Tax Compliance Auditor | **implemented** | `tests/test_fct_auditor.py` |
| **E63** | CIT Finalization | - US-180: CIT Finalization Engine<br>- US-181: CIT Scenario Modeler | **implemented** | `tests/test_cit.py` |
| **E64** | Schema & Custom Metadata | - US-182: XML Schema Extension Engine<br>- US-183: Dynamic Metadata Reporter | **implemented** | `tests/test_schema_validation.py` |
| **E65** | Multi-Sig & Blockchain Integrity | - US-184: Multi-Signature Approver<br>- US-185: Blockchain Audit Ledger | **implemented** | `tests/test_audit_ledger.py` |
| **E66** | Customs XML Parser & Matching | - US-190: Customs XML Parser<br>- US-191: Customs to Invoice Matcher | **implemented** | `tests/test_reconciliation.py` |
| **E67** | PIT & Payroll Audit Engine | - US-192: Payroll Compliance Engine<br>- US-193: Automated PIT Finalizer | **implemented** | `tests/test_reconciliation.py` |
| **E68** | Secure Archiving & TSA Cryptography | - US-194: Decree-123 Digital Vault<br>- US-195: Long-Term Signature Validator | **implemented** | `tests/test_signature_verification.py` |
| **E69** | BCTC Statutory Scaffolder | - US-200: Statutory BCTC Scaffolder<br>- US-201: Ledger Integrity Auditor | **implemented** | `tests/test_v17_features.py` |
| **E70** | Tax Payment & Bank Reconciliation | - US-202: Tax Payment Slip Scaffolder<br>- US-203: Bank Transaction Reconciler | **implemented** | `tests/test_v17_features.py` |
| **E71** | E-Commerce Ingestion & Matcher | - US-204: Ecommerce Invoice Synchronizer<br>- US-205: Ecommerce Revenue Tax Matcher | **implemented** | `tests/test_v17_features.py` |
| **E72** | Webapp UI/UX Audit & Refinement | - US-206: CSS Theme Refactor<br>- US-207: Bento Grid KPI Search UI<br>- US-208: Cashflow SVG charts<br>- US-209: Forms CRO Optimize<br>- US-210: Captcha Pytest Suit<br>- US-211: AI Copilot Contextual Assistant Upgrade<br>- US-212: Supplier Risk Radar | **implemented** | `tests/test_settings_filters.py`, `tests/test_v12_cashflow.py`, `tests/test_auth.py`, `tests/test_captcha_solver.py`, `tests/test_supplier_risk.py` |
| **E85** | IAS 12 Deferred Tax | - US-300: IAS 12 Temporary Difference Engine<br>- US-301: Deferred Tax Balance Sheet Integration | **implemented** | `tests/test_ifrs_engine.py` |
| **E86** | IFRS 16 Leases | - US-302: Present Value Calculator<br>- US-303: Lease Liability Amortization Schedule | **implemented** | `tests/test_ifrs_engine.py` |
| **E87** | OECD Pillar Two | - US-304: Cross-Tenant Consolidation Router<br>- US-305: GloBE Top-up Tax Estimator | **implemented** | `tests/test_ifrs_engine.py` |
| **E88** | Decree 132 Related-Party & EBITDA Cap | - US-310: Database Schema & Catalog Management<br>- US-311: Core EBITDA interest cap & Form 01/132 disclosures | **implemented** | `tests/test_v19_us191_partner_schema.py`, `tests/test_cit.py` |
| **E89** | Circular 103 FCT Withholding Auditor | - US-312: FCT Classifier & Line-item calculations<br>- US-313: FCT Form 01/NTNN Excel Exporter | **implemented** | `tests/test_fct_auditor.py` |
| **E90** | Circular 78 CIT Preferential Rates & Tax Holidays | - US-314: Preferred CIT Rates, Tax Holidays & R&D Modeler<br>- US-315: End-to-End Integration & Suite Verification | **implemented** | `tests/test_cit.py`, `tests/test_ifrs_engine.py`, `scripts/validate.bat` |
| **E91** | Tax AI Agent Swarm | - US-320: Local Agent Mailroom & Coordination Hub<br>- US-321: Autonomous Joint Audit Coordinator | **planned** | `tests/test_ai_swarm.py` |
| **E92** | Bank Stream Ingestion & Matching | - US-322: Bank Feed Ingestion & Transaction Normalizer<br>- US-323: Automated Bank-to-Invoice Matcher | **planned** | `tests/test_bank_matching.py` |
| **E93** | ML Tax Forecast & Sandbox | - US-324: Machine Learning Tax Liability Predictor<br>- US-325: Tax Scenario Simulation Sandbox | **planned** | `tests/test_ml_forecast.py` |
| **E94** | Graph Fraud Analyzer | - US-330: Taxpayer Network Graph Generator<br>- US-331: VAT Fraud Ring Network Detector | **planned** | `tests/test_graph_fraud.py` |
| **E95** | Cryptographic TSA Ledger | - US-332: Immutable Cryptographic Merkle Ledger<br>- US-333: Zero-Knowledge Proof Tax Compliance | **planned** | `tests/test_cryptographic_ledger.py` |
| **E96** | Customs VAT Reconciler | - US-334: Customs XML Declaration Parser<br>- US-335: Import VAT Reconciliation & Mitigation | **planned** | `tests/test_customs_reconciler.py` |

## Harness Growth Backlog

Future harness extensions and product enhancements are tracked in [docs/HARNESS_BACKLOG.md](file:///d:/LearnAnyThing/Webapp%20XML/docs/HARNESS_BACKLOG.md).


