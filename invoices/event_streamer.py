"""High-Throughput PubSub Event Streamer (US-122).

Provides an in-process, thread-safe asynchronous publishing daemon that emits
events (e.g. invoice.created, invoice.audited, invoice.mutated) immediately
after transaction commits.
"""

from __future__ import annotations

import queue
import logging
import threading
from datetime import datetime, timezone
from typing import Any, Callable

logger = logging.getLogger(__name__)


class EventStreamer:
    """Thread-safe PubSub Event Streamer for low-latency push integrations."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """Singleton pattern to ensure global system-wide event hub access."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(EventStreamer, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._subscribers: dict[str, list[Callable[[dict], None]]] = {}
        self._global_subscribers: list[Callable[[str, dict], None]] = []
        self._event_queue: queue.Queue[tuple[str, dict]] = queue.Queue()
        self._lock = threading.Lock()
        self._worker_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._initialized = True
        
        # Start async background event dispatcher daemon
        self.start_daemon()

    def start_daemon(self):
        """Start the background worker thread for asynchronous event dispatches."""
        with self._lock:
            if self._worker_thread is not None and self._worker_thread.is_alive():
                return
            
            self._stop_event.clear()
            self._worker_thread = threading.Thread(
                target=self._process_queue_loop,
                name="GDT-Event-Streamer-Daemon",
                daemon=True
            )
            self._worker_thread.start()
            logger.info("Asynchronous PubSub Event Streamer daemon successfully started.")

    def stop_daemon(self):
        """Shut down the background dispatcher gracefully."""
        self._stop_event.set()
        # Put a sentinel value to wake up the block
        self._event_queue.put((None, None))
        if self._worker_thread:
            self._worker_thread.join(timeout=3.0)
            self._worker_thread = None
        logger.info("Event Streamer daemon stopped.")

    def subscribe(self, topic: str, callback: Callable[[dict], None]):
        """Subscribe to a specific event topic in a thread-safe manner."""
        with self._lock:
            if topic not in self._subscribers:
                self._subscribers[topic] = []
            self._subscribers[topic].append(callback)
            logger.debug(f"Subscribed callback to topic: '{topic}'")

    def subscribe_all(self, callback: Callable[[str, dict], None]):
        """Subscribe to all topics globally (useful for audit logging)."""
        with self._lock:
            self._global_subscribers.append(callback)

    def unsubscribe(self, topic: str, callback: Callable[[dict], None]):
        """Unsubscribe from a specific event topic."""
        with self._lock:
            if topic in self._subscribers:
                try:
                    self._subscribers[topic].remove(callback)
                except ValueError:
                    pass

    def publish(self, topic: str, payload: dict):
        """Enqueue an event to be dispatched asynchronously by the daemon."""
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        event_envelope = {
            "topic": topic,
            "timestamp": now,
            "data": payload
        }
        self._event_queue.put((topic, event_envelope))

    def get_queue_size(self) -> int:
        """Return number of pending events."""
        return self._event_queue.qsize()

    def _process_queue_loop(self):
        """Background loop consuming and routing enqueued events to subscribers."""
        while not self._stop_event.is_set():
            try:
                # Wait for next event
                topic, envelope = self._event_queue.get(timeout=1.0)
                if topic is None:  # Sentinel value to exit
                    self._event_queue.task_done()
                    break

                # Dispatch
                self._route_event(topic, envelope)
                self._event_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in Event Streamer worker loop: {e}")

    def _route_event(self, topic: str, envelope: dict):
        """Route event message envelopes to both specific and global subscribers."""
        # 1. Dispatch to global subscribers
        global_targets = []
        with self._lock:
            global_targets = list(self._global_subscribers)

        for callback in global_targets:
            try:
                callback(topic, envelope)
            except Exception as e:
                logger.error(f"Global subscriber callback failed for topic '{topic}': {e}")

        # 2. Dispatch to topic-specific subscribers
        specific_targets = []
        with self._lock:
            if topic in self._subscribers:
                specific_targets = list(self._subscribers[topic])

        for callback in specific_targets:
            try:
                callback(envelope)
            except Exception as e:
                logger.error(f"Topic subscriber callback failed for topic '{topic}': {e}")


def setup_webhook_delivery_bridge():
    """Bridges the PubSub EventStreamer with the WebhookHub so published events trigger signed pushing."""
    from invoices.event_streamer import EventStreamer
    from invoices.webhook_hub import WebhookHub
    from invoices.models import WebhookSubscription
    from extensions import db

    streamer = EventStreamer()
    # Avoid duplicate registrations
    if hasattr(streamer, "_webhook_bridge_active") and streamer._webhook_bridge_active:
        return
        
    hub = WebhookHub(db_session=db.session)

    def route_to_webhooks(topic: str, envelope: dict):
        # Retrieve all active webhook subscriptions from the database
        try:
            active_subs = WebhookSubscription.query.filter_by(is_active=True).all()
            for sub in active_subs:
                hub.trigger(
                    url=sub.url,
                    secret=sub.secret,
                    event_topic=topic,
                    payload=envelope,
                    subscription_id=sub.id
                )
        except Exception as e:
            logger.error(f"Error bridging event '{topic}' to active webhooks: {e}")

    streamer.subscribe_all(route_to_webhooks)
    streamer._webhook_bridge_active = True
    logger.info("Durable Webhook-to-PubSub bridge successfully initialized.")

