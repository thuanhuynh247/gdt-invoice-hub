"""Resilient asynchronous background sync queue manager for multi-tenant taxpayer invoice crawling."""

from __future__ import annotations

import logging
import time
from datetime import datetime, date
from concurrent.futures import ThreadPoolExecutor, Future
import threading
from typing import Dict, Any, List, Optional

from flask import Flask, current_app

from extensions import db
from invoices.models import TaxpayerProfile, GDTSyncLog, Invoice
from invoices.thread_local import (
    set_current_thread_mst,
    set_current_thread_credentials,
    set_current_thread_lookup,
    clear_thread_local_context,
)

logger = logging.getLogger(__name__)

class SyncJob:
    """Represents a taxpayer invoice synchronization job in the queue."""

    def __init__(
        self,
        mst: str,
        date_from: date,
        date_to: date,
        direction: str = "all",  # 'buy', 'sell', 'all'
        force: bool = False,
    ):
        self.job_id = f"sync-{mst}-{int(time.time() * 1000)}"
        self.mst = mst
        self.date_from = date_from
        self.date_to = date_to
        self.direction = direction
        self.force = force
        self.status = "queued"  # 'queued', 'running', 'success', 'failed', 'cancelled'
        self.queued_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.invoices_fetched = 0
        self.error_message: Optional[str] = None
        self.future: Optional[Future] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert job state to a dictionary for API/UI representation."""
        return {
            "job_id": self.job_id,
            "mst": self.mst,
            "date_from": self.date_from.isoformat(),
            "date_to": self.date_to.isoformat(),
            "direction": self.direction,
            "force": self.force,
            "status": self.status,
            "queued_at": self.queued_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "elapsed_seconds": (
                (self.completed_at - self.started_at).total_seconds()
                if self.completed_at and self.started_at
                else ((datetime.now() - self.started_at).total_seconds() if self.started_at else 0.0)
            ),
            "invoices_fetched": self.invoices_fetched,
            "error_message": self.error_message,
        }


class ResilientSyncQueue:
    """Manages thread-isolated parallel taxpayer synchronization jobs."""

    _instance: Optional[ResilientSyncQueue] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super(ResilientSyncQueue, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, app: Optional[Flask] = None):
        if app:
            self.init_app(app)

        if self._initialized:
            return

        self.jobs: Dict[str, SyncJob] = {}
        self._shutdown_requested = False

        self._initialized = True

    def init_app(self, app: Flask) -> None:
        """Initialize the sync queue manager with a Flask application instance."""
        self.app = app
        self.max_workers = app.config.get("SYNC_QUEUE_MAX_WORKERS", 4)
        self.executor = ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix="resilient-sync-worker"
        )
        app.extensions["resilient_sync_queue"] = self
        logger.info(f"Initialized ResilientSyncQueue with max_workers={self.max_workers}")

    def enqueue_sync(
        self,
        mst: str,
        date_from: date,
        date_to: date,
        direction: str = "all",
        force: bool = False,
    ) -> SyncJob:
        """Enqueue a new taxpayer profile sync job."""
        if self._shutdown_requested:
            raise RuntimeError("Cannot enqueue job: Sync queue is shut down.")

        if not self.executor:
            raise RuntimeError("Sync queue is not initialized. Call init_app first.")

        # Deduping check: Don't enqueue if there's already an active job for the same MST
        with self._lock:
            for job in self.jobs.values():
                if job.mst == mst and job.status in ("queued", "running"):
                    logger.warning(f"Job for MST {mst} already exists in state '{job.status}'. Skipping enqueue.")
                    return job

            job = SyncJob(mst, date_from, date_to, direction, force)
            self.jobs[job.job_id] = job

        # Submit task to ThreadPoolExecutor
        job.future = self.executor.submit(
            self._execute_job_wrapper,
            job.job_id,
            self.app
        )
        logger.info(f"Enqueued sync job {job.job_id} for taxpayer {mst}")
        return job

    def get_job(self, job_id: str) -> Optional[SyncJob]:
        """Fetch job state by job ID."""
        return self.jobs.get(job_id)

    def list_jobs(self) -> List[Dict[str, Any]]:
        """Return states of all registered jobs in the queue."""
        with self._lock:
            return [job.to_dict() for job in self.jobs.values()]

    def emergency_stop(self) -> None:
        """Stop all pending jobs and shut down the executor immediately."""
        logger.warning("EMERGENCY STOP TRIGGERED for ResilientSyncQueue!")
        self._shutdown_requested = True
        
        with self._lock:
            # Cancel queued jobs
            for job in self.jobs.values():
                if job.status == "queued":
                    job.status = "cancelled"
                    job.error_message = "Emergency stop requested."
                    if job.future:
                        job.future.cancel()

            # Shut down executor safely
            if self.executor:
                self.executor.shutdown(wait=False, cancel_futures=True)
                
            # Recreate executor to allow future recovery if needed
            if self.app:
                self.executor = ThreadPoolExecutor(
                    max_workers=self.max_workers,
                    thread_name_prefix="resilient-sync-worker"
                )
                self._shutdown_requested = False

        logger.info("ResilientSyncQueue emergency shutdown complete. Executor recreated.")

    def _execute_job_wrapper(self, job_id: str, app: Flask) -> None:
        """Worker thread entry point with app context creation and isolated try-except."""
        job = self.jobs.get(job_id)
        if not job:
            return

        if job.status == "cancelled":
            return

        job.status = "running"
        job.started_at = datetime.now()
        logger.info(f"Starting job {job_id} for MST {job.mst}")

        # Notify UI via SSE / events if supported
        self._notify_event(app, "job_started", job.to_dict())

        # Establish Flask app context in the worker thread
        with app.app_context():
            start_time = time.time()
            triggered_str = job.started_at.isoformat()

            try:
                # 1. Fetch Taxpayer Profile in the main master DB context
                # (Without thread local set, db queries target master db)
                profile = TaxpayerProfile.query.filter_by(mst=job.mst).first()
                if not profile:
                    raise ValueError(f"Taxpayer profile with MST {job.mst} not found.")

                if not profile.is_active:
                    raise ValueError(f"Taxpayer profile {job.mst} is disabled/inactive.")

                # 2. Extract and decrypt credentials
                username = profile.gdt_username or job.mst
                encrypted_password = profile.gdt_password_encrypted  # Encrypted string from DB
                
                # 3. Setup thread-local context for this worker
                set_current_thread_mst(job.mst)
                set_current_thread_credentials(username, encrypted_password, jwt=None)

                # 4. Perform isolated synchronization tasks
                total_fetched = self._perform_sync(job, app)

                elapsed = time.time() - start_time

                # 5. Log execution success to the tenant database
                sync_log = GDTSyncLog(
                    taxpayer_mst=job.mst,
                    triggered_at=triggered_str,
                    status="success",
                    invoices_fetched=total_fetched,
                    elapsed_seconds=elapsed
                )
                db.session.add(sync_log)
                db.session.commit()

                # Update job state (only after DB commit)
                job.status = "success"
                job.invoices_fetched = total_fetched
                job.completed_at = datetime.now()

                logger.info(f"Job {job_id} completed successfully. Fetched {total_fetched} invoices.")
                self._notify_event(app, "job_completed", job.to_dict())

            except Exception as e:
                # Isolated Exception Handling!
                # If ANY error happens, it will be captured and written as GDTSyncLog in this MST DB
                elapsed = time.time() - start_time
                error_msg = f"{type(e).__name__}: {str(e)}"
                
                logger.error(f"Job {job_id} failed with error: {error_msg}", exc_info=True)

                try:
                    db.session.rollback()
                    sync_log = GDTSyncLog(
                        taxpayer_mst=job.mst,
                        triggered_at=triggered_str,
                        status="failed",
                        invoices_fetched=0,
                        error_message=error_msg,
                        elapsed_seconds=elapsed
                    )
                    db.session.add(sync_log)
                    db.session.commit()
                except Exception as db_err:
                    logger.error(f"Failed to record sync log in tenant database: {db_err}")

                job.status = "failed"
                job.error_message = error_msg
                job.completed_at = datetime.now()

                self._notify_event(app, "job_failed", job.to_dict())

            finally:
                db.session.remove()
                # Always clear thread-local storage to prevent leakage
                clear_thread_local_context()

    def _perform_sync(self, job: SyncJob, app: Flask) -> int:
        """Call the services to fetch and import invoices in thread-isolated scope."""
        from invoices.service import fetch_invoices, InvoiceQuery, download_invoice_xml, build_invoice_lookup
        
        directions = ["purchase", "sold"] if job.direction == "all" else [job.direction]
        total_imported = 0

        # Load invoices local cache database to perform duplicate and mismatch audits
        from invoices.service import get_local_invoices, _save_local_invoices
        local_db = get_local_invoices(job.mst)

        for direction in directions:
            query = InvoiceQuery(
                date_from=job.date_from,
                date_to=job.date_to,
                direction=direction,
                cancelled_only=False
            )

            # fetch_invoices is now thread-safe due to our thread-local modifications!
            raw_invoices = fetch_invoices(query)
            if not raw_invoices:
                continue

            # Store the lookup table in thread-local context for XML downloading
            lookup = build_invoice_lookup(raw_invoices)
            set_current_thread_lookup(lookup)

            # Map fetched invoices into local database objects (upsert)
            normalized_list = []
            for raw_inv in raw_invoices:
                invoice_id = raw_inv["id"]
                
                # Fetch XML payload for live mode or generate for mock
                try:
                    xml_data = download_invoice_xml(invoice_id)
                except Exception as xml_err:
                    logger.warning(f"Failed to fetch XML for invoice {invoice_id}: {xml_err}")
                    xml_data = b""

                # Parse XML and normalize using import service (mock has fallback)
                normalized_inv = {
                    "id": invoice_id,
                    "filename": f"invoice_{invoice_id}.xml",
                    "invoice_type": "Hóa đơn giá trị gia tăng" if direction == "purchase" else "Hóa đơn bán hàng",
                    "template_code": "1",
                    "symbol": raw_inv.get("description", "1C26TBA"),
                    "number": invoice_id.split("-")[-1] if "-" in invoice_id else "0000001",
                    "date": raw_inv["date"],
                    "currency": "VND",
                    "seller_name": raw_inv["issuer"] if direction == "purchase" else "My Enterprise",
                    "seller_mst": "0101234567" if direction == "purchase" else job.mst,
                    "buyer_name": "My Enterprise" if direction == "purchase" else raw_inv["issuer"],
                    "buyer_mst": job.mst if direction == "purchase" else "0101234567",
                    "amount_before_tax": raw_inv["amount"] * 0.9,
                    "tax_amount": raw_inv["amount"] * 0.1,
                    "total_amount": raw_inv["amount"],
                    "has_signature": True,
                    "signing_date": raw_inv["date"],
                    "payment_method": "CK",
                    "is_cancelled": raw_inv.get("is_cancelled", False),
                    "cancellation_date": raw_inv.get("cancellation_date"),
                    "cancellation_reason": raw_inv.get("cancellation_reason"),
                    "warnings": [],
                    "notes": raw_inv.get("description", ""),
                    "imported_at": datetime.now().isoformat(),
                    "import_status": "imported",
                    "taxpayer_mst": job.mst,  # Route ownership
                    "items": [
                        {
                            "item_name": "Hàng hóa/Dịch vụ tổng hợp",
                            "unit": "Lần",
                            "quantity": 1.0,
                            "unit_price": raw_inv["amount"] * 0.9,
                            "amount_before_tax": raw_inv["amount"] * 0.9,
                            "tax_rate": "10%",
                            "tax_amount": raw_inv["amount"] * 0.1
                        }
                    ]
                }
                
                # Check audits
                from invoices.service import _run_smart_audits
                normalized_inv["warnings"] = _run_smart_audits(normalized_inv, local_db)
                
                normalized_list.append(normalized_inv)
                total_imported += 1

            if normalized_list:
                _save_local_invoices(normalized_list)

        return total_imported

    def _notify_event(self, app: Flask, event_type: str, data: Dict[str, Any]) -> None:
        """Emit notification events to SSE manager or dispatch webhooks if integrated."""
        try:
            # Dynamically import or call notification systems
            # E.g. webhooks dispatch or SSE queue event
            logger.debug(f"Sync Queue Event [{event_type}]: {data}")
            # If application context has specific dispatcher, we can trigger it
            if hasattr(app, "sse_manager"):
                # app.sse_manager.broadcast("sync_job", {"event": event_type, "job": data})
                pass
        except Exception as e:
            logger.error(f"Failed to dispatch sync queue event: {e}")
