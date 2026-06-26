"""Invoice Validation Service (v78) - Ported from VBA modKiemTraHoaDon.

Six automated checks run against Invoice records in the webapp database:
  1. Trạng thái bất thường (tthai)  – cancelled, replaced, adjusted
  2. Kết quả xử lý (ttxly)         – pending CQT approval
  3. Chéo thuế (Tax Cross-Check)    – total != before_tax + tax
  4. Chữ ký số (nky)                – missing / late signature
  5. Aging (thời hạn)               – older than 12 months
  6. MST hợp lệ                    – format / empty checks
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any

from invoices.models import Invoice, LineItem


# ── severity constants ─────────────────────────────────────────────
SEV_CRITICAL = "Nghiêm trọng"
SEV_WARNING  = "Cảnh báo"

# ── valid VAT rates ────────────────────────────────────────────────
VALID_TAX_RATES = {0, 5, 8, 10, -1, -2}  # -1=KKKNT, -2=KCT

MST_PATTERN = re.compile(r"^\d{10}(-\d{3})?$")


def _parse_date(d: str | None) -> datetime | None:
    """Try to parse a date string in common formats."""
    if not d:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(d.strip()[:19], fmt)
        except (ValueError, TypeError):
            continue
    return None


# ── individual check functions ─────────────────────────────────────

def _check_trang_thai(inv: Invoice) -> list[dict[str, Any]]:
    """1. Kiểm tra trạng thái bất thường."""
    alerts: list[dict[str, Any]] = []
    status = (inv.invoice_status or "").lower()

    if inv.is_cancelled:
        alerts.append({
            "check": "Trạng thái",
            "severity": SEV_CRITICAL,
            "detail": "Hóa đơn đã bị HỦY. Không được sử dụng để kê khai thuế.",
        })
    if "thay th" in status and ("bị" in status or "replace" in status.lower()):
        alerts.append({
            "check": "Trạng thái",
            "severity": SEV_CRITICAL,
            "detail": f"Hóa đơn bị thay thế ({inv.invoice_status}). Cần kiểm tra HĐ thay thế tương ứng.",
        })
    if "điều chỉnh" in status or "dieu chinh" in status:
        alerts.append({
            "check": "Trạng thái",
            "severity": SEV_WARNING,
            "detail": f"Hóa đơn bị điều chỉnh ({inv.invoice_status}). Cần kiểm tra HĐ điều chỉnh tương ứng.",
        })
    return alerts


def _check_ket_qua_xu_ly(inv: Invoice) -> list[dict[str, Any]]:
    """2. Kiểm tra kết quả xử lý (ttxly) từ warnings / import_status."""
    alerts: list[dict[str, Any]] = []
    imp = (inv.import_status or "").lower()
    status = (inv.invoice_status or "").lower()

    # Chưa có MCCQT = chưa được cấp mã CQT
    if not inv.mccqt and inv.has_signature:
        alerts.append({
            "check": "KQ Xử lý",
            "severity": SEV_WARNING,
            "detail": "Hóa đơn chưa có Mã CQT (mccqt trống). Chưa được cấp mã cơ quan thuế.",
        })

    # Kiểm tra nếu đang chờ xử lý
    if "pending" in imp or "đang" in status:
        alerts.append({
            "check": "KQ Xử lý",
            "severity": SEV_WARNING,
            "detail": f"Hóa đơn đang trong trạng thái chờ xử lý ({inv.import_status}).",
        })
    return alerts


def _check_cheo_thue(inv: Invoice) -> list[dict[str, Any]]:
    """3. Kiểm tra chéo thuế – tổng phải khớp."""
    alerts: list[dict[str, Any]] = []
    before = inv.amount_before_tax or 0.0
    tax    = inv.tax_amount or 0.0
    total  = inv.total_amount or 0.0

    if total > 0 and before > 0:
        expected = before + tax
        diff = abs(total - expected)
        if diff > 1:  # tolerance 1 VND
            alerts.append({
                "check": "Chéo thuế",
                "severity": SEV_CRITICAL,
                "detail": (
                    f"Tổng thanh toán ({total:,.0f}) ≠ Chưa thuế ({before:,.0f}) + "
                    f"Thuế ({tax:,.0f}). Chênh lệch: {diff:,.0f} VND."
                ),
            })

    if tax < 0:
        alerts.append({
            "check": "Chéo thuế",
            "severity": SEV_WARNING,
            "detail": f"Tiền thuế âm: {tax:,.0f}. Cần xác nhận lại.",
        })

    # Kiểm tra chi tiết hàng hóa vs tổng
    if inv.items:
        items_tax_sum = sum(getattr(it, "tax_amount", 0) or 0 for it in inv.items)
        if abs(items_tax_sum - tax) > 1 and items_tax_sum > 0:
            alerts.append({
                "check": "Chéo thuế",
                "severity": SEV_WARNING,
                "detail": (
                    f"Tổng thuế chi tiết ({items_tax_sum:,.0f}) ≠ "
                    f"Thuế tổng hợp ({tax:,.0f}). Chênh: {abs(items_tax_sum - tax):,.0f}."
                ),
            })
    return alerts


def _check_chu_ky_so(inv: Invoice) -> list[dict[str, Any]]:
    """4. Kiểm tra chữ ký số."""
    alerts: list[dict[str, Any]] = []

    if not inv.has_signature:
        alerts.append({
            "check": "Chữ ký số",
            "severity": SEV_CRITICAL,
            "detail": "Hóa đơn chưa có chữ ký số. Không hợp lệ để kê khai.",
        })
        return alerts

    dt_sign = _parse_date(inv.signing_date)
    dt_issue = _parse_date(inv.date)

    if not dt_sign and inv.has_signature:
        alerts.append({
            "check": "Chữ ký số",
            "severity": SEV_WARNING,
            "detail": "Có chữ ký số nhưng không có ngày ký (signing_date trống).",
        })
        return alerts

    if dt_sign and dt_issue:
        if dt_sign < dt_issue:
            alerts.append({
                "check": "Chữ ký số",
                "severity": SEV_WARNING,
                "detail": (
                    f"Ngày ký ({dt_sign:%d/%m/%Y}) TRƯỚC ngày lập "
                    f"({dt_issue:%d/%m/%Y}). Bất thường."
                ),
            })
        days_late = (dt_sign - dt_issue).days
        if days_late > 5:
            alerts.append({
                "check": "Chữ ký số",
                "severity": SEV_WARNING,
                "detail": f"Ký số chậm {days_late} ngày sau ngày lập.",
            })
    return alerts


def _check_aging(inv: Invoice) -> list[dict[str, Any]]:
    """5. Kiểm tra thời hạn – HĐ quá cũ."""
    alerts: list[dict[str, Any]] = []
    dt_issue = _parse_date(inv.date)
    if not dt_issue:
        return alerts

    age_days = (datetime.now() - dt_issue).days
    if age_days > 365:
        months = round(age_days / 30, 1)
        alerts.append({
            "check": "Aging",
            "severity": SEV_WARNING,
            "detail": (
                f"Hóa đơn đã {age_days} ngày (~{months} tháng) từ ngày lập "
                f"{dt_issue:%d/%m/%Y}. Kiểm tra đã kê khai chưa."
            ),
        })
    return alerts


def _check_mst(inv: Invoice) -> list[dict[str, Any]]:
    """6. Kiểm tra MST hợp lệ."""
    alerts: list[dict[str, Any]] = []

    for role, mst_val in [("người bán", inv.seller_mst), ("người mua", inv.buyer_mst)]:
        mst = (mst_val or "").strip()
        if not mst:
            alerts.append({
                "check": "MST",
                "severity": SEV_CRITICAL,
                "detail": f"MST {role} trống. Hóa đơn không hợp lệ để khấu trừ thuế.",
            })
            continue
        clean = mst.replace("-", "")
        if not MST_PATTERN.match(mst) and (len(clean) not in (10, 13)):
            alerts.append({
                "check": "MST",
                "severity": SEV_WARNING,
                "detail": f"MST {role} [{mst}] không đúng định dạng (cần 10 hoặc 13 ký tự số).",
            })
        elif not clean.isdigit():
            alerts.append({
                "check": "MST",
                "severity": SEV_WARNING,
                "detail": f"MST {role} [{mst}] chứa ký tự không phải số.",
            })
    return alerts


def _check_supplier_risk(inv: Invoice) -> list[dict[str, Any]]:
    """7. Kiểm tra rủi ro nhà cung cấp (Supplier Risk Index)."""
    alerts: list[dict[str, Any]] = []
    
    from invoices.models import Partner
    try:
        partner = Partner.query.filter_by(mst=inv.seller_mst).first()
        if partner:
            status = (partner.mst_status or "").strip()
            if status in ("Ngừng hoạt động", "Bỏ trốn", "Đã đóng mã số thuế", "Đóng mã số thuế"):
                alerts.append({
                    "check": "Rủi ro NCC",
                    "severity": SEV_CRITICAL,
                    "detail": f"Nhà cung cấp {partner.name or inv.seller_name} ({inv.seller_mst}) đã NGỪNG HOẠT ĐỘNG/ĐÓNG MST. Hóa đơn không có giá trị khấu trừ thuế!",
                })
            elif status in ("Rủi ro cao", "Nghi ngờ bán hóa đơn khống"):
                alerts.append({
                    "check": "Rủi ro NCC",
                    "severity": SEV_CRITICAL,
                    "detail": f"Nhà cung cấp {partner.name or inv.seller_name} ({inv.seller_mst}) nằm trong danh sách DOANH NGHIỆP RỦI RO CAO VỀ THUẾ!",
                })
            elif "tạm ngưng" in status.lower() or "tam ngung" in status.lower():
                alerts.append({
                    "check": "Rủi ro NCC",
                    "severity": SEV_WARNING,
                    "detail": f"Nhà cung cấp {partner.name or inv.seller_name} ({inv.seller_mst}) đang TẠM NGƯNG HOẠT ĐỘNG. Cần rà soát chứng từ kỹ lưỡng.",
                })
        
        # Heuristic check on seller address for shell/virtual offices
        addr = (inv.seller_address or "").lower()
        virtual_keywords = ["dịch vụ ảo", "virtual office", "hộp thư", "phòng chia sẻ", "shared office", "co-working space"]
        for kw in virtual_keywords:
            if kw in addr:
                alerts.append({
                    "check": "Rủi ro NCC",
                    "severity": SEV_WARNING,
                    "detail": f"Địa chỉ nhà cung cấp chứa dấu hiệu văn phòng ảo/văn phòng chia sẻ ({kw}). Nguy cơ doanh nghiệp ma.",
                })
    except Exception:
        pass
    return alerts


# ── public API ─────────────────────────────────────────────────────

ALL_CHECKS = [
    _check_trang_thai,
    _check_ket_qua_xu_ly,
    _check_cheo_thue,
    _check_chu_ky_so,
    _check_aging,
    _check_mst,
    _check_supplier_risk,
]


def validate_invoice(inv: Invoice) -> list[dict[str, Any]]:
    """Run all 6 checks on a single invoice.  Returns list of alert dicts."""
    results: list[dict[str, Any]] = []
    for fn in ALL_CHECKS:
        for alert in fn(inv):
            alert["invoice_id"] = inv.id
            alert["symbol"] = inv.symbol or ""
            alert["number"] = inv.number or ""
            alert["seller_mst"] = inv.seller_mst or ""
            alert["buyer_mst"] = inv.buyer_mst or ""
            alert["date"] = inv.date or ""
            results.append(alert)
    return results


# ── Trục 3: Advanced Fraud & Anomaly Audit checks ───────────────────

def calculate_benford_distribution(amounts: list[float]) -> dict[str, Any]:
    """Calculate Benford's Law distribution and Chi-Square goodness-of-fit for first digits."""
    counts = {d: 0 for d in range(1, 10)}
    valid_count = 0
    for val in amounts:
        if not val or val <= 0:
            continue
        # Extract first non-zero digit
        val_str = str(abs(val)).replace(".", "").lstrip("0")
        if val_str:
            first_digit = int(val_str[0])
            if first_digit in counts:
                counts[first_digit] += 1
                valid_count += 1

    expected_pct = {
        1: 30.1, 2: 17.6, 3: 12.5, 4: 9.7, 5: 7.9,
        6: 6.7, 7: 5.8, 8: 5.1, 9: 4.6
    }
    
    observed_pct = {}
    chi_square = 0.0
    
    for d in range(1, 10):
        obs = counts[d]
        pct = (obs / valid_count * 100) if valid_count > 0 else 0.0
        observed_pct[d] = round(pct, 1)
        
        if valid_count >= 20:
            exp_count = valid_count * (expected_pct[d] / 100)
            chi_square += ((obs - exp_count) ** 2) / exp_count
            
    # Determine status
    if valid_count < 20:
        status = "Thiếu dữ liệu"
        message = "Chưa đủ số lượng hóa đơn (cần tối thiểu 20 hóa đơn) để thực hiện phân tích thống kê Định luật Benford."
    elif chi_square > 20.09:
        status = "Nghiêm trọng"
        message = (
            f"Bất thường nghiêm trọng! Phân phối chữ số đầu tiên lệch cực lớn so với Định luật Benford "
            f"(Chi-square = {chi_square:.2f} > 20.09). Cần rà soát nguy cơ chế biến chứng từ."
        )
    elif chi_square > 15.51:
        status = "Cảnh báo"
        message = (
            f"Bất thường! Phân phối chữ số đầu tiên có sai lệch thống kê đáng kể so với Định luật Benford "
            f"(Chi-square = {chi_square:.2f} > 15.51). Đề xuất kiểm tra các hóa đơn có chữ số đầu bất thường."
        )
    else:
        status = "Đạt"
        message = f"Hợp lệ. Phân phối chữ số đầu tiên hoàn toàn khớp với Định luật Benford (Chi-square = {chi_square:.2f} <= 15.51)."

    return {
        "valid_count": valid_count,
        "observed_counts": counts,
        "observed_percentages": observed_pct,
        "expected_percentages": expected_pct,
        "chi_square_stat": round(chi_square, 2),
        "critical_value_05": 15.51,
        "critical_value_01": 20.09,
        "status": status,
        "message": message
    }


def _serialize_items(invoice: Invoice) -> tuple[tuple[str, float, float], ...]:
    """Serialize and sort line items for precise content duplication comparison."""
    items = getattr(invoice, "items", []) or []
    sorted_items = sorted(
        [(getattr(it, "item_name", "") or "").strip().lower(),
         round(getattr(it, "quantity", 0) or 0.0, 4),
         round(getattr(it, "unit_price", 0) or 0.0, 2)]
        for it in items
    )
    return tuple(tuple(x) for x in sorted_items)


def check_semantic_duplicates(invoices: list[Invoice]) -> list[dict[str, Any]]:
    """Detect semantic duplicate invoices (same buyer, seller, amount, and close dates).
    
    Flags as SEV_CRITICAL if items are identical, or SEV_WARNING if items differ or are empty.
    """
    alerts: list[dict[str, Any]] = []
    n = len(invoices)
    
    # Pre-parse dates for performance
    parsed_dates = {}
    for inv in invoices:
        parsed_dates[inv.id] = _parse_date(inv.date)
        
    for i in range(n):
        inv1 = invoices[i]
        date1 = parsed_dates[inv1.id]
        if not date1:
            continue
            
        items1 = _serialize_items(inv1)
        
        for j in range(i + 1, n):
            inv2 = invoices[j]
            date2 = parsed_dates[inv2.id]
            if not date2:
                continue
                
            # Same seller, buyer, and amount (within 1 VND tolerance)
            if (inv1.seller_mst == inv2.seller_mst and
                inv1.buyer_mst == inv2.buyer_mst and
                abs((inv1.total_amount or 0.0) - (inv2.total_amount or 0.0)) < 1.0):
                
                # Within 2 days of each other
                day_diff = abs((date1 - date2).days)
                if day_diff <= 2:
                    items2 = _serialize_items(inv2)
                    
                    # Check if items are identical
                    if items1 and items2 and items1 == items2:
                        detail1 = (
                            f"Phát hiện trùng lặp nội dung HOÀN TOÀN với HĐ số {inv2.number} "
                            f"(Ký hiệu {inv2.symbol}) ngày {inv2.date}. Số tiền: {inv1.total_amount:,.0f} VND."
                        )
                        detail2 = (
                            f"Phát hiện trùng lặp nội dung HOÀN TOÀN với HĐ số {inv1.number} "
                            f"(Ký hiệu {inv1.symbol}) ngày {inv1.date}. Số tiền: {inv2.total_amount:,.0f} VND."
                        )
                        severity = SEV_CRITICAL
                    else:
                        detail1 = (
                            f"Nghi ngờ trùng lặp giao dịch (cùng số tiền {inv1.total_amount:,.0f} VND, cùng đối tác) "
                            f"với HĐ số {inv2.number} ngày {inv2.date}."
                        )
                        detail2 = (
                            f"Nghi ngờ trùng lặp giao dịch (cùng số tiền {inv2.total_amount:,.0f} VND, cùng đối tác) "
                            f"với HĐ số {inv1.number} ngày {inv1.date}."
                        )
                        severity = SEV_WARNING
                        
                    alerts.append({
                        "check": "Trùng lặp",
                        "severity": severity,
                        "detail": detail1,
                        "invoice_id": inv1.id,
                        "symbol": inv1.symbol or "",
                        "number": inv1.number or "",
                        "seller_mst": inv1.seller_mst or "",
                        "buyer_mst": inv1.buyer_mst or "",
                        "date": inv1.date or "",
                    })
                    
                    alerts.append({
                        "check": "Trùng lặp",
                        "severity": severity,
                        "detail": detail2,
                        "invoice_id": inv2.id,
                        "symbol": inv2.symbol or "",
                        "number": inv2.number or "",
                        "seller_mst": inv2.seller_mst or "",
                        "buyer_mst": inv2.buyer_mst or "",
                        "date": inv2.date or "",
                    })
                    
    return alerts


def validate_all_invoices(taxpayer_mst: str | None = None) -> dict[str, Any]:
    """Run validation on all invoices, optionally filtered by taxpayer MST.

    Returns summary + list of alerts sorted by severity.
    """
    query = Invoice.query
    if taxpayer_mst:
        query = query.filter_by(taxpayer_mst=taxpayer_mst)

    invoices = query.all()
    all_alerts: list[dict[str, Any]] = []
    checked = 0
    alerted_ids = set()

    # 1. Run single-invoice checks
    for inv in invoices:
        alerts = validate_invoice(inv)
        checked += 1
        if alerts:
            alerted_ids.add(inv.id)
            all_alerts.extend(alerts)

    # 2. Run cross-invoice semantic duplicate check
    dup_alerts = check_semantic_duplicates(invoices)
    for a in dup_alerts:
        alerted_ids.add(a["invoice_id"])
        all_alerts.extend(a for a in dup_alerts if a not in all_alerts) # prevent exact dup alerts in list

    # Sort: critical first
    severity_order = {SEV_CRITICAL: 0, SEV_WARNING: 1}
    all_alerts.sort(key=lambda a: severity_order.get(a["severity"], 9))

    # Summary by check type
    summary_by_check: dict[str, dict[str, int]] = {}
    for a in all_alerts:
        chk = a["check"]
        if chk not in summary_by_check:
            summary_by_check[chk] = {"critical": 0, "warning": 0, "total": 0}
        summary_by_check[chk]["total"] += 1
        if a["severity"] == SEV_CRITICAL:
            summary_by_check[chk]["critical"] += 1
        else:
            summary_by_check[chk]["warning"] += 1

    # 3. Run Benford's Law analysis
    amounts = [inv.amount_before_tax for inv in invoices]
    benford_res = calculate_benford_distribution(amounts)

    clean = max(0, checked - len(alerted_ids))

    return {
        "total_invoices": checked,
        "clean_invoices": clean,
        "total_alerts": len(all_alerts),
        "critical_count": sum(1 for a in all_alerts if a["severity"] == SEV_CRITICAL),
        "warning_count": sum(1 for a in all_alerts if a["warning_count"] == SEV_WARNING) if False else sum(1 for a in all_alerts if a["severity"] == SEV_WARNING),
        "summary_by_check": summary_by_check,
        "alerts": all_alerts,
        "benford_analysis": benford_res
    }
"""Invoice Validation Service v78 — end of module."""
