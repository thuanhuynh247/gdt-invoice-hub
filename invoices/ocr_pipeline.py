"""Intelligent Document Processing (IDP) Pipeline for scanned invoices (US-102, US-103).

Provides regex-based OCR text extraction and structured field parsing for
Vietnamese VAT invoices. Works with pre-extracted text (from Tesseract,
Google Vision, etc.) to maintain zero external dependency.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone


@dataclass
class OCRExtractionResult:
    """Result of raw text extraction from a document."""
    raw_text: str
    source_filename: str = ""
    page_count: int = 1
    extracted_at: str = ""
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ParsedInvoiceFields:
    """Structured invoice fields extracted from OCR text."""
    seller_name: str = ""
    seller_mst: str = ""
    seller_address: str = ""
    buyer_name: str = ""
    buyer_mst: str = ""
    buyer_address: str = ""
    invoice_number: str = ""
    invoice_symbol: str = ""
    invoice_date: str = ""
    amount_before_tax: float = 0.0
    tax_rate: str = ""
    tax_amount: float = 0.0
    total_amount: float = 0.0
    payment_method: str = ""
    confidence: float = 0.0
    warnings: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ── Vietnamese Number Parsing ─────────────────────────────────────

def parse_vietnamese_number(text: str) -> float:
    """Parse a Vietnamese-formatted number string to float.

    Vietnamese uses dots for thousands and commas for decimals:
      '1.500.000' -> 1500000.0
      '2.350.000,50' -> 2350000.5
      '150000' -> 150000.0
    """
    if not text:
        return 0.0

    cleaned = text.strip().replace(" ", "")

    # Handle Vietnamese decimal format: comma is decimal separator
    if "," in cleaned:
        parts = cleaned.rsplit(",", 1)
        integer_part = parts[0].replace(".", "")
        decimal_part = parts[1] if len(parts) > 1 else "0"
        try:
            return float(f"{integer_part}.{decimal_part}")
        except ValueError:
            return 0.0
    else:
        # Remove dot thousands separators
        cleaned = cleaned.replace(".", "")
        try:
            return float(cleaned)
        except ValueError:
            return 0.0


# ── OCR Text Extraction (US-102) ──────────────────────────────────

def extract_text_from_content(content: str, filename: str = "") -> OCRExtractionResult:
    """Process raw text content (simulating OCR output).

    In production, this would call Tesseract or Google Vision API.
    For now, it accepts pre-OCR'd text and normalizes it.
    """
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Basic text normalization
    normalized = content.strip()
    normalized = re.sub(r'\r\n', '\n', normalized)
    normalized = re.sub(r'[ \t]+', ' ', normalized)

    # Estimate confidence based on presence of key invoice markers
    confidence = 0.0
    markers = [
        r'(?i)h[oó]a\s*[dđ][oơ]n',    # "hóa đơn"
        r'(?i)m[aã]\s*s[oố]\s*thu[eế]', # "mã số thuế"
        r'(?i)MST',
        r'(?i)c[oộ]ng\s*ti[eề]n',       # "cộng tiền"
        r'\d{10,13}',                     # MST pattern
    ]
    for pattern in markers:
        if re.search(pattern, normalized):
            confidence += 0.2

    confidence = min(confidence, 1.0)

    return OCRExtractionResult(
        raw_text=normalized,
        source_filename=filename,
        page_count=max(1, normalized.count("\f") + 1),
        extracted_at=now,
        confidence=round(confidence, 2),
    )


# ── Structured Invoice Parser (US-103) ────────────────────────────

# Regex patterns for Vietnamese invoice field extraction
PATTERNS = {
    "mst": re.compile(
        r'(?:MST|M[aã]\s*s[oố]\s*thu[eế]|m[aã]\s*s[oố]\s*thu[eế])\s*[:\-]?\s*(\d[\d\-]{8,14})',
        re.IGNORECASE,
    ),
    "invoice_number": re.compile(
        r'(?:S[oố]\s*[:\-]?\s*|No[.\s]*[:\-]?\s*)(\d{4,10})',
        re.IGNORECASE,
    ),
    "invoice_symbol": re.compile(
        r'(?:K[yý]\s*hi[eệ]u\s*[:\-]?\s*|Symbol\s*[:\-]?\s*)([A-Z0-9/\-]{2,20})',
        re.IGNORECASE,
    ),
    "date": re.compile(
        r'(?:Ng[aà]y\s*|Date\s*[:\-]?\s*)(\d{1,2}[/\-]\d{1,2}[/\-]\d{4})',
        re.IGNORECASE,
    ),
    "amount": re.compile(
        r'(?:C[oộ]ng\s*ti[eề]n\s*h[aà]ng|Th[aà]nh\s*ti[eề]n|Amount)\s*[:\-]?\s*([\d.,]+)',
        re.IGNORECASE,
    ),
    "tax_amount": re.compile(
        r'(?:Ti[eề]n\s*thu[eế]\s*GTGT|Thu[eế]\s*GTGT|VAT\s*Amount)\s*[:\-]?\s*([\d.,]+)',
        re.IGNORECASE,
    ),
    "total": re.compile(
        r'(?:T[oổ]ng\s*c[oộ]ng|T[oổ]ng\s*thanh\s*to[aá]n|Total)\s*[:\-]?\s*([\d.,]+)',
        re.IGNORECASE,
    ),
    "tax_rate": re.compile(
        r'(?:Thu[eế]\s*su[aấ]t|Tax\s*Rate)\s*[:\-]?\s*(\d+)\s*%',
        re.IGNORECASE,
    ),
    "payment_method": re.compile(
        r'(?:H[iì]nh\s*th[uứ]c\s*thanh\s*to[aá]n|Payment)\s*[:\-]?\s*(.+?)(?:\n|$)',
        re.IGNORECASE,
    ),
    "company_name": re.compile(
        r'(?:C[oô]ng\s*ty|T[eê]n\s*[dđ][oơ]n\s*v[iị]|Company)\s*[:\-]?\s*(.+?)(?:\n|$)',
        re.IGNORECASE,
    ),
    "address": re.compile(
        r'(?:[DĐ][iị]a\s*ch[iỉ]|Address)\s*[:\-]?\s*(.+?)(?:\n|$)',
        re.IGNORECASE,
    ),
}


def parse_invoice_from_text(raw_text: str) -> ParsedInvoiceFields:
    """Extract structured invoice fields from OCR text using regex patterns."""
    result = ParsedInvoiceFields()
    warnings = []
    fields_found = 0

    # Extract MSTs (first = seller, second = buyer)
    mst_matches = PATTERNS["mst"].findall(raw_text)
    if len(mst_matches) >= 1:
        result.seller_mst = mst_matches[0].replace("-", "")
        fields_found += 1
    else:
        warnings.append("Không tìm thấy MST người bán")

    if len(mst_matches) >= 2:
        result.buyer_mst = mst_matches[1].replace("-", "")
        fields_found += 1
    else:
        warnings.append("Không tìm thấy MST người mua")

    # Company names (first = seller, second = buyer)
    names = PATTERNS["company_name"].findall(raw_text)
    if len(names) >= 1:
        result.seller_name = names[0].strip()
        fields_found += 1
    if len(names) >= 2:
        result.buyer_name = names[1].strip()

    # Addresses
    addrs = PATTERNS["address"].findall(raw_text)
    if len(addrs) >= 1:
        result.seller_address = addrs[0].strip()
    if len(addrs) >= 2:
        result.buyer_address = addrs[1].strip()

    # Invoice number
    num_match = PATTERNS["invoice_number"].search(raw_text)
    if num_match:
        result.invoice_number = num_match.group(1)
        fields_found += 1
    else:
        warnings.append("Không tìm thấy số hóa đơn")

    # Invoice symbol
    sym_match = PATTERNS["invoice_symbol"].search(raw_text)
    if sym_match:
        result.invoice_symbol = sym_match.group(1)

    # Date
    date_match = PATTERNS["date"].search(raw_text)
    if date_match:
        result.invoice_date = date_match.group(1)
        fields_found += 1

    # Amounts
    amt_match = PATTERNS["amount"].search(raw_text)
    if amt_match:
        result.amount_before_tax = parse_vietnamese_number(amt_match.group(1))
        fields_found += 1

    tax_match = PATTERNS["tax_amount"].search(raw_text)
    if tax_match:
        result.tax_amount = parse_vietnamese_number(tax_match.group(1))
        fields_found += 1

    total_match = PATTERNS["total"].search(raw_text)
    if total_match:
        result.total_amount = parse_vietnamese_number(total_match.group(1))
        fields_found += 1

    # Tax rate
    rate_match = PATTERNS["tax_rate"].search(raw_text)
    if rate_match:
        result.tax_rate = f"{rate_match.group(1)}%"

    # Payment method
    pay_match = PATTERNS["payment_method"].search(raw_text)
    if pay_match:
        result.payment_method = pay_match.group(1).strip()

    # Compute confidence score based on fields found
    max_fields = 7  # MST seller, MST buyer, number, date, amount, tax, total
    result.confidence = round(fields_found / max_fields, 2)
    result.warnings = warnings

    return result


# ── Review Queue Management ───────────────────────────────────────

REVIEW_QUEUE: list[dict] = []


def add_to_review_queue(parsed: ParsedInvoiceFields, filename: str = ""):
    """Add a low-confidence parsed result to the manual review queue."""
    REVIEW_QUEUE.append({
        "filename": filename,
        "parsed_fields": parsed.to_dict(),
        "added_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })


def get_review_queue() -> list[dict]:
    """Return all items in the manual review queue."""
    return list(REVIEW_QUEUE)


def clear_review_queue():
    """Clear the review queue."""
    REVIEW_QUEUE.clear()
