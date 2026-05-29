# US-163 Smart Document Classifier

## Status

planned

## Lane

normal

## Product Contract

The application must automatically suggest expense category tags for imported invoices based on seller name patterns, line-item descriptions, and historical classification data. Users can confirm, override, or reject suggested tags.

## Relevant Product Docs

- `docs/product/v13_roadmap.md`

## Acceptance Criteria

- [ ] Implement classifier analyzing seller name, line-item descriptions, and historical patterns.
- [ ] Suggest expense categories (raw_materials, services, assets, welfare, utilities, transport, other).
- [ ] Display suggestions with confidence scores (0.0–1.0) on invoice detail view.
- [ ] Allow users to confirm/override/reject suggestions via UI buttons.
- [ ] Store confirmed classifications to improve future suggestions (learning loop).
- [ ] Write tests verifying classification accuracy for known seller patterns.

## Design Notes

- **Algorithm**: Keyword matching + TF-IDF-like scoring from historical confirmed tags.
- **Model**: `DocumentClassification` in `invoices/models.py`.
- **No ML dependency**: Pure Python pattern matching for v13; ML upgrade deferred.

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | `pytest tests/test_v13_classifier.py` with known seller/item patterns |
| Integration | UI displays suggestions and stores user confirmations |
