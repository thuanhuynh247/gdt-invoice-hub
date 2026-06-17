---
id: PRD-AUTH
type: prd
brd_goals:
  - BRD-G5
status: draft
lang: en
owner: Dev-Lead
version: 3.0.0
created: "2026-06-08"
updated: "2026-06-08"
personas:
  - "General Accountant"
scope: in
moscow: must
horizon: now
metrics:
  - "Captcha solve success rate (>90%)"
risks:
  - description: "GDT Portal changes its login form parameters or captcha structure."
    impact: high
    likelihood: med
    mitigation: "Use modular parser and browser-based Selenium fallback."
    status: open
competitive_parity: {}
---

# Authentication & Captcha Bypass — PRD PRD-AUTH

## Overview & Problem | Tổng quan và Vấn đề

Accountants need to log in to the GDT portal to download invoices, but login requires solving image-based Captchas, which is manual and slow. 

## Personas | Nhóm người dùng

* General Accountant

## Functional Requirements (MoSCoW) | Yêu cầu chức năng (MoSCoW)

### Must | Bắt buộc

* Support login credentials cache.
* Automatic Captcha solving using local OCR/neural models.
* Session recovery on expiration.

### Should | Nên có

* Provide manual Captcha input fallback in the web UI.

### Could | Có thể có

* Multi-account management.

### Won't (this round) | Không (lần này)

* Multi-factor authentication (MFA) bypass.

## Non-Functional Requirements | Yêu cầu phi chức năng

* Captcha solving must complete in under 5 seconds.
* Account passwords must be encrypted locally.
