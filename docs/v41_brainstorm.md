# Brainstorm & Design Plan: Version 41.0.0 — Export Customs & VAT Refund Hub (Circular 80)

This document outlines the conceptual design, user experience details, and technical schema for **Version 41.0.0** of the GDT Invoice Hub.

---

## 🎨 1. Frontend Aesthetic & Interactive Design System

For this premium hub, we will adopt a **Cyber-Corporate Emerald & Steel Gray** theme, indicating treasury security, international trade, and tax refund compliance.

### Theme & Palette (Glassmorphic Dark Mode)
- **Primary Background**: Midnight Slate (`#0B0F19`)
- **Card Background**: Glassmorphic Deep Steel (`rgba(22, 28, 45, 0.7)`) with border (`rgba(255, 255, 255, 0.08)`) and backdrop-filter (`blur(16px)`).
- **Primary / Compliance Accent**: Mint Emerald (`#10B981` / `rgb(16, 185, 129)`)
- **Customs / Import-Export Accent**: Bright Cyan (`#06B6D4` / `rgb(6, 182, 212)`)
- **Warning / Audit Accent**: Amber Gold (`#F59E0B`)

### Font Pairing
- **Headings**: `Outfit` (sans-serif, modern, geometric)
- **Body**: `Inter` (neutral, high-readability)

### Dynamic Elements & Micro-animations
- **Interactive SVG Refund Timeline**: A linear progress track with pulsating nodes representing stages of the VAT refund audit (Drafting -> Submission -> Customs Verification -> Bank Payment Verification -> GDT Decision -> Refund Completed). Hovering over each node reveals required compliance documents.
- **Interactive File Upload Area**: Drag-and-drop area for Customs XML files, featuring an upload progress ring and success state animation.

---

## ⚙️ 2. Core Modules & Technical Specifications

### Module A: Customs XML Parser & Reconciliation (US-530 & US-531)
- **XML Structure**: Simulates the General Department of Customs (Tổng cục Hải quan) export declaration format, extracting:
  - Declaration Number (`Số tờ khai`)
  - Registration Date & Clearance Date (`Ngày thông quan`)
  - Exporting MST (`MST người xuất khẩu`)
  - Total Export Value (`Trị giá USD / VND`)
  - HS Codes & Item Details
- **Reconciliation Engine**:
  - Compares the Customs Declaration record with GTGT export invoices (invoice type code `01GTKT` or export invoice `02GTTT` / `08GSTK`).
  - Validates key compliance criteria: matching buyer/seller tax IDs, value tolerances (under 0.5% exchange rate difference), and clearance date alignment.

### Module B: Circular 80 Form 01-1/GTGT & 01/ĐNHT Builders (US-532 & US-533)
- **Form 01-1/GTGT**: Compiles a structured, exportable tabular layout of export declarations, clearance dates, linked export invoices, and values.
- **Form 01/ĐNHT (Request for Refund)**: Scaffold wizard calculating:
  - Cumulative input tax credits (`Thuế GTGT đầu vào chưa khấu trừ hết`)
  - Export revenue ratio (`Tỷ lệ doanh thu xuất khẩu`)
  - Refundable input VAT allocated to exports (`Thuế GTGT đầu vào phân bổ hoàn thuế cho xuất khẩu`)
  - Non-cash payment proof compliance checklists.

### Module C: Interactive VAT Refund Audit Dashboard & SVG Timeline (US-534)
- **Compliance Checks Panel**:
  - Verification of non-cash payment bank vouchers (chứng từ thanh toán không dùng tiền mặt) for export transactions over 20 million VND.
  - Tracking time limit for customs declaration checking (usually 150 days from registration date).
- **SVG Timeline Visualizer**:
  - SVG element representing the refund timeline.
  - Hovering/clicking a node shows the detailed audit status of that stage.

---

## 🗄️ 3. Database Schema Updates

We will add three new models to support these features in the database:
1. `CustomsDeclaration`:
   - `id` (integer, primary key)
   - `declaration_num` (string, unique, non-null)
   - `registration_date` (date)
   - `clearance_date` (date)
   - `taxpayer_mst` (string)
   - `export_value_usd` (float)
   - `exchange_rate` (float)
   - `export_value_vnd` (float)
   - `hs_codes` (string)
   - `status` (string)
2. `DeclarationInvoiceMatch`:
   - `id` (integer, primary key)
   - `declaration_id` (integer, foreign key to `CustomsDeclaration.id`)
   - `invoice_id` (integer, foreign key to `Invoice.id`)
   - `match_status` (string)
   - `value_difference` (float)
   - `notes` (string)
3. `VatRefundApplication`:
   - `id` (integer, primary key)
   - `taxpayer_mst` (string)
   - `period_start` (string)
   - `period_end` (string)
   - `total_input_vat` (float)
   - `allocated_export_vat` (float)
   - `refund_requested_amount` (float)
   - `status` (string)  # Draft, Submitted, Approved, Rejected
   - `created_at` (datetime)
