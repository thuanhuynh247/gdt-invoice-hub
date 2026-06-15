"""Module for managing background worker threads and sync daemons."""

import os
from flask import Flask

def init_background_workers(app: Flask) -> None:
    """Initialize all background worker threads and sync daemons for the application.
    
    This abstracts background threads away from the main app factory to prevent
    pollution of app.py and simplify lifecycle management.
    """
    if app.config.get("TESTING") or os.getenv("TESTING") == "True":
        return

    # 1. Captcha prefetch worker
    if os.getenv("ENABLE_CAPTCHA_PREFETCH", "true").lower() == "true":
        try:
            from auth.captcha import start_captcha_prefetch_worker
            start_captcha_prefetch_worker(app)
            app.logger.info("Initialized Captcha Prefetch Worker background thread.")
        except Exception as e:
            app.logger.error(f"Failed to start Captcha Prefetch Worker: {e}")

    # 2. Scheduler worker
    if os.getenv("ENABLE_SCHEDULER_WORKER", "true").lower() == "true":
        try:
            from invoices.scheduler import start_scheduler_worker
            start_scheduler_worker(app)
            app.logger.info("Initialized Scheduler Worker background thread.")
        except Exception as e:
            app.logger.error(f"Failed to start Scheduler Worker: {e}")

    # 3. Dynamic PDF ingestion thread
    if os.getenv("ENABLE_PDF_INGESTION", "true").lower() == "true":
        try:
            from invoices.ai_service import start_dynamic_pdf_ingestion_thread
            start_dynamic_pdf_ingestion_thread(app)
            app.logger.info("Initialized Dynamic PDF Ingestion background thread.")
        except Exception as e:
            app.logger.error(f"Failed to start Dynamic PDF Ingestion thread: {e}")

    # 4. GDT Sync Daemon
    if os.getenv("ENABLE_SYNC_DAEMON", "true").lower() == "true":
        try:
            from invoices.sync_daemon import GDTSyncDaemon
            daemon = GDTSyncDaemon(app, interval_minutes=1)
            daemon.start()
            app.logger.info("Initialized GDTSyncDaemon background thread (1m interval).")
        except Exception as e:
            app.logger.error(f"Failed to start GDTSyncDaemon: {e}")
