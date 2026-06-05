# Story Pack - Version 22.0.0: Intelligent Tax Penalty Predictor & Advanced Corporate Tax Compliance

This story pack covers the entire implementation of US-340 to US-345.

## Story Queue & Progress

- **US-340: Statutory Tax Penalty & Interest Calculator**
  - **Status**: Implemented
  - **Deliverable**: Penalty & interest calculator logic in `invoices/refund_service.py` under the `audit/calculate-penalties` path.
- **US-341: AI-Generated Audit Explanation & Defense Template Builder**
  - **Status**: Implemented
  - **Deliverable**: Prompt composition engine utilizing templates citing Decree 125/2020/NĐ-CP to generate defense letters.
- **US-342: Shopee, Lazada & TikTok Shop Order Normalizer**
  - **Status**: Implemented
  - **Deliverable**: Data parsers normalizing Shopee/Lazada/TikTok sales logs.
- **US-343: E-Commerce Tax Compliance Matching & Warning Engine**
  - **Status**: Implemented
  - **Deliverable**: Compliance warning checker that compares normalized orders against issued buyer-seller invoices.
- **US-344: Interactive Payroll Audit Dashboard**
  - **Status**: Implemented
  - **Deliverable**: Interactive payroll audit reports detailing individual progressive PIT brackets.
- **US-345: PIT Finalizer & Form 05/QTT-TNCN UI**
  - **Status**: Implemented
  - **Deliverable**: Step-by-step PIT wizard UI producing GDT XML schema files.

## Verification & Proof

- **Unit Proof**:
  - `tests/test_v22_features.py` (or consolidated `tests/test_v27_features.py`)
- **Integration Proof**:
  - `invoices/routes.py` and front-end interface endpoints.
