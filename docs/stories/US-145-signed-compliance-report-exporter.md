# US-145 Signed Compliance Report Exporter

## Status

planned

## Lane

normal

## Product Contract

The application must allow users to export verified ledgers of invoices to PDF or Excel formats with an embedded cryptographic SHA-256 integrity block. This signature acts as proof that the compiled invoice list has not been tampered with post-audit.

## Relevant Product Docs

- `docs/product/v11_roadmap.md`

## Acceptance Criteria

- [ ] Implement API endpoint `GET /api/reports/signed-compliance` exporting the audited ledger.
- [ ] Calculate a SHA-256 digest of the exported data table rows and append the signature block at the footer.
- [ ] Integrate a verification panel where users can upload an exported report file to re-calculate and verify its integrity signature.
- [ ] Write tests ensuring signature verification matches original file content and detects alterations.

## Design Notes

- **Export engine**: Generates PDF/Excel with checksum calculated from concatenated row data (invoice ID + total + date).
- **Security keys**: Signature calculated with a hash derived from system secret keys.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | `pytest tests/test_v11_signed_report.py` checking bhash calculations and verification |
| Integration | Downloaded reports show matching signatures and fail verification if contents are modified |
