"""
V34 Compliance Service – Invoice Aging Analysis & AR/AP Management Engine.

US-460: Invoice Aging Analysis & Accounts Receivable/Payable Engine
US-461: Interactive AR/AP Aging Dashboard & Heatmap UI
"""

from __future__ import annotations

import datetime
import random
from typing import Any, Dict, List, Optional


# ── Aging Bucket Definitions ────────────────────────────────────────────────────

AGING_BUCKETS = [
    {"key": "current", "label": "Chưa đến hạn", "min_days": None, "max_days": 0, "color": "#22c55e"},
    {"key": "1_30", "label": "1-30 ngày", "min_days": 1, "max_days": 30, "color": "#eab308"},
    {"key": "31_60", "label": "31-60 ngày", "min_days": 31, "max_days": 60, "color": "#f97316"},
    {"key": "61_90", "label": "61-90 ngày", "min_days": 61, "max_days": 90, "color": "#ef4444"},
    {"key": "90_plus", "label": "Trên 90 ngày", "min_days": 91, "max_days": None, "color": "#dc2626"},
]


def _classify_aging(days_overdue: int) -> str:
    """Return the aging bucket key for a given number of overdue days."""
    if days_overdue <= 0:
        return "current"
    elif days_overdue <= 30:
        return "1_30"
    elif days_overdue <= 60:
        return "31_60"
    elif days_overdue <= 90:
        return "61_90"
    else:
        return "90_plus"


# ── Mock Invoice Data Generator ─────────────────────────────────────────────────

def _generate_mock_invoices(taxpayer_mst: str, as_of: datetime.date) -> Dict[str, List[Dict]]:
    """Generate realistic mock AR/AP invoice data for aging analysis."""
    random.seed(hash(taxpayer_mst) % 10000)

    ar_invoices = []
    ap_invoices = []

    sellers = ["NCC Thép Việt", "NCC Nhựa Đại Phong", "NCC Điện tử Hoàng Long", "NCC Vật liệu Minh Đức", "NCC Gỗ Phú Quý"]
    buyers = ["KH Xây dựng Hòa Bình", "KH Thương mại Sơn Hà", "KH Sản xuất Tân Phát", "KH Dịch vụ Bảo An", "KH Xuất khẩu Đông Á"]

    for i in range(15):
        days_ago = random.randint(-10, 150)
        due_date = as_of - datetime.timedelta(days=days_ago)
        issue_date = due_date - datetime.timedelta(days=random.randint(15, 45))
        amount = random.randint(5, 200) * 1_000_000

        ar_invoices.append({
            "number": f"HD-BAN-{2026}{i+1:04d}",
            "buyer": random.choice(buyers),
            "issue_date": issue_date.isoformat(),
            "due_date": due_date.isoformat(),
            "amount": float(amount),
            "vat_amount": float(amount * 0.1),
            "total": float(amount * 1.1),
            "days_overdue": max(0, (as_of - due_date).days),
            "paid": random.random() < 0.3,
        })

    for i in range(12):
        days_ago = random.randint(-5, 120)
        due_date = as_of - datetime.timedelta(days=days_ago)
        issue_date = due_date - datetime.timedelta(days=random.randint(10, 30))
        amount = random.randint(3, 150) * 1_000_000

        ap_invoices.append({
            "number": f"HD-MUA-{2026}{i+1:04d}",
            "seller": random.choice(sellers),
            "issue_date": issue_date.isoformat(),
            "due_date": due_date.isoformat(),
            "amount": float(amount),
            "vat_amount": float(amount * 0.1),
            "total": float(amount * 1.1),
            "days_overdue": max(0, (as_of - due_date).days),
            "paid": random.random() < 0.4,
        })

    return {"ar": ar_invoices, "ap": ap_invoices}


# ── US-460: Invoice Aging Analysis Engine ────────────────────────────────────────

def analyze_invoice_aging(
    taxpayer_mst: str,
    as_of_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyze invoice aging for AR (phải thu) and AP (phải trả).
    Returns aging buckets with invoice counts, amounts, and details.
    """
    if as_of_date:
        as_of = datetime.date.fromisoformat(as_of_date)
    else:
        as_of = datetime.date.today()

    mock_data = _generate_mock_invoices(taxpayer_mst, as_of)

    def build_aging(invoices: List[Dict]) -> Dict[str, Any]:
        unpaid = [inv for inv in invoices if not inv["paid"]]
        buckets = {}
        for b in AGING_BUCKETS:
            buckets[b["key"]] = {"label": b["label"], "color": b["color"], "count": 0, "total": 0.0, "invoices": []}

        for inv in unpaid:
            bucket_key = _classify_aging(inv["days_overdue"])
            buckets[bucket_key]["count"] += 1
            buckets[bucket_key]["total"] += inv["total"]
            buckets[bucket_key]["invoices"].append(inv)

        total_outstanding = sum(b["total"] for b in buckets.values())
        total_count = sum(b["count"] for b in buckets.values())
        overdue_amount = sum(b["total"] for k, b in buckets.items() if k != "current")

        return {
            "buckets": buckets,
            "total_outstanding": total_outstanding,
            "total_count": total_count,
            "overdue_amount": overdue_amount,
            "overdue_pct": (overdue_amount / total_outstanding * 100) if total_outstanding > 0 else 0,
        }

    ar_aging = build_aging(mock_data["ar"])
    ap_aging = build_aging(mock_data["ap"])

    return {
        "taxpayer_mst": taxpayer_mst,
        "as_of_date": as_of.isoformat(),
        "accounts_receivable": ar_aging,
        "accounts_payable": ap_aging,
        "status": "analyzed",
    }


# ── US-461: Heatmap Data Generator ──────────────────────────────────────────────

def generate_aging_heatmap_data(aging_result: Dict[str, Any]) -> Dict[str, Any]:
    """Transform aging analysis into structured heatmap grid data."""
    sections = []
    for section_key, label in [("accounts_receivable", "Phải thu (AR)"), ("accounts_payable", "Phải trả (AP)")]:
        section = aging_result.get(section_key, {})
        buckets = section.get("buckets", {})
        total = section.get("total_outstanding", 0)
        cells = []
        for b_def in AGING_BUCKETS:
            bk = b_def["key"]
            bd = buckets.get(bk, {"count": 0, "total": 0})
            pct = (bd["total"] / total * 100) if total > 0 else 0
            intensity = min(pct / 40, 1.0)
            cells.append({
                "bucket": bk,
                "label": b_def["label"],
                "count": bd["count"],
                "total": bd["total"],
                "percentage": round(pct, 1),
                "color": b_def["color"],
                "intensity": round(intensity, 2),
            })
        sections.append({"key": section_key, "label": label, "cells": cells, "grand_total": total})

    return {"sections": sections}


# ── US-461: AR/AP Debt Collection Swarm Advisory ────────────────────────────────

def run_aging_advisory_swarm(
    taxpayer_mst: str,
    taxpayer_name: str,
) -> Dict[str, Any]:
    """Multi-agent swarm advisory for AR/AP aging management and debt collection."""
    aging = analyze_invoice_aging(taxpayer_mst)
    ar = aging["accounts_receivable"]
    ap = aging["accounts_payable"]

    ts = datetime.datetime.now()
    steps = []

    def add(agent, role, msg, cls, offset):
        steps.append({
            "agent": agent, "role": role, "message": msg, "avatar_class": cls,
            "timestamp": (ts + datetime.timedelta(seconds=offset)).strftime("%H:%M:%S"),
        })

    add("DebtCoordinator", "Điều phối công nợ",
        f"Khởi động phân tích công nợ cho <strong>{taxpayer_name}</strong> (MST: {taxpayer_mst}). "
        f"Tổng phải thu: <strong>{ar['total_outstanding']:,.0f}đ</strong> ({ar['total_count']} hóa đơn). "
        f"Tổng phải trả: <strong>{ap['total_outstanding']:,.0f}đ</strong> ({ap['total_count']} hóa đơn).",
        "bg-primary", 0)

    overdue_90_ar = ar["buckets"].get("90_plus", {}).get("total", 0)
    add("ARCollector", "Thu hồi công nợ",
        f"Cảnh báo: <strong>{ar['overdue_pct']:.1f}%</strong> tổng phải thu đã quá hạn. "
        f"Nợ quá hạn trên 90 ngày: <strong>{overdue_90_ar:,.0f}đ</strong>. "
        f"Khuyến nghị: Gửi thư nhắc nợ cho khách hàng quá hạn 31-60 ngày, "
        f"chuyển sang bộ phận pháp lý cho khoản nợ trên 90 ngày.",
        "bg-danger", 3)

    add("APPlanner", "Quản lý thanh toán",
        f"Phải trả chưa thanh toán: <strong>{ap['total_outstanding']:,.0f}đ</strong>. "
        f"Ưu tiên thanh toán hóa đơn gần đến hạn để duy trì uy tín với nhà cung cấp và "
        f"đảm bảo quyền khấu trừ thuế GTGT theo Luật 48/2024/QH15 (thanh toán qua ngân hàng ≥ 5 triệu VND).",
        "bg-warning", 7)

    net_position = ar["total_outstanding"] - ap["total_outstanding"]
    add("DebtCoordinator", "Điều phối công nợ",
        f"Hoàn thành phân tích. Vị thế công nợ ròng: <strong>{net_position:,.0f}đ</strong> "
        f"({'dương - doanh nghiệp đang cho vay ròng' if net_position > 0 else 'âm - doanh nghiệp đang nợ ròng'}). "
        f"Đề xuất lập kế hoạch thu hồi nợ và thanh toán theo thứ tự ưu tiên.",
        "bg-primary", 11)

    report_md = f"""# BÁO CÁO PHÂN TÍCH TUỔI NỢ & QUẢN LÝ CÔNG NỢ

## I. THÔNG TIN CHUNG
- **Doanh nghiệp**: {taxpayer_name}
- **MST**: {taxpayer_mst}
- **Ngày phân tích**: {datetime.datetime.now().strftime('%d/%m/%Y')}

## II. TỔNG HỢP PHẢI THU (AR)
| Nhóm tuổi nợ | Số HĐ | Số tiền (VND) |
|---|---|---|
| Chưa đến hạn | {ar['buckets']['current']['count']} | {ar['buckets']['current']['total']:,.0f} |
| 1-30 ngày | {ar['buckets']['1_30']['count']} | {ar['buckets']['1_30']['total']:,.0f} |
| 31-60 ngày | {ar['buckets']['31_60']['count']} | {ar['buckets']['31_60']['total']:,.0f} |
| 61-90 ngày | {ar['buckets']['61_90']['count']} | {ar['buckets']['61_90']['total']:,.0f} |
| Trên 90 ngày | {ar['buckets']['90_plus']['count']} | {ar['buckets']['90_plus']['total']:,.0f} |
| **Tổng** | **{ar['total_count']}** | **{ar['total_outstanding']:,.0f}** |

## III. TỔNG HỢP PHẢI TRẢ (AP)
| Nhóm tuổi nợ | Số HĐ | Số tiền (VND) |
|---|---|---|
| Chưa đến hạn | {ap['buckets']['current']['count']} | {ap['buckets']['current']['total']:,.0f} |
| 1-30 ngày | {ap['buckets']['1_30']['count']} | {ap['buckets']['1_30']['total']:,.0f} |
| 31-60 ngày | {ap['buckets']['31_60']['count']} | {ap['buckets']['31_60']['total']:,.0f} |
| 61-90 ngày | {ap['buckets']['61_90']['count']} | {ap['buckets']['61_90']['total']:,.0f} |
| Trên 90 ngày | {ap['buckets']['90_plus']['count']} | {ap['buckets']['90_plus']['total']:,.0f} |
| **Tổng** | **{ap['total_count']}** | **{ap['total_outstanding']:,.0f}** |

## IV. KHUYẾN NGHỊ
1. Gửi thư nhắc nợ cho khách hàng quá hạn 31-60 ngày.
2. Chuyển hồ sơ pháp lý cho khoản nợ trên 90 ngày.
3. Ưu tiên thanh toán nhà cung cấp gần đến hạn.
4. Đảm bảo thanh toán qua ngân hàng ≥ 5 triệu VND (Luật 48/2024).

*meInvoice AI Debt Management Swarm - Version 34.0.0*
"""

    return {
        "status": "success",
        "chat_steps": steps,
        "report_markdown": report_md,
        "aging": aging,
    }
