# Story Specification: US-312 — Foreign Contractor Tax (FCT) Classifier & Line-Item Auditor

## 📋 Context & Business Value
Under Circular 103/2014/TT-BTC, domestic buyers must withhold Foreign Contractor Tax (FCT/NTNN) when buying services or service-attached goods from foreign entities. This story builds an automated classifier to identify contractor purchase invoices and audit individual line items to split FCT VAT and FCT CIT obligations.

---

## 🎯 Acceptance Criteria

### 1. Foreign Contractor Classification
- Identify contractor invoices among purchase records:
  - Seller MST begins with prefix `900`.
  - Seller MST is empty/missing, and the seller name contains matches for known foreign service providers (e.g., "Google", "Zoom", "AWS", "Amazon", "Microsoft", "Facebook").

### 2. Line-Item Splitting & Rates Assignment
- Scan and evaluate each line-item description for specific categories:
  - **SaaS / Software Licenses**: VAT = 0% (exempt), CIT = 5%.
  - **Online Advertising / Hosting / Cloud Services**: VAT = 5%, CIT = 5%.
  - **Royalties / Brand Rights**: VAT = 0% (exempt), CIT = 10%.
  - **General Services**: VAT = 5%, CIT = 5%.
- Calculate withheld tax values dynamically based on gross/net contracts:
  - VAT withheld = Gross Revenue * VAT rate * 50% (if subject to direct method credit).
  - CIT withheld = (Gross Revenue - VAT withheld) * CIT rate.

---

## 🛠️ Verification & Test Plan
- Run Pytest verification using `tests/test_fct_auditor.py`.
- Assert correct classification, rate matching, and mathematical splits on Google Ads, Zoom SaaS, and AWS hosting test datasets.
