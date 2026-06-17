"""Captcha helpers for mock mode and live GDT integration."""

from __future__ import annotations

import html
import logging
import threading
import time
from datetime import datetime, timezone

import requests
from flask import current_app

# Thread-safe CAPTCHA prefetch queue configurations
CAPTCHA_QUEUE = []
CAPTCHA_LOCK = threading.Lock()
PREFETCH_WORKER_THREAD = None
PREFETCH_WORKER_STOP = False

logger = logging.getLogger(__name__)


def fetch_captcha_payload() -> dict:
    """Fetch captcha metadata from GDT or return a deterministic mock payload."""

    if current_app.config["GDT_USE_MOCK"]:
        return {
            "key": "mock-captcha-key",
            "content": _build_mock_svg("MOCK"),
            "cookies": {},
        }

    from auth.gdt_client import gdt_request
    response = gdt_request(
        "GET",
        "api/captcha",
    )
    response.raise_for_status()
    data = response.json()
    return {
        "key": data["key"],
        "content": data["content"],
        "cookies": response.cookies.get_dict(),
    }


def _build_mock_svg(text: str) -> str:
    """Create a simple SVG captcha for local mock mode."""

    safe_text = html.escape(text)
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="48">'
        '<rect width="100%" height="100%" fill="#dce8f3" rx="10" ry="10"/>'
        '<text x="50%" y="58%" dominant-baseline="middle" text-anchor="middle" '
        'font-size="24" font-family="monospace" fill="#1f4e78">'
        f"{safe_text}"
        "</text></svg>"
    )


def pop_prefetched_captcha() -> dict | None:
    """Pop a fresh, valid solved captcha from the queue if available."""
    global CAPTCHA_QUEUE
    with CAPTCHA_LOCK:
        now = datetime.now(timezone.utc)
        # Prune expired captchas (> 120s old)
        CAPTCHA_QUEUE[:] = [
            c for c in CAPTCHA_QUEUE
            if (now - c["created_at"]).total_seconds() < 120
        ]
        if CAPTCHA_QUEUE:
            return CAPTCHA_QUEUE.pop(0)
    return None


def _captcha_prefetch_worker(app):
    """Background daemon loop that solves captchas and keeps the queue populated."""
    global PREFETCH_WORKER_STOP, CAPTCHA_QUEUE
    time.sleep(1)  # Initial grace delay
    backoff_delay = 1.0

    while not PREFETCH_WORKER_STOP:
        try:
            with app.app_context():
                if not app.config.get("AUTO_SOLVE_CAPTCHA"):
                    time.sleep(5)
                    continue

                # Prune and check size under lock
                with CAPTCHA_LOCK:
                    now = datetime.now(timezone.utc)
                    CAPTCHA_QUEUE[:] = [
                        c for c in CAPTCHA_QUEUE
                        if (now - c["created_at"]).total_seconds() < 120
                    ]
                    queue_size = len(CAPTCHA_QUEUE)

                if queue_size < 2:
                    payload = fetch_captcha_payload()

                    # Solve offline using captcha_solver
                    from auth.captcha_solver import solve_captcha_from_svg
                    solved_text = solve_captcha_from_svg(payload["content"])

                    new_item = {
                        "key": payload["key"],
                        "content": payload["content"],
                        "cookies": payload.get("cookies", {}),
                        "solved_text": solved_text,
                        "created_at": datetime.now(timezone.utc)
                    }

                    with CAPTCHA_LOCK:
                        CAPTCHA_QUEUE.append(new_item)
                        app.logger.info(
                            f"Prefetched solved CAPTCHA: '{solved_text}'. "
                            f"Queue size: {len(CAPTCHA_QUEUE)}"
                        )
                    # Reset backoff on successful fetch & solve
                    backoff_delay = 1.0

            # Check every second to respond fast when items are consumed
            time.sleep(1)
        except Exception as e:
            try:
                with app.app_context():
                    app.logger.error(
                        f"Error in captcha prefetch worker: {e}. "
                        f"Retrying in {backoff_delay:.1f}s...",
                        exc_info=True
                    )
            except Exception:
                pass
            time.sleep(backoff_delay)
            # Increase backoff exponentially up to 60s
            backoff_delay = min(backoff_delay * 2, 60.0)


def start_captcha_prefetch_worker(app):
    """Launch the background daemon thread for captcha prefetching."""
    global PREFETCH_WORKER_THREAD, PREFETCH_WORKER_STOP
    thread_to_join = None
    with CAPTCHA_LOCK:
        if PREFETCH_WORKER_THREAD is not None and PREFETCH_WORKER_THREAD.is_alive():
            PREFETCH_WORKER_STOP = True
            thread_to_join = PREFETCH_WORKER_THREAD

    if thread_to_join:
        thread_to_join.join(timeout=2.0)

    with CAPTCHA_LOCK:
        PREFETCH_WORKER_STOP = False
        PREFETCH_WORKER_THREAD = threading.Thread(
            target=_captcha_prefetch_worker,
            args=(app,),
            daemon=True,
            name="CaptchaPrefetchWorker"
        )
        PREFETCH_WORKER_THREAD.start()
        app.logger.info("Captcha prefetch daemon worker started.")


def stop_captcha_prefetch_worker():
    """Stop the background daemon thread for captcha prefetching."""
    global PREFETCH_WORKER_STOP, PREFETCH_WORKER_THREAD
    thread_to_join = None
    with CAPTCHA_LOCK:
        PREFETCH_WORKER_STOP = True
        if PREFETCH_WORKER_THREAD is not None:
            thread_to_join = PREFETCH_WORKER_THREAD
            PREFETCH_WORKER_THREAD = None

    if thread_to_join:
        thread_to_join.join(timeout=2.0)



