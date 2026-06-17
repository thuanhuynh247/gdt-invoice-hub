"""Live GDT integration smoke test.

Tests the real connection to hoadondientu.gdt.gov.vn:
  1. Fetch captcha SVG + cookies
  2. Solve captcha offline with ddddocr
  3. Attempt login via smart-invoice API endpoint

Run: venv\Scripts\python.exe scripts\test_live_gdt_api.py
"""

import os
import sys
import json

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force live mode
os.environ["GDT_USE_MOCK"] = "false"
os.environ["TESTING"] = "True"
os.environ["OPENBLAS_NUM_THREADS"] = "1"

SEPARATOR = "=" * 70


def main():
    print(SEPARATOR)
    print("  GDT Live Integration Smoke Test")
    print(SEPARATOR)

    # --- Step 1: Direct request to GDT captcha endpoint ---
    print("\n[STEP 1] Kết nối trực tiếp tới GDT captcha API...")
    import requests

    gdt_base = os.getenv("GDT_BASE_URL", "https://hoadondientu.gdt.gov.vn")
    captcha_url = f"{gdt_base}/api/captcha"

    try:
        resp = requests.get(captcha_url, timeout=15)
        print(f"  HTTP Status: {resp.status_code}")
        print(f"  Response Headers (Content-Type): {resp.headers.get('Content-Type', 'N/A')}")

        if resp.status_code == 200:
            data = resp.json()
            captcha_key = data.get("key", "")
            captcha_svg = data.get("content", "")
            cookies = resp.cookies.get_dict()

            print(f"  ✅ Captcha key: {captcha_key[:30]}...")
            print(f"  ✅ SVG content length: {len(captcha_svg)} chars")
            print(f"  ✅ Cookies received: {list(cookies.keys())}")

            # Show first 200 chars of SVG
            print(f"  SVG preview: {captcha_svg[:200]}...")
        else:
            print(f"  ❌ GDT trả về lỗi: {resp.status_code}")
            print(f"  Response body: {resp.text[:500]}")
            return
    except requests.exceptions.ConnectionError as e:
        print(f"  ❌ Không kết nối được tới GDT: {e}")
        return
    except requests.exceptions.Timeout:
        print(f"  ❌ GDT không phản hồi trong 15 giây")
        return
    except Exception as e:
        print(f"  ❌ Lỗi không xác định: {e}")
        return

    # --- Step 2: Solve captcha offline ---
    print(f"\n[STEP 2] Giải captcha bằng ddddocr (offline solver)...")
    try:
        from auth.captcha_solver import solve_captcha_from_svg, captcha_analytics
        solved = solve_captcha_from_svg(captcha_svg)
        stats = captcha_analytics.get_stats()
        print(f"  ✅ Captcha đã giải: '{solved}'")
        print(f"  Latency trung bình: {stats['average_latency_seconds']}s")
    except Exception as e:
        print(f"  ❌ Không giải được captcha: {e}")
        solved = None

    # --- Step 3: Attempt login via GDT authenticate endpoint ---
    if solved:
        print(f"\n[STEP 3] Thử đăng nhập vào GDT với captcha '{solved}'...")

        username = os.getenv("GDT_USERNAME", "0316459946")
        password = os.getenv("GDT_PASSWORD", "12345678aA@")

        auth_url = f"{gdt_base}/api/security-taxpayer/authenticate"
        auth_payload = {
            "username": username,
            "password": password,
            "cvalue": solved,
            "ckey": captcha_key,
        }

        try:
            auth_resp = requests.post(
                auth_url,
                json=auth_payload,
                cookies=cookies,
                timeout=15,
            )
            print(f"  HTTP Status: {auth_resp.status_code}")

            if auth_resp.status_code == 200:
                auth_data = auth_resp.json()
                jwt_token = auth_data.get("token") or auth_data.get("jwt")
                if jwt_token:
                    print(f"  ✅ JWT nhận được! (dài {len(jwt_token)} chars)")
                    print(f"  JWT preview: {jwt_token[:60]}...")
                else:
                    print(f"  ⚠️ Response 200 nhưng không có token field")
                    print(f"  Response keys: {list(auth_data.keys())}")
            else:
                try:
                    err_data = auth_resp.json()
                    msg = err_data.get("message") or err_data.get("error") or err_data.get("details", {})
                    print(f"  ❌ GDT từ chối: {msg}")
                except Exception:
                    print(f"  ❌ GDT từ chối: {auth_resp.text[:500]}")
        except Exception as e:
            print(f"  ❌ Lỗi khi gọi authenticate: {e}")
    else:
        print("\n[STEP 3] Bỏ qua — không có captcha đã giải")

    # --- Step 4: Test via Flask app internal endpoint ---
    print(f"\n[STEP 4] Kiểm tra qua Flask app (chế độ LIVE)...")
    try:
        os.environ["GDT_USE_MOCK"] = "false"
        from app import create_app
        app = create_app()
        app.config["GDT_USE_MOCK"] = False
        app.config["TESTING"] = True

        with app.test_client() as client:
            # Phase 1: Get captcha via /API/login
            resp1 = client.post("/API/login", json={
                "username": "0316459946",
                "password": "12345678aA@",
                "captcha": "",
                "key": "",
            })
            print(f"  /API/login Phase 1 status: {resp1.status_code}")

            if resp1.status_code == 200:
                phase1_data = resp1.get_json()
                key2 = phase1_data.get("key", "")
                svg2 = phase1_data.get("content", "")
                print(f"  ✅ Key: {key2[:30]}...")
                print(f"  ✅ SVG length: {len(svg2)} chars")

                # Solve this new captcha
                solved2 = solve_captcha_from_svg(svg2)
                print(f"  ✅ Captcha giải: '{solved2}'")

                # Phase 2: Attempt login
                resp2 = client.post("/API/login", json={
                    "username": "0316459946",
                    "password": "12345678aA@",
                    "captcha": solved2,
                    "key": key2,
                })
                print(f"  /API/login Phase 2 status: {resp2.status_code}")

                if resp2.status_code == 200:
                    token2 = resp2.data.decode("utf-8")
                    print(f"  ✅ TOKEN NHẬN ĐƯỢC! ({len(token2)} chars)")
                    print(f"  Token preview: {token2[:60]}...")
                else:
                    try:
                        err = resp2.get_json()
                        print(f"  ❌ Đăng nhập thất bại: {err.get('error', resp2.data.decode('utf-8')[:200])}")
                    except Exception:
                        print(f"  ❌ Đăng nhập thất bại: {resp2.data.decode('utf-8')[:200]}")
            else:
                print(f"  ❌ Phase 1 thất bại: {resp1.data.decode('utf-8')[:200]}")
    except Exception as e:
        print(f"  ❌ Lỗi Flask app: {e}")
        import traceback
        traceback.print_exc()

    print(f"\n{SEPARATOR}")
    print("  Kết thúc kiểm tra")
    print(SEPARATOR)


if __name__ == "__main__":
    main()
