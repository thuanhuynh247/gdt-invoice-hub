# Context: Webapp XML (Vietnam E-Invoice & Compliance Hub Platform)

## Overview

**Webapp XML** is an enterprise-grade web application and compliance intelligence engine designed to process, parse, validate, and audit Vietnamese electronic invoices (Hóa đơn điện tử - HĐĐT) according to Decree 123/2020/NĐ-CP, Circular 78/2021/TT-BTC, Law 48/2024, Law 149/2024, and international tax frameworks (IFRS, Pillar 2 Global Minimum Tax).

The platform provides multi-tenant data isolation per taxpayer (MST), high-performance XML batch processing, an automated compliance DSL engine, and responsive glassmorphic interfaces adhering to the **Wise Fintech** design system.

---

## Ubiquitous Language (Glossary)

### 1. E-Invoice & Tax Domain
- **E-Invoice (Hóa đơn điện tử / HĐĐT)**: An electronic invoice formatted in XML specified by the General Department of Taxation (Tổng cục Thuế - GDT). Contains header (Ký hiệu, Số HĐ, Ngày lập), seller (Bên bán), buyer (Bên mua), line items (Danh mục hàng hóa/dịch vụ), VAT rates (0%, 5%, 8%, 10%), and digital signature (Chữ ký số / HSM).
- **Tax Authority Code (Mã CQT)**: A unique identifier assigned by GDT to validated invoices.
- **Taxpayer / Tenant (Mã số thuế / MST)**: The 10-digit or 13-digit tax code representing the legal business entity. Each taxpayer has an isolated database sandbox (`tenant_<MST>.db`).
- **T-Score (Tax Compliance Score)**: A 0–100 numerical score evaluating invoice and taxpayer risk posture calculated by the Compliance DSL Engine based on blacklisted suppliers, cash payments exceeding 20,000,000 VND, timing anomalies, or tax rate discrepancies.

### 2. Modular Compliance Hubs (V-Series)
- **Compliance Hub**: A specialized UI and analytical engine module auditing a specific regulatory vertical.
  - **V55–V61**: VAT deduction eligibility, corporate income tax (CIT - Luật 149/2024), invoice status verification.
  - **V62–V69**: Transfer pricing risk flags, non-cash payment compliance, cross-border withholding tax.
  - **V78 (Validation Engine)**: XML structure validation, digital signature verification, schema tampering detection.
  - **V79 (Global Minimum Tax / Pillar 2)**: Multilateral enterprise anomaly audit, top-up tax calculations, and transfer pricing benchmarking.

### 3. UI/UX Architecture (Wise Fintech)
- **Lego Component**: Reusable, atomic HTML/CSS/JS interface components (metric stat cards, filter bars, badge pills, responsive datatables with sticky headers, modal drill-downs).
- **Glassmorphism**: Visual aesthetic characterized by semi-transparent background cards (`backdrop-filter: blur(12px)`), subtle borders (`1px solid rgba(255, 255, 255, 0.08)`), and soft layered shadows.
- **Color Tokens**: CSS custom properties using HSL format (e.g. `--primary-hsl`, `--bg-surface`, `--text-main`, `--badge-success`, `--badge-warning`, `--badge-danger`).
- **Typography**: Primary UI font **Outfit** or **Inter**; Monospace numeric data font **Roboto Mono** or **JetBrains Mono** for monetary amounts, tax codes, and invoice numbers.

### 4. Harness & Engineering Orchestration
- **Harness Database (`harness.db`)**: Central SQLite database storing all stories, tasks, telemetry traces, and unified quality gates.
- **TSA (Trace Signature Authority)**: Automated cryptographic signing of verification runs and test results before turn conclusion.
- **ADR (Architecture Decision Record)**: Permanent records in `docs/decisions/` recording architectural invariants.

---

## Synonyms & Avoided Terms

| Concept | Preferred Term | Avoid (Ambiguous / Outdated) |
|---|---|---|
| Electronic Invoice | `HĐĐT` / `e-invoice` | `bill`, `receipt`, `paper invoice` |
| Tax Entity | `Taxpayer` / `MST` | `user`, `account`, `customer` |
| Audit Interface | `Compliance Hub` | `page`, `screen`, `tab` |
| Scoring Metric | `T-Score` | `rating`, `star score` |
| UI Component Pattern | `Lego Component` | `widget`, `div block` |

---

## System Architecture & Codebase Map

```
/
├── app.py                             ← Application factory & Blueprint registration
├── invoices/                          ← Core domain package
│   ├── routes/                        ← Modular Blueprints (shared state)
│   │   ├── core.py                    ← Dashboard, list, and upload endpoints
│   │   ├── compliance.py              ← Compliance Hub router (V55–V79)
│   │   ├── reconciliation.py          ← Bank & customs reconciliation
│   │   └── ...
│   ├── service.py                     ← Multi-tenant database service & XML parsing
│   ├── sync_queue.py                  ← Background GDT sync queue & daemon
│   └── v79_service.py                 ← Pillar 2 & Transfer Pricing audit engine
├── templates/                         ← Jinja2 HTML templates (Wise Fintech Lego components)
│   ├── v55_compliance_hub.html ... v79_compliance_hub.html
│   └── ...
├── static/                            ← Stylesheets & client-side scripts
├── docs/                              ← Specifications & architecture documentation
│   ├── ARCHITECTURE.md                ← Layering & parse-first boundaries
│   ├── CONCEPT_MAP.md                 ← 7-page concept map for routing & compliance
│   ├── decisions/                     ← ADRs (0001 to 0007+)
│   └── agents/                        ← Matt Pocock skills documentation
└── tests/                             ← Pytest automated test suites
```

---

## Architectural Invariants (ADRs)

- **ADR-0001**: Harness-First Development (`docs/decisions/0001-harness-first-development.md`).
- **ADR-0004**: SQLite Durable Layer & WAL Mode (`docs/decisions/0004-sqlite-durable-layer.md`).
- **ADR-0006**: Regulation RAG & Chatbot Integration (`docs/decisions/0006-chatbot-gemma4-regulation-rag.md`).
- **ADR-0007**: Concept Map Expander Integration (`docs/decisions/0007-concept-map-expander-integration.md`).
