from __future__ import annotations
import time
from flask import jsonify, request, session, render_template, current_app
from auth.decorators import roles_required
from invoices.routes.shared import invoices_blueprint
from invoices.routes.helpers import _ensure_logged_in
from auth.proxy_manager import proxy_manager
from extensions import db

@invoices_blueprint.get("/v77-waf-resilience")
@roles_required("admin", "auditor")
def page_waf_resilience():
    """Render the WAF resilience and proxy status dashboard."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized
    return render_template("v77_waf_resilience.html")


@invoices_blueprint.get("/api/waf-resilience/status")
@roles_required("admin", "auditor")
def api_waf_resilience_status():
    """Retrieve current proxy metrics, latency, and global cooldown state."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    stats = proxy_manager.get_all_proxy_stats()
    cooldown_active = proxy_manager.is_global_cooldown()
    cooldown_rem = proxy_manager.get_global_cooldown_remaining()

    return jsonify({
        "status": "success",
        "global_cooldown_active": cooldown_active,
        "global_cooldown_remaining": round(cooldown_rem, 1),
        "dynamic_delay_min": round(proxy_manager.dynamic_delay_min, 2),
        "dynamic_delay_max": round(proxy_manager.dynamic_delay_max, 2),
        "proxies": stats,
        "timestamp": time.time()
    })


@invoices_blueprint.post("/api/waf-resilience/control")
@roles_required("admin", "auditor")
def api_waf_resilience_control():
    """Control and simulate proxy state and configuration."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    payload = request.get_json(silent=True) or {}
    action = payload.get("action")

    if action == "clear_cooldowns":
        proxy_manager.clear_cooldowns()
        return jsonify({"status": "success", "message": "Đã reset toàn bộ cool-down và lịch sử lỗi."})

    elif action == "simulate_request":
        # Simulate request testing
        proxy_url = payload.get("proxy_url")
        status_code = int(payload.get("status_code", 200))
        error_msg = payload.get("error_msg", "")
        latency = float(payload.get("latency_ms", 150.0))

        if status_code in [200, 201]:
            proxy_manager.report_success(proxy_url, latency)
            return jsonify({"status": "success", "message": f"Mô phỏng thành công cho proxy {proxy_url} ({latency}ms)."})
        else:
            proxy_manager.report_failure(proxy_url, status_code, error_msg or f"Simulated HTTP {status_code}")
            return jsonify({"status": "success", "message": f"Mô phỏng thất bại cho proxy {proxy_url}."})

    elif action == "add_proxy":
        proxy_url = payload.get("proxy_url", "").strip()
        if not proxy_url:
            return jsonify({"status": "error", "message": "Proxy URL không được để trống."}), 400

        # Save to SystemConfig database
        try:
            from invoices.models import SystemConfig
            cfg = SystemConfig.query.filter_by(key="gdt_proxies").first()
            current_list = []
            if cfg and cfg.value.strip():
                current_list = [p.strip() for p in cfg.value.split(",") if p.strip()]

            if proxy_url not in current_list:
                current_list.append(proxy_url)
                val_str = ",".join(current_list)
                if cfg:
                    cfg.value = val_str
                else:
                    cfg = SystemConfig(key="gdt_proxies", value=val_str)
                    db.session.add(cfg)
                db.session.commit()
                proxy_manager.sync_proxies()
                return jsonify({"status": "success", "message": f"Đã thêm proxy: {proxy_url}"})
            else:
                return jsonify({"status": "error", "message": "Proxy đã tồn tại."}), 400
        except Exception as e:
            db.session.rollback()
            return jsonify({"status": "error", "message": f"Không thể lưu proxy: {str(e)}"}), 500

    elif action == "delete_proxy":
        proxy_url = payload.get("proxy_url", "").strip()
        if not proxy_url:
            return jsonify({"status": "error", "message": "Proxy URL không được để trống."}), 400

        try:
            from invoices.models import SystemConfig
            cfg = SystemConfig.query.filter_by(key="gdt_proxies").first()
            if cfg and cfg.value.strip():
                current_list = [p.strip() for p in cfg.value.split(",") if p.strip()]
                if proxy_url in current_list:
                    current_list.remove(proxy_url)
                    val_str = ",".join(current_list)
                    cfg.value = val_str
                    db.session.commit()
                    proxy_manager.sync_proxies()
                    return jsonify({"status": "success", "message": f"Đã xóa proxy: {proxy_url}"})
            return jsonify({"status": "error", "message": "Proxy không tìm thấy trong database."}), 404
        except Exception as e:
            db.session.rollback()
            return jsonify({"status": "error", "message": f"Không thể xóa proxy: {str(e)}"}), 500

    return jsonify({"status": "error", "message": "Hành động không hợp lệ."}), 400
