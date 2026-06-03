"""Auth routes for login, logout and session checks."""

from __future__ import annotations

from datetime import datetime, timezone

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
                        solved_value = solve_captcha_from_svg(current_captcha_svg)
                    current_app.logger.info(f"Auto-solved captcha attempt {attempt+1}: {solved_value}")
                except Exception as ocr_err:
                    current_app.logger.error(f"Failed to solve captcha: {ocr_err}")
                    current_captcha_svg = ""
                    current_captcha_key = ""
                    current_captcha_cookies = {}
                    pre_solved = ""
                    last_error = AuthenticationError(f"Loi giai ma captcha: {ocr_err}")
                    continue

                current_app.config["CURRENT_CAPTCHA_KEY"] = current_captcha_key
                current_app.config["CURRENT_CAPTCHA_COOKIES"] = current_captcha_cookies

                try:
                    auth_data = authenticate_user(username, password, solved_value)
                    from auth.captcha_solver import captcha_analytics
                    captcha_analytics.record_success()
                    break
                except AuthenticationError as error:
                    last_error = error
                    msg = str(error)
                    if "captcha" in msg.lower():
                        current_app.logger.warning(f"Auto-solve attempt {attempt+1} failed with captcha error. Retrying...")
                        from auth.captcha_solver import captcha_analytics
                        captcha_analytics.record_fail()
                        current_captcha_svg = ""
                        current_captcha_key = ""
                        current_captcha_cookies = {}
                        pre_solved = ""
                    else:
                        raise error
            else:
                raise last_error or AuthenticationError(f"Tu dong giaima captcha that bai sau {attempts} lan thu.")
        else:
            current_app.config["CURRENT_CAPTCHA_KEY"] = session.get("auth_captcha_key", "")
            current_app.config["CURRENT_CAPTCHA_COOKIES"] = session.get("auth_captcha_cookies", {})
            auth_data = authenticate_user(username, password, captcha)
    except AuthenticationError as error:
        from invoices.security_audit_service import log_security_event
        log_security_event("AUTH", f"User login failed: {error}", username=username)
        return jsonify({"error": str(error)}), 401
    finally:
        current_app.config["CURRENT_CAPTCHA_KEY"] = ""
        current_app.config["CURRENT_CAPTCHA_COOKIES"] = {}


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
    """Load credentials and token from session to current_app config.
    
    This ensures that downstream API callers in the current request thread
    can inspect and decrypt credentials if a 401 Unauthorized is returned
    by GDT, triggering automatic transparent re-authentication.
    """
    if session.get("logged_in"):
        current_app.config["CURRENT_JWT"] = session.get("jwt")
        current_app.config["CURRENT_USERNAME"] = session.get("username")
        current_app.config["CURRENT_ENCRYPTED_PASSWORD"] = session.get("encrypted_password")


@auth_blueprint.teardown_app_request
def clear_config_credentials(exception=None):
    """Clean credentials from config after request processing completes."""
    # Prevent leaking passwords in application config across requests
    current_app.config.pop("CURRENT_JWT", None)
    current_app.config.pop("CURRENT_USERNAME", None)
    current_app.config.pop("CURRENT_ENCRYPTED_PASSWORD", None)

