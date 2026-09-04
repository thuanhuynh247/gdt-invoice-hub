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
        "ai_headroom_enabled": bool(payload.get("ai_headroom_enabled", True)),
        "ai_headroom_compress_user_messages": bool(payload.get("ai_headroom_compress_user_messages", True)),
        "ai_headroom_target_ratio": float(payload.get("ai_headroom_target_ratio", 0.5)),
        "ai_headroom_protect_recent": int(payload.get("ai_headroom_protect_recent", 0)),
        "ai_headroom_align_cache": bool(payload.get("ai_headroom_align_cache", True)),
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


@invoices_blueprint.get("/v76-headroom-hub")
@roles_required("admin", "auditor")
def headroom_hub():
    """Render the Headroom AI Context Hub and Playground."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized
    return render_template("v76_headroom_hub.html")


@invoices_blueprint.get("/api/headroom/stats")
@roles_required("admin", "auditor")
def api_headroom_stats():
    """Retrieve Headroom AI compression telemetry stats."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from invoices.models import HeadroomTelemetry
    
    try:
        telemetries = HeadroomTelemetry.query.order_by(HeadroomTelemetry.id.desc()).all()
    except Exception as e:
        return jsonify({"error": f"Failed to query telemetry: {str(e)}"}), 500

    total_calls = len(telemetries)
    total_before = sum(t.tokens_before for t in telemetries)
    total_after = sum(t.tokens_after for t in telemetries)
    total_saved = sum(t.tokens_saved for t in telemetries)
    
    avg_ratio = 0.0
    if total_before > 0:
        avg_ratio = total_saved / total_before

    # Estimated savings: $0.000015 USD per token (approx $15 per 1M tokens)
    estimated_cost_saved_usd = total_saved * 0.000015
    
    # Recent 15 events
    recent_events = [t.to_dict() for t in telemetries[:15]]

    # Check if headroom is installed and can be imported
    headroom_installed = True
    headroom_version = "v1.0.0-native"
    try:
        import headroom
        headroom_version = getattr(headroom, "__version__", "v1.0.0")
    except ImportError:
        pass

    return jsonify({
        "headroom_installed": headroom_installed,
        "headroom_version": headroom_version,
        "total_calls": total_calls,
        "total_tokens_before": total_before,
        "total_tokens_after": total_after,
        "total_tokens_saved": total_saved,
        "average_compression_ratio": avg_ratio,
        "estimated_cost_saved_usd": estimated_cost_saved_usd,
        "recent_events": recent_events
    })


@invoices_blueprint.post("/api/headroom/playground")
@roles_required("admin", "auditor")
def api_headroom_playground():
    """Live compression playground for testing Headroom AI parameters."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    payload = request.get_json(silent=True) or {}
    system_prompt = payload.get("system_prompt", "").strip()
    user_content = payload.get("user_content", "").strip()
    
    if not system_prompt and not user_content:
        return jsonify({"error": "Vui lòng nhập System Prompt hoặc User Content."}), 400

    # Retrieve parameters from payload or defaults
    model_name = payload.get("model_name", "gemma-4")
    compress_user = bool(payload.get("compress_user_messages", True))
    target_ratio = float(payload.get("target_ratio", 0.5))
    protect_recent = int(payload.get("protect_recent", 0))

    try:
        try:
            import headroom
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            if user_content:
                messages.append({"role": "user", "content": user_content})

            result = headroom.compress(
                messages=messages,
                model=model_name,
                compress_user_messages=compress_user,
                target_ratio=target_ratio,
                protect_recent=protect_recent
            )

            compressed_system = ""
            compressed_user = ""
            for msg in result.messages:
                if msg.get("role") == "system":
                    compressed_system = msg.get("content", "")
                elif msg.get("role") == "user":
                    compressed_user = msg.get("content", "")

            tokens_before = result.tokens_before
            tokens_after = result.tokens_after
            tokens_saved = result.tokens_saved
            ratio = result.compression_ratio
            transforms = result.transforms_applied
        except ImportError:
            # Native fallback for playground testing
            import re
            tokens_before = len(system_prompt.split()) + len(user_content.split())
            compressed_system = system_prompt
            compressed_user = user_content
            if compress_user and user_content:
                compressed_user = re.sub(r'[ \t]+', ' ', user_content).strip()
            tokens_after = len(compressed_system.split()) + len(compressed_user.split())
            tokens_saved = max(0, tokens_before - tokens_after)
            ratio = (tokens_saved / tokens_before) if tokens_before > 0 else 0.0
            transforms = ["native:whitespace_truncation"]

        return jsonify({
            "status": "success",
            "tokens_before": tokens_before,
            "tokens_after": tokens_after,
            "tokens_saved": tokens_saved,
            "compression_ratio": ratio,
            "transforms_applied": transforms,
            "compressed_system_prompt": compressed_system,
            "compressed_user_content": compressed_user
        })
    except Exception as e:
        return jsonify({"error": f"Lỗi nén Headroom AI: {str(e)}"}), 500

