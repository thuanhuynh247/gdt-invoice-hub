"""Auth routes for login, logout and session checks."""

from __future__ import annotations

import time
from datetime import datetime, timezone
import requests

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, session, url_for

from auth.captcha import fetch_captcha_payload, pop_prefetched_captcha
from auth.captcha_solver import solve_captcha_from_svg
from auth.crypto import encrypt_password, decrypt_password
from auth.service import AuthenticationError, authenticate_user, logout_user
from auth.security import rate_limit




auth_blueprint = Blueprint("auth", __name__)


def _session_expired() -> bool:
    """Return True when the stored session expiry timestamp has passed."""

    expires_at = session.get("expires_at")
    if not expires_at:
        return True
    return datetime.fromisoformat(expires_at) <= datetime.now(timezone.utc)


@auth_blueprint.get("/login")
def login_page():
    """Render the login form."""

    if session.get("logged_in"):
        return redirect(url_for("invoices.invoices_page"))
    return render_template("login.html")


@auth_blueprint.get("/signup")
def signup_page():
    """Render the signup form."""

    if session.get("logged_in"):
        return redirect(url_for("invoices.dashboard_page"))
    return render_template("signup.html")




@auth_blueprint.get("/api/auth/captcha")
@rate_limit(limit=30, window=60)
def auth_captcha():
    """Return captcha SVG and store the captcha key and cookies in session."""

    prefetched = None
    if current_app.config["AUTO_SOLVE_CAPTCHA"]:
        prefetched = pop_prefetched_captcha()

    if prefetched:
        captcha_payload = prefetched
        session["auth_captcha_key"] = captcha_payload["key"]
        session["auth_captcha_svg"] = captcha_payload["content"]
        session["auth_captcha_cookies"] = captcha_payload.get("cookies", {})
        session["auth_captcha_solved"] = captcha_payload.get("solved_text", "")
    else:
        captcha_payload = fetch_captcha_payload()
        session["auth_captcha_key"] = captcha_payload["key"]
        session["auth_captcha_svg"] = captcha_payload["content"]
        session["auth_captcha_cookies"] = captcha_payload.get("cookies", {})
        session.pop("auth_captcha_solved", None)

    return jsonify(
        {
            "image_svg": captcha_payload["content"],
            "mode": "mock" if current_app.config["GDT_USE_MOCK"] else "live",
            "auto_solve": current_app.config["AUTO_SOLVE_CAPTCHA"],
        }
    )


@auth_blueprint.get("/api/auth/captcha/stats")
def api_captcha_stats():
    """Expose real-time CAPTCHA solver statistics (US-143 / health dashboard)."""
    from auth.captcha_solver import captcha_analytics
    return jsonify(captcha_analytics.get_stats())


@auth_blueprint.post("/api/auth/login")
@rate_limit(limit=10, window=60)
def api_login():
    """Accept login credentials and create a local authenticated session."""

    payload = request.get_json(silent=True) or {}
    username = payload.get("username", "").strip()
    password = payload.get("password", "").strip()
    captcha = payload.get("captcha", "").strip()
    auto_solve_enabled = current_app.config["AUTO_SOLVE_CAPTCHA"]
    auth_data = None

    try:
        if auto_solve_enabled and (not captcha or captcha == "AUTO"):
            attempts = 5
            last_error = None
            current_captcha_svg = session.get("auth_captcha_svg", "")
            current_captcha_key = session.get("auth_captcha_key", "")
            current_captcha_cookies = session.get("auth_captcha_cookies", {})
            pre_solved = session.get("auth_captcha_solved", "")

            for attempt in range(attempts):
                if not current_captcha_svg or not current_captcha_key:
                    cached = pop_prefetched_captcha()
                    if cached:
                        current_captcha_svg = cached["content"]
                        current_captcha_key = cached["key"]
                        current_captcha_cookies = cached["cookies"]
                        pre_solved = cached.get("solved_text", "")
                    else:
                        try:
                            captcha_payload = fetch_captcha_payload()
                            current_captcha_svg = captcha_payload["content"]
                            current_captcha_key = captcha_payload["key"]
                            current_captcha_cookies = captcha_payload.get("cookies", {})
                            pre_solved = ""
                        except Exception as fetch_err:
                            last_error = AuthenticationError(f"Khong the tai captcha tu GDT: {fetch_err}")
                            continue

                try:
                    if pre_solved:
                        solved_value = pre_solved
                    else:
                        solved_value = solve_captcha_from_svg(current_captcha_svg, captcha_key=current_captcha_key)
                    current_app.logger.info(f"Auto-solved captcha attempt {attempt+1}: {solved_value}")
                except Exception as ocr_err:
                    current_app.logger.error(f"Failed to solve captcha: {ocr_err}")
                    current_captcha_svg = ""
                    current_captcha_key = ""
                    current_captcha_cookies = {}
                    pre_solved = ""
                    last_error = AuthenticationError(f"Loi giai ma captcha: {ocr_err}")
                    continue

                try:
                    auth_data = authenticate_user(
                        username,
                        password,
                        solved_value,
                        captcha_key=current_captcha_key,
                        captcha_cookies=current_captcha_cookies,
                    )
                    from auth.captcha_solver import captcha_analytics
                    captcha_analytics.record_success()
                    break
                except (AuthenticationError, requests.RequestException) as error:
                    last_error = error
                    msg = str(error)
                    
                    # Check if this is a permanent credential/lock error
                    is_permanent = False
                    msg_lower = msg.lower()
                    permanent_terms = [
                        "mật khẩu không đúng",
                        "tên đăng nhập hoặc mật khẩu",
                        "tài khoản không tồn tại",
                        "tài khoản đang bị khóa",
                        "tài khoản chưa đăng ký",
                        "locked",
                        "thong tin dang nhap va captcha khong du"
                    ]
                    for term in permanent_terms:
                        if term in msg_lower:
                            is_permanent = True
                            break
                    
                    if is_permanent:
                        current_app.logger.error(f"Permanent credential failure detected: {msg}. Aborting retry loop.")
                        raise error
                    
                    # Otherwise, it's a captcha error or transient network/GDT gateway error
                    current_app.logger.warning(
                        f"Auto-solve attempt {attempt+1} failed with transient error: {msg}. Retrying..."
                    )
                    
                    # Record fail in captcha analytics if it seems to be captcha-related
                    if "captcha" in msg_lower or isinstance(error, AuthenticationError):
                        from auth.captcha_solver import captcha_analytics
                        captcha_analytics.record_fail()
                        
                    current_captcha_svg = ""
                    current_captcha_key = ""
                    current_captcha_cookies = {}
                    pre_solved = ""
                    
                    if attempt < attempts - 1:
                        time.sleep(0.5)
            else:
                raise last_error or AuthenticationError(f"Tu dong giaima captcha that bai sau {attempts} lan thu.")
        else:
            auth_data = authenticate_user(
                username,
                password,
                captcha,
                captcha_key=session.get("auth_captcha_key", ""),
                captcha_cookies=session.get("auth_captcha_cookies", {}),
            )
    except AuthenticationError as error:
        from invoices.security_audit_service import log_security_event
        log_security_event("AUTH", f"User login failed: {error}", username=username)
        return jsonify({"error": str(error)}), 401


    session.clear()
    session.permanent = True
    session["logged_in"] = True
    session["username"] = auth_data["username"]
    session["encrypted_password"] = encrypt_password(password)
    session["login_time"] = auth_data["login_time"]
    session["expires_at"] = auth_data["expires_at"]
    session["session_token"] = auth_data["session_token"]
    session["jwt"] = auth_data["jwt"]
    session["tax_code"] = auth_data["profile"].get("mst")
    session["display_name"] = auth_data["profile"].get("display_name") or auth_data["username"]

    # Assign role based on username
    username_lower = auth_data["username"].lower()
    if username_lower == "admin":
        session["user_role"] = "admin"
    elif "auditor" in username_lower:
        session["user_role"] = "auditor"
    else:
        session["user_role"] = "viewer"

    from invoices.security_audit_service import log_security_event
    log_security_event(
        "AUTH",
        f"User logged in successfully (role: {session['user_role']})",
        username=session["username"],
        tax_code=session.get("tax_code"),
    )

    return jsonify(
        {
            "status": "success",
            "message": "Dang nhap thanh cong.",
            "expires_at": auth_data["expires_at"],
            "mode": "mock" if current_app.config["GDT_USE_MOCK"] else "live",
            "tax_code": auth_data["profile"].get("mst"),
        }
    )


@auth_blueprint.post("/api/auth/signup")
@rate_limit(limit=10, window=60)
def api_signup():
    """Register a new trial taxpayer profile and optionally seed mock invoices."""
    from datetime import timedelta

    payload = request.get_json(silent=True) or {}
    company_name = payload.get("company_name", "").strip()
    mst = payload.get("mst", "").strip()
    username = payload.get("username", "").strip()
    password = payload.get("password", "").strip()
    seed_mock_data = payload.get("seed_mock_data", True)

    if not all([company_name, mst, username, password]):
        return jsonify({"error": "Vui lòng nhập đầy đủ thông tin đăng ký."}), 400

    if len(mst) != 10 or not mst.isdigit():
        return jsonify({"error": "Mã số thuế phải gồm đúng 10 ký tự số."}), 400

    from invoices.models import TaxpayerProfile
    from extensions import db

    try:
        # Check if MST already exists
        existing_profile = db.session.get(TaxpayerProfile, mst)
        if existing_profile:
            return jsonify({"error": f"Doanh nghiệp với Mã số thuế {mst} đã được đăng ký."}), 400

        # Check if username already exists
        existing_username = TaxpayerProfile.query.filter_by(gdt_username=username).first()
        if existing_username:
            return jsonify({"error": f"Tên đăng nhập '{username}' đã được sử dụng bởi doanh nghiệp khác."}), 400

        # Create TaxpayerProfile
        new_profile = TaxpayerProfile(
            mst=mst,
            company_name=company_name,
            gdt_username=username,
            gdt_password_encrypted=encrypt_password(password),
            is_active=True,
            created_at=datetime.now(timezone.utc).isoformat()
        )
        db.session.add(new_profile)

        if seed_mock_data:
            _seed_mock_invoices_for_mst(mst, company_name)

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Signup error: {e}")
        return jsonify({"error": f"Có lỗi xảy ra trong quá trình đăng ký: {str(e)}"}), 500

    # Auto-login after successful registration
    session.clear()
    session.permanent = True
    session["logged_in"] = True
    session["username"] = username
    session["encrypted_password"] = encrypt_password(password)
    session["login_time"] = datetime.now(timezone.utc).isoformat()
    session["expires_at"] = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
    session["session_token"] = f"mock-session-{username.lower()}"
    session["jwt"] = None
    session["tax_code"] = mst
    session["display_name"] = company_name
    session["user_role"] = "viewer"

    from invoices.security_audit_service import log_security_event
    log_security_event(
        "AUTH",
        f"Trial user signed up & logged in (role: {session['user_role']})",
        username=username,
        tax_code=mst,
    )

    return jsonify(
        {
            "status": "success",
            "message": "Đăng ký tài khoản dùng thử thành công.",
            "expires_at": session["expires_at"],
            "mode": "mock",
            "tax_code": mst,
        }
    )


def _seed_mock_invoices_for_mst(mst: str, company_name: str):
    """Seed purchase and sales invoices for mock dashboard experience."""
    from invoices.models import Invoice, LineItem
    from extensions import db
    from datetime import datetime, timedelta

    # 7 Purchase entries with different expense categories
    categories_and_items = [
        {"category": "Chi phí văn phòng", "seller": "Công ty Cổ phần Văn phòng phẩm Hồng Hà", "seller_mst": "0100100101", "item": "Giấy in A4 Double A 70gsm & Văn phòng phẩm tổng hợp", "price": 450000.0, "qty": 10.0},
        {"category": "Nguyên vật liệu", "seller": "Tổng Công ty Thép Việt Nam - CTCP", "seller_mst": "0100100102", "item": "Thép xây dựng Hòa Phát phi 10", "price": 15000000.0, "qty": 2.0},
        {"category": "Chi phí vận chuyển", "seller": "Công ty Cổ phần Giao Hàng Tiết Kiệm", "seller_mst": "0100100103", "item": "Dịch vụ chuyển phát nhanh hàng hóa", "price": 1250000.0, "qty": 4.0},
        {"category": "Chi phí điện nước", "seller": "Tổng Công ty Điện lực miền Bắc EVN", "seller_mst": "0100100104", "item": "Hóa đơn tiền điện năng tiêu thụ tháng 05/2026", "price": 8450000.0, "qty": 1.0},
        {"category": "Chi phí tiếp khách", "seller": "Nhà hàng Sen Tây Hồ - Công ty F&B", "seller_mst": "0100100105", "item": "Chi phí tiệc tiếp khách hàng đối tác", "price": 3200000.0, "qty": 1.0},
        {"category": "Thiết bị công nghệ", "seller": "Công ty Cổ phần Thế Giới Di Động", "seller_mst": "0100100106", "item": "Laptop ASUS Zenbook OLED 14", "price": 18500000.0, "qty": 3.0},
        {"category": "Dịch vụ đám mây", "seller": "Công ty Cổ phần VNG Cloud", "seller_mst": "0100100107", "item": "Dịch vụ đám mây vServer Standard 2vCPU/8GB", "price": 5400000.0, "qty": 1.0},
        {"category": "Chi phí văn phòng", "seller": "Công ty TNHH Dịch vụ Vệ sinh Hoàn Mỹ", "seller_mst": "0100100108", "item": "Dịch vụ vệ sinh công nghiệp văn phòng", "price": 2500000.0, "qty": 2.0},
        {"category": "Chi phí vận chuyển", "seller": "Tổng Công ty Cổ phần Bưu chính Viettel", "seller_mst": "0100100109", "item": "Dịch vụ chuyển phát đường bộ liên tỉnh", "price": 9800000.0, "qty": 2.0},
    ]

    now = datetime.now()
    for i, entry in enumerate(categories_and_items):
        inv_date = (now - timedelta(days=i + 1)).strftime("%Y-%m-%d")
        number = f"0000{100 + i}"
        symbol = "C26TAA"
        inv_id = f"{entry['seller_mst']}-{symbol}-{number}"

        amount_before_tax = entry["price"] * entry["qty"]
        tax_amount = amount_before_tax * 0.10
        total_amount = amount_before_tax + tax_amount

        invoice = Invoice(
            id=inv_id,
            filename=f"invoice_{inv_id}.xml",
            invoice_type="Hóa đơn giá trị gia tăng",
            template_code="1",
            symbol=symbol,
            number=number,
            date=inv_date,
            currency="VND",
            seller_name=entry["seller"],
            seller_mst=entry["seller_mst"],
            seller_address="Hà Nội, Việt Nam",
            buyer_name=company_name,
            buyer_mst=mst,
            amount_before_tax=amount_before_tax,
            tax_amount=tax_amount,
            total_amount=total_amount,
            has_signature=True,
            signing_date=inv_date,
            payment_method="Chuyển khoản",
            imported_at=datetime.now(timezone.utc).isoformat(),
            import_status="imported",
            invoice_status="Gốc",
            taxpayer_mst=mst,
            ai_audited=True,
            t_score=100,
            t_rating="A++"
        )

        line_item = LineItem(
            item_name=entry["item"],
            unit="Cái" if entry["qty"] > 1 else "Lần",
            quantity=entry["qty"],
            unit_price=entry["price"],
            amount_before_tax=amount_before_tax,
            tax_rate="10%",
            tax_amount=tax_amount,
            expense_category=entry["category"],
            amount_after_tax=total_amount
        )
        invoice.items.append(line_item)
        db.session.add(invoice)

    # 3 Sales (Bán ra) - where taxpayer_mst is seller_mst, buyer is client
    clients = [
        {"name": "Công ty TNHH Đầu tư An Phát", "mst": "0311223344", "price": 45000000.0, "qty": 1.0, "item": "Dịch vụ tư vấn tối ưu hóa quy trình tài chính gói Gold"},
        {"name": "Công ty Cổ phần Công nghệ Sao Bắc Đẩu", "mst": "0311223355", "price": 120000000.0, "qty": 1.0, "item": "Xây dựng hệ thống phần mềm quản lý kho bãi"},
        {"name": "Ngân hàng TMCP Ngoại thương Việt Nam (Vietcombank)", "mst": "0100112437", "price": 60000000.0, "qty": 2.0, "item": "Bản quyền phần mềm phân tích XML chuyên sâu"},
    ]

    for i, client in enumerate(clients):
        inv_date = (now - timedelta(days=2 * i + 2)).strftime("%Y-%m-%d")
        number = f"0000{500 + i}"
        symbol = "C26TBB"
        inv_id = f"{mst}-{symbol}-{number}"

        amount_before_tax = client["price"] * client["qty"]
        tax_amount = amount_before_tax * 0.10
        total_amount = amount_before_tax + tax_amount

        invoice = Invoice(
            id=inv_id,
            filename=f"invoice_{inv_id}.xml",
            invoice_type="Hóa đơn giá trị gia tăng",
            template_code="1",
            symbol=symbol,
            number=number,
            date=inv_date,
            currency="VND",
            seller_name=company_name,
            seller_mst=mst,
            seller_address="Hồ Chí Minh, Việt Nam",
            buyer_name=client["name"],
            buyer_mst=client["mst"],
            buyer_address="Hà Nội, Việt Nam",
            amount_before_tax=amount_before_tax,
            tax_amount=tax_amount,
            total_amount=total_amount,
            has_signature=True,
            signing_date=inv_date,
            payment_method="Chuyển khoản",
            imported_at=datetime.now(timezone.utc).isoformat(),
            import_status="imported",
            invoice_status="Gốc",
            taxpayer_mst=mst,
            ai_audited=True,
            t_score=100,
            t_rating="A++"
        )

        line_item = LineItem(
            item_name=client["item"],
            unit="Hợp đồng" if "Hợp đồng" in client["item"] else "Lần",
            quantity=client["qty"],
            unit_price=client["price"],
            amount_before_tax=amount_before_tax,
            tax_rate="10%",
            tax_amount=tax_amount,
            expense_category="Doanh thu dịch vụ",
            amount_after_tax=total_amount
        )
        invoice.items.append(line_item)
        db.session.add(invoice)


@auth_blueprint.post("/api/auth/logout")
def api_logout():
    """Clear the session and return a JSON success response."""

    username = session.get("username", "unknown")
    tax_code = session.get("tax_code")
    from invoices.security_audit_service import log_security_event
    log_security_event("AUTH", "User logged out.", username=username, tax_code=tax_code)

    logout_user(session.get("jwt"))
    session.clear()
    return jsonify({"status": "success", "message": "Da dang xuat."})


@auth_blueprint.get("/api/session-status")
def session_status():
    """Expose session state for the frontend timeout and redirect logic."""

    if not session.get("logged_in"):
        return jsonify({"logged_in": False, "expires_in": 0})

    if _session_expired():
        session.clear()
        return jsonify({"logged_in": False, "expires_in": 0, "expired": True}), 401

    expires_at = datetime.fromisoformat(session["expires_at"])
    remaining_seconds = int((expires_at - datetime.now(timezone.utc)).total_seconds())
    return jsonify(
        {
            "logged_in": True,
            "username": session.get("display_name") or session["username"],
            "tax_code": session.get("tax_code"),
            "role": session.get("user_role", "viewer"),
            "expires_in": max(0, remaining_seconds),
            "warning_threshold_seconds": 60,
        }
    )


@auth_blueprint.before_app_request
def load_session_to_config():
    """Load credentials and token from session to current_app config and thread-local context.
    
    This ensures that downstream API callers in the current request thread
    can inspect and decrypt credentials if a 401 Unauthorized is returned
    by GDT, triggering automatic transparent re-authentication.
    """
    if session.get("logged_in"):
        jwt = session.get("jwt")
        username = session.get("username")
        enc_password = session.get("encrypted_password")
        
        current_app.config["CURRENT_JWT"] = jwt
        current_app.config["CURRENT_USERNAME"] = username
        current_app.config["CURRENT_ENCRYPTED_PASSWORD"] = enc_password
        
        try:
            from invoices.thread_local import set_current_thread_credentials
            set_current_thread_credentials(username, enc_password, jwt=jwt)
        except ImportError:
            pass


@auth_blueprint.teardown_app_request
def clear_config_credentials(exception=None):
    """Clean credentials from config and thread-local context after request completes."""
    # Prevent leaking passwords in application config across requests
    current_app.config.pop("CURRENT_JWT", None)
    current_app.config.pop("CURRENT_USERNAME", None)
    current_app.config.pop("CURRENT_ENCRYPTED_PASSWORD", None)
    try:
        from invoices.thread_local import clear_thread_local_context
        clear_thread_local_context()
    except ImportError:
        pass

