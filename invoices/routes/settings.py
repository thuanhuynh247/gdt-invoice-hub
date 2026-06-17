from __future__ import annotations
from io import BytesIO
from flask import Blueprint, Response, current_app, jsonify, redirect, render_template, request, send_file, session, url_for
from export.excel import generate_excel_workbook, generate_local_excel_workbook
from invoices.parser import DateValidationError, validate_date_range
from invoices.service import (
    GDTIntegrationNotReadyError,
    InvoiceQuery,
    build_invoice_lookup,
    download_invoice_xml,
    fetch_invoices,
    resolve_live_download_name,
    fetch_invoice_line_items,
    extract_partners_from_invoices,
    generate_tax_usage_report,
)
from extensions import db
from auth.decorators import roles_required
import os
import uuid
import threading
from datetime import datetime
from flask import send_file
import io
from invoices.routes.shared import invoices_blueprint, DOWNLOAD_TASKS, DOWNLOAD_TASKS_LOCK
from invoices.routes.helpers import (
    _ensure_logged_in,
    get_supplier_pivot_data,
    _AGING_BUCKETS,
    classify_fct_item,
    generate_fct_excel,
    require_api_signature,
    get_harness_db,
    render_html_to_pdf
)

@invoices_blueprint.get("/api/settings")
@roles_required("admin", "auditor")
def api_get_settings():
    """Retrieve current scheduler and SMTP settings with masked passwords."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from invoices.scheduler import load_scheduler_settings
    settings = load_scheduler_settings()

    # Mask sensitive credentials
    if settings.get("smtp_pass"):
        settings["smtp_pass"] = "••••••••"
    if settings.get("gdt_password"):
        settings["gdt_password"] = "••••••••"
    if settings.get("ai_api_key"):
        settings["ai_api_key"] = "••••••••"
    if settings.get("telegram_bot_token"):
        settings["telegram_bot_token"] = "••••••••"
    if settings.get("gdrive_client_secret"):
        settings["gdrive_client_secret"] = "••••••••"
    if settings.get("gdrive_refresh_token"):
        settings["gdrive_refresh_token"] = "••••••••"
    if settings.get("onedrive_client_secret"):
        settings["onedrive_client_secret"] = "••••••••"
    # Mask sensitive credentials
    if settings.get("smtp_pass"):
        settings["smtp_pass"] = "••••••••"
    if settings.get("gdt_password"):
        settings["gdt_password"] = "••••••••"
    if settings.get("ai_api_key"):
        settings["ai_api_key"] = "••••••••"
    if settings.get("telegram_bot_token"):
        settings["telegram_bot_token"] = "••••••••"
    if settings.get("gdrive_client_secret"):
        settings["gdrive_client_secret"] = "••••••••"
    if settings.get("gdrive_refresh_token"):
        settings["gdrive_refresh_token"] = "••••••••"
    if settings.get("onedrive_client_secret"):
        settings["onedrive_client_secret"] = "••••••••"
    if settings.get("onedrive_refresh_token"):
        settings["onedrive_refresh_token"] = "••••••••"
    if settings.get("erp_auth_token"):
        settings["erp_auth_token"] = "••••••••"
    if settings.get("webhook_secret"):
        settings["webhook_secret"] = "••••••••"

    return jsonify(settings)

@invoices_blueprint.post("/api/settings")
@roles_required("admin")
def api_post_settings():
    """Save scheduler and SMTP settings."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    payload = request.get_json(silent=True) or {}

    try:
        smtp_port = int(payload.get("smtp_port", 587))
        schedule_weekday = int(payload.get("schedule_weekday", 0))
        realtime_interval = int(payload.get("realtime_sync_interval", 15))
    except ValueError:
        return jsonify({"error": "Dữ liệu cấu hình không hợp lệ."}), 400

    from invoices.scheduler import save_scheduler_settings
    save_scheduler_settings({
        "smtp_host": payload.get("smtp_host", "").strip(),
        "smtp_port": smtp_port,
        "smtp_user": payload.get("smtp_user", "").strip(),
        "smtp_pass": payload.get("smtp_pass", ""),
        "smtp_use_tls": bool(payload.get("smtp_use_tls", True)),
        "recipient_email": payload.get("recipient_email", "").strip(),
        "schedule_enabled": bool(payload.get("schedule_enabled", False)),
        "schedule_interval": payload.get("schedule_interval", "daily"),
        "schedule_time": payload.get("schedule_time", "08:00").strip(),
        "schedule_weekday": schedule_weekday,
        "gdt_username": payload.get("gdt_username", "").strip(),
        "gdt_password": payload.get("gdt_password", ""),
        "ai_enabled": bool(payload.get("ai_enabled", False)),
        "ai_provider": payload.get("ai_provider", "ollama").strip(),
        "ai_ollama_endpoint": payload.get("ai_ollama_endpoint", "http://localhost:11434").strip(),
        "ai_api_key": payload.get("ai_api_key", ""),
        "ai_model_name": payload.get("ai_model_name", "gemma-4").strip(),
        "ai_system_prompt": payload.get("ai_system_prompt", "").strip(),
        "telegram_enabled": bool(payload.get("telegram_enabled", False)),
        "telegram_bot_token": payload.get("telegram_bot_token", ""),
        "telegram_chat_id": payload.get("telegram_chat_id", "").strip(),
        "audit_agent_enabled": bool(payload.get("audit_agent_enabled", False)),
        "audit_agent_schedule_time": payload.get("audit_agent_schedule_time", "23:00").strip(),
        "gdrive_enabled": bool(payload.get("gdrive_enabled", False)),
        "gdrive_client_id": payload.get("gdrive_client_id", "").strip(),
        "gdrive_client_secret": payload.get("gdrive_client_secret", ""),
        "gdrive_refresh_token": payload.get("gdrive_refresh_token", ""),
        "gdrive_folder_id": payload.get("gdrive_folder_id", "").strip(),
        "onedrive_enabled": bool(payload.get("onedrive_enabled", False)),
        "onedrive_client_id": payload.get("onedrive_client_id", "").strip(),
        "onedrive_client_secret": payload.get("onedrive_client_secret", ""),
        "onedrive_refresh_token": payload.get("onedrive_refresh_token", ""),
        "onedrive_folder_path": payload.get("onedrive_folder_path", "HoaDon_DienTu").strip(),
        "erp_enabled": bool(payload.get("erp_enabled", False)),
        "erp_type": payload.get("erp_type", "none").strip(),
        "erp_api_url": payload.get("erp_api_url", "").strip(),
        "erp_auth_token": payload.get("erp_auth_token", ""),
        "realtime_sync_enabled": bool(payload.get("realtime_sync_enabled", False)),
        "realtime_sync_interval": realtime_interval,
        "webhook_enabled": bool(payload.get("webhook_enabled", False)),
        "webhook_url": payload.get("webhook_url", "").strip(),
        "webhook_secret": payload.get("webhook_secret", ""),
        "signature_filter_enabled": bool(payload.get("signature_filter_enabled", True)),
        "blacklist_filter_enabled": bool(payload.get("blacklist_filter_enabled", True))
    })

    from invoices.security_audit_service import log_security_event
    log_security_event("UPDATE", "Updated application settings (SMTP, scheduler, AI, cloud sync, ERP, and webhooks).")

    return jsonify({"status": "success", "message": "Đã lưu thiết lập thành công."})

@invoices_blueprint.get("/api/blacklist")
@roles_required("admin", "auditor")
def api_list_blacklist():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized
    from invoices.models import BlacklistedMST
    blacklist = BlacklistedMST.query.all()
    return jsonify([item.to_dict() for item in blacklist])

@invoices_blueprint.post("/api/blacklist")
@roles_required("admin", "auditor")
def api_add_blacklist():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized
    payload = request.json or {}
    mst = payload.get("mst", "").strip()
    reason = payload.get("reason", "").strip()
    if not mst:
        return jsonify({"error": "Mã số thuế không được để trống"}), 400
    
    from invoices.models import BlacklistedMST
    from extensions import db
    import datetime
    
    existing = db.session.get(BlacklistedMST, mst)
    if existing:
        existing.reason = reason
        existing.blacklisted_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        item = BlacklistedMST(
            mst=mst,
            reason=reason,
            blacklisted_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        db.session.add(item)
    db.session.commit()
    return jsonify({"status": "success", "message": "Đã thêm mã số thuế vào danh sách đen."})

@invoices_blueprint.delete("/api/blacklist/<mst>")
@roles_required("admin", "auditor")
def api_delete_blacklist(mst):
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized
    from invoices.models import BlacklistedMST
    from extensions import db
    
    item = db.session.get(BlacklistedMST, mst)
    if not item:
        return jsonify({"error": "Không tìm thấy mã số thuế trong danh sách đen."}), 404
        
    db.session.delete(item)
    db.session.commit()
    return jsonify({"status": "success", "message": "Đã xóa mã số thuế khỏi danh sách đen."})

@invoices_blueprint.post("/api/settings/test-email")
@roles_required("admin")
def api_test_email():
    """Trigger a manual test email with the provided SMTP parameters."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    payload = request.get_json(silent=True) or {}

    from invoices.scheduler import load_scheduler_settings, SchedulerThread
    current_settings = load_scheduler_settings()

    smtp_host = payload.get("smtp_host", "").strip()
    try:
        smtp_port = int(payload.get("smtp_port", 587))
    except ValueError:
        return jsonify({"error": "Cổng SMTP không hợp lệ."}), 400

    smtp_user = payload.get("smtp_user", "").strip()
    smtp_pass = payload.get("smtp_pass", "").strip()
    smtp_use_tls = payload.get("smtp_use_tls", True)
    recipient = payload.get("recipient_email", "").strip()

    if not smtp_host or not smtp_user or not recipient:
        return jsonify({"error": "Vui lòng nhập đầy đủ SMTP Host, SMTP User và Email nhận."}), 400

    # Retrieve existing encrypted password if they passed the mask
    if smtp_pass == "••••••••" or not smtp_pass:
        from auth.crypto import decrypt_password
        enc_pass = current_settings.get("smtp_pass", "")
        if enc_pass:
            try:
                smtp_pass = decrypt_password(enc_pass)
            except Exception:
                return jsonify({"error": "Không thể giải mã mật khẩu SMTP đã lưu."}), 500
        else:
            return jsonify({"error": "Mật khẩu SMTP trống."}), 400

    # Build a simple text test message
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    
    msg = MIMEMultipart()
    msg["From"] = smtp_user
    msg["To"] = recipient
    msg["Subject"] = "[GDT Invoice Hub] Kiểm tra kết nối SMTP thành công"
    msg.attach(MIMEText("Kết nối SMTP từ GDT Invoice Hub của bạn hoạt động bình thường!", "plain"))

    try:
        SchedulerThread.send_smtp_message(smtp_host, smtp_port, smtp_user, smtp_pass, smtp_use_tls, recipient, msg)
        return jsonify({"status": "success", "message": "Đã gửi email thử nghiệm thành công!"})
    except Exception as e:
        return jsonify({"error": f"Lỗi gửi email thử nghiệm: {str(e)}"}), 500

@invoices_blueprint.post("/api/settings/test-audit")
@roles_required("admin")
def api_test_audit():
    """Trigger a manual run of the autonomous AI audit agent immediately."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from invoices.scheduler import load_scheduler_settings, SchedulerThread
    settings = load_scheduler_settings()
    # Force audit agent to run synchronously by ignoring its scheduled time check
    thread = SchedulerThread(current_app)
    try:
        thread.execute_autonomous_audit(settings)
        return jsonify({"status": "success", "message": "Đã chạy kiểm toán tự động thành công!"})
    except Exception as e:
        return jsonify({"error": f"Lỗi chạy kiểm toán tự động: {str(e)}"}), 500

@invoices_blueprint.get("/api/settings/logs")
@roles_required("admin", "auditor")
def api_get_settings_logs():
    """Retrieve history of background scheduler executions."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from invoices.scheduler import get_scheduler_logs
    return jsonify(get_scheduler_logs())
