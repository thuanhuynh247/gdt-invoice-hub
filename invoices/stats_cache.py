"""Thread-safe, high-performance key-value caching pipeline for dashboard stats (US-124)."""

import threading
from typing import Any

# Global thread-safe cache store
_cache: dict[str, Any] = {}
_cache_lock = threading.Lock()

def _make_key(mst: str | None, from_date: str, to_date: str, direction: str) -> str:
    mst_key = mst or "global"
    return f"{mst_key}:{from_date}:{to_date}:{direction}"

def get_cached_stats(mst: str | None, from_date: str, to_date: str, direction: str) -> dict | None:
    """Retrieve cached dashboard statistics if available."""
    key = _make_key(mst, from_date, to_date, direction)
    with _cache_lock:
        return _cache.get(key)

def set_cached_stats(mst: str | None, from_date: str, to_date: str, direction: str, stats: dict) -> None:
    """Store calculated stats in cache."""
    key = _make_key(mst, from_date, to_date, direction)
    with _cache_lock:
        _cache[key] = stats

def invalidate_stats_cache(mst: str | None = None) -> None:
    """Invalidate cache regions globally or for a specific taxpayer MST."""
    with _cache_lock:
        if mst is None:
            _cache.clear()
        else:
            prefix = f"{mst}:"
            keys_to_del = [k for k in _cache.keys() if k.startswith(prefix)]
            for k in keys_to_del:
                _cache.pop(k, None)
