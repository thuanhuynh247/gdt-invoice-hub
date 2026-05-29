"""Tests for the Signed Webhook Dispatcher Hub & Retry Engine (US-123)."""

from __future__ import annotations

import time
import pytest
import hmac
import hashlib
import json
from unittest.mock import patch, MagicMock
from invoices.webhook_hub import WebhookHub
from invoices.models import WebhookDeliveryLog
from extensions import db


class TestWebhookHub:
    """US-123: Signed Webhook Deliveries with Auto-Retry & Rate Limiting Test Suite."""

    def test_compute_signature_correctness(self):
        """Verify the HMAC-SHA256 signature generator calculation conforms exactly to standard."""
        hub = WebhookHub()
        secret = "super-secret-key"
        timestamp = 1716940800
        payload = {"event": "invoice.created", "amount": 500000}
        payload_str = json.dumps(payload)

        signature = hub.compute_signature(secret, timestamp, payload_str)
        
        # Calculate manually
        message = f"{timestamp}.{payload_str}".encode("utf-8")
        expected_hash = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
        expected_sig = f"sha256={expected_hash}"

        assert signature == expected_sig

    @patch("requests.post")
    def test_webhook_delivery_success(self, mock_post):
        """Verify a successful webhook dispatch routes payload with correct headers."""
        # Mock 200 OK response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        hub = WebhookHub()
        # Set short wait intervals for testing speed
        hub.initial_delay = 0.01

        payload = {"id": "INV-WEB-001", "total": 10000}
        hub.trigger(
            url="https://api.receiver.com/webhook",
            secret="shhh",
            event_topic="invoice.created",
            payload=payload,
            subscription_id="sub_test_001"
        )
        
        # Graceful thread pool processing wait
        hub.shutdown()

        assert mock_post.call_count == 1
        
        # Verify headers sent
        args, kwargs = mock_post.call_args
        headers = kwargs["headers"]
        assert "X-GDT-Signature" in headers
        assert "X-GDT-Timestamp" in headers
        assert headers["Content-Type"] == "application/json; charset=utf-8"

    @patch("requests.post")
    def test_webhook_retry_backoff(self, mock_post):
        """Verify that failed webhook deliveries trigger exponential backoff retry cycles."""
        # Mock connection failures followed by eventual permanent failure
        mock_post.side_effect = Exception("Connection Timeout")

        hub = WebhookHub()
        hub.initial_delay = 0.001  # extremely fast for testing
        hub.backoff_factor = 2.0
        hub.max_attempts = 3

        payload = {"id": "INV-WEB-002"}
        
        # Deliver synchronously inside testing to assert exact try count
        hub._deliver_with_retry(
            url="https://api.receiver.com/webhook",
            secret="shhh",
            event_topic="invoice.created",
            payload=payload,
            subscription_id="sub_test_002",
            attempt=1
        )

        # Should attempt 3 times (1 initial + 2 retries)
        assert mock_post.call_count == 3

    def test_webhook_db_logging(self, app):
        """Verify that webhook dispatch operations save auditable traces in the database."""
        with app.app_context():
            # Clean old logs
            WebhookDeliveryLog.query.delete()
            db.session.commit()

            hub = WebhookHub(db_session=db.session)
            
            # Manually trigger a logged delivery success
            hub._log_delivery(
                subscription_id="sub_enterprise_001",
                event_topic="invoice.audited",
                payload='{"id": "INV-1"}',
                attempt_number=1,
                status_code=200,
                success=True,
                error_message=None
            )

            # Assert DB record exists
            log = WebhookDeliveryLog.query.filter_by(subscription_id="sub_enterprise_001").first()
            assert log is not None
            assert log.event_topic == "invoice.audited"
            assert log.attempt_number == 1
            assert log.status_code == 200
            assert log.success is True

            # Cleanup
            WebhookDeliveryLog.query.delete()
            db.session.commit()
