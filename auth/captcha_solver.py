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

# Custom signatures persistence path
CUSTOM_SIGNATURES_FILE = os.path.join(os.path.dirname(__file__), "custom_signatures.json")
_custom_signatures = {}
_custom_signatures_lock = threading.Lock()

# Thread-safe queue for buffered candidate mappings prior to taxpayer login confirmation
_pending_mappings = {}
_pending_lock = threading.Lock()


class CaptchaAnalytics:
    """Thread-safe statistics counter for CAPTCHA solving engine performance."""
    def __init__(self):
        self.lock = threading.Lock()
        self.success_count = 0
        self.fail_count = 0
        self.total_latency = 0.0
        self.solve_count = 0
        self.vector_solve_count = 0
        self.ocr_solve_count = 0

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

    def record_vector_solve(self):
        with self.lock:
            self.vector_solve_count += 1

    def record_ocr_solve(self):
        with self.lock:
            self.ocr_solve_count += 1

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
                "vector_solve_count": self.vector_solve_count,
                "ocr_solve_count": self.ocr_solve_count,
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


# Standard base signatures mapped to characters (derived from VBA modDetectCaptcha)
BASE_SIGNATURES = {
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
    "MQQQQZMQQQQQQQQQQZMQQQQQQQQQQQQQQQZMQQQQQQQQZ": "P",  # Standardized from MQQQQQQZMQQQQQQQQQQZMQQQQQQQQQQQQQQQZMQQQQQQQQZ
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


def load_custom_signatures():
    """Load previously learned custom vector signatures from disk."""
    global _custom_signatures
    if os.path.exists(CUSTOM_SIGNATURES_FILE):
        try:
            with open(CUSTOM_SIGNATURES_FILE, "r", encoding="utf-8") as f:
                with _custom_signatures_lock:
                    _custom_signatures = json.load(f)
            logger.info(f"Loaded {len(_custom_signatures)} custom signatures from {CUSTOM_SIGNATURES_FILE}")
        except Exception as e:
            logger.error(f"Failed to load custom signatures: {e}")
            with _custom_signatures_lock:
                _custom_signatures = {}
    else:
        with _custom_signatures_lock:
            _custom_signatures = {}


def get_active_signatures() -> dict:
    """Return merged dictionary of base and custom signatures."""
    with _custom_signatures_lock:
        return {**BASE_SIGNATURES, **_custom_signatures}


def prune_pending_mappings():
    """Prune candidate CAPTCHA mappings that are older than 5 minutes."""
    cutoff = time.time() - 300.0
    expired = []
    with _pending_lock:
        for k, v in _pending_mappings.items():
            if v.get("timestamp", 0) < cutoff:
                expired.append(k)
        for k in expired:
            _pending_mappings.pop(k, None)
    if expired:
        logger.info(f"Pruned {len(expired)} expired pending CAPTCHA mappings.")


def commit_learned_signatures(captcha_key: str | None) -> None:
    """Commit buffered custom signatures to file after taxpayer successfully logs in."""
    if not captcha_key:
        return
        
    with _pending_lock:
        pending = _pending_mappings.pop(captcha_key, None)
        
    if not pending:
        logger.debug(f"No pending vector signatures found for CAPTCHA key '{captcha_key}'")
        return
        
    mappings = pending["mappings"]
    active = get_active_signatures()
    new_sigs = {}
    for sig, char in mappings:
        if active.get(sig) != char:
            new_sigs[sig] = char
            
    if new_sigs:
        try:
            with _custom_signatures_lock:
                current_custom = {}
                if os.path.exists(CUSTOM_SIGNATURES_FILE):
                    with open(CUSTOM_SIGNATURES_FILE, "r", encoding="utf-8") as f:
                        current_custom = json.load(f)
                
                updated = False
                for sig, char in new_sigs.items():
                    if current_custom.get(sig) != char:
                        current_custom[sig] = char
                        updated = True
                        
                if updated:
                    with open(CUSTOM_SIGNATURES_FILE, "w", encoding="utf-8") as f:
                        json.dump(current_custom, f, indent=4, ensure_ascii=False)
                    global _custom_signatures
                    _custom_signatures = current_custom
                    logger.info(f"Committed {len(new_sigs)} new custom signatures to file for key '{captcha_key}'. Total custom: {len(_custom_signatures)}")
        except Exception as e:
            logger.error(f"Error committing custom signatures: {e}")


# Initialize custom signatures on import
load_custom_signatures()


def solve_via_vector_signatures_from_root(root) -> str | None:
    """
    Directly recognize letters from the SVG paths based on curve and close command signatures.
    Derived from the optimized logic in VBA modDetectCaptcha.
    """
    paths = [p for p in root.iter() if p.tag.endswith('path')]
    signatures = get_active_signatures()
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
            
        # Extract MQZ path pattern (case-insensitive)
        signature = re.sub(r'([MQZmqz])([^MQZmqz]*)', r'\1', d)
        signature = signature.upper()
        signature = re.sub(r'\s+', '', signature)
        
        if signature in signatures:
            char = signatures[signature]
            detected_chars.append((start_x, char))
        else:
            logger.debug(f"Unknown vector path signature: '{signature}' at start_x={start_x}")
            return None
            
    if not detected_chars:
        return None
        
    # Sort characters left to right
    detected_chars.sort(key=lambda x: x[0])
    return "".join(char for _, char in detected_chars)


def solve_captcha_from_svg(svg_content: str, captcha_key: str | None = None) -> str:
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
                captcha_analytics.record_vector_solve()
                captcha_analytics.record_solve(latency)
                return t.text.strip().upper()

        # Prune expired pending mappings periodically
        prune_pending_mappings()

        # Try pure vector signature solver
        vector_result = solve_via_vector_signatures_from_root(root)
        if vector_result:
            logger.info(f"CAPTCHA solved via Vector Path Signatures: {vector_result}")
            latency = time.time() - start_time
            captcha_analytics.record_vector_solve()
            captcha_analytics.record_solve(latency)
            return vector_result

        # Fallback to OCR solver
        # 1. Locate all path elements across namespaces
        paths = [p for p in root.iter() if p.tag.endswith('path')]
        
        # Build parent map to safely remove nested paths in any XML structure
        parent_map = {c: p for p in root.iter() for c in p}
        
        # 2. Separate noise paths and keep character paths
        character_paths = []
        for p in paths:
            fill = p.attrib.get('fill', '').lower()
            stroke = p.attrib.get('stroke', '')

            # Noise lines have fill="none" or a stroke value
            if fill == 'none' or stroke:
                parent = parent_map.get(p, root)
                try:
                    parent.remove(p)
                except ValueError:
                    pass
            else:
                character_paths.append(p)

        # 3. Extract the starting X coordinate to sort letters left-to-right.
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
            logger.info(f"CAPTCHA solved: {solved_text} (OCR Fallback)")
            latency = time.time() - start_time
            captcha_analytics.record_ocr_solve()
            captcha_analytics.record_solve(latency)

            # Store candidate vector signatures in pending mapping queue
            if captcha_key and len(sorted_character_paths) == len(solved_text):
                import re
                candidates = []
                for i, p in enumerate(sorted_character_paths):
                    d = p.attrib.get('d', '')
                    if d:
                        sig = re.sub(r'([MQZmqz])([^MQZmqz]*)', r'\1', d).upper()
                        sig = re.sub(r'\s+', '', sig)
                        candidates.append((sig, solved_text[i]))
                if len(candidates) == len(solved_text):
                    with _pending_lock:
                        _pending_mappings[captcha_key] = {
                            "mappings": candidates,
                            "timestamp": time.time()
                        }
                    logger.debug(f"Saved {len(candidates)} pending signature mappings for key '{captcha_key}'")

            return solved_text
            
    except Exception as e:
        latency = time.time() - start_time
        captcha_analytics.record_solve(latency)
        logger.error(f"Error solving captcha from SVG: {e}", exc_info=True)
        raise RuntimeError(f"Lỗi giải captcha: {e}") from e

    latency = time.time() - start_time
    captcha_analytics.record_solve(latency)
    return ""

