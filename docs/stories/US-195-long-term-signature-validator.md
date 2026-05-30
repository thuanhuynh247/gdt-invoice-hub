# US-195 Long-Term Signature & TSA Validator

## Status

planned

## Lane

normal

## Product Contract

The application must provide a cryptographic signature validator that parses electronic invoice XML files, extracts signing certificates and timestamp authority (TSA) tokens, and verifies their historical validity to ensure non-repudiation.

## Relevant Product Docs

- `docs/product/v16_roadmap.md`

## Acceptance Criteria

- [ ] Extract digital signature tokens, trust anchors, and embedded certificates from standard GDT XML files.
- [ ] Parse and decode RFC-3161 Timestamp Authority (TSA) tokens verifying the signing date and time.
- [ ] Check certificate revocation status (mocked CRL/OCSP checking).
- [ ] Build a verification result dashboard showing trust chain path, certificate status, signing time, and validity flags.
- [ ] Expose API endpoint `POST /api/vault/verify-signature` to process XML files and return cryptographic validation logs.
- [ ] Write unit tests verifying XML signature parsing, TSA token verification, and error response on tampered inputs.

## Design Notes

- **Module**: `invoices/signature_validator.py`
- **Verification standard**: Follows Vietnamese Government Cryptographic Standards and RFC-3161.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | `pytest tests/test_v16_signature_validator.py` verifying parsing of XML signature elements and validation of simulated TSA timestamps |
| Integration | Uploading a valid signed invoice XML returns successful validation indicators and certificate owner name |
