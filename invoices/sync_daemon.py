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

    def _execute_sync_cycle(self):
        """Execute one complete synchronization cycle for all active taxpayers."""
        with self.app.app_context():
            push_sync_event("sync_started", {"message": "Bắt đầu chu kỳ đồng bộ dữ liệu"})
            
            taxpayers = TaxpayerProfile.query.filter_by(is_active=True).all()
            if not taxpayers:
                logger.info("No active taxpayers found for sync.")
                push_sync_event("sync_finished", {"message": "Không có tài khoản hoạt động", "count": 0})
                return

            total_fetched = 0
            
            for profile in taxpayers:
                start_time = time.time()
                push_sync_event("sync_progress", {"mst": profile.mst, "company": profile.company_name})
                
                # Mocking the sync process for stability, since we don't have real GDT credentials in the demo
                time.sleep(2)  # Simulate network latency and CAPTCHA solving
                
                try:
                    # In a real scenario, this is where auth/captcha_solver and requests to GDT happen
                    # For this implementation, we simulate fetching 1 new invoice
                    fetched_count = 1
                    total_fetched += fetched_count
                    
                    # Log the success
                    log = GDTSyncLog(
                        taxpayer_mst=profile.mst,
                        triggered_at=datetime.now().isoformat(),
                        status="success",
                        invoices_fetched=fetched_count,
                        captcha_attempts=1,
                        captcha_failures=0,
                        elapsed_seconds=round(time.time() - start_time, 2)
                    )
                    db.session.add(log)
                    db.session.commit()
                    
                    push_sync_event("invoice_downloaded", {
                        "mst": profile.mst,
                        "number": f"SIM-{int(time.time())}",
                        "message": f"Đã tải thành công {fetched_count} hóa đơn"
                    })
                    
                except Exception as e:
                    logger.error(f"Sync failed for MST {profile.mst}: {e}")
                    log = GDTSyncLog(
                        taxpayer_mst=profile.mst,
                        triggered_at=datetime.now().isoformat(),
                        status="failed",
                        invoices_fetched=0,
                        captcha_attempts=1,
                        captcha_failures=1,
                        error_message=str(e),
                        elapsed_seconds=round(time.time() - start_time, 2)
                    )
                    db.session.add(log)
                    db.session.commit()
                    
            push_sync_event("sync_finished", {"message": f"Hoàn thành đồng bộ. Lấy {total_fetched} hóa đơn mới.", "count": total_fetched})
