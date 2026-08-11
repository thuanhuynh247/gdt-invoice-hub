# User Story: US-V81 - Personal Income Tax (PIT) Compliance Hub & Real-time Live Telemetry

## 1. Business Context & Legal Basis
- **Circular 111/2013/TT-BTC** & **Circular 25/2018/TT-BTC**: Detailed guidance on Personal Income Tax (PIT) withholding, family circumstance deductions, and freelance service compensation.
- **Circular 78/2021/TT-BTC** & **Decree 123/2020/NĐ-CP**: Electronic PIT withholding receipts (Chứng từ khấu trừ thuế TNCN điện tử).
- **Law on Tax Administration No. 38/2019/QH14**: Requirements for withholding declarations, Form 08/CK-TNCN conditions, and Form 05/KK-TNCN quarterly/annual finalizations.

## 2. Core Functional Requirements
1. **PIT Withholding Engine**:
   - **Contract Type A (Labor contract $\ge 3$ months)**: Standard progressive tax rates (5% to 35%), Personal deduction (11,000,000 VND/month), Dependent deduction (4,400,000 VND/dependent/month), Mandatory social/health/unemployment insurance deductions.
   - **Contract Type B (Freelance / Contract < 3 months / Non-contract)**:
     - If payment per instance $< 2,000,000$ VND: No mandatory withholding at source.
     - If payment per instance $\ge 2,000,000$ VND: Mandatory **10% withholding** (or 20% for non-residents).
2. **Form 08/CK-TNCN Commitment Validation**:
   - Condition 1: Individual has registered a Personal Tax Code (MST) before/at signing.
   - Condition 2: Total estimated annual taxable income after personal/family deductions is below taxable bracket ($\le 132,000,000$ VND/year if 0 dependents, $\le 184,800,000$ VND/year if 1 dependent, etc.).
   - Condition 3: Individual signs commitment asserting they only earn income from this sole payer during the tax year.
   - **Violation Detection**: Flag invalid Form 08 commitments (e.g. missing MST, multiple payer records, or income already exceeding annual threshold) and mandate 10% tax withholding plus late filing penalty calculations.
3. **Electronic Withholding Certificate Management**:
   - Verification of electronic certificate issuance under Circular 78.
   - Verification of digital signatures and transmission status to GDT portal.
4. **Form 05/KK-TNCN XML Generator**:
   - Generates compliant XML structure for Form 05/KK-TNCN ready for import into HTKK (Hỗ trợ Kê khai thuế).
5. **Multi-Agent Debate Consensus**:
   - **PIT Tax Inspector (Cán bộ Thuế TNCN)**: Audits legal compliance, Form 08 validity, and withholding obligations.
   - **HR & Payroll Director (Trưởng phòng Nhân sự & Tiền lương)**: Balances employee net take-home pay, contract clauses, and commitment letters.
   - **Chief Internal Auditor (Trưởng ban Kiểm toán Nội bộ)**: Assesses tax audit exposure, penalties under Decree 125/2020/NĐ-CP, and corporate income tax disallowances.
6. **Real-time Server-Sent Events (SSE) Live Telemetry Stream**:
   - Broadcast live system and audit events over `/api/telemetry/stream` to the `_live_telemetry_stream.html` console.

## 3. Architecture & Persistence
- Backend: `invoices/v81_service.py`
- Routes: `invoices/routes/compliance.py`
- Frontend: `templates/v81_compliance_hub.html` using Wise Fintech Jinja2 Lego components
- Database: Multi-tenant SQLite table `v81_pit_audit_logs` in `data/{tenant_mst}.db`.
- Tests: `tests/test_v81_features.py`
