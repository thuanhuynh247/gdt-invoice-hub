"""Resilient GDT client with OPTIONS preflight, port 30000 fallback, proxy rotation, and rate-limit prevention."""

from __future__ import annotations

import logging
import random
import time
import requests
from flask import current_app

logger = logging.getLogger(__name__)


from auth.proxy_manager import proxy_manager

def _get_request_proxies() -> dict | None:
    """Select a rotated proxy from proxy_manager."""
    try:
        return proxy_manager.get_active_proxy()
    except Exception as e:
        logger.warning(f"Error selecting proxy from manager: {e}")
        return None


def gdt_request(method: str, path: str, **kwargs) -> requests.Response:
    """
    Perform a resilient request to GDT.
    - path: GDT path (e.g. 'api/captcha' or 'api/security-taxpayer/authenticate')
    - If standard request fails (network error or HTTP 403, 408, 429, 500+),
      automatically retries with direct port 30000 fallback (removing '/api/' prefix).
    - Sets browser-emulating headers to bypass WAF bot-detection.
    - Automatically rotates proxies from GDTProxyManager to bypass IP bans/limits.
    - Automatically sleeps dynamically based on proxy cooling state.
    """
    # 0. Check global cool-down first
    if proxy_manager.is_global_cooldown():
        rem = proxy_manager.get_global_cooldown_remaining()
        logger.warning(f"GDT request blocked by active global cool-down. Remaining: {rem:.1f}s")
        raise RuntimeError(f"GDT client is in global cool-down mode. Try again in {rem:.1f}s.")

    # Apply dynamic request delay for rate limit prevention
    try:
        delay_min = proxy_manager.dynamic_delay_min
        delay_max = proxy_manager.dynamic_delay_max
        if delay_max > delay_min:
            sleep_time = random.uniform(delay_min, delay_max)
            logger.debug(f"Applying rate limit delay of {sleep_time:.2f}s before GDT request")
            time.sleep(sleep_time)
    except Exception as e:
        logger.warning(f"Failed to apply rate-limiting delay: {e}")

    base_url = current_app.config["GDT_BASE_URL"]
    timeout = kwargs.pop("timeout", current_app.config.get("GDT_TIMEOUT_SECONDS", 30))

    # Construct clean headers
    headers = kwargs.get("headers", {}).copy()
    if "User-Agent" not in headers or "Mozilla" not in headers.get("User-Agent", ""):
        headers["User-Agent"] = proxy_manager.get_random_user_agent()
    if "Accept" not in headers:
        headers["Accept"] = "application/json, text/plain, */*"
    if "Accept-Language" not in headers:
        headers["Accept-Language"] = "vi,en-US;q=0.9,en;q=0.8"

    kwargs["headers"] = headers
    kwargs["timeout"] = timeout

    # Attach proxy if configured (unless overridden in kwargs)
    proxy_used = None
    if "proxies" not in kwargs:
        proxy_dict = _get_request_proxies()
        if proxy_dict:
            kwargs["proxies"] = proxy_dict
            proxy_used = proxy_dict.get("http")

    # 1. Try standard URL
    clean_path = path.lstrip('/')
    standard_url = f"{base_url.rstrip('/')}/{clean_path}"
    logger.debug(f"GDT standard request: {method} {standard_url}")

    last_error = None
    resp = None
    start_time = time.time()

    try:
        # Send OPTIONS preflight handshake if doing credentials authentication
        if method.upper() == "POST" and "authenticate" in clean_path:
            try:
                preflight_headers = {
                    "User-Agent": headers["User-Agent"],
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                }
                requests.options(standard_url, headers=preflight_headers, cookies=kwargs.get("cookies"), timeout=5, proxies=kwargs.get("proxies"))
                logger.debug(f"Standard preflight OPTIONS completed successfully.")
            except Exception as opt_err:
                logger.warning(f"Standard preflight OPTIONS handshake failed (non-blocking): {opt_err}")

        if method.upper() == "POST":
            resp = requests.post(standard_url, **kwargs)
        elif method.upper() == "GET":
            resp = requests.get(standard_url, **kwargs)
        else:
            resp = requests.request(method, standard_url, **kwargs)

        latency_ms = (time.time() - start_time) * 1000.0

        if resp.status_code not in [403, 408, 429, 500, 502, 503, 504]:
            if proxy_used:
                proxy_manager.report_success(proxy_used, latency_ms)
            return resp

        last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
        if proxy_used:
            proxy_manager.report_failure(proxy_used, resp.status_code, last_error)
    except Exception as e:
        last_error = str(e)
        if proxy_used:
            proxy_manager.report_failure(proxy_used, None, last_error)

    # 2. Port 30000 direct fallback (matching VBA client)
    logger.warning(f"GDT standard request failed ({last_error}). Retrying with direct port 30000 fallback...")

    # For fallback, check global cooldown again
    if proxy_manager.is_global_cooldown():
        raise RuntimeError(f"GDT client fallback aborted due to active global cool-down. Error: {last_error}")

    # Rotate proxy for fallback
    proxy_used_fallback = None
    if "proxies" in kwargs:
        new_proxy_dict = _get_request_proxies()
        if new_proxy_dict:
            kwargs["proxies"] = new_proxy_dict
            proxy_used_fallback = new_proxy_dict.get("http")
        else:
            kwargs.pop("proxies", None)

    from urllib.parse import urlparse, urlunparse
    parsed = urlparse(base_url)
    netloc = parsed.netloc.split(":")[0] if ":" in parsed.netloc else parsed.netloc
    netloc = f"{netloc}:30000"

    # Remove /api prefix for port 30000 direct backend route
    fallback_path = clean_path
    if fallback_path.startswith("api/"):
        fallback_path = fallback_path[len("api/"):]

    fallback_url = urlunparse(parsed._replace(netloc=netloc, path=fallback_path.lstrip('/')))
    logger.info(f"GDT fallback request: {method} {fallback_url}")

    fallback_headers = headers.copy()
    if "captcha" in clean_path:
        fallback_headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9"
        fallback_headers["Accept-Encoding"] = "gzip;q=1.0"
        fallback_headers["Content-Encoding"] = "gzip"
        fallback_headers["Content-Type"] = "application/gzip;application/json; application/x-www-form-urlencoded; charset=UTF-8"

    kwargs["headers"] = fallback_headers

    fallback_start = time.time()
    try:
        # Send OPTIONS preflight on fallback URL if authenticate
        if method.upper() == "POST" and "authenticate" in fallback_path:
            try:
                preflight_headers = {
                    "User-Agent": fallback_headers["User-Agent"],
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                }
                requests.options(fallback_url, headers=preflight_headers, cookies=kwargs.get("cookies"), timeout=5, proxies=kwargs.get("proxies"))
                logger.debug(f"Fallback preflight OPTIONS completed successfully.")
            except Exception as opt_err:
                logger.warning(f"Fallback preflight OPTIONS handshake failed (non-blocking): {opt_err}")

        if method.upper() == "POST":
            resp = requests.post(fallback_url, **kwargs)
        elif method.upper() == "GET":
            resp = requests.get(fallback_url, **kwargs)
        else:
            resp = requests.request(method, fallback_url, **kwargs)

        fallback_latency = (time.time() - fallback_start) * 1000.0

        if resp.status_code not in [403, 408, 429, 500, 502, 503, 504]:
            if proxy_used_fallback:
                proxy_manager.report_success(proxy_used_fallback, fallback_latency)
            return resp

        fallback_err_msg = f"HTTP {resp.status_code}: {resp.text[:200]}"
        if proxy_used_fallback:
            proxy_manager.report_failure(proxy_used_fallback, resp.status_code, fallback_err_msg)
        raise RuntimeError(f"GDT connection failed (fallback status code: {resp.status_code})")
    except Exception as fallback_err:
        logger.error(f"GDT direct port 30000 fallback failed: {fallback_err}")
        if proxy_used_fallback:
            proxy_manager.report_failure(proxy_used_fallback, None, str(fallback_err))
        raise RuntimeError(f"GDT connection failed (fallback error: {fallback_err})") from fallback_err

