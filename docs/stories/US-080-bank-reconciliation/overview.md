# Overview: US-080 & US-081 AI-Powered Multi-Source Bank Reconciliation

## Current Behavior
Currently, meInvoice is extremely effective at crawling, normalizing, and auditing sales and purchase invoices (hóa đơn đầu vào và đầu ra). However, the actual bank transactions (bank collection and payments) that represent the actual cash settlement of these invoices exist in completely disjoint bank statements (Techcombank, Vietcombank, ACB). Corporate accountants must manually open the bank statements, look at each transaction amount and description, search for matching invoices in the system, and manually track what has been paid, what is outstanding, and whether there are cash discrepancies.

## Target Behavior
With US-080 & US-081, meInvoice transitions into a unified accounts ledger and reconciliation platform.
- **US-080**: Allows accountants to import statements (Techcombank, Vietcombank Excel/CSV) associated with specific taxpayer MSTs. The transactions are stored securely in a relational SQLite table and rendered on a gorgeous Glassmorphism dashboard.
- **US-081**: An intelligent AI Reconciliation Agent automatically executes a fuzzy matching algorithm. It parses the bank transfer remarks (Nội dung chuyển khoản), extracts invoice numbers or vendor name references, uses phonetic/keyword similarities to handle abbreviations, calculates match confidence, and pairs transactions with invoices.

## Affected Users
- **Corporate CFOs**: Need real-time cash ledger clarity and automated payment tracking.
- **Chief Accountants & Ledger Clerks**: Perform reconciliation, verify payments, and flag customer payment delays or short-payments.

## Affected Product Docs
- `docs/product/v5_roadmap.md` (New Roadmap entry)
- `docs/TEST_MATRIX.md` (Updated with bank reconciliation test vectors)

## Non-Goals
- Real-time direct bank API integrations (using bank scraper bots or tokens) which are highly unstable and violate Vietnamese banking security laws. We focus on standardized Excel/CSV ingestions and robust mock sandbox upload files.
- Automated bank payouts or wire transfers directly from our interface.
