"""Tests for invoice_validator.py (v78) – 6 validation checks."""

import types
import pytest
from unittest.mock import MagicMock
from datetime import datetime, timedelta


def _make_invoice(**overrides):
    """Create a mock Invoice object with sensible defaults."""
    inv = MagicMock()
    defaults = {
        "id": "0123456789-C1-001",
        "symbol": "C26TBB",
        "number": "00000001",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "seller_name": "Cong Ty ABC",
        "seller_mst": "0123456789",
        "buyer_name": "Cong Ty XYZ",
        "buyer_mst": "9876543210",
        "amount_before_tax": 1000000,
        "tax_amount": 100000,
        "total_amount": 1100000,
        "has_signature": True,
        "signing_date": datetime.now().strftime("%Y-%m-%d"),
        "is_cancelled": False,
        "invoice_status": "Gốc",
        "import_status": "imported",
        "mccqt": "MCCQT123456",
        "msttcgp": "0100684378",
        "items": [],
        "warnings_json": None,
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(inv, k, v)
    return inv


# ---------- Import ----------
from invoices.invoice_validator import (
    validate_invoice,
    validate_all_invoices,
    SEV_CRITICAL,
    SEV_WARNING,
)


# ============================================================
# 1. Trạng thái bất thường
# ============================================================
class TestTrangThai:
    def test_cancelled_invoice(self):
        inv = _make_invoice(is_cancelled=True)
        alerts = validate_invoice(inv)
        critical = [a for a in alerts if a["check"] == "Trạng thái" and a["severity"] == SEV_CRITICAL]
        assert len(critical) >= 1
        assert "HỦY" in critical[0]["detail"]

    def test_clean_invoice_no_status_alert(self):
        inv = _make_invoice()
        alerts = [a for a in validate_invoice(inv) if a["check"] == "Trạng thái"]
        assert len(alerts) == 0


# ============================================================
# 2. Kết quả xử lý
# ============================================================
class TestKQXuLy:
    def test_missing_mccqt(self):
        inv = _make_invoice(mccqt=None)
        alerts = [a for a in validate_invoice(inv) if a["check"] == "KQ Xử lý"]
        assert len(alerts) >= 1
        assert "Mã CQT" in alerts[0]["detail"]

    def test_has_mccqt_no_alert(self):
        inv = _make_invoice(mccqt="VALID_CODE")
        alerts = [a for a in validate_invoice(inv) if a["check"] == "KQ Xử lý"]
        assert len(alerts) == 0


# ============================================================
# 3. Chéo thuế
# ============================================================
class TestCheoThue:
    def test_mismatch_total(self):
        inv = _make_invoice(
            amount_before_tax=1000000,
            tax_amount=100000,
            total_amount=1200000,  # Should be 1100000
        )
        alerts = [a for a in validate_invoice(inv) if a["check"] == "Chéo thuế"]
        assert any("Chênh lệch" in a["detail"] for a in alerts)

    def test_negative_tax(self):
        inv = _make_invoice(tax_amount=-50000)
        alerts = [a for a in validate_invoice(inv) if a["check"] == "Chéo thuế"]
        assert any("âm" in a["detail"] for a in alerts)

    def test_correct_amounts_no_alert(self):
        inv = _make_invoice(
            amount_before_tax=1000000,
            tax_amount=100000,
            total_amount=1100000,
        )
        alerts = [a for a in validate_invoice(inv) if a["check"] == "Chéo thuế" and "Chênh lệch" in a.get("detail", "")]
        assert len(alerts) == 0


# ============================================================
# 4. Chữ ký số
# ============================================================
class TestChuKySo:
    def test_no_signature(self):
        inv = _make_invoice(has_signature=False)
        alerts = [a for a in validate_invoice(inv) if a["check"] == "Chữ ký số"]
        assert any(a["severity"] == SEV_CRITICAL for a in alerts)

    def test_sign_before_issue(self):
        inv = _make_invoice(
            date="2026-06-20",
            signing_date="2026-06-15",
        )
        alerts = [a for a in validate_invoice(inv) if a["check"] == "Chữ ký số"]
        assert any("TRƯỚC" in a["detail"] for a in alerts)

    def test_late_signing(self):
        inv = _make_invoice(
            date="2026-06-01",
            signing_date="2026-06-15",
        )
        alerts = [a for a in validate_invoice(inv) if a["check"] == "Chữ ký số"]
        assert any("chậm" in a["detail"] for a in alerts)


# ============================================================
# 5. Aging
# ============================================================
class TestAging:
    def test_old_invoice(self):
        old_date = (datetime.now() - timedelta(days=400)).strftime("%Y-%m-%d")
        inv = _make_invoice(date=old_date)
        alerts = [a for a in validate_invoice(inv) if a["check"] == "Aging"]
        assert len(alerts) >= 1

    def test_recent_invoice_no_aging(self):
        inv = _make_invoice(date=datetime.now().strftime("%Y-%m-%d"))
        alerts = [a for a in validate_invoice(inv) if a["check"] == "Aging"]
        assert len(alerts) == 0


# ============================================================
# 6. MST
# ============================================================
class TestMST:
    def test_empty_seller_mst(self):
        inv = _make_invoice(seller_mst="")
        alerts = [a for a in validate_invoice(inv) if a["check"] == "MST"]
        assert any("trống" in a["detail"] and "người bán" in a["detail"] for a in alerts)

    def test_invalid_mst_format(self):
        inv = _make_invoice(seller_mst="ABC123")
        alerts = [a for a in validate_invoice(inv) if a["check"] == "MST"]
        assert len(alerts) >= 1

    def test_valid_mst_10_digits(self):
        inv = _make_invoice(seller_mst="0123456789", buyer_mst="9876543210")
        alerts = [a for a in validate_invoice(inv) if a["check"] == "MST"]
        assert len(alerts) == 0

    def test_valid_mst_13_with_dash(self):
        inv = _make_invoice(seller_mst="0123456789-001", buyer_mst="9876543210")
        alerts = [a for a in validate_invoice(inv) if a["check"] == "MST"]
        assert len(alerts) == 0


# ============================================================
# 7. Định luật Benford (Benford's Law)
# ============================================================
class TestBenfordLaw:
    def test_insufficient_data(self):
        from invoices.invoice_validator import calculate_benford_distribution
        amounts = [100.0] * 10
        res = calculate_benford_distribution(amounts)
        assert res["status"] == "Thiếu dữ liệu"
        assert "tối thiểu 20" in res["message"]

    def test_benford_anomaly_critical(self):
        from invoices.invoice_validator import calculate_benford_distribution
        # 100 amounts all starting with 9 (extremely skewed, expected frequency for 9 is 4.6%)
        amounts = [900000.0] * 100
        res = calculate_benford_distribution(amounts)
        assert res["status"] == "Nghiêm trọng"
        assert res["chi_square_stat"] > 20.09
        assert "lệch cực lớn" in res["message"]


# ============================================================
# 8. Trùng lặp Nội dung (Semantic Duplicates)
# ============================================================
class TestSemanticDuplicates:
    def test_no_duplicates(self):
        from invoices.invoice_validator import check_semantic_duplicates
        inv1 = _make_invoice(id="inv1", number="001", date="2026-06-01")
        inv2 = _make_invoice(id="inv2", number="002", date="2026-06-10") # 9 days apart
        alerts = check_semantic_duplicates([inv1, inv2])
        assert len(alerts) == 0

    def test_warning_duplicate_different_or_no_items(self):
        from invoices.invoice_validator import check_semantic_duplicates
        inv1 = _make_invoice(id="inv1", number="001", date="2026-06-01", total_amount=1000000)
        inv2 = _make_invoice(id="inv2", number="002", date="2026-06-02", total_amount=1000000) # same amount, within 2 days
        alerts = check_semantic_duplicates([inv1, inv2])
        assert len(alerts) == 2 # 1 alert for each referencing the other
        assert all(a["check"] == "Trùng lặp" for a in alerts)
        assert all(a["severity"] == SEV_WARNING for a in alerts)
        assert "Nghi ngờ trùng lặp" in alerts[0]["detail"]

    def test_critical_duplicate_identical_items(self):
        from invoices.invoice_validator import check_semantic_duplicates
        
        # Mock items
        item1 = MagicMock()
        item1.item_name = "Giấy A4"
        item1.quantity = 10.0
        item1.unit_price = 50000.0
        
        item2 = MagicMock()
        item2.item_name = "Giấy A4"
        item2.quantity = 10.0
        item2.unit_price = 50000.0

        inv1 = _make_invoice(id="inv1", number="001", date="2026-06-01", total_amount=500000, items=[item1])
        inv2 = _make_invoice(id="inv2", number="002", date="2026-06-02", total_amount=500000, items=[item2])
        
        alerts = check_semantic_duplicates([inv1, inv2])
        assert len(alerts) == 2
        assert all(a["severity"] == SEV_CRITICAL for a in alerts)
        assert "HOÀN TOÀN" in alerts[0]["detail"]

