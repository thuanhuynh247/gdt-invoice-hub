# Story Specification: US-390 — Electronic Delivery Notes XML Sync & Validation Parser

## 📋 Context & Business Value
To support cross-checking goods movement against commercial invoicing under Decree 123, the system needs to synchronize, parse, and validate XML packages representing Electronic Delivery Notes (Phiếu xuất kho kiêm vận chuyển điện tử - PXK).

---

## 🎯 Acceptance Criteria
- **XML Parsing Engine**:
  - Parse electronic delivery notes (PXK) structured XML, extracting metadata fields: delivery note number (`SoPXK`), issue date (`NgayXuat`), warehouse dispatcher (`KhoXuat`), recipient warehouse (`KhoNhap`), driver name (`NguoiVanChuyen`), and transport vehicle (`PhuongTienVanChuyen`).
  - Extract SKU list items containing: SKU code (`MaHang`), item name (`TenHang`), unit (`DonViTinh`), and quantity (`SoLuong`).
- **Signature & Format Validation**:
  - Verify signature tag existence and format conformity. Return parsed structure as a serialized JSON dictionary if valid, or raise an error for malformed structures.

---

## 🛠️ Verification & Test Plan
- Run tests:
  ```powershell
  python scripts/harness_win.py validate --cmd "venv\Scripts\python -m pytest tests/test_v27_features.py -k test_delivery_notes_parsing"
  ```
