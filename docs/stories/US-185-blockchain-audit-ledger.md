# US-185 Blockchain-Based Invoice Integrity Ledger

## Status

planned

## Lane

normal

## Product Contract

The application must provide a cryptographic ledger anchoring invoice hashes sequentially (mocking blockchain ledger anchoring) to ensure and verify that invoice details, transaction history, and compliance audit logs have not been retroactively altered.

## Relevant Product Docs

- `docs/product/v15_roadmap.md`

## Acceptance Criteria

- [ ] Automatically calculate a SHA-256 hash of invoice data, digital signature, and audit results upon approval.
- [ ] Implement a sequential cryptographic hashing chain (each block contains the hash of the previous block) representing the integrity ledger.
- [ ] Build a verification panel allowing users/auditors to upload an invoice XML file to check it against the cryptographic ledger hash.
- [ ] Expose API endpoint `GET /api/blockchain/verify` to validate the overall integrity of the ledger chain.
- [ ] Write unit tests verifying block serialization, hashing chain integrity checks, and detection of modified mock invoice entries.

## Design Notes

- **Module**: `invoices/integrity_ledger.py`
- **Ledger Storage**: Persists ledger chain blocks in a local database table `IntegrityLedger`.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | `pytest tests/test_v15_integrity_ledger.py` testing sequential hashing chain verification and block tampering checks |
| Integration | Uploading a tampered invoice file to the verification endpoint triggers a cryptographic validation mismatch error |
