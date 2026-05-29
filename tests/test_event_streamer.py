"""Tests for the High-Throughput PubSub Event Streamer (US-122)."""

from __future__ import annotations

import time
import pytest
import threading
from invoices.event_streamer import EventStreamer


class TestEventStreamer:
    """US-122: High-Throughput PubSub Event Streamer Test Suite."""

    @pytest.fixture(autouse=True)
    def clean_streamer(self):
        """Reset the Singleton instance before each test to ensure test isolation."""
        streamer = EventStreamer()
        streamer.stop_daemon()
        with streamer._lock:
            streamer._subscribers.clear()
            streamer._global_subscribers.clear()
            # Drain queue
            while not streamer._event_queue.empty():
                try:
                    streamer._event_queue.get_nowait()
                    streamer._event_queue.task_done()
                except Exception:
                    pass
        streamer.start_daemon()
        yield
        streamer.stop_daemon()

    def test_singleton_pattern(self):
        """Verify that the EventStreamer enforces a strict singleton pattern."""
        s1 = EventStreamer()
        s2 = EventStreamer()
        assert s1 is s2

    def test_topic_subscription_and_dispatch(self):
        """Verify that a callback subscribed to a topic is invoked when events are published."""
        streamer = EventStreamer()
        events_received = []

        def on_invoice_created(event):
            events_received.append(event)

        streamer.subscribe("invoice.created", on_invoice_created)
        
        # Publish an event
        payload = {"invoice_id": "INV-PUB-001", "amount": 10000}
        streamer.publish("invoice.created", payload)
        
        # Allow time for async queue consumption
        time.sleep(0.15)
        
        assert len(events_received) == 1
        assert events_received[0]["topic"] == "invoice.created"
        assert events_received[0]["data"]["invoice_id"] == "INV-PUB-001"
        assert "timestamp" in events_received[0]

    def test_global_subscriber(self):
        """Verify that global subscribers receive all events across all topics."""
        streamer = EventStreamer()
        global_log = []

        def logger_callback(topic, envelope):
            global_log.append((topic, envelope))

        streamer.subscribe_all(logger_callback)

        streamer.publish("invoice.created", {"id": "INV-1"})
        streamer.publish("invoice.mutated", {"id": "INV-2"})
        
        time.sleep(0.15)
        
        assert len(global_log) == 2
        topics = [log[0] for log in global_log]
        assert "invoice.created" in topics
        assert "invoice.mutated" in topics

    def test_concurrent_publishing_throughput(self):
        """Verify that high-concurrency event publishing runs without thread locks or drops."""
        streamer = EventStreamer()
        received_count = 0
        lock = threading.Lock()

        def increment_callback(envelope):
            nonlocal received_count
            with lock:
                received_count += 1

        streamer.subscribe("invoice.bulk", increment_callback)

        def publish_bulk():
            for _ in range(50):
                streamer.publish("invoice.bulk", {"status": "processing"})

        threads = [threading.Thread(target=publish_bulk) for _ in range(5)]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Wait for background queue completion
        time.sleep(0.25)
        
        # 5 threads * 50 publishes = 250 total enqueued events
        assert received_count == 250
