# US-016 Interactive SVG Charts & Late Signing Audit

## Status

implemented

## Lane

normal

## Product Contract

The application should replace static/legacy progress bars with custom, responsive, interactive SVG charts (SVG Donut Chart for tax rate breakdown with center text readout and synchronization, and SVG Horizontal Bar Chart for Top 5 vendors with hover tooltips and entrance width animations). Additionally, the system should implement a 5th smart audit rule: Late Signing Compliance warning, which highlights XML invoices signed more than 24 hours after their creation date.

## Relevant Product Docs

- `01_constitution.md` (Principle 10: Dependency Minimalism - zero-library interactive SVGs)
- `docs/ARCHITECTURE.md`

## Acceptance Criteria

- [x] Parse `NgayKy`, `SigningTime`, or `NgayKyHDon` from XML invoices in `invoices/parser.py`.
- [x] Map and save `signing_date` in local database records.
- [x] Implement the 5th Smart Audit warning check in `invoices/service.py`: if `signing_date` differs from `date` by more than 24 hours, add warning.
- [x] Style SVG graphs, circles, rects, animations, and interactive tooltips in `static/css/style.css`.
- [x] Support responsive flex layout and tooltip element in `templates/invoices.html`.
- [x] Build SVG Bar chart renderer, SVG Donut chart renderer, dynamic tooltips, center readout text updating, and hover sync in `static/js/main.js`.
- [x] Write pytest test cases to verify valid vs. late signing XML documents.
- [x] Ensure all 56 tests pass with >70% coverage.

## Design Notes

- **Zero-Dependency SVG**: Using pure CSS and SVG DOM features for charts and tooltips.
- **Auditing Rule**: Complying with real-world tax audit practices for delayed signing (risk check).

## Validation

| Layer | Expected proof |
| --- | --- |
| Unit | `pytest tests/test_meinvoice.py::test_late_signing_audit` checks correct auditing warnings |
| Integration | Validation script runs successfully with 100% success and 78% code coverage |

## Harness Delta

N/A

## Evidence

- **`tests/test_meinvoice.py`**:
  - `test_late_signing_audit`: Verified that XML invoices signed within 24 hours generate no warnings, and XML invoices signed > 24 hours later trigger the warning *"Hóa đơn ký số chậm (Ngày lập: DD/MM/YYYY, Ngày ký: DD/MM/YYYY) - Rủi ro thuế và thời điểm kê khai."*
- **Test Integrity**: All 56 tests passed successfully.
