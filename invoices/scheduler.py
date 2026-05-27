"""Background scheduler service for US-024.

Manages automated daily/weekly invoice fetching, Excel report generation,
and email dispatching using SMTP.
"""

from __future__ import annotations

import os
import json
import threading
import time
from datetime import datetime, timedelta, date
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# File locking to prevent concurrent read/write issues in Flask
DB_DIR = "data"
DB_FILE = os.path.join(DB_DIR, "invoices_db.json")
DB_LOCK = threading.Lock()

DEFAULT_SETTINGS = {
    "smtp_host": "",
    "smtp_port": 587,
    "smtp_user": "",
    "smtp_pass": "",
    "smtp_use_tls": True,
    "recipient_email": "",
    "schedule_enabled": False,
    "schedule_interval": "daily",
    "schedule_time": "08:00",
    "schedule_weekday": 0,
    "gdt_username": "",
    "gdt_password": "",
    "last_run": "",
    "ai_enabled": False,
    "ai_provider": "ollama",
    "ai_ollama_endpoint": "http://localhost:11434",
    "ai_api_key": "",
    "ai_model_name": "gemma-4",
    "ai_system_prompt": "Bạn là Trợ lý Kiểm toán Thuế chuyên nghiệp tại Việt Nam (Senior Tax Auditor), am hiểu Luật Thuế GTGT Việt Nam, các Nghị định và Thông tư hướng dẫn.\nNhiệm vụ của bạn là thực hiện kiểm toán tuân thủ chi tiết từng mặt hàng và giao dịch trên hóa đơn để xác định các rủi ro về thuế và khấu trừ thuế đầu vào (ví dụ: personal_purchase, price_anomaly, invoice_timing, cash_payment_risk, tax_rate_mismatch, suspicious_transaction). Trả về kết quả dưới dạng JSON.",
    "telegram_enabled": False,
    "telegram_bot_token": "",
    "telegram_chat_id": "",
    "audit_agent_enabled": False,
    "audit_agent_schedule_time": "23:00",
    "last_audit_run": "",
    "gdrive_enabled": False,
    "gdrive_client_id": "",
    "gdrive_client_secret": "",
    "gdrive_refresh_token": "",
    "gdrive_folder_id": "",
    "onedrive_enabled": False,
    "onedrive_client_id": "",
    "onedrive_client_secret": "",
    "onedrive_refresh_token": "",
    "onedrive_folder_path": "HoaDon_DienTu",
    "erp_enabled": False,
    "erp_type": "none",
    "erp_api_url": "",
    "erp_auth_token": "",
    "realtime_sync_enabled": False,
    "realtime_sync_interval": 15,
    "last_realtime_sync_run": "",
    "webhook_enabled": False,
    "webhook_url": "",
    "webhook_secret": ""
}


# Global reference to the scheduler worker
_scheduler_thread = None

import queue
REALTIME_CLIENT_QUEUES = []
REALTIME_QUEUES_LOCK = threading.Lock()

def push_realtime_sync_event(event_data: dict):
    """Push realtime sync status event to all active SSE streams."""
    with REALTIME_QUEUES_LOCK:
        # Clean up stale/full queues, and put data
        for q in REALTIME_CLIENT_QUEUES:
            try:
                q.put_nowait(event_data)
            except queue.Full:
                pass


def load_scheduler_settings() -> dict:
    """Load scheduler settings from the local SQLite database."""
    from invoices.models import SystemConfig
    
    settings = DEFAULT_SETTINGS.copy()
    try:
        configs = SystemConfig.query.all()
        for cfg in configs:
            if cfg.key in settings:
                val = cfg.value
                if isinstance(settings[cfg.key], bool):
                    settings[cfg.key] = val.lower() == "true"
                elif isinstance(settings[cfg.key], int):
                    try:
                        settings[cfg.key] = int(val)
                    except ValueError:
                        pass
                else:
                    settings[cfg.key] = val
    except Exception:
        pass
    return settings


def save_scheduler_settings(settings: dict) -> None:
    """Save scheduler settings and encrypt new GDT or SMTP passwords."""
    from extensions import db
    from invoices.models import SystemConfig
    from auth.crypto import encrypt_password

    current_settings = {}
    try:
        configs = SystemConfig.query.all()
        for cfg in configs:
            current_settings[cfg.key] = cfg.value
    except Exception:
        pass

    old_smtp_pass = current_settings.get("smtp_pass", "")
    new_smtp_pass = settings.get("smtp_pass", "")
    if new_smtp_pass and new_smtp_pass != "••••••••" and new_smtp_pass != old_smtp_pass:
        settings["smtp_pass"] = encrypt_password(new_smtp_pass)
    else:
        settings["smtp_pass"] = old_smtp_pass

    old_gdt_pass = current_settings.get("gdt_password", "")
    new_gdt_pass = settings.get("gdt_password", "")
    if new_gdt_pass and new_gdt_pass != "••••••••" and new_gdt_pass != old_gdt_pass:
        settings["gdt_password"] = encrypt_password(new_gdt_pass)
    else:
        settings["gdt_password"] = old_gdt_pass

    old_ai_api_key = current_settings.get("ai_api_key", "")
    new_ai_api_key = settings.get("ai_api_key", "")
    if new_ai_api_key and new_ai_api_key != "••••••••" and new_ai_api_key != old_ai_api_key:
        settings["ai_api_key"] = encrypt_password(new_ai_api_key)
    else:
        settings["ai_api_key"] = old_ai_api_key

    old_telegram_bot_token = current_settings.get("telegram_bot_token", "")
    new_telegram_bot_token = settings.get("telegram_bot_token", "")
    if new_telegram_bot_token and new_telegram_bot_token != "••••••••" and new_telegram_bot_token != old_telegram_bot_token:
        settings["telegram_bot_token"] = encrypt_password(new_telegram_bot_token)
    else:
        settings["telegram_bot_token"] = old_telegram_bot_token

    # Encrypt Google Drive credentials
    old_gdrive_secret = current_settings.get("gdrive_client_secret", "")
    new_gdrive_secret = settings.get("gdrive_client_secret", "")
    if new_gdrive_secret and new_gdrive_secret != "••••••••" and new_gdrive_secret != old_gdrive_secret:
        settings["gdrive_client_secret"] = encrypt_password(new_gdrive_secret)
    else:
        settings["gdrive_client_secret"] = old_gdrive_secret

    old_gdrive_refresh = current_settings.get("gdrive_refresh_token", "")
    new_gdrive_refresh = settings.get("gdrive_refresh_token", "")
    if new_gdrive_refresh and new_gdrive_refresh != "••••••••" and new_gdrive_refresh != old_gdrive_refresh:
        settings["gdrive_refresh_token"] = encrypt_password(new_gdrive_refresh)
    else:
        settings["gdrive_refresh_token"] = old_gdrive_refresh

    # Encrypt Microsoft OneDrive credentials
    old_onedrive_secret = current_settings.get("onedrive_client_secret", "")
    new_onedrive_secret = settings.get("onedrive_client_secret", "")
    if new_onedrive_secret and new_onedrive_secret != "••••••••" and new_onedrive_secret != old_onedrive_secret:
        settings["onedrive_client_secret"] = encrypt_password(new_onedrive_secret)
    else:
        settings["onedrive_client_secret"] = old_onedrive_secret

    old_onedrive_refresh = current_settings.get("onedrive_refresh_token", "")
    new_onedrive_refresh = settings.get("onedrive_refresh_token", "")
    if new_onedrive_refresh and new_onedrive_refresh != "••••••••" and new_onedrive_refresh != old_onedrive_refresh:
        settings["onedrive_refresh_token"] = encrypt_password(new_onedrive_refresh)
    else:
        settings["onedrive_refresh_token"] = old_onedrive_refresh

    # Encrypt ERP authorization credentials
    old_erp_auth_token = current_settings.get("erp_auth_token", "")
    new_erp_auth_token = settings.get("erp_auth_token", "")
    if new_erp_auth_token and new_erp_auth_token != "••••••••" and new_erp_auth_token != old_erp_auth_token:
        settings["erp_auth_token"] = encrypt_password(new_erp_auth_token)
    else:
        settings["erp_auth_token"] = old_erp_auth_token

    # Encrypt Webhook secret
    old_webhook_secret = current_settings.get("webhook_secret", "")
    new_webhook_secret = settings.get("webhook_secret", "")
    if new_webhook_secret and new_webhook_secret != "••••••••" and new_webhook_secret != old_webhook_secret:
        settings["webhook_secret"] = encrypt_password(new_webhook_secret)
    else:
        settings["webhook_secret"] = old_webhook_secret

    try:
        for key, val in settings.items():
            cfg = db.session.get(SystemConfig, key)

            if cfg:
                cfg.value = str(val)
            else:
                cfg = SystemConfig(key=key, value=str(val))
                db.session.add(cfg)
        db.session.commit()
    except Exception:
        db.session.rollback()


def add_scheduler_log(status: str, details: str) -> None:
    """Append a log entry for auditing background report dispatches."""
    from extensions import db
    from invoices.models import SchedulerLog
    try:
        new_log = SchedulerLog(
            timestamp=datetime.now().isoformat(),
            status=status,
            details=details
        )
        db.session.add(new_log)
        
        count = SchedulerLog.query.count()
        if count > 50:
            oldest_logs = SchedulerLog.query.order_by(SchedulerLog.id.asc()).limit(count - 50).all()
            for old_log in oldest_logs:
                db.session.delete(old_log)
        
        db.session.commit()

    except Exception:
        db.session.rollback()


def get_scheduler_logs() -> list[dict]:
    """Retrieve recent scheduler execution history logs."""
    from invoices.models import SchedulerLog
    try:
        logs = SchedulerLog.query.order_by(SchedulerLog.id.desc()).all()
        return [
            {
                "time": log.timestamp,
                "status": log.status,
                "details": log.details
            }
            for log in logs
        ]
    except Exception:
        return []



def should_trigger(settings: dict, now: datetime) -> bool:
    """Determine if schedule settings are active and matches the current clock."""
    if not settings.get("schedule_enabled", False):
        return False

    time_str = settings.get("schedule_time", "08:00")
    try:
        sched_hour, sched_min = map(int, time_str.split(":"))
    except ValueError:
        return False

    # Check if matching time (hour and minute with a 5-minute window for polling tolerance)
    sched_dt = now.replace(hour=sched_hour, minute=sched_min, second=0, microsecond=0)
    diff_sec = abs((now - sched_dt).total_seconds())
    if diff_sec > 300:  # 5 minutes window
        return False

    interval = settings.get("schedule_interval", "daily")

    # Check weekday matching for weekly schedules
    if interval == "weekly":
        sched_weekday = int(settings.get("schedule_weekday", 0))
        if now.weekday() != sched_weekday:
            return False

    # Avoid double runs within the same calendar day
    today_str = now.date().isoformat()
    if settings.get("last_run") == today_str:
        return False

    return True


def should_trigger_audit_agent(settings: dict, now: datetime) -> bool:
    """Determine if audit agent settings are active and matches the current clock."""
    if not settings.get("audit_agent_enabled", False):
        return False

    time_str = settings.get("audit_agent_schedule_time", "23:00")
    try:
        sched_hour, sched_min = map(int, time_str.split(":"))
    except ValueError:
        return False

    sched_dt = now.replace(hour=sched_hour, minute=sched_min, second=0, microsecond=0)
    diff_sec = abs((now - sched_dt).total_seconds())
    if diff_sec > 300:  # 5 minutes window
        return False

    today_str = now.date().isoformat()
    if settings.get("last_audit_run") == today_str:
        return False

    return True

def should_trigger_realtime_sync(settings: dict, now: datetime) -> bool:
    """Determine if real-time synchronization agent should trigger based on configured interval."""
    if not settings.get("realtime_sync_enabled", False):
        return False

    last_run_str = settings.get("last_realtime_sync_run", "")
    interval_minutes = int(settings.get("realtime_sync_interval", 15))
    if not last_run_str:
        return True

    try:
        last_run_dt = datetime.fromisoformat(last_run_str)
        # Add 5 seconds tolerance to prevent minute rounding issues
        return (now - last_run_dt).total_seconds() >= (interval_minutes * 60 - 5)
    except Exception:
        return True


class SchedulerThread(threading.Thread):
    """Background daemon worker checking schedules and dispatching email reports."""

    def __init__(self, app):
        super().__init__(name="GDTInvoiceSchedulerThread")
        self.app = app
        self.daemon = True
        self._stop_event = threading.Event()

    def stop(self):
        """Signal thread shutdown."""
        self._stop_event.set()

    def run(self):
        """Thread main polling loop."""
        self.app.logger.info("Background Scheduler Thread started.")
        while not self._stop_event.is_set():
            try:
                self.check_and_trigger_job()
            except Exception as e:
                self.app.logger.error(f"Error in scheduler check: {e}")
            
            # Poll every 10 seconds to respond quickly to stops/changes
            if self._stop_event.wait(timeout=10):
                break

    def check_and_trigger_job(self):
        """Check if schedule settings are active and matches the current clock."""
        with self.app.app_context():
            settings = load_scheduler_settings()
            now = datetime.now()

            # Check if real-time sync should trigger
            if should_trigger_realtime_sync(settings, now):
                try:
                    self.execute_realtime_sync(settings)
                except Exception as e:
                    self.app.logger.error(f"Real-time sync execution failed: {e}")

            # Check if autonomous AI audit agent should trigger
            if should_trigger_audit_agent(settings, now):
                # Commit last run date BEFORE execution to prevent race condition/double dispatch
                settings["last_audit_run"] = now.date().isoformat()
                save_scheduler_settings(settings)

                self.app.logger.info("Triggering scheduled autonomous AI audit agent.")
                try:
                    self.execute_autonomous_audit(settings)
                except Exception as e:
                    self.app.logger.error(f"Autonomous AI audit agent execution failed: {e}")
                    add_scheduler_log("FAILED", f"Lỗi chạy kiểm toán tự động: {str(e)}")

            if not should_trigger(settings, now):
                return

            # Commit last run date BEFORE execution to prevent race condition/double dispatch
            settings["last_run"] = now.date().isoformat()
            save_scheduler_settings(settings)

            interval = settings.get("schedule_interval", "daily")
            self.app.logger.info(f"Triggering scheduled report execution: interval={interval}")

            # Execute the scheduled process
            try:
                self.execute_scheduled_report(settings, now)
            except Exception as e:
                self.app.logger.error(f"Scheduled report execution failed: {e}")
                add_scheduler_log("FAILED", f"Lỗi chạy báo cáo: {str(e)}")


    def execute_scheduled_report(self, settings: dict, run_time: datetime):
        """Fetch invoices for the preceding period, compile to Excel, and email."""
        interval = settings.get("schedule_interval", "daily")

        # Determine date ranges (Daily = yesterday; Weekly = preceding 7 days)
        if interval == "daily":
            date_from = (run_time - timedelta(days=1)).date()
            date_to = (run_time - timedelta(days=1)).date()
        else:
            date_from = (run_time - timedelta(days=7)).date()
            date_to = (run_time - timedelta(days=1)).date()

        self.app.logger.info(f"Scheduled fetching range: {date_from} to {date_to}")

        gdt_user = settings.get("gdt_username", "")
        gdt_pass_enc = settings.get("gdt_password", "")

        from invoices.service import fetch_invoices, InvoiceQuery, download_invoice_xml, import_xml_invoice
        from export.excel import generate_excel_workbook
        from invoices.models import TaxpayerProfile
        from auth.crypto import decrypt_password

        # Load active taxpayer profiles
        profiles = []
        try:
            profiles = TaxpayerProfile.query.filter_by(is_active=True).all()
        except Exception as e:
            self.app.logger.error(f"Error loading taxpayer profiles in scheduler: {e}")

        targets = []
        if profiles:
            for p in profiles:
                try:
                    gdt_pwd = decrypt_password(p.gdt_password_encrypted)
                    targets.append({
                        "mst": p.mst,
                        "username": p.gdt_username,
                        "password_encrypted": p.gdt_password_encrypted,
                        "company_name": p.company_name
                    })
                except Exception as ex:
                    self.app.logger.error(f"Failed to decrypt credentials for profile {p.mst}: {ex}")
        else:
            # Fallback to single-tenant default settings
            if gdt_user and gdt_pass_enc:
                targets.append({
                    "mst": None,
                    "username": gdt_user,
                    "password_encrypted": gdt_pass_enc,
                    "company_name": "Default Tenant"
                })

        all_invoices = []
        total_buy = 0
        total_sell = 0

        for target in targets:
            mst = target["mst"]
            user = target["username"]
            pass_enc = target["password_encrypted"]

            self.app.logger.info(f"Scheduled crawl: taxpayer_mst={mst or 'Default'}...")

            # Temporarily inject GDT credentials & active taxpayer MST into app.config
            old_user = self.app.config.get("CURRENT_USERNAME")
            old_pass = self.app.config.get("CURRENT_ENCRYPTED_PASSWORD")
            old_mst = self.app.config.get("CURRENT_TAXPAYER_MST")

            try:
                self.app.config["CURRENT_USERNAME"] = user
                self.app.config["CURRENT_ENCRYPTED_PASSWORD"] = pass_enc
                self.app.config["CURRENT_TAXPAYER_MST"] = mst

                # Query GDT for both buy (purchase) and sell (sold) transactions
                query_buy = InvoiceQuery(date_from, date_to, cancelled_only=False, direction="purchase")
                query_sell = InvoiceQuery(date_from, date_to, cancelled_only=False, direction="sold")

                invoices_buy = fetch_invoices(query_buy)
                invoices_sell = fetch_invoices(query_sell)

                # Auto-import into local database
                for inv in (invoices_buy + invoices_sell):
                    try:
                        invoice_id = inv["id"]

                        # Check if invoice already exists locally with same status
                        from extensions import db
                        from invoices.models import Invoice

                        local_id = None
                        raw = inv.get("raw") or {}
                        if raw.get("nbmst") and raw.get("khhdon") and raw.get("shdon"):
                            shdon_raw = raw.get("shdon", "00000000")
                            try:
                                number = f"{int(shdon_raw):08d}"
                            except ValueError:
                                number = shdon_raw
                            local_id = f"{raw.get('nbmst')}-{raw.get('khhdon')}-{number}"
                        else:
                            local_id = invoice_id

                        existing_invoice = db.session.get(Invoice, local_id) if local_id else None
                        if existing_invoice:
                            # Skip download and import if status has not changed
                            gdt_cancelled = inv.get("is_cancelled", False)
                            if existing_invoice.is_cancelled == gdt_cancelled:
                                continue

                        xml_bytes = download_invoice_xml(invoice_id)
                        filename = f"GDT_{inv.get('issuer', 'NB').replace(' ', '_')}_{inv['date']}_{invoice_id}.xml"
                        import_xml_invoice(xml_bytes, filename, duplicate_strategy="overwrite", taxpayer_mst=mst)
                    except Exception as e:
                        self.app.logger.error(f"Failed to import background crawled invoice {inv.get('id')}: {e}")

                all_invoices.extend(invoices_buy + invoices_sell)
                total_buy += len(invoices_buy)
                total_sell += len(invoices_sell)

            except Exception as e:
                self.app.logger.error(f"Failed scheduled crawl for profile {mst or 'Default'}: {e}")
            finally:
                # Restore previous context credentials
                self.app.config["CURRENT_USERNAME"] = old_user
                self.app.config["CURRENT_ENCRYPTED_PASSWORD"] = old_pass
                self.app.config["CURRENT_TAXPAYER_MST"] = old_mst

        # Compile data to Excel binary stream
        excel_data = generate_excel_workbook(all_invoices)

        # Dispatch the email report
        self.send_report_email(settings, date_from, date_to, all_invoices, total_buy, total_sell, excel_data)

        # Append audit log entry
        add_scheduler_log(
            "SUCCESS",
            f"Đã gửi báo cáo tự động từ {date_from.strftime('%d/%m/%Y')} đến {date_to.strftime('%d/%m/%Y')}. "
            f"Tổng số: {len(all_invoices)} hóa đơn ({total_buy} mua vào, {total_sell} bán ra) "
            f"tới {settings.get('recipient_email')}."
        )

    def execute_realtime_sync(self, settings: dict):
        """Perform automated GDT real-time crawling and dispatch events/webhooks."""
        now_dt = datetime.now()
        
        # 1. Update last run timestamp immediately
        settings["last_realtime_sync_run"] = now_dt.isoformat()
        save_scheduler_settings(settings)
        
        self.app.logger.info("Executing real-time GDT invoice synchronization agent...")
        
        from invoices.service import fetch_invoices, InvoiceQuery, download_invoice_xml, import_xml_invoice
        from invoices.models import TaxpayerProfile, Invoice
        from auth.crypto import decrypt_password
        from extensions import db
        import hmac
        import hashlib
        import requests
        
        # Setup date range
        if self.app.config.get("GDT_USE_MOCK"):
            date_from = date(2026, 5, 1)
            date_to = date(2026, 5, 20)
        else:
            date_from = (now_dt - timedelta(days=1)).date()
            date_to = now_dt.date()
            
        # Load active profiles
        profiles = []
        try:
            profiles = TaxpayerProfile.query.filter_by(is_active=True).all()
        except Exception as e:
            self.app.logger.error(f"Error loading taxpayer profiles in real-time sync: {e}")
            
        targets = []
        if profiles:
            for p in profiles:
                try:
                    targets.append({
                        "mst": p.mst,
                        "username": p.gdt_username,
                        "password_encrypted": p.gdt_password_encrypted,
                        "company_name": p.company_name
                    })
                except Exception as ex:
                    self.app.logger.error(f"Failed to load credentials for profile {p.mst}: {ex}")
        else:
            gdt_user = settings.get("gdt_username", "")
            gdt_pass_enc = settings.get("gdt_password", "")
            if gdt_user and gdt_pass_enc:
                targets.append({
                    "mst": None,
                    "username": gdt_user,
                    "password_encrypted": gdt_pass_enc,
                    "company_name": "Default Tenant"
                })
                
        imported_count = 0
        updated_count = 0
        
        webhook_enabled = settings.get("webhook_enabled", False)
        webhook_url = settings.get("webhook_url", "")
        webhook_secret_enc = settings.get("webhook_secret", "")
        
        webhook_secret = ""
        if webhook_enabled and webhook_url and webhook_secret_enc:
            try:
                webhook_secret = decrypt_password(webhook_secret_enc)
            except Exception as ex:
                self.app.logger.error(f"Failed to decrypt webhook secret: {ex}")
                
        for target in targets:
            mst = target["mst"]
            user = target["username"]
            pass_enc = target["password_encrypted"]
            company = target["company_name"]
            
            old_user = self.app.config.get("CURRENT_USERNAME")
            old_pass = self.app.config.get("CURRENT_ENCRYPTED_PASSWORD")
            old_mst = self.app.config.get("CURRENT_TAXPAYER_MST")
            old_jwt = self.app.config.get("CURRENT_JWT")
            old_lookup = self.app.config.get("CURRENT_INVOICE_LOOKUP")
            
            try:
                self.app.config["CURRENT_USERNAME"] = user
                self.app.config["CURRENT_ENCRYPTED_PASSWORD"] = pass_enc
                self.app.config["CURRENT_TAXPAYER_MST"] = mst
                self.app.config["CURRENT_JWT"] = None # Force fresh authentication
                
                # Fetch purchase and sold
                query_buy = InvoiceQuery(date_from, date_to, cancelled_only=False, direction="purchase")
                query_sell = InvoiceQuery(date_from, date_to, cancelled_only=False, direction="sold")
                
                invoices_buy = fetch_invoices(query_buy)
                invoices_sell = fetch_invoices(query_sell)
                
                crawled_list = invoices_buy + invoices_sell
                
                # Build and inject lookup map for download_invoice_xml
                from auth.service import build_invoice_lookup
                self.app.config["CURRENT_INVOICE_LOOKUP"] = build_invoice_lookup(crawled_list)
                
                for inv in crawled_list:
                    try:
                        invoice_id = inv["id"]
                        
                        # Calculate high-fidelity unique key
                        local_id = None
                        raw = inv.get("raw") or {}
                        if raw.get("nbmst") and raw.get("khhdon") and raw.get("shdon"):
                            shdon_raw = raw.get("shdon", "00000000")
                            try:
                                number = f"{int(shdon_raw):08d}"
                            except ValueError:
                                number = shdon_raw
                            local_id = f"{raw.get('nbmst')}-{raw.get('khhdon')}-{number}"
                        else:
                            local_id = invoice_id
                            
                        existing = db.session.get(Invoice, local_id) if local_id else None
                        
                        is_new = existing is None
                        is_status_changed = False
                        if existing:
                            gdt_cancelled = inv.get("is_cancelled", False)
                            if existing.is_cancelled != gdt_cancelled:
                                is_status_changed = True
                                
                        if not is_new and not is_status_changed:
                            continue
                            
                        # Download XML content
                        xml_bytes = download_invoice_xml(invoice_id)
                        filename = f"GDT_REALTIME_{inv.get('issuer', 'NB').replace(' ', '_')}_{inv['date']}_{invoice_id}.xml"
                        
                        # Import and run audit / forecasting automatically!
                        import_xml_invoice(xml_bytes, filename, duplicate_strategy="overwrite", taxpayer_mst=mst)
                        
                        if is_new:
                            imported_count += 1
                        else:
                            updated_count += 1
                            
                        # Fetch the fully audited local invoice to get T-Score, T-Rating, and structured fields!
                        db_invoice = db.session.get(Invoice, local_id)
                        if db_invoice:
                            event_data = {
                                "event": "invoice_downloaded",
                                "id": db_invoice.id,
                                "number": db_invoice.invoice_number,
                                "date": db_invoice.invoice_date.isoformat(),
                                "seller_name": db_invoice.seller_name,
                                "total_amount": float(db_invoice.total_amount),
                                "t_score": db_invoice.t_score,
                                "t_rating": db_invoice.t_rating,
                                "is_new": is_new,
                                "is_cancelled": db_invoice.is_cancelled
                            }
                            
                            # A. Dispatch Server-Sent Event (SSE)
                            push_realtime_sync_event(event_data)
                            
                            # B. Dispatch Secure HMAC-Signed Webhook
                            if webhook_enabled and webhook_url:
                                def dispatch_hook(url=webhook_url, secret=webhook_secret, data=event_data):
                                    payload = {
                                        "event": "invoice.imported",
                                        "timestamp": datetime.utcnow().isoformat() + "Z",
                                        "data": data
                                    }
                                    payload_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                                    headers = {
                                        "Content-Type": "application/json",
                                        "X-Invoice-Event": "invoice.imported"
                                    }
                                    if secret:
                                        sig = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
                                        headers["X-Invoice-Signature"] = sig
                                    try:
                                        requests.post(url, data=payload_bytes, headers=headers, timeout=5)
                                    except Exception as err:
                                        self.app.logger.error(f"Failed to dispatch webhook for invoice {data['number']}: {err}")
                                
                                t = threading.Thread(target=dispatch_hook, daemon=True)
                                t.start()
                                
                    except Exception as inv_err:
                        self.app.logger.error(f"Failed to process real-time invoice {inv.get('id')}: {inv_err}")
                        
            except Exception as target_err:
                self.app.logger.error(f"Real-time crawl failed for profile {mst or 'Default'}: {target_err}")
            finally:
                self.app.config["CURRENT_USERNAME"] = old_user
                self.app.config["CURRENT_ENCRYPTED_PASSWORD"] = old_pass
                self.app.config["CURRENT_TAXPAYER_MST"] = old_mst
                self.app.config["CURRENT_JWT"] = old_jwt
                self.app.config["CURRENT_INVOICE_LOOKUP"] = old_lookup
                
        if imported_count > 0 or updated_count > 0:
            add_scheduler_log(
                "SUCCESS",
                f"Đồng bộ thời gian thực: Tải mới {imported_count} hóa đơn, cập nhật {updated_count} hóa đơn thành công."
            )

    def send_report_email(self, settings: dict, date_from: date, date_to: date,
                          invoices: list[dict], buy_count: int, sell_count: int, excel_data: bytes):
        """Construct a structured multipart email and dispatch via SMTP."""
        recipient = settings.get("recipient_email")
        if not recipient:
            raise ValueError("Chưa cấu hình địa chỉ nhận báo cáo (recipient_email).")

        smtp_host = settings.get("smtp_host")
        smtp_port = int(settings.get("smtp_port", 587))
        smtp_user = settings.get("smtp_user")
        smtp_pass_enc = settings.get("smtp_pass")
        smtp_use_tls = settings.get("smtp_use_tls", True)

        if not smtp_host or not smtp_user or not smtp_pass_enc:
            raise ValueError("Cấu hình SMTP chưa đầy đủ.")

        from auth.crypto import decrypt_password
        smtp_pass = decrypt_password(smtp_pass_enc)

        # Build standard MIME message
        msg = MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = recipient

        interval_label = "Hàng ngày" if settings.get("schedule_interval") == "daily" else "Hàng tuần"
        date_str = datetime.now().strftime("%d/%m/%Y")
        msg["Subject"] = f"[GDT Invoice Hub] Báo cáo hóa đơn tự động {interval_label} - {date_str}"

        # Aggregate report figures
        total_invoices = len(invoices)
        total_amount = sum(inv.get("total_amount", 0) for inv in invoices)
        total_vat = sum(inv.get("total_vat", 0) for inv in invoices)

        # Premium HSL/dark-emerald styled HTML body
        html_body = f"""
        <html>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #1e293b; line-height: 1.6; background-color: #f8fafc; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05); background-color: #ffffff;">
                <div style="background-color: #064e3b; color: #ffffff; padding: 30px; text-align: center;">
                    <h2 style="margin: 0; font-size: 22px; font-weight: 600; letter-spacing: 0.5px;">GDT INVOICE HUB REPORT</h2>
                    <p style="margin: 6px 0 0 0; opacity: 0.9; font-size: 14px;">Khoảng thời gian: {date_from.strftime('%d/%m/%Y')} - {date_to.strftime('%d/%m/%Y')}</p>
                </div>
                <div style="padding: 30px;">
                    <p style="font-size: 16px; margin-top: 0;">Xin chào,</p>
                    <p style="font-size: 15px;">Hệ thống GDT Invoice Hub gửi đến bạn báo cáo tổng hợp hóa đơn tự động định kỳ <strong>{interval_label.lower()}</strong>.</p>
                    
                    <div style="background-color: #f0fdf4; border-radius: 8px; padding: 20px; margin: 24px 0; border-left: 5px solid #10b981;">
                        <h4 style="margin: 0 0 12px 0; color: #064e3b; font-size: 16px; font-weight: 600;">Tóm tắt dữ liệu báo cáo:</h4>
                        <table style="width: 100%; border-collapse: collapse; font-size: 14px; color: #334155;">
                            <tr>
                                <td style="padding: 6px 0; color: #64748b;">Tổng số hóa đơn:</td>
                                <td style="padding: 6px 0; text-align: right; font-weight: 600; color: #0f172a;">{total_invoices} ({buy_count} mua vào, {sell_count} bán ra)</td>
                            </tr>
                            <tr>
                                <td style="padding: 6px 0; color: #64748b;">Tổng tiền trước thuế:</td>
                                <td style="padding: 6px 0; text-align: right; font-weight: 600; color: #0f172a;">{total_amount:,.0f} VND</td>
                            </tr>
                            <tr>
                                <td style="padding: 6px 0; color: #64748b;">Tổng tiền thuế VAT:</td>
                                <td style="padding: 6px 0; text-align: right; font-weight: 600; color: #0f172a;">{total_vat:,.0f} VND</td>
                            </tr>
                            <tr style="border-top: 1px solid #cbd5e1;">
                                <td style="padding: 12px 0 0 0; font-weight: 700; color: #0f172a; font-size: 15px;">Tổng cộng (Sau thuế):</td>
                                <td style="padding: 12px 0 0 0; text-align: right; font-weight: 700; color: #10b981; font-size: 18px;">{(total_amount + total_vat):,.0f} VND</td>
                            </tr>
                        </table>
                    </div>
                    
                    <p style="font-size: 15px;">Chi tiết danh sách các hóa đơn đã được xuất thành công và gửi đính kèm trong file Excel của email này.</p>
                    
                    <div style="margin-top: 40px; border-top: 1px solid #e2e8f0; padding-top: 15px; font-size: 12px; color: #94a3b8;">
                        <p style="margin: 0 0 4px 0;">Email này được hệ thống gửi tự động định kỳ.</p>
                        <p style="margin: 0;">Vui lòng không trả lời trực tiếp email này.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(html_body, "html"))

        # Attach Excel file
        part = MIMEBase("application", "octet-stream")
        part.set_payload(excel_data)
        encoders.encode_base64(part)
        filename = f"Bao_cao_hoa_don_{date_from.strftime('%Y%m%d')}_{date_to.strftime('%Y%m%d')}.xlsx"
        part.add_header("Content-Disposition", f"attachment; filename={filename}")
        msg.attach(part)

        # Dispatch via SMTP
        self.send_smtp_message(smtp_host, smtp_port, smtp_user, smtp_pass, smtp_use_tls, recipient, msg)

    @staticmethod
    def send_smtp_message(host: str, port: int, user: str, password: str, use_tls: bool, recipient: str, msg: MIMEMultipart):
        """Low-level SMTP connection dispatcher supporting SSL/TLS protocols."""
        server = None
        try:
            if port == 465:
                server = smtplib.SMTP_SSL(host, port, timeout=20)
            else:
                server = smtplib.SMTP(host, port, timeout=20)
                if use_tls:
                    server.starttls()
            
            server.login(user, password)
            server.sendmail(user, [recipient], msg.as_string())
        finally:
            if server:
                try:
                    server.quit()
                except Exception:
                    pass

    def execute_autonomous_audit(self, settings: dict):
        """Pillar 4: Query all unaudited invoices, run compliance audits, and calculate T-Score.
        If a high-risk T-Score (< 50) is detected, dispatch real-time alerts.
        """
        from extensions import db
        from invoices.models import Invoice
        from invoices.ai_service import AIComplianceAuditor
        from invoices.service import calculate_invoice_t_score

        self.app.logger.info("Autonomous AI audit agent scanning for new invoices...")
        
        # Find all invoices where ai_audited is False
        unaudited_invoices = Invoice.query.filter(Invoice.ai_audited == False).all()
        if not unaudited_invoices:
            self.app.logger.info("No unaudited invoices found.")
            return

        auditor = AIComplianceAuditor()
        audited_count = 0
        alert_count = 0

        for invoice in unaudited_invoices:
            try:
                # 1. Run the AI audit (recalculates T-Score automatically at the end of audit_invoice, then commits)
                auditor.audit_invoice(invoice)
                
                # Check the resulting T-Score
                t_score = invoice.t_score
                t_rating = invoice.t_rating
                
                self.app.logger.info(f"Audited invoice {invoice.id}: T-Score = {t_score} ({t_rating})")
                audited_count += 1

                # 2. If high-risk (< 50), trigger real-time notification
                if t_score < 50:
                    self.send_compliance_alert(settings, invoice)
                    alert_count += 1

            except Exception as e:
                self.app.logger.error(f"Error auditing invoice {invoice.id} in background: {e}")

        # Add scheduler log
        add_scheduler_log(
            "SUCCESS",
            f"Kiểm toán tự động hoàn thành. Đã kiểm tra {audited_count} hóa đơn mới, "
            f"phát hiện {alert_count} hóa đơn rủi ro cao."
        )

    def send_compliance_alert(self, settings: dict, invoice):
        """Send alert via Email (SMTP) and/or Telegram if configured."""
        recipient = settings.get("recipient_email")
        telegram_enabled = settings.get("telegram_enabled", False)
        
        # Assemble list of all warnings (smart audits + AI warnings)
        warnings_list = []
        try:
            if invoice.warnings:
                warnings_list.extend(invoice.warnings)
        except Exception:
            pass

        try:
            if invoice.ai_audit_results:
                for w in invoice.ai_audit_results:
                    warnings_list.append(w.explanation)
        except Exception:
            pass
            
        warnings_str = "\n".join([f"- {w}" for w in warnings_list]) if warnings_list else "- Không phát hiện lỗi cụ thể."

        # 1. Send Telegram Alert
        if telegram_enabled:
            bot_token = settings.get("telegram_bot_token")
            chat_id = settings.get("telegram_chat_id")
            
            # Decrypt bot token if it is encrypted
            if bot_token:
                try:
                    from auth.crypto import decrypt_password
                    if bot_token.startswith("gAAAAA"):
                        bot_token = decrypt_password(bot_token)
                except Exception:
                    pass

            if bot_token and chat_id:
                try:
                    import requests
                    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                    text_message = (
                        f"⚠️ *CẢNH BÁO KIỂM TOÁN THUẾ* ⚠️\n\n"
                        f"Hệ thống phát hiện hóa đơn rủi ro cao!\n"
                        f"*Mã HĐ:* `{invoice.id}`\n"
                        f"*Số HĐ:* {invoice.number}\n"
                        f"*Ngày HĐ:* {invoice.date}\n"
                        f"*Người bán:* {invoice.seller_name}\n"
                        f"*MST Người bán:* {invoice.seller_mst}\n"
                        f"*Tổng tiền:* {invoice.total_amount:,.0f} VND\n"
                        f"*T-Score:* {invoice.t_score} ({invoice.t_rating})\n\n"
                        f"*Danh sách lỗi phát hiện:*\n{warnings_str}"
                    )
                    payload = {
                        "chat_id": chat_id,
                        "text": text_message,
                        "parse_mode": "Markdown"
                    }
                    resp = requests.post(url, json=payload, timeout=10)
                    resp.raise_for_status()
                    self.app.logger.info(f"Telegram alert sent for invoice {invoice.id}")
                except Exception as ex:
                    self.app.logger.error(f"Failed to send Telegram alert: {ex}")

        # 2. Send SMTP Email Alert
        if recipient and settings.get("smtp_host"):
            try:
                smtp_host = settings.get("smtp_host")
                smtp_port = int(settings.get("smtp_port", 587))
                smtp_user = settings.get("smtp_user")
                smtp_pass_enc = settings.get("smtp_pass")
                smtp_use_tls = settings.get("smtp_use_tls", True)
                try:
                    from auth.crypto import decrypt_password
                    smtp_pass = decrypt_password(smtp_pass_enc)
                except Exception:
                    smtp_pass = smtp_pass_enc

                msg = MIMEMultipart()
                msg["From"] = smtp_user
                msg["To"] = recipient
                msg["Subject"] = f"[CẢNH BÁO] Phát hiện Hóa Đơn Rủi Ro Cao ({invoice.t_rating}) - Số {invoice.number}"

                # Render HTML warning email
                warnings_html = "".join([f"<li style='margin-bottom: 8px; color: #dc2626;'>{w}</li>" for w in warnings_list]) if warnings_list else "<li>Không phát hiện lỗi cụ thể.</li>"
                
                html_body = f"""
                <html>
                <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #1e293b; line-height: 1.6; background-color: #fef2f2; padding: 20px;">
                    <div style="max-width: 600px; margin: 0 auto; border: 1px solid #fee2e2; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 10px rgba(220, 38, 38, 0.1); background-color: #ffffff;">
                        <div style="background-color: #991b1b; color: #ffffff; padding: 30px; text-align: center;">
                            <h2 style="margin: 0; font-size: 22px; font-weight: 600; letter-spacing: 0.5px;">⚠️ CẢNH BÁO KIỂM TOÁN RỦI RO</h2>
                            <p style="margin: 6px 0 0 0; opacity: 0.9; font-size: 14px;">Mã hóa đơn: {invoice.id}</p>
                        </div>
                        <div style="padding: 30px;">
                            <p style="font-size: 16px; margin-top: 0; font-weight: 600; color: #991b1b;">Phát hiện hóa đơn có chỉ số tuân thủ thuế cực thấp!</p>
                            
                            <div style="background-color: #fef2f2; border-radius: 8px; padding: 20px; margin: 24px 0; border-left: 5px solid #dc2626;">
                                <table style="width: 100%; border-collapse: collapse; font-size: 14px; color: #334155;">
                                    <tr>
                                        <td style="padding: 6px 0; color: #64748b;">Số Hóa Đơn:</td>
                                        <td style="padding: 6px 0; text-align: right; font-weight: 600; color: #0f172a;">{invoice.number}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 6px 0; color: #64748b;">Ngày Hóa Đơn:</td>
                                        <td style="padding: 6px 0; text-align: right; font-weight: 600; color: #0f172a;">{invoice.date}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 6px 0; color: #64748b;">Người Bán (Seller):</td>
                                        <td style="padding: 6px 0; text-align: right; font-weight: 600; color: #0f172a;">{invoice.seller_name}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 6px 0; color: #64748b;">MST Người Bán:</td>
                                        <td style="padding: 6px 0; text-align: right; font-weight: 600; color: #0f172a;">{invoice.seller_mst}</td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 6px 0; color: #64748b;">Tổng Giá Trị:</td>
                                        <td style="padding: 6px 0; text-align: right; font-weight: 600; color: #0f172a;">{invoice.total_amount:,.0f} VND</td>
                                    </tr>
                                    <tr style="border-top: 1px solid #fee2e2;">
                                        <td style="padding: 12px 0 0 0; font-weight: 700; color: #991b1b; font-size: 15px;">Chỉ Số Tuân Thủ T-Score:</td>
                                        <td style="padding: 12px 0 0 0; text-align: right; font-weight: 700; color: #dc2626; font-size: 18px;">{invoice.t_score} ({invoice.t_rating})</td>
                                    </tr>
                                </table>
                            </div>

                            <h4 style="margin: 20px 0 10px 0; color: #991b1b; font-size: 16px;">Các lỗi tuân thủ & cảnh báo phát hiện:</h4>
                            <ul style="padding-left: 20px; margin: 0; font-size: 14px; color: #334155;">
                                {warnings_html}
                            </ul>
                            
                            <div style="margin-top: 40px; border-top: 1px solid #e2e8f0; padding-top: 15px; font-size: 12px; color: #94a3b8;">
                                <p style="margin: 0 0 4px 0;">Email cảnh báo thời gian thực được gửi tự động bởi GDT Invoice Hub.</p>
                            </div>
                        </div>
                    </div>
                </body>
                </html>
                """
                msg.attach(MIMEText(html_body, "html"))
                self.send_smtp_message(smtp_host, smtp_port, smtp_user, smtp_pass, smtp_use_tls, recipient, msg)
                self.app.logger.info(f"Email compliance alert sent for invoice {invoice.id}")
            except Exception as ex:
                self.app.logger.error(f"Failed to send Email compliance alert: {ex}")


def start_scheduler_worker(app) -> None:
    """Initialize and run the background scheduler worker."""
    global _scheduler_thread
    if _scheduler_thread is not None and _scheduler_thread.is_alive():
        return
    _scheduler_thread = SchedulerThread(app)
    _scheduler_thread.start()


def stop_scheduler_worker() -> None:
    """Stop the background scheduler worker thread."""
    global _scheduler_thread
    if _scheduler_thread is not None:
        _scheduler_thread.stop()
        _scheduler_thread.join(timeout=5)
        _scheduler_thread = None


def trigger_scheduled_export_job(app) -> None:
    """Manually trigger the scheduled export job using loaded configurations."""
    with app.app_context():
        settings = load_scheduler_settings()
        thread = SchedulerThread(app)
        thread.execute_scheduled_report(settings, datetime.now())

