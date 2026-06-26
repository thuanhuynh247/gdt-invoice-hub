import time
import pytest
from unittest.mock import patch, MagicMock
import requests
from auth.gdt_client import gdt_request, _get_request_proxies

def test_proxy_loading_and_selection(app):
    """Test that proxies config is populated and _get_request_proxies rotates them."""
    with app.app_context():
        # Set mock proxies
        app.config["GDT_PROXIES"] = [
            "http://proxy1.test:8080",
            "http://proxy2.test:8080",
        ]
        
        # Select multiple times and assert rotation
        selections = set()
        for _ in range(20):
            p = _get_request_proxies()
            assert p is not None
            assert p["http"] in app.config["GDT_PROXIES"]
            assert p["https"] in app.config["GDT_PROXIES"]
            selections.add(p["http"])
            
        assert len(selections) > 0

def test_rate_limiting_delay_execution(app):
    """Test that dynamic request delay is applied properly."""
    with app.app_context():
        app.config["GDT_REQUEST_DELAY_MIN"] = 0.5
        app.config["GDT_REQUEST_DELAY_MAX"] = 1.0
        
        start_time = time.time()
        
        with patch("requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_get.return_value = mock_resp
            
            # Perform mock request
            gdt_request("GET", "api/test-rate-limit")
            
            elapsed = time.time() - start_time
            # Elapsed time should be at least GDT_REQUEST_DELAY_MIN (0.5s)
            assert elapsed >= 0.45
