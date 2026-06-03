# 🛡️ Harness v0 Enabled

This repository uses **Harness v0** for agent-driven software development. 
Before making any changes to the codebase, all agents MUST read:
- [Agent Operating Guide (AGENTS.md)](file:///d:/LearnAnyThing/Webapp%20XML/AGENTS.md)
- [Human-Agent operating model (docs/HARNESS.md)](file:///d:/LearnAnyThing/Webapp%20XML/docs/HARNESS.md)
- [Feature Intake & Risk Classification (docs/FEATURE_INTAKE.md)](file:///d:/LearnAnyThing/Webapp%20XML/docs/FEATURE_INTAKE.md)

---

# Invoice Download Webapp

Local Flask webapp de dang nhap, tra cuu hoa don, tai XML va xuat Excel theo spec-kit `INVOICE-WEBAPP-PLAN-A`.

## Current Status

- Applying PLAYBOOK 1: Environment Setup
- Applying PLAYBOOK 3: Da xac minh captcha, auth JWT va invoice list endpoints ngay `2026-05-21`
- Applying PLAYBOOK 4-5: App da chay duoc o mock mode va da co live login + live invoice list foundation

## Features Available Now

- Dang nhap local mock session
- Dang nhap live bang captcha thu cong tu he thong thue
- Tra cuu hoa don theo khoang ngay
- Chon danh sach `mua vao` hoac `ban ra`
- Loc hoa don huy
- Tai XML live theo contract production bundle
- Xuat Excel
- Session status va logout

## Live Mode

1. Mo `.env`
2. Dat:
   ```env
   GDT_USE_MOCK=false
   ```
3. Chay lai app
4. Login se hien captcha that tu `gdt.gov.vn`

Luu y:
- XML live hien la best-effort integration theo production bundle. Can test bang tai khoan that de xac nhan chinh xac tren hoa don that.
- Route XML chi hoat dong khi dong hoa don co `hsgoc` trong du lieu tra ve.

## Project Structure

```text
auth/               Authentication routes and services
invoices/           Invoice routes, parsing and service layer
export/             Excel export logic
templates/          Flask HTML templates
static/             CSS and JavaScript
tests/              Pytest suite
docs/API_ANALYSIS.md
app.py
config.py
requirements.txt
```

## Setup

1. Tao virtual environment:
   ```powershell
   python -m venv venv
   ```
2. Kich hoat venv:
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
3. Cai dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
4. Tao file `.env`:
   ```powershell
   Copy-Item .env.example .env
   ```
5. Chay app:
   ```powershell
   python app.py
   ```
6. Mo `http://127.0.0.1:5000`.

## Testing

```powershell
pytest -q
```

## API Endpoints

- `GET /api/auth/captcha`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/session-status`
- `GET /api/invoices`
- `GET /api/cancelled-invoices`
- `GET /api/invoices/<invoice_id>/download`
- `GET /api/export-excel`

## Safety Notes

- Khong luu credential trong code.
- Mac dinh dung `GDT_USE_MOCK=true`.
- Live mode da ho tro manual captcha login va JWT bearer invoice list.
- Khong chuyen phan XML don le sang live mode cho toi khi capture du request contract that.

---

## 🌟 Release Notes: Version 3.0.0 Enterprise (2026-05)
- **Real-Time Synchronizer & SSE**: Background daemon that fetches new invoices continuously. Updates the UI in real-time via Server-Sent Events (SSE) and Glassmorphism toast notifications.
- **RAG-Enhanced Mitigation Generator**: Uses local FTS5 vector search against Law 48/2024 and Law 149/2025 to auto-inject precise legal citations into tax explanation letters.
- **FCT Auditor**: Automatically detects foreign contractor digital services (Google, AWS, Zoom) using MST prefix `900` and computes Form 01/NTNN withholding VAT & CIT.
- **Durable Validation**: Protected by 231 local automated unit and integration tests under the Harness v0 Agent workflow.

---

## 🚀 Release Notes: Version 3.1.0 "Autonomous Ecosystem" (2026-05)
- **Vision LLM OCR**: Integrated Multimodal AI (Gemini/LLaVA) to process, extract, and digitize paper invoices / receipts (`.jpg`, `.png`, `.pdf`) for full-spectrum accounting.
- **Automated Bank Reconciliation**: New matching engine automatically cross-references and matches banking CSV exports against >20M VND invoices, proactively flagging non-compliance / cash-payment risks.
- **Telegram/Zalo CFO Bot**: Background scheduler pushes highly formatted markdown summary reports to designated groups on a daily/weekly basis, containing real-time insights on Input VAT, FCT, and High-Risk items.
