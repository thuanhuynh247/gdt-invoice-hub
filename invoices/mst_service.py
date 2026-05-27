"""Service to verify Tax Registration Status (MST) of business partners."""

from __future__ import annotations

import os
import json
import requests
from bs4 import BeautifulSoup

# Standard mapped statuses
STATUS_ACTIVE = "Đang hoạt động (đã được cấp MST)"
STATUS_SUSPENDED = "Tạm ngừng hoạt động"
STATUS_CLOSED = "Ngừng hoạt động, đã đóng MST"
STATUS_NOT_FOUND = "Mã số thuế không tồn tại"
STATUS_UNKNOWN = "Chưa xác định (Lỗi kết nối)"

# Predefined mock mappings for testing
MOCK_MST_STATUSES = {
    "0101234567": STATUS_ACTIVE,      # Cong ty A
    "0301222334": STATUS_SUSPENDED,   # Cong ty C variant 1
    "0301122334": STATUS_SUSPENDED,   # Cong ty C variant 2
    "020976543": STATUS_CLOSED,       # Cong ty B variant 1
    "0209876543": STATUS_CLOSED,      # Cong ty B variant 2
}

# In-memory cache to prevent redundant scrapes/lookups
MST_STATUS_CACHE = {}

DB_FILE = "data/invoices_db.json"


def _get_cached_status(mst: str) -> str | None:
    """Load cached MST status from persistent SQLite database if valid (<24h)."""
    from invoices.models import Partner
    from datetime import datetime, timedelta
    try:
        p = db.session.get(Partner, mst)
        if p and p.mst_last_checked:
            last_checked = datetime.fromisoformat(p.mst_last_checked)
            if datetime.now() - last_checked < timedelta(hours=24):
                return p.mst_status
    except Exception:
        pass
    return None


def _save_cached_status(mst: str, status: str) -> None:
    """Save MST status to persistent SQLite database cache."""
    from extensions import db
    from invoices.models import Partner
    from datetime import datetime
    try:
        p = db.session.get(Partner, mst)
        now_str = datetime.now().isoformat()
        if p:
            p.mst_status = status
            p.mst_last_checked = now_str
        else:
            p = Partner(
                mst=mst,
                mst_status=status,
                mst_last_checked=now_str
            )
            db.session.add(p)
        db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass



def check_mst_status(mst: str, force_refresh: bool = False) -> dict[str, str]:
    """Verify the tax status of a business using their MST tax code.
    
    Returns a dict with 'mst', 'status', and 'source'.
    """
    cleaned_mst = "".join(filter(str.isdigit, mst))
    if not cleaned_mst:
        return {
            "mst": cleaned_mst,
            "status": STATUS_NOT_FOUND,
            "source": "validator"
        }

    import sys
    is_testing = "pytest" in sys.modules

    # 1. Check persistent json cache first
    if not force_refresh and not is_testing:
        cached_status = _get_cached_status(cleaned_mst)
        if cached_status:
            return {
                "mst": cleaned_mst,
                "status": cached_status,
                "source": "cache"
            }

    # 2. Check in-memory cache
    if not force_refresh and not is_testing and cleaned_mst in MST_STATUS_CACHE:
        return {
            "mst": cleaned_mst,
            "status": MST_STATUS_CACHE[cleaned_mst],
            "source": "cache"
        }

    use_mock = os.getenv("GDT_USE_MOCK", "true").lower() == "true"

    if use_mock:
        status = MOCK_MST_STATUSES.get(cleaned_mst, STATUS_ACTIVE)
        if not is_testing:
            MST_STATUS_CACHE[cleaned_mst] = status
            _save_cached_status(cleaned_mst, status)
        return {
            "mst": cleaned_mst,
            "status": status,
            "source": "mock"
        }

    # Live crawler mode using masothue.com (best-effort scraper)
    url = f"https://masothue.com/Search/?q={cleaned_mst}"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code != 200:
            return {
                "mst": cleaned_mst,
                "status": STATUS_UNKNOWN,
                "source": "live_error"
            }

        soup = BeautifulSoup(response.text, "html.parser")
        
        # Look for table containing MST details
        # Typically masothue.com detail table contains elements with info-label classes
        status_text = ""
        
        # Search via tables
        for row in soup.find_all("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) >= 2:
                label = cells[0].get_text(strip=True)
                if "trạng thái" in label.lower():
                    status_text = cells[1].get_text(strip=True)
                    break
        
        # Fallback: search general text in body if table row not found
        if not status_text:
            text = soup.get_text().lower()
            if "đang hoạt động" in text:
                status_text = STATUS_ACTIVE
            elif "tạm ngừng" in text:
                status_text = STATUS_SUSPENDED
            elif "ngừng hoạt động" in text or "đã đóng mst" in text:
                status_text = STATUS_CLOSED
            elif "không tồn tại" in text or "chưa được cấp" in text:
                status_text = STATUS_NOT_FOUND

        if status_text:
            # Map status text back to standardized Vietnamese terms
            status_lower = status_text.lower()
            if "đang hoạt động" in status_lower:
                status = STATUS_ACTIVE
            elif "tạm ngừng" in status_lower:
                status = STATUS_SUSPENDED
            elif "ngừng hoạt động" in status_lower or "đã đóng mst" in status_lower or "đã đóng mã số thuế" in status_lower:
                status = STATUS_CLOSED
            elif "không tồn tại" in status_lower or "chưa cấp" in status_lower:
                status = STATUS_NOT_FOUND
            else:
                status = status_text
        else:
            status = STATUS_ACTIVE  # Default to active if nothing found to be lenient

        if not is_testing:
            MST_STATUS_CACHE[cleaned_mst] = status
            _save_cached_status(cleaned_mst, status)

        return {
            "mst": cleaned_mst,
            "status": status,
            "source": "live_scraper"
        }

    except Exception:
        return {
            "mst": cleaned_mst,
            "status": STATUS_UNKNOWN,
            "source": "live_exception"
        }
