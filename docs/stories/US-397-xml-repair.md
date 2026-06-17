# Story Specification: US-397 — Decree 123 XML Compliance Auditing & Auto-Repair Suite

## 📋 Context & Business Value
Under Decree 123/2020/ND-CP, e-invoice XML format correctness is strictly enforced. Schema misalignments, wrong MSTs, missing namespaces, and late signature timestamps cause compliance rejection. This suite audits invoice XML and automatically patches/repairs these issues, including signing with a mock HSM certificate.

---

## 🎯 Acceptance Criteria
- **XML Compliance Audit Engine**:
  - Check for valid/invalid XML structure, standard GDT namespace, and correct MST digit length (10 or 14 digits).
  - Verify cash payment limits (>= 20M VND) under Circular 80/2021/TT-BTC.
  - Detect late signature timing discrepancies (invoice date vs signing date).
- **XML Auto-Repair Suite**:
  - Clean non-numeric characters from seller/buyer MSTs.
  - Automatically convert TM (Cash) payment to CK (Bank transfer) for invoices >= 20M VND.
  - Re-order dynamic children of `<DLHDon>` (e.g. `<TTChung>`, `<NDHDon>`, `<TToan>`) to satisfy official XSD schema order.
  - Clear invalid signatures and append a fresh XMLDSig signature using a mock HSM certificate.
- **REST Endpoints**:
  - Expose `/api/compliance/xml-audit` and `/api/compliance/xml-auto-repair`.

---

## 🛠️ Verification & Test Plan
- Run tests:
  ```powershell
  venv\Scripts\python -m pytest tests/test_v28_features.py -k "test_xml_compliance_auditing or test_xml_auto_repair"
  ```
