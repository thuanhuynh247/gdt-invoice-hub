# Intent: MISA meInvoice Beater - Next-Gen GDT Invoice Hub

## Problem Statement & Context
- **[PRB-1] MISA Quota & License Lock-in**: Traditional software like MISA meInvoice (`meinvoice.vn`) charges per invoice quota, locks user data behind proprietary software, and forces costly annual renewals.
- **[PRB-2] Slow & Unreliable GDT Sync / CAPTCHA Blocking**: Users in Facebook groups (`hotromeinvoice`) frequently report CAPTCHA failure, session expiration, and slow manual background sync.
- **[PRB-3] Outdated Accounting Standards**: Existing tools rely on old Circular 200 guidelines and require accountants to manually map Debit/Credit accounts for every single line item.
- **[PRB-4] Missing Tax Deductibility Audit**: Accountants face severe tax audit risks because legacy systems do not automatically flag non-cash payment violations (invoices ≥ 20,000,000 VND under Circular 219).
- **[PRB-5] No International Standard (IFRS / Peppol)**: Cross-border enterprises cannot export structured invoice data compliant with global standards (Peppol EN 16931).
- **[PRB-6] Clunky & Slow User Experience**: Outdated desktop UI layouts slow down daily accounting workflows.

## Desired Outcomes
- **[OUT-1] 100% Free & Unlimited Self-Hosted Hub**: Zero fee per invoice, zero quota lock, unlimited storage.
- **[OUT-2] Autonomous AI CAPTCHA & Prefetch Worker**: Background worker pre-fetches solved CAPTCHA tokens for instant 1-click GDT login and sync.
- **[OUT-3] Automated TT 99/2025/TT-BTC Accounting Engine**: Smart double-entry GL journal voucher generator (Circular 99/2025/TT-BTC & TT 133/2016).
- **[OUT-4] Automated Decree 123 & Circular 219 Tax Audit**: Live compliance risk score (`A+` rating), non-cash payment warning banner for ≥20M VND transactions.
- **[OUT-5] Dual VAS & IFRS / Peppol BIS Billing 3.0 Export**: VCB Exchange Rate converter + EN 16931 global invoice interoperability.
- **[OUT-6] Wise Fintech Bento Grid Portal**: Dark glassmorphism header, 4-tab interactive switcher, 1-Click XML Copy, and CA Digital Signature audit.
