# Feasibility Matrix & Validation Plan: Version 17.0.0

This document defines the validation roadmap and testing requirements for Version 17.0.0 integration and compliance checkups.

---

## 🔍 Validation Matrix

| Story ID | Requirement | Test Type | Verification Vector |
| :--- | :--- | :--- | :--- |
| **US-200** | Balance Sheet Equations | Unit | Assert `Assets == Liabilities + Equity` |
| **US-200** | HTKK XML Schema | Integration | Validate output against GDT schema definitions |
| **US-201** | Ledger-to-Invoice Matcher | Unit | Check tolerance mapping for time (30-day window) and rounding |
| **US-202** | Form 711/MB XML format | Integration | Assert target codes (VAT `1701`, CIT `1052`) inside XML output |
| **US-202** | VietQR String Syntax | Unit | Verify VietQR conforms to NAPAS standard structure |
| **US-203** | Statement Excel Parsers | Unit | Test Techcombank / VCB mock parser on transaction lines |
| **US-203** | 20M VND Non-Cash Deductions | Integration | Check that a invoice ≥ 20M without payment causes warning status |
| **US-204** | Shopee Fee Deductor | Unit | Assert that commission and processing fees reduce net sales |
| **US-205** | Daily Retail Matching | Integration | Verify consolidated Daily Invoice matches sum of mock retail orders |

---

## 🏃 Execution Commands

1. **Run Unit and Integration Tests**:
   ```bash
   pytest tests/test_v17_*.py
   ```
2. **HTKK XML Validation Run**:
   Validate exported BCTC/Payment Slip XML strings against official XSD files in the resources directory.
