"""Signed Webhook Dispatcher Hub with Exponential Retries (US-123).

Signs payloads using HMAC-SHA256 secret keys and delivers events asynchronously
with automatic exponential backoff retry rules and delivery auditing logs.
"""

from __future__ import annotations

import hmac
import hashlib
import json
import time
import logging
import threading
import requests
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class WebhookHub:
    """Enterprise-grade secure Webhook Dispatcher Hub."""

    def __init__(self, db_session=None, max_workers: int = 4):
        self.db_session = db_session
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="GDT-Webhook-Worker")
        self.initial_delay = 1.0  # seconds
        self.backoff_factor = 2.0
        self.max_attempts = 4
        self.timeout = 5.0  # seconds

    def compute_signature(self, secret: str, timestamp: int, payload_str: str) -> str:
        """Compute the HMAC-SHA256 signature for secure webhook payload validation."""
        message = f"{timestamp}.{payload_str}".encode("utf-8")
        signature = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
        return f"sha256={signature}"

    def trigger(self, url: str, secret: str, event_topic: str, payload: dict, subscription_id: str = "custom_sub"):
        """Asynchronously trigger the webhook delivery using the worker pool."""
        self.executor.submit(
            self._deliver_with_retry,
            url,
            secret,
            event_topic,
            payload,
            subscription_id,
            attempt=1
        )

    def _deliver_with_retry(
        self,
        url: str,
        secret: str,
        event_topic: str,
        payload: dict,
        subscription_id: str,
        attempt: int
    ):
        """Perform synchronous HTTP POST delivery of signed webhook payload with retry logic."""
        timestamp = int(time.time())
        payload_str = json.dumps(payload, ensure_ascii=False)
        signature = self.compute_signature(secret, timestamp, payload_str)

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "X-GDT-Signature": signature,
            "X-GDT-Timestamp": str(timestamp),
            "User-Agent": "GDT-Invoice-Hub-Webhook-Agent/9.0.0",
        }

        success = False
        status_code = None
        error_msg = None

        try:
            response = requests.post(
                url,
                data=payload_str.encode("utf-8"),
                headers=headers,
                timeout=self.timeout
            )
            status_code = response.status_code
            if 200 <= status_code < 300:
                success = True
            else:
                error_msg = f"HTTP Error status code: {status_code}"
        except Exception as e:
            error_msg = str(e)

        # Log delivery attempt (audit trail)
        self._log_delivery(
            subscription_id=subscription_id,
            event_topic=event_topic,
            payload=payload_str,
            attempt_number=attempt,
            status_code=status_code,
            success=success,
            error_message=error_msg
        )

        if success:
            logger.info(f"Webhook delivered successfully to {url} (Topic: {event_topic})")
            return

        # Perform retry with exponential backoff if failed and max attempts not exceeded
        if attempt < self.max_attempts:
            delay = self.initial_delay * (self.backoff_factor ** (attempt - 1))
            logger.warning(
                f"Webhook attempt {attempt} to {url} failed. "
                f"Retrying in {delay}s (Error: {error_msg})"
            )
            # Spawn scheduled task or sleep & retry in worker thread
            time.sleep(delay)
            self._deliver_with_retry(
                url,
                secret,
                event_topic,
                payload,
                subscription_id,
                attempt=attempt + 1
            )
        else:
            logger.error(f"Webhook to {url} permanently failed after {self.max_attempts} attempts.")

    def _log_delivery(
        self,
        subscription_id: str,
        event_topic: str,
        payload: str,
        attempt_number: int,
        status_code: int | None,
        success: bool,
        error_message: str | None
    ):
        """Durable persistence or console log fallback for audit auditing."""
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        # If running inside Flask application with active session, save to db
        if self.db_session:
            try:
                from invoices.models import WebhookDeliveryLog
                log = WebhookDeliveryLog(
                    subscription_id=subscription_id,
                    event_topic=event_topic,
                    payload=payload,
                    attempt_number=attempt_number,
                    status_code=status_code,
                    success=success,
                    error_message=error_message,
                    timestamp=now
                )
                self.db_session.add(log)
                self.db_session.commit()
            except Exception as e:
                logger.error(f"Failed to log webhook delivery to DB: {e}")
        else:
            # Standalone mode / testing logger callback
            logger.debug(
                f"[WEBHOOK AUDIT] Sub: {subscription_id} | Topic: {event_topic} | "
                f"Attempt: {attempt_number} | Success: {success} | Status: {status_code}"
            )

    def shutdown(self):
        """Shut down the ThreadPoolExecutor gracefully."""
        self.executor.shutdown(wait=True)
