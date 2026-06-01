"""UAT Smoke Test Script — Automated API Endpoint Verification.

Runs through all critical API endpoints to verify system readiness
before manual UAT begins. This is a pre-UAT gate check.

Usage:
    python scripts/uat_smoke_test.py
"""

from __future__ import annotations

import json
import sys
import time
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["TESTING"] = "True"
os.environ["GDT_USE_MOCK"] = "true"

from app import create_app

PASS = "✅ PASS"
FAIL = "❌ FAIL"
SKIP = "⏭️ SKIP"


def smoke_test():
    """Run all UAT smoke tests against the Flask test client."""
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    client = app.test_client()

    results = []
    start = time.time()

    def record(name: str, status: str, details: str = ""):
        results.append({"name": name, "status": status, "details": details})
        icon = status
        print(f"  {icon}  {name}" + (f" — {details}" if details else ""))

    print("=" * 70)
    print("🧪 UAT SMOKE TEST — GDT Invoice Hub v17.0.0")
    print("=" * 70)
    print()

    # ── 1. Health Check ──────────────────────────────────────────────
    print("📌 Module: SYSTEM HEALTH")
    resp = client.get("/health")
    if resp.status_code == 200 and resp.get_json().get("status") == "ok":
        record("GET /health", PASS, f"mode={resp.get_json().get('mode')}")
    else:
        record("GET /health", FAIL, f"status_code={resp.status_code}")

    # ── 2. Auth — Unauthenticated Access ────────────────────────────
    print("\n📌 Module: AUTHENTICATION")
    resp = client.get("/api/invoices")
    if resp.status_code == 401:
        record("GET /api/invoices (no auth)", PASS, "Correctly returns 401")
    else:
        record("GET /api/invoices (no auth)", FAIL, f"Expected 401, got {resp.status_code}")

    resp = client.get("/api/invoices/stats?from=2026-05-01&to=2026-05-31")
    if resp.status_code == 401:
        record("GET /api/invoices/stats (no auth)", PASS)
    else:
        record("GET /api/invoices/stats (no auth)", FAIL, f"Got {resp.status_code}")

    # ── 3. Landing page redirect ────────────────────────────────────
    resp = client.get("/", follow_redirects=False)
    if resp.status_code in (302, 301):
        record("GET / redirect", PASS, f"Redirects to login (HTTP {resp.status_code})")
    else:
        record("GET / redirect", FAIL, f"Expected redirect, got {resp.status_code}")

    # ── 4. Config endpoint ──────────────────────────────────────────
    resp = client.get("/api/config")
    if resp.status_code == 200 and "mock_mode" in resp.get_json():
        record("GET /api/config", PASS, f"mock_mode={resp.get_json()['mock_mode']}")
    else:
        record("GET /api/config", FAIL)

    # ── 5. Authenticated endpoints ──────────────────────────────────
    print("\n📌 Module: AUTHENTICATED API ENDPOINTS")
    with client.session_transaction() as sess:
        sess["logged_in"] = True
        sess["user_role"] = "admin"
        sess["username"] = "uat_admin"
        sess["display_name"] = "UAT Admin"
        sess["taxpayer_mst"] = "0109998887"
        sess["tax_code"] = "0109998887"

    # 5a. Invoice search
    resp = client.get("/api/invoices?from=2026-05-01&to=2026-05-31&direction=purchase")
    if resp.status_code == 200:
        data = resp.get_json()
        record("GET /api/invoices (authenticated)", PASS, f"total_count={data.get('total_count', 0)}")
    else:
        record("GET /api/invoices (authenticated)", FAIL, f"status={resp.status_code}")

    # 5b. Stats
    resp = client.get("/api/invoices/stats?from=2026-05-01&to=2026-05-31&direction=purchase")
    if resp.status_code == 200 and "total_spend" in resp.get_json():
        record("GET /api/invoices/stats", PASS)
    else:
        record("GET /api/invoices/stats", FAIL)

    # 5c. Partners
    resp = client.get("/api/partners?from=2026-05-01&to=2026-05-31")
    if resp.status_code == 200:
        record("GET /api/partners", PASS)
    else:
        record("GET /api/partners", FAIL)

    # ── 6. BCTC Compiler ────────────────────────────────────────────
    print("\n📌 Module: BCTC & STATUTORY REPORTING")
    balances = {
        "111": {"opening_debit": 1000, "opening_credit": 0, "debit_movement": 200, "credit_movement": 100, "closing_debit": 1100, "closing_credit": 0},
        "411": {"opening_debit": 0, "opening_credit": 1000, "debit_movement": 0, "credit_movement": 100, "closing_debit": 0, "closing_credit": 1100},
    }
    resp = client.post("/api/bctc/compile", json={
        "balances": balances,
        "mst": "0109998887",
        "company_name": "UAT SMOKE TEST COMPANY",
        "year": 2026,
    })
    if resp.status_code == 200 and "xml" in resp.get_json():
        xml = resp.get_json()["xml"]
        has_tag = "<BangCanDoiKeToan" in xml or "<HSoKhaiThue>" in xml
        record("POST /api/bctc/compile", PASS, f"XML generated ({len(xml)} chars), HTKK={has_tag}")
    else:
        record("POST /api/bctc/compile", FAIL, f"status={resp.status_code}")

    # 6b. Audit ledger
    resp = client.post("/api/bctc/audit-ledger", json={
        "balances": balances,
        "taxpayer_mst": "0109998887",
    })
    if resp.status_code == 200 and "compliance_score" in resp.get_json():
        record("POST /api/bctc/audit-ledger", PASS, f"compliance_score={resp.get_json()['compliance_score']}")
    else:
        record("POST /api/bctc/audit-ledger", FAIL)

    # ── 7. Tax Payment Slip & VietQR ────────────────────────────────
    print("\n📌 Module: TAX PAYMENT & VIETQR")
    resp = client.post("/api/payments/tax-slip", json={
        "tax_type": "vat",
        "amount": 15000000.0,
        "chapter_type": "domestic_private",
    })
    if resp.status_code == 200:
        data = resp.get_json()
        has_qr = data.get("vietqr_base64") is not None
        record("POST /api/payments/tax-slip", PASS, f"VietQR={'✓' if has_qr else '✗'}, XML={'✓' if 'xml' in data else '✗'}")
    else:
        record("POST /api/payments/tax-slip", FAIL)

    # ── 8. E-Commerce Sync ──────────────────────────────────────────
    print("\n📌 Module: E-COMMERCE SYNC")
    orders = [
        {"order_id": "UAT-ORD-001", "date": "2026-05-20", "gross_revenue": 500000.0, "commission_fee": 15000.0, "service_fee": 5000.0},
    ]
    resp = client.post("/api/ecommerce/sync", json={
        "orders": orders,
        "platform": "Shopee",
        "taxpayer_mst": "0109998887",
    })
    if resp.status_code == 200 and resp.get_json().get("status") == "success":
        record("POST /api/ecommerce/sync", PASS, f"invoices_created={resp.get_json().get('invoices_created', 0)}")
    else:
        record("POST /api/ecommerce/sync", FAIL, f"status={resp.status_code}")

    # ── 9. ERP Export ───────────────────────────────────────────────
    print("\n📌 Module: ERP EXPORT")
    resp = client.get("/api/erp/export/misa")
    if resp.status_code == 200 and resp.content_type and "spreadsheet" in resp.content_type:
        record("GET /api/erp/export/misa", PASS, f"size={len(resp.data)} bytes")
    else:
        record("GET /api/erp/export/misa", FAIL, f"status={resp.status_code}, type={resp.content_type}")

    resp = client.get("/api/erp/export/odoo")
    if resp.status_code == 200:
        record("GET /api/erp/export/odoo", PASS, f"size={len(resp.data)} bytes")
    else:
        record("GET /api/erp/export/odoo", FAIL)

    # ── 10. Page renders ────────────────────────────────────────────
    print("\n📌 Module: PAGE RENDERING")
    for path, name in [
        ("/invoices", "Invoices Dashboard"),
        ("/cashflow", "Cashflow Oracle"),
        ("/tax-bctc", "Tax & BCTC"),
        ("/harness", "Harness Control Center"),
    ]:
        resp = client.get(path)
        if resp.status_code == 200:
            record(f"GET {path} ({name})", PASS, f"size={len(resp.data)} bytes")
        else:
            record(f"GET {path} ({name})", FAIL, f"status={resp.status_code}")

    # ── 11. 404 Handler ─────────────────────────────────────────────
    print("\n📌 Module: ERROR HANDLING")
    resp = client.get("/api/nonexistent-endpoint")
    if resp.status_code == 404:
        record("GET /api/nonexistent (404)", PASS)
    else:
        record("GET /api/nonexistent (404)", FAIL)

    # ── Summary ─────────────────────────────────────────────────────
    elapsed = time.time() - start
    passed = sum(1 for r in results if r["status"] == PASS)
    failed = sum(1 for r in results if r["status"] == FAIL)
    skipped = sum(1 for r in results if r["status"] == SKIP)
    total = len(results)

    print()
    print("=" * 70)
    print(f"📊 KẾT QUẢ SMOKE TEST UAT")
    print(f"   Tổng: {total} | ✅ Passed: {passed} | ❌ Failed: {failed} | ⏭️ Skipped: {skipped}")
    print(f"   Thời gian: {elapsed:.2f}s")
    print("=" * 70)

    if failed > 0:
        print("\n⚠️  CÓ ENDPOINT THẤT BẠI — CẦN KHẮC PHỤC TRƯỚC KHI BẮT ĐẦU UAT THỦ CÔNG")
        for r in results:
            if r["status"] == FAIL:
                print(f"   ❌ {r['name']}: {r['details']}")
        return 1
    else:
        print("\n🎉 TẤT CẢ SMOKE TEST ĐỀU PASS — HỆ THỐNG SẴN SÀNG CHO UAT THỦ CÔNG!")
        return 0


if __name__ == "__main__":
    sys.exit(smoke_test())
