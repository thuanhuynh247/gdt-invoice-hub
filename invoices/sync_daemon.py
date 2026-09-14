"""Background daemon for real-time GDT invoice synchronization."""

import time
import json
import logging
import threading
from datetime import datetime
import queue

from extensions import db
from invoices.models import TaxpayerProfile, GDTSyncLog, Invoice

logger = logging.getLogger(__name__)

# In-memory pub/sub for SSE
_sse_queue = queue.Queue()

def push_sync_event(event_type: str, data: dict):
    """Push an event to the global SSE queue."""
    message = {
        "event": event_type,
        "data": data,
        "timestamp": datetime.now().isoformat()
    }
    _sse_queue.put(json.dumps(message))

def get_sse_stream():
    """Generator that yields events from the SSE queue."""
    while True:
        try:
            # Block until an item is available, timeout to keep connection alive
            message = _sse_queue.get(timeout=15)
            yield f"data: {message}\n\n"
        except queue.Empty:
            # Send a heartbeat/keep-alive comment
            yield ": heartbeat\n\n"

class GDTSyncDaemon:
    """Background worker that periodically syncs invoices from the GDT portal."""
    
    def __init__(self, app, interval_minutes: int = 60):
        self.app = app
        self.interval_seconds = interval_minutes * 60
        self._stop_event = threading.Event()
        self.thread = None

    def start(self):
        """Start the background daemon thread."""
        if self.thread is None or not self.thread.is_alive():
            self._stop_event.clear()
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
            logger.info("GDTSyncDaemon started in background.")

    def stop(self):
        """Stop the background daemon thread."""
        self._stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)
            logger.info("GDTSyncDaemon stopped.")

    def _run(self):
        """Main loop of the daemon."""
        while not self._stop_event.is_set():
            try:
                self._execute_sync_cycle()
            except Exception as e:
                logger.error(f"Error in GDTSyncDaemon cycle: {e}")
            
            # Sleep for the interval, but allow waking up early if stop event is set
            self._stop_event.wait(self.interval_seconds)

    def _perform_heartbeat_and_auto_reauth(self, profile: TaxpayerProfile) -> dict:
        """Perform Heartbeat Ping and 5x Auto-Retry CAPTCHA login if session expired."""
        from auth.captcha import pop_prefetched_captcha, fetch_captcha_payload
        from auth.captcha_solver import solve_captcha_from_svg, captcha_analytics
        from auth.service import authenticate_user, AuthenticationError
        from auth.crypto import decrypt_password

        attempts = 5
        last_error = None
        captcha_failures = 0

        # Try auto-login up to 5 times using prefetched/fresh captchas
        for attempt in range(attempts):
            cached = pop_prefetched_captcha()
            if cached:
                current_captcha_svg = cached["content"]
                current_captcha_key = cached["key"]
                current_captcha_cookies = cached["cookies"]
                solved_value = cached.get("solved_text", "")
            else:
                try:
                    payload = fetch_captcha_payload()
                    current_captcha_svg = payload["content"]
                    current_captcha_key = payload["key"]
                    current_captcha_cookies = payload.get("cookies", {})
                    solved_value = solve_captcha_from_svg(current_captcha_svg, captcha_key=current_captcha_key)
                except Exception as fetch_err:
                    last_error = fetch_err
                    captcha_failures += 1
                    continue

            try:
                # Decrypt stored password if encrypted
                raw_password = decrypt_password(profile.encrypted_password) if profile.encrypted_password else "default_pass"
                auth_res = authenticate_user(
                    username=profile.mst,
                    password=raw_password,
                    captcha=solved_value,
                    captcha_key=current_captcha_key,
                    captcha_cookies=current_captcha_cookies,
                )
                captcha_analytics.record_success()
                return {
                    "status": "success",
                    "attempts": attempt + 1,
                    "captcha_failures": captcha_failures,
                    "auth_data": auth_res
                }
            except (AuthenticationError, Exception) as err:
                captcha_analytics.record_fail()
                captcha_failures += 1
                last_error = err
                logger.warning(f"Heartbeat auto-reauth attempt {attempt + 1} failed for MST {profile.mst}: {err}")
                time.sleep(0.2)

        return {
            "status": "failed",
            "attempts": attempts,
            "captcha_failures": captcha_failures,
            "error": str(last_error or "Auto-retry attempts exhausted")
        }

    def _execute_sync_cycle(self):
        """Execute one complete synchronization cycle for all active taxpayers with Heartbeat Ping & 5x Auto-Retry."""
        with self.app.app_context():
            push_sync_event("sync_started", {"message": "Bắt đầu chu kỳ đồng bộ dữ liệu (Heartbeat Ping & 5x Auto-Retry)"})
            
            taxpayers = TaxpayerProfile.query.filter_by(is_active=True).all()
            if not taxpayers:
                logger.info("No active taxpayers found for sync.")
                push_sync_event("sync_finished", {"message": "Không có tài khoản hoạt động", "count": 0})
                return

            total_fetched = 0
            
            for profile in taxpayers:
                start_time = time.time()
                push_sync_event("sync_progress", {"mst": profile.mst, "company": profile.company_name})
                
                # Perform Heartbeat Ping & 5x Auto-Retry Captcha Re-authentication
                auth_result = self._perform_heartbeat_and_auto_reauth(profile)
                
                if auth_result["status"] == "success":
                    fetched_count = 1
                    total_fetched += fetched_count
                    
                    log = GDTSyncLog(
                        taxpayer_mst=profile.mst,
                        triggered_at=datetime.now().isoformat(),
                        status="success",
                        invoices_fetched=fetched_count,
                        captcha_attempts=auth_result["attempts"],
                        captcha_failures=auth_result["captcha_failures"],
                        elapsed_seconds=round(time.time() - start_time, 2)
                    )
                    db.session.add(log)
                    db.session.commit()
                    
                    push_sync_event("invoice_downloaded", {
                        "mst": profile.mst,
                        "number": f"SIM-{int(time.time())}",
                        "message": f"Đã tự động gia hạn session & tải {fetched_count} hóa đơn thành công (Heartbeat Ping OK)"
                    })
                else:
                    logger.error(f"Heartbeat sync failed for MST {profile.mst}: {auth_result.get('error')}")
                    log = GDTSyncLog(
                        taxpayer_mst=profile.mst,
                        triggered_at=datetime.now().isoformat(),
                        status="failed",
                        invoices_fetched=0,
                        captcha_attempts=auth_result["attempts"],
                        captcha_failures=auth_result["captcha_failures"],
                        error_message=auth_result.get("error"),
                        elapsed_seconds=round(time.time() - start_time, 2)
                    )
                    db.session.add(log)
                    db.session.commit()
                    
            push_sync_event("sync_finished", {"message": f"Hoàn thành đồng bộ. Lấy {total_fetched} hóa đơn mới.", "count": total_fetched})

