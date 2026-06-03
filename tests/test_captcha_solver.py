"""Tests for the GDT CAPTCHA auto-solving engine."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from unittest.mock import patch, MagicMock
import pytest

from auth.captcha_solver import solve_captcha_from_svg
from auth.service import AuthenticationError


def test_svg_noise_filtering_and_sorting():
    """Verify that background noise paths are removed and letters are sorted left-to-right."""
    # SVG containing noise paths and out-of-order character paths
    svg_data = """<svg xmlns="http://www.w3.org/2000/svg" width="150" height="50">
        <!-- Noise path 1: fill="none" -->
        <path fill="none" stroke="#777" d="M 0 0 L 150 50" />
        <!-- Character path 1: X start coordinate 50.0 -->
        <path fill="#222" d="M50.0 10 L 50 40" />
        <!-- Noise path 2: stroke exists -->
        <path stroke="#111" d="M 0 50 L 150 0" />
        <!-- Character path 2: X start coordinate 10.0 -->
        <path fill="#222" d="M10.0 10 L 10 40" />
    </svg>"""

    # We mock ddddocr's classification so it doesn't run the actual ONNX model on this mock SVG
    with patch("auth.captcha_solver.get_ocr_instance") as mock_get_ocr:
        mock_ocr = MagicMock()
        mock_ocr.classification.return_value = "OK"
        mock_get_ocr.return_value = mock_ocr

        solve_captcha_from_svg(svg_data)

        # Verify XML parsing and sorting logic
        ET.register_namespace('', 'http://www.w3.org/2000/svg')
        root = ET.fromstring(svg_data)
        paths = [p for p in root.iter() if p.tag.endswith('path')]
        
        # Verify initial path count
        assert len(paths) == 4
        
        # Run noise filtering
        character_paths = []
        for p in paths:
            fill = p.attrib.get('fill', '').lower()
            stroke = p.attrib.get('stroke', '')
            if fill == 'none' or stroke:
                root.remove(p)
            else:
                character_paths.append(p)
                
        # Only characters should remain
        assert len(root.findall('.//{http://www.w3.org/2000/svg}path')) == 2

        # Sort remaining character paths
        def get_start_x(path_element) -> float:
            d = path_element.attrib.get('d', '')
            parts = d.replace(',', ' ').split()
            for i, part in enumerate(parts):
                if part.upper().startswith('M'):
                    val = part[1:]
                    if val:
                        return float(val)
            return 0.0

        for p in character_paths:
            root.remove(p)

        sorted_paths = sorted(character_paths, key=get_start_x)
        for p in sorted_paths:
            root.append(p)

        # Verify correct left-to-right order: X coordinate 10.0 must be first, then 50.0
        final_paths = root.findall('.//{http://www.w3.org/2000/svg}path')
        assert final_paths[0].attrib['d'].startswith('M10.0')
        assert final_paths[1].attrib['d'].startswith('M50.0')


def test_solve_captcha_mock_text_tag():
    """Verify that solve_captcha_from_svg correctly parses mock captchas with text tags."""
    mock_svg = """<svg xmlns="http://www.w3.org/2000/svg">
        <text>MOCK</text>
    </svg>"""
    result = solve_captcha_from_svg(mock_svg)
    assert result == "MOCK"


def test_api_login_auto_solve_loop(app, client):
    """Test the 5-attempt retry loop on captcha failure under simulated live login."""
    # Enable AUTO_SOLVE_CAPTCHA and disable mock mode for this integration test
    app.config["AUTO_SOLVE_CAPTCHA"] = True
    app.config["GDT_USE_MOCK"] = False

    # Mock captcha fetch to return a test SVG
    mock_captcha = {
        "key": "test-captcha-key",
        "content": '<svg xmlns="http://www.w3.org/2000/svg"><text>SOLVED</text></svg>',
        "cookies": {"test-cookie": "val"}
    }

    # Set up session transaction
    with client.session_transaction() as session:
        session["auth_captcha_key"] = mock_captcha["key"]
        session["auth_captcha_svg"] = mock_captcha["content"]
        session["auth_captcha_cookies"] = mock_captcha["cookies"]

    # We will mock requests.post (in auth/service.py _authenticate_live)
    # GDT auth fails on first 2 attempts with captcha error, then succeeds on 3rd attempt
    mock_response_fail = MagicMock()
    mock_response_fail.status_code = 401
    mock_response_fail.json.return_value = {"message": "Mã captcha không đúng"}

    mock_response_success = MagicMock()
    mock_response_success.status_code = 200
    mock_response_success.json.return_value = {"token": "success-jwt-token"}

    # Mock requests.get for profile fetch
    mock_response_profile = MagicMock()
    mock_response_profile.status_code = 200
    mock_response_profile.json.return_value = {
        "fullName": "Cong Ty Test",
        "mst": "0102030405"
    }

    with patch("auth.routes.fetch_captcha_payload", return_value=mock_captcha) as mock_fetch, \
         patch("auth.service.requests.post") as mock_post, \
         patch("auth.service.requests.get") as mock_get:
        
        # Side effect: first two posts fail with captcha error, third succeeds
        mock_post.side_effect = [mock_response_fail, mock_response_fail, mock_response_success]
        mock_get.return_value = mock_response_profile

        # Call the login endpoint
        response = client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "password", "captcha": "AUTO"}
        )

        assert response.status_code == 200
        payload = response.get_json()
        assert payload["status"] == "success"
        
        # Assert that fetch_captcha_payload was called 2 times to fetch new captcha for retries
        # (the first attempt used the session-cached captcha)
        assert mock_fetch.call_count == 2
        # Total posts is 3
        assert mock_post.call_count == 3
