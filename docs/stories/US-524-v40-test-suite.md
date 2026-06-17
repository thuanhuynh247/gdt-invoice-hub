# Story US-524: End-to-End V40 Verification Test Suite

## Title
End-to-End V40 Verification Test Suite

## Description
This story implements the comprehensive automated verification suite for FCT, Related-Party transactions EBITDA caps, and e-invoice XML signature verification.

## Target Outputs
- Pytest suite file `tests/test_v40_features.py` covering:
  - `test_fct_withholding_calculation`: net/gross scenarios, categories, and rates.
  - `test_decree132_ebitda_cap`: EBITDA calculation, 30% cap enforcement, disallowed interest additions.
  - `test_invoice_xml_signature_authenticator`: signature node presence, X.509 metadata extraction, CA checks.
  - `test_api_endpoints_v40`: unauthorized checks, JSON API payload contracts.

## Verification
- Run: `venv\Scripts\python.exe -m pytest tests/test_v40_features.py`
