"""Captcha solver engine using offline ddddocr and svglib."""

from __future__ import annotations

import io
import json
import logging
import os
import threading
import time
import xml.etree.ElementTree as ET
from flask import current_app
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM

logger = logging.getLogger(__name__)

# Global OCR instance initialized lazily to optimize application startup time
_ocr_instance = None


class CaptchaAnalytics:
    """Thread-safe statistics counter for CAPTCHA solving engine performance."""
    def __init__(self):
        self.lock = threading.Lock()
        self.success_count = 0
        self.fail_count = 0
        self.total_latency = 0.0
        self.solve_count = 0

    def record_solve(self, latency: float):
        with self.lock:
            self.solve_count += 1
            self.total_latency += latency

    def record_success(self):
        with self.lock:
            self.success_count += 1

    def record_fail(self):
        with self.lock:
            self.fail_count += 1

    def get_stats(self) -> dict:
        with self.lock:
            avg_latency = (self.total_latency / self.solve_count) if self.solve_count > 0 else 0.0
            total_solved = self.success_count + self.fail_count
            accuracy = (self.success_count / total_solved * 100.0) if total_solved > 0 else 100.0
            return {
                "success_count": self.success_count,
                "fail_count": self.fail_count,
                "solve_count": self.solve_count,
                "accuracy_rate": round(accuracy, 2),
                "average_latency_seconds": round(avg_latency, 3),
            }


captcha_analytics = CaptchaAnalytics()


def get_ocr_instance():
    """Lazily load the ddddocr instance to optimize memory and startup times."""
    global _ocr_instance
    if _ocr_instance is None:
        import ddddocr
        # Initialize without printing ads
        _ocr_instance = ddddocr.DdddOcr(show_ad=False)
    return _ocr_instance


STATIC_SIGNATURES = {
    "MQQQQQZMQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQZMQQZ": "A",
    "MQQQQQQQQQZMQQQQQQZMQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQZMQQQQQQQQZMQQQQQQQQZ": "B",
    "MQQQQQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQQQQZ": "C",
    "MQQQQQQQQZMQQQQQQQQQQZMQQQQQQQQQQQQQQQZMQQQQQQQZ": "D",
    "MQQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQQQQQQQZ": "E",
    "MQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQZ": "F",
    "MQQQQQQQQQQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQZ": "G",
    "MQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQQQQZ": "H",
    "MQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQZ": "J",
    "MQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQZ": "K",
    "MQQQQQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQQQQQZ": "M",
    "MQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQZ": "N",
    "MQQQQQQZMQQQQQQQQQQZMQQQQQQQQQQQQQQQZMQQQQQQQQZ": "P",
    "MQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQZ": "Q",
    "MQQQQQQZMQQQQQQQQQQQQZMQQQQQQQQQQQQQQQZMQQQQQQQQZ": "R",
    "MQQQQQQQQQQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQZ": "S",
    "MQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQZ": "T",
    "MQQQQQQQQQQZMQQQQQQQQQQQQQQQQZ": "V",
    "MQQQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQQQQQQQZ": "W",
    "MQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQZ": "X",
    "MQQQQQQQQQZMQQQQQQQQQQQQQZ": "Y",
    "MQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQZ": "Z",
    "MQQQQQQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQQQQQQQQQZ": "2",
    "MQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQZ": "3",
    "MQQQQZMQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQZMQQQQQZ": "4",
    "MQQQQQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQQQQQQQQQQZ": "5",
    "MQQQQQQQQQZMQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQZMQQQQQQQQZ": "6",
    "MQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQQZ": "7",
    "MQQQQQQQQZMQQQQQQQZMQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQQZMQQQQQQQQQZMQQQQQQQZ": "8",
    "MQQQQQQQQZMQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQQQQQQQQQQZMQQQQQQQQQQQZ": "9"
}

_dynamic_signatures = None
_dynamic_signatures_lock = threading.Lock()


def get_dynamic_signatures() -> dict:
    global _dynamic_signatures
    if _dynamic_signatures is None:
        with _dynamic_signatures_lock:
            if _dynamic_signatures is None:
                path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "dynamic_signatures.json")
                if os.path.exists(path):
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            _dynamic_signatures = json.load(f)
                    except Exception as e:
                        logger.error(f"Failed to load dynamic signatures: {e}")
                        _dynamic_signatures = {}
                else:
                    _dynamic_signatures = {}
    return _dynamic_signatures


def save_dynamic_signatures(new_sigs: dict):
    global _dynamic_signatures
    with _dynamic_signatures_lock:
        if _dynamic_signatures is None:
            _dynamic_signatures = get_dynamic_signatures()
        else:
            path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "dynamic_signatures.json")
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        disk_sigs = json.load(f)
                        _dynamic_signatures.update(disk_sigs)
                except Exception as e:
                    logger.warning(f"Could not reload signatures from disk before save: {e}")
        
        _dynamic_signatures.update(new_sigs)
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "dynamic_signatures.json")
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(_dynamic_signatures, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save dynamic signatures: {e}")


def solve_via_vector_signatures_from_root(root) -> str | None:
    """
    Directly recognize letters from the SVG paths based on curve and close command signatures.
    Derived from the optimized logic in VBA modDetectCaptcha.
    """
    paths = [p for p in root.iter() if p.tag.endswith('path')]
    dynamic_sigs = get_dynamic_signatures()
    import re
    detected_chars = []
    
    for p in paths:
        fill = p.attrib.get('fill', '').lower()
        stroke = p.attrib.get('stroke', '')
        
        # Filter background noise paths (fill="none" or stroke attributes)
        if fill == 'none' or stroke:
            continue
            
        d = p.attrib.get('d', '')
        if not d:
            continue
            
        # Extract starting X coordinate for sorting
        x_match = re.search(r'[Mm]\s*(-?\d+\.?\d*)', d)
        if not x_match:
            continue
        try:
            start_x = float(x_match.group(1))
        except ValueError:
            continue
            
        # Extract MQZ path pattern
        signature = re.sub(r'([MQZ])([^MQZ]*)', r'\1', d)
        signature = re.sub(r'\s+', '', signature)
        
        if signature in STATIC_SIGNATURES:
            char = STATIC_SIGNATURES[signature]
            detected_chars.append((start_x, char))
        elif signature in dynamic_sigs:
            char = dynamic_sigs[signature]
            detected_chars.append((start_x, char))
        else:
            logger.debug(f"Unknown vector path signature: '{signature}' at start_x={start_x}")
            return None
            
    if not detected_chars:
        return None
        
    # Sort characters left to right
    detected_chars.sort(key=lambda x: x[0])
    return "".join(char for _, char in detected_chars)


def solve_captcha_from_svg(svg_content: str) -> str:
    """
    Solve GDT vector captcha offline.
    
    Workflow:
    1. Parse the GDT SVG XML.
    2. Try pure vector path signature matching for an instant 100% accurate solution.
    3. If vector matching fails, render the clean character SVG in-memory to PNG bytes and solve with ddddocr.
    """
    if not svg_content:
        return ""

    start_time = time.time()
    try:
        # Register default namespace for correct serialization
        ET.register_namespace('', 'http://www.w3.org/2000/svg')
        root = ET.fromstring(svg_content)

        # Check if there is a text element (used in mock mode captchas)
        text_elements = [t for t in root.iter() if t.tag.endswith('text')]
        for t in text_elements:
            if t.text and t.text.strip():
                logger.info(f"Mock CAPTCHA solved via text tag: {t.text.strip().upper()}")
                latency = time.time() - start_time
                captcha_analytics.record_solve(latency)
                return t.text.strip().upper()

        # Try pure vector signature solver
        vector_result = solve_via_vector_signatures_from_root(root)
        if vector_result:
            logger.info(f"CAPTCHA solved via Vector Path Signatures: {vector_result}")
            latency = time.time() - start_time
            captcha_analytics.record_solve(latency)
            return vector_result

        # 1. Locate all path elements across namespaces
        paths = [p for p in root.iter() if p.tag.endswith('path')]
        
        # Build parent map to safely remove nested paths in any XML structure
        parent_map = {c: p for p in root.iter() for c in p}
        
        # 2. Separate noise paths and keep character paths
        character_paths = []
        for p in paths:
            fill = p.attrib.get('fill', '').lower()
            stroke = p.attrib.get('stroke', '')

            # Noise lines have fill="none" or a stroke value (like #777, #222)
            if fill == 'none' or stroke:
                parent = parent_map.get(p, root)
                try:
                    parent.remove(p)
                except ValueError:
                    pass
            else:
                character_paths.append(p)

        # 3. Extract the starting X coordinate to sort letters left-to-right.
        # This is critical because character paths in GDT SVGs are occasionally out of order.
        # Path data 'd' command starts with M/m followed by coordinates (e.g. M24.98 35.13)
        def get_start_x(path_element) -> float:
            d = path_element.attrib.get('d', '')
            import re
            match = re.search(r'[Mm]\s*(-?\d+\.?\d*)', d)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    pass
            parts = d.replace(',', ' ').split()
            for i, part in enumerate(parts):
                if part.upper().startswith('M'):
                    val = part[1:]
                    if val:
                        try:
                            return float(val)
                        except ValueError:
                            pass
                    # If there's a space after M command, read next part
                    if i + 1 < len(parts):
                        try:
                            return float(parts[i + 1])
                        except ValueError:
                            pass
            return 0.0

        # Remove keep-paths so we can append them back in sorted order
        for p in character_paths:
            parent = parent_map.get(p, root)
            try:
                parent.remove(p)
            except ValueError:
                pass

        # Sort paths by their horizontal position
        sorted_character_paths = sorted(character_paths, key=get_start_x)
        for p in sorted_character_paths:
            root.append(p)

        # Write the cleaned SVG to byte string
        cleaned_svg_bytes = ET.tostring(root, encoding='utf-8')

        # 4. Render clean SVG to PNG bytes in-memory using svglib and reportlab
        drawing = svg2rlg(io.BytesIO(cleaned_svg_bytes))
        png_buffer = io.BytesIO()
        renderPM.drawToFile(drawing, png_buffer, fmt="PNG")
        png_bytes = png_buffer.getvalue()

        # 5. Classify the clean image using ddddocr
        ocr = get_ocr_instance()
        result = ocr.classification(png_bytes)
        
        # 6. Standardize results (uppercase letters & digits only)
        if result:
            solved_text = result.strip().upper()
            logger.info(f"CAPTCHA solved: {solved_text}")
            
            # Dynamic self-learning logic:
            # If the solved text length matches the number of paths exactly, learn unknown signatures.
            if len(solved_text) == len(sorted_character_paths):
                new_sigs = {}
                import re
                dynamic_sigs = get_dynamic_signatures()
                for idx, path_el in enumerate(sorted_character_paths):
                    d_attr = path_el.attrib.get('d', '')
                    if d_attr:
                        sig = re.sub(r'([MQZ])([^MQZ]*)', r'\1', d_attr)
                        sig = re.sub(r'\s+', '', sig)
                        if sig not in STATIC_SIGNATURES and sig not in dynamic_sigs:
                            char_val = solved_text[idx]
                            new_sigs[sig] = char_val
                if new_sigs:
                    save_dynamic_signatures(new_sigs)
                    logger.info(f"CAPTCHA solver dynamically learned new vector signature(s): {new_sigs}")

            latency = time.time() - start_time
            captcha_analytics.record_solve(latency)
            return solved_text
            
    except Exception as e:
        latency = time.time() - start_time
        captcha_analytics.record_solve(latency)
        logger.error(f"Error solving captcha from SVG: {e}", exc_info=True)
        raise RuntimeError(f"Lỗi giải captcha: {e}") from e

    latency = time.time() - start_time
    captcha_analytics.record_solve(latency)
    return ""
