# Brainstorming Version 38: E-Delivery Note Reconciliation, Inventory Valuation & AI Logistics Cost Allocation Suite

## 1. Objectives & Compliance Context
Under Vietnamese Law (Decree 123/2020/NĐ-CP and Circular 78/2021/TT-BTC), the issuance of **Electronic Delivery Notes for Internal Transfers (Phiếu xuất kho kiêm vận chuyển điện tử)** and **Agency Goods Consignment Notes (Phiếu xuất kho gửi bán đại lý)** is strictly regulated. 
Specifically:
- Goods moved internally or sent to agents must be accompanied by these legal electronic documents.
- Official commercial e-invoices must be issued within prescribed timeframes (normally upon completion of sales or within 10 days of agent sales reports). Late invoicing triggers hefty administrative fines and risks CIT deductibility rejection of related transport costs.
- Furthermore, under VAS 02 (Vietnamese Accounting Standard 02 - Inventory), physical inventory and fixed asset cost bases must include directly attributable shipping/freight costs (logistics invoices).

Version 38 introduces a comprehensive reconciliation, validation, and cost allocation suite to ensure compliance and cost optimization.

---

## 2. Architectural Pillars

### Pillar A: Electronic Delivery Note (PXK) Parser & Reconciliation Engine (US-500)
- **Database Schema**: Add `DeliveryNote` database model with fields for `note_number`, `note_date`, `type` (`internal_transfer` or `agent_consignment`), `sender_mst`, `receiver_mst`, `transport_contract`, `status` (`Pending`, `Invoiced`, `Overdue`), and link to subsequent `Invoice`.
- **Relational Matching Engine**: Parse GDT-standard XML files for delivery notes (PXKKVCĐT & PXKGBHDL). Match delivery notes to corresponding commercial invoices based on product description, quantity, and contract references.
- **Late Invoicing Penalty Alert**: Track compliance with time limits. Flag transfers not invoiced within 10 days of shipping or agent sale report, calculating potential administrative penalties.

### Pillar B: E-Delivery Note Reconciliation & Timeline Dashboard (US-501, US-502)
- **Glassmorphic Command Center**: Visual grid showing all electronic delivery notes and their matched invoices.
- **Visual Compliance Badges**: Highlight "Matched", "Pending Invoice", "Partial Invoice", "Overdue Invoicing (>10 Days)".
- **Interactive Timeline**: Render a Gantt-like timeline tracking days elapsed between delivery note issuance and invoice signing date. Highlight potential CIT/VAT warning regions.

### Pillar C: AI Logistics Cost Allocation & Inventory Valuation Engine (US-503, US-504)
- **VAS 02 Cost Allocation Engine**: Relate transportation, freight, customs clearance, and warehouse storage invoices (logistics costs) to corresponding inventory purchase invoices.
- **AI Allocation Suggestion**: Match logistics line items to purchased item values using keyword similarity, date matching, and vendor relationships.
- **Inventory Valuation Adjuster**: Calculate updated cost bases including Allocated Logistics Expense, generating compliance audit reports ready for CIT defense.

### Pillar D: End-to-End Test Suite & Verification (US-505)
- **Pytest Suite**: Complete validation covering XML parser, matching logic, late invoice penalties, and AI cost allocation.
