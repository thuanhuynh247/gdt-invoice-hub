"""UAT Live API Integration Test — Runs against the live Flask server on port 5000."""

import requests
import sys

BASE = "http://127.0.0.1:5000"
results = []


def test(name, ok, detail=""):
    status = "PASS" if ok else "FAIL"
    results.append((name, status, detail))
    icon = "\u2705" if ok else "\u274c"
    suffix = f" -- {detail}" if detail else ""
    print(f"  {icon} {status}  {name}{suffix}")


print("=" * 65)
print("\U0001f9ea UAT LIVE API INTEGRATION TEST")
print("=" * 65)

# 1. Health
r = requests.get(f"{BASE}/health")
mode = r.json().get("mode", "?")
test("Health Check", r.status_code == 200, f"mode={mode}")

# 2. Login page renders with autofocus
r = requests.get(f"{BASE}/login")
has_af = "autofocus" in r.text
test("Login Page with Autofocus", r.status_code == 200 and has_af,
     "autofocus=found" if has_af else "autofocus=MISSING")

# 3. Captcha endpoint
r = requests.get(f"{BASE}/api/auth/captcha")
svg_ok = "<svg" in r.json().get("image_svg", "")
auto = r.json().get("auto_solve", False)
test("Captcha SVG Endpoint", r.status_code == 200 and svg_ok, f"auto_solve={auto}")

# 4. Login with wrong credentials -> mock mode accepts all, so test response structure
s1 = requests.Session()
s1.get(f"{BASE}/api/auth/captcha")
r = s1.post(f"{BASE}/api/auth/login",
            json={"username": "demo", "password": "wrong", "captcha": "1234"})
# In mock mode, all logins succeed. In live mode, wrong pw returns 401.
is_mock = r.status_code == 200 and r.json().get("mode") == "mock"
is_rejected = r.status_code == 401
test("Login Auth (mock accepts all)", is_mock or is_rejected,
     f"status={r.status_code}, mode={r.json().get('mode','?')}")

# 5. Login with correct credentials
s2 = requests.Session()
s2.get(f"{BASE}/api/auth/captcha")
r = s2.post(f"{BASE}/api/auth/login",
            json={"username": "admin", "password": "secret", "captcha": "AUTO"})
login_status = r.json().get("status", "?")
test("Login Success (admin creds)", r.status_code == 200, f"status={login_status}")

# 6. Session active
r = s2.get(f"{BASE}/api/session-status")
data = r.json()
test("Session Active (admin)", r.status_code == 200 and data.get("logged_in"),
     f"user={data.get('username')}, role={data.get('role')}")

# 7. Issue Invoice page has autofocus
r = s2.get(f"{BASE}/issue-invoice")
has_af2 = "autofocus" in r.text
test("Issue Invoice Page Autofocus", r.status_code == 200 and has_af2,
     "autofocus=found" if has_af2 else "autofocus=MISSING")

# 7b. Set active taxpayer MST (required for draft)
s2.post(f"{BASE}/api/profiles", json={
    "mst": "0108234857",
    "company_name": "UAT Test Company",
    "gdt_username": "admin",
    "gdt_password": "secret",
})
s2.post(f"{BASE}/api/profiles/switch", json={"mst": "0108234857"})

# 8. Issue invoice draft
r = s2.post(f"{BASE}/api/invoices/issue/draft", json={
    "buyer_mst": "0100234008",
    "buyer_name": "Viettel Telecom",
    "buyer_address": "So 1 Giang Van Minh, Ha Noi",
    "symbol": "1C26TYY",
    "items": [{
        "item_name": "Thiet bi dinh tuyen Cisco ISR 4331",
        "unit": "Cai",
        "quantity": 2,
        "unit_price": 15000000,
        "tax_rate": "10%",
    }],
})
inv_data = r.json().get("invoice", {})
inv_num = inv_data.get("number", "?")
inv_id = inv_data.get("id", "")
test("Issue Draft Invoice", r.status_code == 200 and r.json().get("status") == "success",
     f"number={inv_num}")

# 9. Digital signature
if inv_id:
    r = s2.post(f"{BASE}/api/invoices/issue/sign", json={"invoice_id": inv_id})
    signed_id = r.json().get("invoice_id", "?")
    test("Digital Signature (USB Token)", r.status_code == 200,
         f"invoice_id={signed_id}")
else:
    test("Digital Signature (USB Token)", False, "Skipped - no draft ID")

# 10. triggerInputError helper in main.js
r = s2.get(f"{BASE}/static/js/main.js")
has_trigger = "triggerInputError" in r.text
test("triggerInputError in main.js", has_trigger, "shake validation helper present")

# 11. Shake animation CSS (in style.css)
r = s2.get(f"{BASE}/static/css/style.css")
has_shake = "shakeError" in r.text
test("Shake Animation CSS", r.status_code == 200 and has_shake, "shakeError keyframes found")

# 12. Invoices Dashboard
r = s2.get(f"{BASE}/invoices")
test("Invoices Dashboard Loads", r.status_code == 200, f"size={len(r.text)} chars")

# 13. Cashflow Oracle
r = s2.get(f"{BASE}/cashflow")
test("Cashflow Oracle Loads", r.status_code == 200, f"size={len(r.text)} chars")

# 14. Tax & BCTC
r = s2.get(f"{BASE}/tax-bctc")
test("Tax & BCTC Page Loads", r.status_code == 200, f"size={len(r.text)} chars")

# 15. Logout
r = s2.post(f"{BASE}/api/auth/logout")
test("Logout", r.status_code == 200 and r.json().get("status") == "success")

# 16. Session cleared
r = s2.get(f"{BASE}/api/session-status")
test("Session Cleared After Logout", not r.json().get("logged_in"))

# Summary
passed = sum(1 for _, s, _ in results if s == "PASS")
failed = sum(1 for _, s, _ in results if s == "FAIL")
total = len(results)

print()
print("=" * 65)
print(f"\U0001f4ca RESULTS: Total={total} | \u2705 Passed={passed} | \u274c Failed={failed}")
if failed == 0:
    print("\U0001f389 ALL LIVE API TESTS PASSED!")
else:
    print("\u26a0\ufe0f  SOME TESTS FAILED - REVIEW REQUIRED")
print("=" * 65)

sys.exit(1 if failed else 0)
