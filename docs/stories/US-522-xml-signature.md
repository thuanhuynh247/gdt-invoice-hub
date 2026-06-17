# Story US-522: E-Invoice XML Signature Authenticator & Certificate Chain Validator

## Title
E-Invoice XML Signature Authenticator & Certificate Chain Validator

## Description
Under Decree 123/2020/NĐ-CP, electronic invoices must be digitally signed. Valid signatures are critical for tax deductibility.
This story implements a parser to inspect the XML signature structure, extract the X.509 signing certificate metadata (subject, issuer, dates, serial number), check validity against expiry, and simulate trust chain verification against trusted Vietnamese Certificate Authorities (CAs).

## Target Outputs
- Service method `InvoiceSignatureService.verify_invoice_xml_signature(xml_content)`
- Return structured calculation result with fields: `has_signature`, `signature_node_type`, `cert_subject`, `cert_issuer`, `valid_from`, `valid_to`, `is_expired`, `is_trusted_ca`, `status` (VALID/INVALID/EXPIRED/UNTRUSTED).

## Verification
- Unit test in `tests/test_v40_features.py`: `test_invoice_xml_signature_authenticator()`.
