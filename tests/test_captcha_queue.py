"""Tests for the CAPTCHA Prefetch Queue and daemon worker."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from auth.captcha import (
    CAPTCHA_LOCK,
    CAPTCHA_QUEUE,
    pop_prefetched_captcha,
    start_captcha_prefetch_worker,
    stop_captcha_prefetch_worker,
)


def test_pop_empty_queue():
    """Popping from an empty queue should return None."""
    stop_captcha_prefetch_worker()
    with CAPTCHA_LOCK:
        global CAPTCHA_QUEUE
        CAPTCHA_QUEUE.clear()

    assert pop_prefetched_captcha() is None


def test_pop_valid_and_expired_items():
    """Verify that expired items (> 120s) are automatically pruned, and valid ones popped."""
    stop_captcha_prefetch_worker()
    now = datetime.now(timezone.utc)
    expired_time = now - timedelta(seconds=121)
    valid_time = now - timedelta(seconds=30)

    with CAPTCHA_LOCK:
        global CAPTCHA_QUEUE
        CAPTCHA_QUEUE.clear()
        # Add an expired captcha
        CAPTCHA_QUEUE.append({
            "key": "expired-key",
            "content": "<svg>expired</svg>",
            "cookies": {},
            "solved_text": "EXP",
            "created_at": expired_time
        })
        # Add a valid captcha
        CAPTCHA_QUEUE.append({
            "key": "valid-key",
            "content": "<svg>valid</svg>",
            "cookies": {},
            "solved_text": "VAL",
            "created_at": valid_time
        })

    # The expired item should be pruned during pop, and we should get the valid one
    item = pop_prefetched_captcha()
    assert item is not None
    assert item["key"] == "valid-key"
    assert item["solved_text"] == "VAL"

    # Queue should be empty now
    assert pop_prefetched_captcha() is None


def test_prefetch_worker_populates_queue(app):
    """The background worker should automatically keep the queue populated in mock mode."""
    stop_captcha_prefetch_worker()
    with CAPTCHA_LOCK:
        global CAPTCHA_QUEUE
        CAPTCHA_QUEUE.clear()

    # Worker was already started in app startup, or we can restart it for the test
    start_captcha_prefetch_worker(app)

    # Let worker run and populate the queue (it checks every second, mock is fast)
    max_attempts = 15
    populated = False
    for _ in range(max_attempts):
        with CAPTCHA_LOCK:
            if len(CAPTCHA_QUEUE) >= 1:
                populated = True
                break
        time.sleep(0.2)

    assert populated is True
    with CAPTCHA_LOCK:
        assert len(CAPTCHA_QUEUE) <= 2
        item = CAPTCHA_QUEUE[0]
        assert "key" in item
        assert "content" in item
        assert "solved_text" in item
        assert item["solved_text"] == "MOCK"

    # Stop the worker thread at the end of the test to keep isolation
    stop_captcha_prefetch_worker()


def test_route_uses_prefetched_captcha(logged_in_client):
    """The /api/auth/captcha route should pop and return a prefetched captcha if available."""
    stop_captcha_prefetch_worker()
    # Seed the queue with a custom captcha to verify the route pops it
    custom_item = {
        "key": "custom-seed-key",
        "content": "<svg>custom-seed-svg</svg>",
        "cookies": {"foo": "bar"},
        "solved_text": "SEED",
        "created_at": datetime.now(timezone.utc)
    }

    with CAPTCHA_LOCK:
        global CAPTCHA_QUEUE
        CAPTCHA_QUEUE.clear()
        CAPTCHA_QUEUE.append(custom_item)

    # Fetch captcha through route
    response = logged_in_client.get("/api/auth/captcha")
    assert response.status_code == 200
    data = response.get_json()
    assert data["image_svg"] == "<svg>custom-seed-svg</svg>"

    # Ensure it was popped and stored in the session
    with logged_in_client.session_transaction() as sess:
        assert sess.get("auth_captcha_key") == "custom-seed-key"
        assert sess.get("auth_captcha_svg") == "<svg>custom-seed-svg</svg>"
        assert sess.get("auth_captcha_cookies") == {"foo": "bar"}
        assert sess.get("auth_captcha_solved") == "SEED"

