"""Cybersecurity hardening module for GDT Invoice Hub.

Implements lightweight in-memory rate limiting and applies strict HTTP security headers.
"""

from __future__ import annotations

import time
import threading
from functools import wraps
from flask import Flask, request, jsonify, make_response


class InMemoryRateLimiter:
    """Sliding-window in-memory rate limiter to protect sensitive endpoints from brute-force."""

    def __init__(self, cleanup_interval_seconds: int = 300):
        self.lock = threading.Lock()
        self.requests: dict[str, list[float]] = {}
        self.cleanup_interval = cleanup_interval_seconds
        self.last_cleanup = time.time()

    def _cleanup(self, now: float) -> None:
        """Remove expired request timestamps to prevent memory leaks."""
        if now - self.last_cleanup < self.cleanup_interval:
            return
        
        expired_keys = []
        for key, timestamps in self.requests.items():
            # Keep only timestamps within the last 1 hour (max conceivable window)
            valid_cutoff = now - 3600
            updated_timestamps = [t for t in timestamps if t > valid_cutoff]
            if not updated_timestamps:
                expired_keys.append(key)
            else:
                self.requests[key] = updated_timestamps

        for key in expired_keys:
            self.requests.pop(key, None)
        
        self.last_cleanup = now

    def is_allowed(self, identifier: str, limit: int, window: int) -> tuple[bool, int, int]:
        """Verify if the request from the identifier is within the limits.

        Returns:
            (allowed, remaining, retry_after)
        """
        now = time.time()
        with self.lock:
            self._cleanup(now)
            
            if identifier not in self.requests:
                self.requests[identifier] = []
            
            timestamps = self.requests[identifier]
            cutoff = now - window
            
            # Filter timestamps in the active window
            active_timestamps = [t for t in timestamps if t > cutoff]
            self.requests[identifier] = active_timestamps
            
            current_count = len(active_timestamps)
            if current_count >= limit:
                # Find retry after based on the oldest active request
                oldest = min(active_timestamps) if active_timestamps else now
                retry_after = int(oldest + window - now) + 1
                return False, 0, max(1, retry_after)
            
            self.requests[identifier].append(now)
            return True, limit - (current_count + 1), 0


# Global Rate Limiter instance
limiter = InMemoryRateLimiter()


def rate_limit(limit: int, window: int):
    """Decorator to apply rate limits to a Flask route based on client IP."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Resolve client IP (respecting proxies securely if configured)
            client_ip = request.headers.get("X-Forwarded-For")
            if client_ip:
                client_ip = client_ip.split(",")[0].strip()
            else:
                client_ip = request.remote_addr or "unknown-ip"
            
            endpoint_key = f"{request.path}:{client_ip}"
            allowed, remaining, retry_after = limiter.is_allowed(endpoint_key, limit, window)
            
            if not allowed:
                response = make_response(
                    jsonify({
                        "error": "too_many_requests",
                        "message": "Quá nhiều yêu cầu. Vui lòng thử lại sau.",
                        "retry_after": retry_after
                    }),
                    429
                )
                response.headers["Retry-After"] = str(retry_after)
                response.headers["X-RateLimit-Limit"] = str(limit)
                response.headers["X-RateLimit-Remaining"] = "0"
                return response
            
            response = make_response(f(*args, **kwargs))
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            return response
        return decorated_function
    return decorator


def apply_security_headers(app: Flask) -> None:
    """Register after_request middleware to enforce strict defense-in-depth headers."""

    @app.after_request
    def set_headers(response):
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevent Clickjacking
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        
        # Cross-Site Scripting Filter protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer controls
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Enforce HTTPS only (if not local testing / HTTP mode)
        if not app.config.get("DEBUG") and not app.config.get("TESTING"):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        # Content Security Policy (Allows Google Fonts, local files, and Tailwind CDN for UI development)
        csp_policies = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' cdn.tailwindcss.com cdn.jsdelivr.net",
            "style-src 'self' 'unsafe-inline' fonts.googleapis.com cdn.tailwindcss.com cdn.jsdelivr.net",
            "font-src 'self' data: fonts.gstatic.com cdn.jsdelivr.net",
            "img-src 'self' data: api.qrserver.com",
            "connect-src 'self' https://api.qrserver.com",
            "frame-ancestors 'none'"
        ]
        response.headers["Content-Security-Policy"] = "; ".join(csp_policies)
        
        # Restrict API Permissions
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response
