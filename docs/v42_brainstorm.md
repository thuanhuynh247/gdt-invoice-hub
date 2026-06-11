# Brainstorm & Design Plan: Version 42.0.0 — Transfer Pricing Form 01/132 & E-Commerce Tax Refund Hub

This document outlines the conceptual design, user experience details, and technical schema for **Version 42.0.0** of the GDT Invoice Hub.

---

## 🎨 1. Frontend Aesthetic & Interactive Design System

For this premium hub, we will adopt a **Cyber-Corporate Gold & Sapphire Blue** theme, indicating transfer pricing benchmarks, treasury wealth, and high-value compliance audits.

### Theme & Palette (Glassmorphic Dark Mode)
- **Primary Background**: Deep Midnight Blue (`#070A13`)
- **Card Background**: Glassmorphic Royal Sapphire (`rgba(17, 24, 43, 0.75)`) with border (`rgba(255, 255, 255, 0.08)`) and backdrop-filter (`blur(16px)`).
- **Primary / Compliance Accent**: Gold / Bronze (`#F59E0B` / `rgb(245, 158, 11)`)
- **E-Commerce / Transaction Accent**: Electric Indigo (`#6366F1` / `rgb(99, 102, 241)`)
- **Warning / Audit Accent**: Rose Red (`#EF4444`)

### Font Pairing
- **Headings**: `Outfit` (geometric, modern)
- **Body**: `Inter` (neutral, high readability)

### Dynamic Elements & Micro-animations
- **Transfer Pricing Arm's Length Range Slider / Chart**: An interactive SVG representation of benchmarking results, showcasing the median and interquartile range (25th to 75th percentile). If the taxpayer's profit margin falls outside the range, it highlights in red and allows adjusting the profit margin to simulate tax adjustments.
- **Interactive File Upload Area**: Drag-and-drop area for E-Commerce platform transaction reports (CSV/Excel files) with upload progress animation and matching statistics.

---

## ⚙️ 2. Core Modules & Technical Specifications

### Module A: Transfer Pricing Ingestion & Benchmark Comparator Engine (US-540)
- **Benchmarking Engine**:
  - Simulates benchmarking database (such as Orbis/Amadeus data) for comparison.
  - Compares taxpayer's profit margins (e.g. Operating Margin / Net Markup) against the arm's length range.
  - Adjusts taxable income based on the median of the range if profit margin is below the 25th percentile, under Decree 132/2020/NĐ-CP.
- **Model / Data Structure**:
  - `TransferPricingBenchmark`: tracks transaction types, comparator ranges (Min, 25th, Median, 75th, Max), and methods used (TNMM, CUP, etc.).

### Module B: Form 01/132 (Related-Party Disclosures & CIT Adjustments) XML Exporter (US-541)
- **Form 01/132 XML Generator**:
  - Generates the XML schema corresponding to GDT's Form 01/132 (Appendix I of Decree 132).
  - Encodes:
    - Related party relationships (Party A, Party B, relationship code A, B, C, D...).
    - Related transaction values (Revenue, Cost, Interest, Loans).
    - CIT adjustment calculation lines (disallowed interest, adjustments of transfer price).

### Module C: E-Commerce Transaction Matcher & Circular 80 Withholding Auditor (US-542)
- **E-Commerce Matcher**:
  - Parses simulated transaction logs from platform floors (Shopee, Lazada, TikTok Shop).
  - Matches transactions against issued sales invoices by date, buyer details, and amount.
  - Identifies revenue gaps (e.g., transactions occurred on the platform but no invoice was issued, or invoice values mismatch).
  - Validates tax withholding compliance (VAT 1%, PIT 0.5% withheld for individual business households, or corporate tax registration).

### Module D: Interactive Transfer Pricing & E-Commerce Audit Dashboard UI (US-543)
- **Visual Controls**:
  - Interactive dashboard located at `/v42-advanced-audit`.
  - Display widgets for Transfer Pricing adjustments and E-Commerce transaction matches.
  - Interactive SVG Arm's Length Range graph and reconciliation charts.
  - Audit Swarm debate summary panel simulating discussions between tax professionals on optimization and compliance.

---

## 🗄️ 3. Database Schema Updates

We will add four new models to support these features in the database:
1. `RelatedPartyTransaction`:
   - `id` (integer, primary key)
   - `taxpayer_mst` (string)
   - `related_party_name` (string)
   - `relationship_type` (string)  # e.g., "A", "B", "C"
   - `transaction_type` (string)  # Purchase, Sale, Loan, Service
   - `amount` (float)
   - `interest_rate` (float, optional)
2. `TransferPricingBenchmark`:
   - `id` (integer, primary key)
   - `taxpayer_mst` (string)
   - `transaction_type` (string)
   - `method_used` (string)  # TNMM, CUP, CPM
   - `taxpayer_margin` (float)
   - `benchmark_p25` (float)  # 25th percentile
   - `benchmark_median` (float)
   - `benchmark_p75` (float)
   - `adjustment_amount` (float)  # Calculated add-back if margin is outside range
3. `ECommercePlatformTransaction`:
   - `id` (integer, primary key)
   - `taxpayer_mst` (string)
   - `platform_name` (string)  # Shopee, Lazada, TikTok Shop
   - `transaction_id` (string)
   - `transaction_date` (string)
   - `buyer_name` (string)
   - `amount` (float)
   - `vat_withheld` (float)
   - `pit_withheld` (float)
   - `invoice_matched_id` (integer, optional)
4. `ECommerceReconciliationReport`:
   - `id` (integer, primary key)
   - `taxpayer_mst` (string)
   - `platform_name` (string)
   - `reconciliation_date` (string)
   - `total_platform_transactions` (integer)
   - `matched_count` (integer)
   - `mismatch_count` (integer)
   - `total_platform_revenue` (float)
   - `total_invoiced_revenue` (float)
   - `gap_amount` (float)
   - `compliance_status` (string)
