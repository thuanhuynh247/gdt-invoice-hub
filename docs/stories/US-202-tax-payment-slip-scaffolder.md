# Story Specification: US-202 — GDT Tax Payment Slip Scaffolder (Form 711/MB)

## 📋 Context & Business Value
Once tax liabilities (VAT, CIT, PIT, Customs Duty) are calculated, corporate accountants must generate and submit the official GDT Tax Payment Slip (Giấy nộp tiền vào Ngân sách Nhà nước - Form 711/MB) to transfer funds. Automating this eliminates the risks of choosing incorrect State Budget codes, which results in tax payments being misclassified and incurring late-payment interest.

---

## 🎯 Acceptance Criteria

### 1. Statutory Code Mappings
- **Requirement**: Implement accurate tax category mapping based on GDT rules.
- **Rules**:
  - Automatically resolve GDT Chapter Code (Chương) based on company type (e.g. Chapter `152` for foreign-invested enterprises, `552` or `757` for domestic private enterprises).
  - Map tax liabilities to correct GDT Sub-Chapter Codes (Tiểu mục):
    - Domestic VAT: `1701`
    - Corporate Income Tax (CIT): `1052`
    - Personal Income Tax (PIT): `1001`
    - Import Duty: `1901`
    - Environmental Tax: `2001`

### 2. State Budget Bank Account Resolution
- **Requirement**: Match the target treasury district (Kho bạc Nhà nước Quận/Huyện) and bank account with the company's tax office registration.

### 3. XML & VietQR Payment Code Output
- **Requirement**: Generate the payment form and payment code.
- **Rules**:
  - Generate a valid XML string conforming to the GDT e-Tax portal Form 711/MB schema.
  - Generate a standard VietQR string containing state payment specifications (Treasury Bank Account, Chapter, Sub-Chapter, Amount, and standard syntax `ND:...`) for instant bank app scanning.

---

## 🛠️ Verification & Test Plan

- **Unit Tests**:
  - Assert correct sub-chapter code lookup for multiple tax types.
  - Test VietQR string builder logic.
- **Integration Tests**:
  - Call `POST /api/payments/tax-slip` passing tax values.
  - Verify returned response includes a valid XML structure and a base64-encoded VietQR code image.
