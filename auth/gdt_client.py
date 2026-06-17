"""Resilient GDT client with OPTIONS preflight and port 30000 fallback."""

from __future__ import annotations

import logging
import requests
from flask import current_app

logger = logging.getLogger(__name__)


def gdt_request(method: str, path: str, **kwargs) -> requests.Response:
    """
    Perform a resilient request to GDT.
    - path: GDT path (e.g. 'api/captcha' or 'api/security-taxpayer/authenticate')
    - If standard request fails (network error or HTTP 403, 408, 429, 500+),
      automatically retries with direct port 30000 fallback (removing '/api/' prefix).
    - Sets browser-emulating headers to bypass WAF bot-detection.
    """
    base_url = current_app.config["GDT_BASE_URL"]
    timeout = kwargs.pop("timeout", current_app.config.get("GDT_TIMEOUT_SECONDS", 30))

    # Construct clean headers
    headers = kwargs.get("headers", {}).copy()
    if "User-Agent" not in headers:
        headers["User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    if "Accept" not in headers:
        headers["Accept"] = "application/json, text/plain, */*"
    if "Accept-Language" not in headers:
        headers["Accept-Language"] = "vi,en-US;q=0.9,en;q=0.8"

    kwargs["headers"] = headers
    kwargs["timeout"] = timeout

    # 1. Try standard URL
    clean_path = path.lstrip('/')
    standard_url = f"{base_url.rstrip('/')}/{clean_path}"
    logger.debug(f"GDT standard request: {method} {standard_url}")

    last_error = None
    try:
        # Send OPTIONS preflight handshake if doing credentials authentication
        if method.upper() == "POST" and "authenticate" in clean_path:
            try:
                preflight_headers = {
                    "User-Agent": headers["User-Agent"],
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                }
                requests.options(standard_url, headers=preflight_headers, cookies=kwargs.get("cookies"), timeout=5)
                logger.debug(f"Standard preflight OPTIONS completed successfully.")
            except Exception as opt_err:
                logger.warning(f"Standard preflight OPTIONS handshake failed (non-blocking): {opt_err}")

        if method.upper() == "POST":
            resp = requests.post(standard_url, **kwargs)
        elif method.upper() == "GET":
            resp = requests.get(standard_url, **kwargs)
        else:
            resp = requests.request(method, standard_url, **kwargs)

        if resp.status_code not in [403, 408, 429, 500, 502, 503, 504]:
            return resp
        last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
    except Exception as e:
        last_error = e

    # 2. Port 30000 direct fallback (matching VBA client)
    logger.warning(f"GDT standard request failed ({last_error}). Retrying with direct port 30000 fallback...")

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

    try:
        # Send OPTIONS preflight on fallback URL if authenticate
        if method.upper() == "POST" and "authenticate" in fallback_path:
            try:
                preflight_headers = {
                    "User-Agent": fallback_headers["User-Agent"],
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                }
                requests.options(fallback_url, headers=preflight_headers, cookies=kwargs.get("cookies"), timeout=5)
                logger.debug(f"Fallback preflight OPTIONS completed successfully.")
            except Exception as opt_err:
                logger.warning(f"Fallback preflight OPTIONS handshake failed (non-blocking): {opt_err}")

        if method.upper() == "POST":
            resp = requests.post(fallback_url, **kwargs)
        elif method.upper() == "GET":
            resp = requests.get(fallback_url, **kwargs)
        else:
            resp = requests.request(method, fallback_url, **kwargs)
        return resp
    except Exception as fallback_err:
        logger.error(f"GDT direct port 30000 fallback failed: {fallback_err}")
        if isinstance(last_error, Exception):
            raise last_error
        raise RuntimeError(f"GDT connection failed (fallback error: {fallback_err})") from fallback_err
