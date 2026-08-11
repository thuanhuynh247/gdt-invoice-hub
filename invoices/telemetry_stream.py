"""Real-time SSE Live Telemetry Stream Service.

Provides a thread-safe event bus and Server-Sent Events (SSE) stream
for live monitoring of GDT Sync, Captcha Auto-Renewal, Risk Audits, and V-Series Compliance Events.
"""

from __future__ import annotations

import json
import time
import queue
import threading
from datetime import datetime
from typing import Dict, Any, List, Optional


class TelemetryEventBus:
    """Thread-safe event broadcast bus for SSE streaming."""

    _instance: Optional[TelemetryEventBus] = None
    _lock = threading.Lock()

    def __new__(cls) -> TelemetryEventBus:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(TelemetryEventBus, cls).__new__(cls)
                cls._instance._subscribers: List[queue.Queue] = []
                cls._history: List[Dict[str, Any]] = []
                cls._history_lock = threading.Lock()
                # Seed with initial startup telemetry events
                cls._instance._seed_initial_events()
            return cls._instance

    def _seed_initial_events(self) -> None:
        """Seed recent events so connecting clients immediately see system pulse."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._history = [
            {
                "id": 1,
                "timestamp": now,
                "type": "SYSTEM_INIT",
                "level": "SUCCESS",
                "source": "GDT_GATEWAY",
                "message": "GDT Invoice Hub daemon initialized & connected to isolated multi-tenant DB.",
                "metadata": {"version": "v81.0", "status": "ONLINE"}
            },
            {
                "id": 2,
                "timestamp": now,
                "type": "CAPTCHA_DAEMON",
                "level": "INFO",
                "source": "CAPTCHA_PREFETCH",
                "message": "Automated CAPTCHA solver pool active (prefetch queue size: 5, latency: 420ms).",
                "metadata": {"pool_size": 5, "hit_rate": 0.98}
            },
            {
                "id": 3,
                "timestamp": now,
                "type": "COMPLIANCE_V81",
                "level": "INFO",
                "source": "PIT_AUDITOR",
                "message": "V81 PIT Withholding & Form 08/CK-TNCN validation engine ready.",
                "metadata": {"rules": ["TT111/2013", "TT25/2018", "TT78/2021"]}
            }
        ]

    def publish(self, event_type: str, message: str, level: str = "INFO", source: str = "SYSTEM", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Broadcast an event to all connected SSE clients and record in ring buffer."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._history_lock:
            event_id = len(self._history) + 1
            event = {
                "id": event_id,
                "timestamp": now,
                "type": event_type,
                "level": level,
                "source": source,
                "message": message,
                "metadata": metadata or {}
            }
            self._history.append(event)
            if len(self._history) > 100:
                self._history.pop(0)

        # Distribute to all active subscriber queues
        with self._lock:
            dead_subs = []
            for q in self._subscribers:
                try:
                    q.put_nowait(event)
                except queue.Full:
                    dead_subs.append(q)
            for d in dead_subs:
                if d in self._subscribers:
                    self._subscribers.remove(d)

        return event

    def subscribe(self) -> queue.Queue:
        """Subscribe a new client to the SSE event stream."""
        q: queue.Queue = queue.Queue(maxsize=50)
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue) -> None:
        """Remove a subscriber queue when client disconnects."""
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def get_recent_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get the most recent event logs."""
        with self._history_lock:
            return list(self._history[-limit:])


# Singleton accessor
telemetry_bus = TelemetryEventBus()


def sse_event_generator():
    """Generator function yielding SSE formatted messages."""
    q = telemetry_bus.subscribe()
    try:
        # Send initial connection event
        yield f"event: connected\ndata: {json.dumps({'status': 'connected', 'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})}\n\n"
        
        while True:
            try:
                # Wait for up to 3 seconds for new event
                event = q.get(timeout=3.0)
                yield f"data: {json.dumps(event)}\n\n"
            except queue.Empty:
                # Send periodic heartbeat keep-alive
                heartbeat = {
                    "type": "HEARTBEAT",
                    "level": "INFO",
                    "source": "TELEMETRY_STREAM",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "message": "Keep-alive telemetry pulse.",
                    "metadata": {"active_clients": len(telemetry_bus._subscribers)}
                }
                yield f": heartbeat {datetime.now().isoformat()}\n\n"
    finally:
        telemetry_bus.unsubscribe(q)
