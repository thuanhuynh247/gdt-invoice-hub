"""High-Performance Parallel Batch XML Parser and Compressor (US-112, US-113).

Provides concurrent XML parsing via thread pools and zlib compression/decompression
pipelines for optimized invoice database storage.
"""

from __future__ import annotations

import zlib
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field


@dataclass
class ParseResult:
    """Outcome of parsing a single XML invoice."""
    filename: str
    success: bool
    data: dict = field(default_factory=dict)
    error_message: str = ""


# ── US-113: Compression and Decompression Pipelines ───────────────

def compress_xml(xml_content: str) -> bytes:
    """Compress XML string into zlib bytes."""
    if not xml_content:
        return b""
    return zlib.compress(xml_content.encode("utf-8"), level=9)


def decompress_xml(compressed_bytes: bytes) -> str:
    """Decompress zlib bytes back into a UTF-8 XML string."""
    if not compressed_bytes:
        return ""
    return zlib.decompress(compressed_bytes).decode("utf-8")


# ── US-112: High-Performance Concurrent Parser ────────────────────

def parse_single_xml(filename: str, xml_content: str) -> ParseResult:
    """Parse a single XML invoice string, extracting core fields."""
    try:
        # Basic XML parsing
        root = ET.fromstring(xml_content)
        
        # Look for invoice data fields (or fallback to tag matching)
        data = {}
        
        # Helper to find tag irrespective of namespace
        def find_tag_text(tag_name: str) -> str:
            for elem in root.iter():
                if elem.tag.split("}")[-1] == tag_name:
                    return elem.text or ""
            return ""

        data["invoice_number"] = find_tag_text("invoice_number") or find_tag_text("SHDon")
        data["seller_mst"] = find_tag_text("seller_mst") or find_tag_text("MSTNBan")
        data["buyer_mst"] = find_tag_text("buyer_mst") or find_tag_text("MSTNMua")
        
        # Numeric parse
        before_tax_str = find_tag_text("amount_before_tax") or find_tag_text("TgTCThue")
        tax_amt_str = find_tag_text("tax_amount") or find_tag_text("TgTThue")
        total_str = find_tag_text("total_amount") or find_tag_text("TgTTTToan")

        try:
            data["amount_before_tax"] = float(before_tax_str) if before_tax_str else 0.0
        except ValueError:
            data["amount_before_tax"] = 0.0

        try:
            data["tax_amount"] = float(tax_amt_str) if tax_amt_str else 0.0
        except ValueError:
            data["tax_amount"] = 0.0

        try:
            data["total_amount"] = float(total_str) if total_str else 0.0
        except ValueError:
            data["total_amount"] = 0.0

        return ParseResult(filename=filename, success=True, data=data)
    except Exception as e:
        return ParseResult(filename=filename, success=False, error_message=str(e))


def parse_batch_xml(
    invoices: list[tuple[str, str]],
    max_workers: int = 4,
) -> list[ParseResult]:
    """Parse a batch of XML invoices concurrently using a thread pool.

    invoices is a list of tuples: (filename, xml_content_string)
    """
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(parse_single_xml, filename, content)
            for filename, content in invoices
        ]
        for future in futures:
            try:
                results.append(future.result())
            except Exception as e:
                results.append(ParseResult(filename="unknown", success=False, error_message=str(e)))
    return results
