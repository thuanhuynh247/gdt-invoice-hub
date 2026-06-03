# US-194 Decree 123 Compliant Digital Vault & XML Archiver

## Status

implemented

## Lane

normal

## Product Contract

The application must provide a legally compliant digital vault to store, compress, encrypt, backup, and full-text index electronic invoice XML files and respective PDF files for a statutory 10-year period under Decree 123/2020/NĐ-CP.

## Relevant Product Docs

- `docs/product/v16_roadmap.md`

## Acceptance Criteria

- [x] Create an archiving scheduler that automatically packages invoice XML and PDF files into compressed ZIP archives.
- [x] Implement ZIP package encryption using AES-256 with user-defined or tenant keys.
- [x] Build a database index system mapping full-text searchable metadata (Date, Tax Code, Issuer, Total, Products).
- [x] Expose an advanced search and retrieval panel in the web interface.
- [x] Provide options to export archives to local disk or cloud backup (mocked).
- [x] Expose API endpoint `POST /api/vault/archive` to manage vault records.
- [x] Write unit tests verifying zip packaging, AES encryption, and metadata index searches.

## Design Notes

- **Module**: `invoices/digital_vault.py`
- **Data storage**: Encrypted zip archives stored in `instance/vault/` folder, database index in `InvoiceArchive` table.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | `pytest tests/test_v16_digital_vault.py` verifying zip compression, AES encryption/decryption, and search index query speed |
| Integration | Calling `/api/vault/archive` packages selected invoices, encrypts files on disk, and stores keys in secure settings |
