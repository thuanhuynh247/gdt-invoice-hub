"""Authentication helpers for mock mode and future live integration."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import requests

from flask import current_app


class AuthenticationError(Exception):
    """Raised when login fails due to invalid credentials or captcha."""


def authenticate_user(
    username: str,
    password: str,
    captcha: str,
    captcha_key: str | None = None,
    captcha_cookies: dict | None = None,
) -> dict:
    """Authenticate a user against mock mode or a future live GDT integration."""

    if not username or not password or not captcha:
        raise AuthenticationError("Thong tin dang nhap va captcha khong du.")

    if current_app.config["GDT_USE_MOCK"]:
        if username.lower() == "locked":
            raise AuthenticationError("Tai khoan tam thoi khong the dang nhap.")
        return _build_mock_session_payload(username)

    return _authenticate_live(
        username,
        password,
        captcha,
        captcha_key=captcha_key,
        captcha_cookies=captcha_cookies,
    )


def _build_mock_session_payload(username: str) -> dict:
    """Create deterministic session metadata for local development."""

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=30)
    return {
        "username": username,
        "login_time": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "session_token": f"mock-session-{username.lower()}",
        "jwt": None,
        "profile": {"display_name": username, "mst": None},
    }


def _authenticate_live(
    username: str,
    password: str,
    captcha: str,
    captcha_key: str | None = None,
    captcha_cookies: dict | None = None,
) -> dict:
    """Authenticate against the real taxpayer endpoint using manual captcha."""

    key = captcha_key or current_app.config.get("CURRENT_CAPTCHA_KEY") or ""
    cookies = captcha_cookies or current_app.config.get("CURRENT_CAPTCHA_COOKIES") or {}
    if not key:
        raise AuthenticationError("Captcha da het han. Vui long tai lai captcha.")

    from auth.gdt_client import gdt_request
    response = gdt_request(
        "POST",
        "api/security-taxpayer/authenticate",
        json={
            "username": username,
            "password": password,
            "cvalue": captcha,
            "ckey": key,
        },
        cookies=cookies,
    )

    if response.status_code >= 400:
        _raise_api_error(response)

    data = response.json()
    jwt_token = data.get("token") or data.get("jwt")
    if not jwt_token:
        raise AuthenticationError("Dang nhap thanh cong nhung khong nhan duoc JWT tu he thong thue.")

    # Commit dynamic CAPTCHA signatures on successful validation from GDT
    try:
        from auth.captcha_solver import commit_learned_signatures
        commit_learned_signatures(key)
    except Exception as e:
        current_app.logger.error(f"Failed to commit learned CAPTCHA signatures: {e}")

    profile = _fetch_profile(jwt_token)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=30)

    return {
        "username": username,
        "login_time": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "session_token": jwt_token,
        "jwt": jwt_token,
        "profile": profile,
    }


def _fetch_profile(jwt_token: str) -> dict:
    """Load taxpayer profile after successful authentication."""

    from auth.gdt_client import gdt_request
    response = gdt_request(
        "GET",
        "api/security-taxpayer/profile",
        headers={
            "Authorization": f"Bearer {jwt_token}",
        },
    )
    if response.status_code >= 400:
        _raise_api_error(response)
    data = response.json()
    return {
        "display_name": data.get("fullName") or data.get("ten") or data.get("username"),
        "mst": data.get("groupId") or data.get("mst"),
        "raw": data,
    }


def logout_user(jwt_token: str | None) -> None:
    """Try to notify the remote system that the session should be closed."""

    if current_app.config["GDT_USE_MOCK"] or not jwt_token:
        return

    try:
        from auth.gdt_client import gdt_request
        gdt_request(
            "GET",
            "api/security-taxpayer/logout",
            headers={
                "Authorization": f"Bearer {jwt_token}",
            },
        )
    except requests.RequestException:
        return


def _raise_api_error(response: requests.Response) -> None:
    """Normalize upstream API errors into AuthenticationError messages."""

    try:
        payload = response.json()
    except ValueError as error:
        raise AuthenticationError("Khong the doc phan hoi tu he thong thue.") from error

    details = payload.get("details")
    if isinstance(details, dict) and details:
        flattened = ", ".join(f"{key}: {value}" for key, value in details.items())
        raise AuthenticationError(flattened)

    message = payload.get("message") or payload.get("error") or "Dang nhap that bai."
    raise AuthenticationError(message)


def auto_refresh_gdt_session() -> bool:
    """Attempt to transparently re-authenticate using encrypted credentials.

    Looks up credentials in the thread local storage first (for parallel workers),
    then the Flask session (for request threads), and falls back to current_app.config.
    """
    username = None
    encrypted_pass = None

    # 0. Try Thread-Local Storage first
    try:
        from invoices.thread_local import get_current_thread_credentials
        tl_username, tl_pass, _ = get_current_thread_credentials()
        if tl_username and tl_pass:
            username = tl_username
            encrypted_pass = tl_pass
    except ImportError:
        pass

    if not username or not encrypted_pass:
        # 1. Try Flask Session
        try:
            from flask import session
            username = session.get("username")
            encrypted_pass = session.get("encrypted_password")
        except RuntimeError:
            # Outside request context (e.g. background threads or celery tasks)
            pass

    # 2. Fall back to current_app config
    if not username or not encrypted_pass:
        username = current_app.config.get("CURRENT_USERNAME")
        encrypted_pass = current_app.config.get("CURRENT_ENCRYPTED_PASSWORD")

    if not username or not encrypted_pass:
        current_app.logger.warning("Auto-refresh skipped: no credentials found.")
        return False

    try:
        from auth.crypto import decrypt_password
        password = decrypt_password(encrypted_pass)
    except Exception as decrypt_err:
        current_app.logger.error(f"Auto-refresh failed: Decryption error: {decrypt_err}")
        return False

    # Standard auto-solve CAPTCHA login flow
    from auth.captcha import pop_prefetched_captcha, fetch_captcha_payload
    from auth.captcha_solver import solve_captcha_from_svg
    from auth.service import authenticate_user, AuthenticationError

    attempts = 5
    last_error = None

    current_app.logger.info(f"Triggering auto-refresh for taxpayer: {username}...")

    for attempt in range(attempts):
        cached = pop_prefetched_captcha()
        if cached:
            captcha_svg = cached["content"]
            captcha_key = cached["key"]
            captcha_cookies = cached["cookies"]
            pre_solved = cached.get("solved_text", "")
        else:
            try:
                captcha_payload = fetch_captcha_payload()
                captcha_svg = captcha_payload["content"]
                captcha_key = captcha_payload["key"]
                captcha_cookies = captcha_payload.get("cookies", {})
                pre_solved = ""
            except Exception as fetch_err:
                last_error = fetch_err
                continue

        try:
            if pre_solved:
                solved_value = pre_solved
            else:
                solved_value = solve_captcha_from_svg(captcha_svg, captcha_key=captcha_key)
        except Exception as ocr_err:
            last_error = ocr_err
            continue

        try:
            auth_data = authenticate_user(
                username,
                password,
                solved_value,
                captcha_key=captcha_key,
                captcha_cookies=captcha_cookies,
            )
            from auth.captcha_solver import captcha_analytics
            captcha_analytics.record_success()

            # Update session variables if we are in a request context
            try:
                from flask import session
                session["logged_in"] = True
                session["username"] = auth_data["username"]
                session["login_time"] = auth_data["login_time"]
                session["expires_at"] = auth_data["expires_at"]
                session["session_token"] = auth_data["session_token"]
                session["jwt"] = auth_data["jwt"]
                session["tax_code"] = auth_data["profile"].get("mst")
                session["display_name"] = auth_data["profile"].get("display_name") or auth_data["username"]
            except RuntimeError:
                pass

            # Update current app configuration (active for this thread)
            current_app.config["CURRENT_JWT"] = auth_data["jwt"]
            try:
                from invoices.thread_local import set_current_thread_jwt
                set_current_thread_jwt(auth_data["jwt"])
            except ImportError:
                pass
            current_app.logger.info("Auto-refresh session completed successfully.")
            return True
        except (AuthenticationError, requests.RequestException) as auth_err:
            last_error = auth_err
            msg = str(auth_err)
            
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
                current_app.logger.error(f"Auto-refresh permanent credential failure: {msg}. Aborting refresh.")
                break
                
            current_app.logger.warning(
                f"Auto-refresh attempt {attempt+1} failed with transient error: {msg}. Retrying..."
            )
            
            if "captcha" in msg_lower or isinstance(auth_err, AuthenticationError):
                from auth.captcha_solver import captcha_analytics
                captcha_analytics.record_fail()
                
            if attempt < attempts - 1:
                import time
                time.sleep(0.5)

    current_app.logger.error(f"Auto-refresh failed after {attempts} attempts: {last_error}")
    return False

