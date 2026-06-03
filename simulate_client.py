import requests

session = requests.Session()

# 1. Login
login_res = session.post("http://127.0.0.1:5000/api/auth/login", json={
    "username": "admin",
    "password": "admin123",
    "captcha": "1234"
})
print("Login status:", login_res.status_code)
print("Login response:", login_res.text)

# 2. Get /invoices
invoices_res = session.get("http://127.0.0.1:5000/invoices")
print("Invoices status:", invoices_res.status_code)
print("Invoices response (first 500 chars):", invoices_res.text[:500])

# 3. Get /advanced-audit
audit_res = session.get("http://127.0.0.1:5000/advanced-audit")
print("Advanced Audit status:", audit_res.status_code)
print("Advanced Audit response (first 500 chars):", audit_res.text[:500])
