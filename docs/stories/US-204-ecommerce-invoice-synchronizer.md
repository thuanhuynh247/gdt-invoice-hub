# Story Specification: US-204 — E-Commerce Seller Portal Invoice Synchronizer

## 📋 Context & Business Value
Multi-channel retail operations on platforms like Shopee, Lazada, and TikTok Shop generate thousands of sales daily. Platform operators charge commissions, shipping fees, and advertising costs, and they auto-issue service invoice files. This story implements standard API hooks and file parsers to import sales invoices and platform expense bills, ensuring complete ledger compliance.

---

## 🎯 Acceptance Criteria

### 1. E-Commerce Platform Parsers
- **Requirement**: Parse official transaction reports and invoice lists.
- **Platforms Supported**:
  - **Shopee**: Parse "Báo cáo thu nhập" (Income Report) and "Hóa đơn dịch vụ" (Service Invoices).
  - **TikTok Shop**: Parse "Bảng kê quyết toán" (Settlement Sheets).
- **Extracted Fields**:
  - Order ID & Platform Order Reference
  - Customer tax code (if B2B sale)
  - Gross sales amount (Revenue)
  - Vouchers, Discounts, and Platform Subsidies
  - Payment Processing Fee, Commission Fee, and Shipping Fees

### 2. Standardized Database Schema Integration
- **Requirement**: Save transaction items to the database, mapping them to corresponding tenant accounts.
- **Rules**:
  - Store platform commission fees as input expenses.
  - Store gross client receipts as output revenues.

### 3. API Integrator
- **Requirement**: Endpoint `POST /api/ecommerce/sync` supporting manual file uploads or mock API payload inputs.

---

## 🛠️ Verification & Test Plan

- **Unit Tests**:
  - Test calculation parser on voucher-subsidized orders (handling seller-sponsored vs Shopee-sponsored vouchers).
- **Integration Tests**:
  - Call `/api/ecommerce/sync` uploading standard Shopee income report mock files.
  - Verify database writes the correct totals to merchant sales records.
