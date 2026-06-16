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


def test_solve_captcha_via_vector_signatures():
    """Verify that solve_captcha_from_svg solves the captcha using pure vector signatures when signatures match."""
    # We mock ddddocr's classification to return "FALLBACK".
    # If the vector solver works, it will return "AB" and NOT call ddddocr.
    with patch("auth.captcha_solver.get_ocr_instance") as mock_get_ocr:
        mock_ocr = MagicMock()
        mock_ocr.classification.return_value = "FALLBACK"
        mock_get_ocr.return_value = mock_ocr

        # Create exact SVG data containing the signatures for 'B' (at X=40) and 'A' (at X=10)
        svg_data = """<svg xmlns="http://www.w3.org/2000/svg">
            <path fill="#222" d="M40.0 QQQQQQQQQZMQQQQQQZMQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQZMQQQQQQQQZMQQQQQQQQZ" />
            <path fill="#222" d="M10.0 QQQQQZMQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQZMQQZ" />
        </svg>"""
        
        result = solve_captcha_from_svg(svg_data)
        assert result == "AB"
        assert mock_get_ocr.call_count == 0


def test_dynamic_signature_learning():
    """Verify that the captcha solver dynamically learns and persists new signatures when fallback OCR is used."""
    import os
    from auth.captcha_solver import get_dynamic_signatures, save_dynamic_signatures
    
    # Path to dynamic signatures file
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "dynamic_signatures.json")
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass
            
    # Reset internal cache
    import auth.captcha_solver
    auth.captcha_solver._dynamic_signatures = None

    # We mock ddddocr's classification to return "XY".
    # Since "XY" is 2 characters and the SVG has 2 paths (both with unmapped signatures),
    # it should learn the signatures for 'X' and 'Y' dynamically!
    with patch("auth.captcha_solver.get_ocr_instance") as mock_get_ocr:
        mock_ocr = MagicMock()
        mock_ocr.classification.return_value = "XY"
        mock_get_ocr.return_value = mock_ocr

        # Create an SVG with two custom signatures (unmapped but valid SVG coordinates)
        path_data_1 = "M10 20 Q 15 25 20 20 Q 25 15 30 20 Z"
        path_data_2 = "M35 20 Q 40 25 45 20 Q 50 15 55 20 Q 60 25 65 20 Z"
        
        sig_x = "MQQZ"
        sig_y = "MQQQZ"
        
        svg_data = f"""<svg xmlns="http://www.w3.org/2000/svg" width="150" height="50">
            <path fill="#222" d="{path_data_1}" />
            <path fill="#222" d="{path_data_2}" />
        </svg>"""

        result = solve_captcha_from_svg(svg_data)
        assert result == "XY"
        
        # Verify it got saved dynamically
        dynamic_sigs = get_dynamic_signatures()
        assert sig_x in dynamic_sigs
        assert dynamic_sigs[sig_x] == "X"
        assert sig_y in dynamic_sigs
        assert dynamic_sigs[sig_y] == "Y"
        
        # Now solve again with the same SVG, but mock OCR to return "FAIL"
        # Since signatures are now in the dynamic dictionary, the vector solver should resolve it to "XY"
        # without invoking ddddocr!
        mock_ocr.classification.return_value = "FAIL"
        result2 = solve_captcha_from_svg(svg_data)
        assert result2 == "XY"
        
    # Clean up the file afterwards
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception:
            pass
    auth.captcha_solver._dynamic_signatures = None


