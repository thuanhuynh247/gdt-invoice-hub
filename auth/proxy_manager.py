"""Proxy manager for GDT requests to mitigate WAF blocking and IP bans."""

from __future__ import annotations

import logging
import random
import time
import threading
from flask import current_app

logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
]


class GDTProxyManager:
    """Thread-safe manager for GDT proxy rotation, health checks, and cool-downs."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super().__new__(cls, *args, **kwargs)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._initialized = True
        self.proxies = {}  # proxy_url -> dict
        self.global_cool_down_until = 0.0
        self.consecutive_global_failures = 0
        self.dynamic_delay_min = 1.0
        self.dynamic_delay_max = 3.0
        self.lock = threading.Lock()
        self.last_sync_time = 0.0

    def sync_proxies(self):
        """Sync proxies with SystemConfig database and app configuration."""
        with self.lock:
            # 1. Gather all proxy URLs
            proxy_urls = set()

            # Load from app config
            try:
                config_proxies = current_app.config.get("GDT_PROXIES", [])
                for p in config_proxies:
                    if p.strip():
                        proxy_urls.add(p.strip())
            except Exception:
                pass

            # Load from SystemConfig db if active context
            try:
                from invoices.models import SystemConfig
                cfg = SystemConfig.query.filter_by(key="gdt_proxies").first()
                if cfg and cfg.value.strip():
                    db_proxies = [p.strip() for p in cfg.value.split(",") if p.strip()]
                    for p in db_proxies:
                        proxy_urls.add(p)
            except Exception:
                pass

            # 2. Add new proxies to dictionary
            for url in proxy_urls:
                if url not in self.proxies:
                    self.proxies[url] = {
                        "url": url,
                        "status": "Active",
                        "cool_down_until": 0.0,
                        "consecutive_failures": 0,
                        "avg_latency_ms": 0.0,
                        "total_requests": 0,
                        "successful_requests": 0,
                        "latencies": []
                    }

            # 3. Remove deleted proxies
            for url in list(self.proxies.keys()):
                if url not in proxy_urls:
                    del self.proxies[url]

            self.last_sync_time = time.time()

    def get_active_proxy(self) -> dict | None:
        """Select a healthy active proxy based on latency, cool-down, and status."""
        self.sync_proxies()
        now = time.time()

        with self.lock:
            # Check global cool-down first
            if now < self.global_cool_down_until:
                logger.warning("GDT Client is currently under Global Cool-down!")
                return None

            available = []
            for p in self.proxies.values():
                # Check status and cooldown
                if p["status"] == "CoolDown" and now >= p["cool_down_until"]:
                    p["status"] = "Active"
                    p["consecutive_failures"] = 0

                if p["status"] == "Active":
                    available.append(p)

            if not available:
                return None

            # Prefer proxies with lower average latency
            # Or use weighted/random choice among top performers
            available.sort(key=lambda x: x["avg_latency_ms"])
            # Return a random choice from the best 50% of available proxies to avoid hot spotting
            sample_size = max(1, len(available) // 2)
            best_proxies = available[:sample_size]
            selected = random.choice(best_proxies)
            return {
                "http": selected["url"],
                "https": selected["url"]
            }

    def report_success(self, proxy_url: str, latency_ms: float):
        """Update metrics for successful proxy requests."""
        with self.lock:
            # Reset global failures
            self.consecutive_global_failures = 0
            # Reset dynamic delay to defaults
            try:
                self.dynamic_delay_min = current_app.config.get("GDT_REQUEST_DELAY_MIN", 1.0)
                self.dynamic_delay_max = current_app.config.get("GDT_REQUEST_DELAY_MAX", 3.0)
            except Exception:
                self.dynamic_delay_min = 1.0
                self.dynamic_delay_max = 3.0

            if proxy_url in self.proxies:
                p = self.proxies[proxy_url]
                p["total_requests"] += 1
                p["successful_requests"] += 1
                p["consecutive_failures"] = 0
                p["status"] = "Active"
                
                # Update moving average latency
                p["latencies"].append(latency_ms)
                if len(p["latencies"]) > 10:
                    p["latencies"].pop(0)
                p["avg_latency_ms"] = sum(p["latencies"]) / len(p["latencies"])

    def report_failure(self, proxy_url: str | None, status_code: int | None, error_msg: str):
        """Handle request failure, setting proxy or global cool-down state."""
        now = time.time()
        is_waf = (status_code in [403, 429]) or ("rate limit" in error_msg.lower()) or ("block" in error_msg.lower())

        with self.lock:
            if proxy_url and proxy_url in self.proxies:
                p = self.proxies[proxy_url]
                p["total_requests"] += 1
                p["consecutive_failures"] += 1

                # If WAF triggered or too many failures, place on cool-down (5 minutes)
                if is_waf or p["consecutive_failures"] >= 3:
                    p["status"] = "CoolDown"
                    p["cool_down_until"] = now + 300.0  # 5 minutes
                    logger.warning(f"Proxy {proxy_url} placed on CoolDown for 5 minutes. Reason: {error_msg}")
            else:
                # Direct connection or untracked proxy failure
                self.consecutive_global_failures += 1

            # Dynamic backoff delay doubling
            self.dynamic_delay_min = min(15.0, self.dynamic_delay_min * 1.5)
            self.dynamic_delay_max = min(30.0, self.dynamic_delay_max * 1.5)

            # Trigger global cooldown if WAF block is hit directly, or if all proxies are dead
            all_dead = len(self.proxies) > 0 and all(p["status"] == "CoolDown" for p in self.proxies.values())
            if is_waf or all_dead or self.consecutive_global_failures >= 5:
                # Place global request loop on cool-down
                self.global_cool_down_until = now + 300.0  # 5 minutes global block
                logger.error("WAF trigger detected! Activating Global Cool-down for 5 minutes to protect IP address.")

    def is_global_cooldown(self) -> bool:
        """Check if global cooldown is active."""
        return time.time() < self.global_cool_down_until

    def get_global_cooldown_remaining(self) -> float:
        """Get remaining seconds for global cooldown."""
        return max(0.0, self.global_cool_down_until - time.time())

    def clear_cooldowns(self):
        """Clear all active cool-downs and failure counts."""
        with self.lock:
            self.global_cool_down_until = 0.0
            self.consecutive_global_failures = 0
            try:
                self.dynamic_delay_min = current_app.config.get("GDT_REQUEST_DELAY_MIN", 1.0)
                self.dynamic_delay_max = current_app.config.get("GDT_REQUEST_DELAY_MAX", 3.0)
            except Exception:
                self.dynamic_delay_min = 1.0
                self.dynamic_delay_max = 3.0

            for p in self.proxies.values():
                p["status"] = "Active"
                p["cool_down_until"] = 0.0
                p["consecutive_failures"] = 0

    def get_random_user_agent(self) -> str:
        """Return a random modern browser user agent."""
        return random.choice(USER_AGENTS)

    def get_all_proxy_stats(self) -> list[dict]:
        """Return a snapshot list of all proxies and their statistics."""
        self.sync_proxies()
        with self.lock:
            now = time.time()
            snapshot = []
            for p in self.proxies.values():
                remaining = max(0.0, p["cool_down_until"] - now)
                snapshot.append({
                    "url": p["url"],
                    "status": p["status"],
                    "cool_down_remaining": round(remaining, 1),
                    "consecutive_failures": p["consecutive_failures"],
                    "avg_latency_ms": round(p["avg_latency_ms"], 1),
                    "total_requests": p["total_requests"],
                    "successful_requests": p["successful_requests"],
                    "success_rate": round((p["successful_requests"] / max(1, p["total_requests"])) * 100, 1)
                })
            return snapshot


# Global single instance
proxy_manager = GDTProxyManager()
