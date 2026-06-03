"""Captcha solver engine using offline ddddocr and svglib."""

from __future__ import annotations

import io
import logging
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


def solve_captcha_from_svg(svg_content: str) -> str:
    """
    Solve GDT vector captcha offline.
    
    Workflow:
    1. Parse the GDT SVG XML.
    2. Filter out background noise grid lines (paths with fill="none" or stroke attributes).
    3. Re-sort remaining letter paths from left to right using their X starting coordinates.
    4. Render the clean character SVG in-memory to PNG bytes.
    5. Pass the clean PNG bytes to ddddocr.
    6. Return the uppercase alphanumeric captcha text.
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

        # 1. Locate all path elements across namespaces

        paths = [p for p in root.iter() if p.tag.endswith('path')]
        
        # 2. Separate noise paths and keep character paths
        character_paths = []
        for p in paths:
            fill = p.attrib.get('fill', '').lower()
            stroke = p.attrib.get('stroke', '')

            # Noise lines have fill="none" or a stroke value (like #777, #222)
            if fill == 'none' or stroke:
                try:
                    # Remove noise path from its parent
                    # Since parent can be root or nested, find container
                    parent = root
                    # If we need to find parent in element tree:
                    # In python 3, we can use a helper or root.remove directly if it's direct child.
                    # If it's a nested child, we can use search. But GDT SVGs are flat.
                    root.remove(p)
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
            try:
                root.remove(p)
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
