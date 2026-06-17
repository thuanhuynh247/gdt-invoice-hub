# Spec: US-500 — Electronic Delivery Note (PXK) Parser & Matcher Engine

## Status
completed

## Lane
normal

## Product Contract
The system provides a GDT-standard XML Electronic Delivery Note (Phiếu xuất kho kiêm vận chuyển điện tử & Phiếu xuất kho gửi bán hàng đại lý) parser and matches them to subsequent commercial invoices based on contract numbers, buyer/seller tax identification numbers, and line-item descriptions/quantities.

## Acceptance Criteria
- [x] Database model `DeliveryNote` stores note number, date, sender/receiver MST, type, status, and linked invoice.
- [x] Parser extracts electronic delivery notes from XML files.
- [x] Relational matching algorithm auto-detects subsequent commercial invoices for each delivery note.
- [x] Supports manual mapping of delivery notes to invoices.

## Validation
- `tests/test_v38_features.py::test_delivery_note_parsing`
- `tests/test_v38_features.py::test_delivery_note_invoice_matching`
