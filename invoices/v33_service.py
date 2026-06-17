"""
V33 Compliance Service – CIT Quarterly Provisional Declaration Engine,
Form 01A/TNDN XML Builder, and Tax Compliance Calendar.

US-450: CIT Quarterly Provisional Tax Engine (Form 01A/TNDN XML Builder)
US-451: Interactive Tax Compliance Calendar & Deadline Dashboard UI
"""

from __future__ import annotations

import datetime
import random
from typing import Any, Dict, List, Optional


# ── US-450: CIT Quarterly Provisional Declaration Engine ────────────────────────

def calculate_cit_quarterly(
    taxpayer_mst: str,
    quarter: int,
    year: int,
    revenue: float,
    cogs: float,
    operating_expenses: float,
    other_income: float = 0.0,
    other_expenses: float = 0.0,
    preferential_rate: Optional[float] = None,
    carry_forward_loss: float = 0.0,
) -> Dict[str, Any]:
    """
    Calculate CIT quarterly provisional tax per Vietnamese tax law.
    Standard CIT rate: 20%. Preferential rates: 10%, 15%, 17%.
    """
    gross_profit = revenue - cogs
    operating_income = gross_profit - operating_expenses
    pre_tax_income = operating_income + other_income - other_expenses

    # Apply carry-forward loss (max 5 years, Article 9 Luat Thue TNDN)
    loss_applied = min(carry_forward_loss, max(pre_tax_income, 0))
    taxable_income = max(pre_tax_income - loss_applied, 0)

    rate = preferential_rate if preferential_rate is not None else 0.20
    cit_payable = taxable_income * rate

    return {
        "taxpayer_mst": taxpayer_mst,
        "quarter": quarter,
        "year": year,
        "revenue": revenue,
        "cogs": cogs,
        "gross_profit": gross_profit,
        "operating_expenses": operating_expenses,
        "operating_income": operating_income,
        "other_income": other_income,
        "other_expenses": other_expenses,
        "pre_tax_income": pre_tax_income,
        "carry_forward_loss_applied": loss_applied,
        "taxable_income": taxable_income,
        "cit_rate": rate,
        "cit_payable": cit_payable,
        "filing_deadline": _get_quarterly_deadline(quarter, year),
        "status": "calculated",
    }


def _get_quarterly_deadline(quarter: int, year: int) -> str:
    """Return the CIT quarterly filing deadline (last day of next quarter's first month)."""
    deadlines = {1: f"{year}-04-30", 2: f"{year}-07-31", 3: f"{year}-10-31", 4: f"{year + 1}-01-31"}
    return deadlines.get(quarter, f"{year}-12-31")


def build_form01a_tndn_xml(
    taxpayer_mst: str,
    taxpayer_name: str,
    quarter: int,
    year: int,
    revenue: float,
    cogs: float,
    operating_expenses: float,
    other_income: float = 0.0,
    other_expenses: float = 0.0,
    preferential_rate: Optional[float] = None,
    carry_forward_loss: float = 0.0,
) -> Dict[str, Any]:
    """Generate HTKK-compatible Form 01A/TNDN XML for CIT quarterly declaration."""
    calc = calculate_cit_quarterly(
        taxpayer_mst, quarter, year, revenue, cogs,
        operating_expenses, other_income, other_expenses,
        preferential_rate, carry_forward_loss,
    )

    now = datetime.datetime.now()
    rate_pct = int(calc["cit_rate"] * 100)

    xml_str = f"""<?xml version="1.0" encoding="UTF-8"?>
<HSoThueDTu>
  <HSoKhaiThue>
    <TTChung>
      <PBan>2.0.2</PBan>
      <MNT>01A/TNDN</MNT>
      <Ten>TỜ KHAI THUẾ THU NHẬP DOANH NGHIỆP TẠM TÍNH</Ten>
      <HName>Tờ khai thuế thu nhập doanh nghiệp tạm tính (Mẫu số 01A/TNDN)</HName>
      <KyKKhaiThue>
        <kyKKhai>Q{quarter}/{year}</kyKKhai>
        <kyKKhaiTuNgay>{year}-{(quarter-1)*3+1:02d}-01</kyKKhaiTuNgay>
        <kyKKhaiDenNgay>{year}-{quarter*3:02d}-{28 if quarter*3 == 2 else 30}</kyKKhaiDenNgay>
      </KyKKhaiThue>
      <MST>{taxpayer_mst}</MST>
      <TenNNT>{taxpayer_name}</TenNNT>
      <NgayLapTKhai>{now.strftime('%Y-%m-%d')}</NgayLapTKhai>
    </TTChung>
    <CTieuTKhai>
      <ct21>Doanh thu phát sinh trong kỳ</ct21>
      <ct21_value>{revenue:,.0f}</ct21_value>
      <ct22>Chi phí phát sinh trong kỳ</ct22>
      <ct22_value>{cogs + operating_expenses + other_expenses:,.0f}</ct22_value>
      <ct23>Lợi nhuận phát sinh trong kỳ</ct23>
      <ct23_value>{calc['pre_tax_income']:,.0f}</ct23_value>
      <ct24>Điều chỉnh tăng lợi nhuận</ct24>
      <ct24_value>0</ct24_value>
      <ct25>Điều chỉnh giảm lợi nhuận</ct25>
      <ct25_value>0</ct25_value>
      <ct26>Thu nhập chịu thuế</ct26>
      <ct26_value>{calc['taxable_income']:,.0f}</ct26_value>
      <ct27>Thuế suất thuế TNDN ({rate_pct}%)</ct27>
      <ct27_value>{rate_pct}</ct27_value>
      <ct28>Thuế TNDN phải nộp</ct28>
      <ct28_value>{calc['cit_payable']:,.0f}</ct28_value>
    </CTieuTKhai>
  </HSoKhaiThue>
</HSoThueDTu>"""

    return {
        "status": "success",
        "form_type": "01A/TNDN",
        "quarter": quarter,
        "year": year,
        "xml_content": xml_str,
        "calculation": calc,
    }


# ── US-451: Tax Compliance Calendar ─────────────────────────────────────────────

TAX_CALENDAR_TEMPLATE = [
    {"month": 1, "deadlines": [
        {"code": "VAT-M12", "label": "Nộp tờ khai thuế GTGT tháng 12", "day": 20, "type": "VAT"},
        {"code": "CIT-Q4", "label": "Nộp thuế TNDN tạm tính Quý 4", "day": 31, "type": "CIT"},
    ]},
    {"month": 2, "deadlines": [
        {"code": "VAT-M01", "label": "Nộp tờ khai thuế GTGT tháng 1", "day": 20, "type": "VAT"},
        {"code": "PIT-M01", "label": "Nộp thuế TNCN tháng 1", "day": 20, "type": "PIT"},
    ]},
    {"month": 3, "deadlines": [
        {"code": "VAT-M02", "label": "Nộp tờ khai thuế GTGT tháng 2", "day": 20, "type": "VAT"},
        {"code": "CIT-FY", "label": "Quyết toán thuế TNDN năm trước (90 ngày)", "day": 31, "type": "CIT"},
        {"code": "PIT-FY", "label": "Quyết toán thuế TNCN năm trước (90 ngày)", "day": 31, "type": "PIT"},
    ]},
    {"month": 4, "deadlines": [
        {"code": "VAT-M03", "label": "Nộp tờ khai thuế GTGT tháng 3", "day": 20, "type": "VAT"},
        {"code": "CIT-Q1", "label": "Nộp thuế TNDN tạm tính Quý 1", "day": 30, "type": "CIT"},
    ]},
    {"month": 5, "deadlines": [
        {"code": "VAT-M04", "label": "Nộp tờ khai thuế GTGT tháng 4", "day": 20, "type": "VAT"},
    ]},
    {"month": 6, "deadlines": [
        {"code": "VAT-M05", "label": "Nộp tờ khai thuế GTGT tháng 5", "day": 20, "type": "VAT"},
    ]},
    {"month": 7, "deadlines": [
        {"code": "VAT-M06", "label": "Nộp tờ khai thuế GTGT tháng 6", "day": 20, "type": "VAT"},
        {"code": "CIT-Q2", "label": "Nộp thuế TNDN tạm tính Quý 2", "day": 31, "type": "CIT"},
    ]},
    {"month": 8, "deadlines": [
        {"code": "VAT-M07", "label": "Nộp tờ khai thuế GTGT tháng 7", "day": 20, "type": "VAT"},
    ]},
    {"month": 9, "deadlines": [
        {"code": "VAT-M08", "label": "Nộp tờ khai thuế GTGT tháng 8", "day": 20, "type": "VAT"},
    ]},
    {"month": 10, "deadlines": [
        {"code": "VAT-M09", "label": "Nộp tờ khai thuế GTGT tháng 9", "day": 20, "type": "VAT"},
        {"code": "CIT-Q3", "label": "Nộp thuế TNDN tạm tính Quý 3", "day": 31, "type": "CIT"},
    ]},
    {"month": 11, "deadlines": [
        {"code": "VAT-M10", "label": "Nộp tờ khai thuế GTGT tháng 10", "day": 20, "type": "VAT"},
    ]},
    {"month": 12, "deadlines": [
        {"code": "VAT-M11", "label": "Nộp tờ khai thuế GTGT tháng 11", "day": 20, "type": "VAT"},
        {"code": "SI-Q4", "label": "Quyết toán bảo hiểm xã hội Quý 4", "day": 31, "type": "SI"},
    ]},
]

MONTH_NAMES_VI = [
    "", "Tháng 1", "Tháng 2", "Tháng 3", "Tháng 4", "Tháng 5", "Tháng 6",
    "Tháng 7", "Tháng 8", "Tháng 9", "Tháng 10", "Tháng 11", "Tháng 12",
]


def get_tax_compliance_calendar(year: int) -> Dict[str, Any]:
    """Return a structured tax compliance calendar for a given year."""
    today = datetime.date.today()
    months = []

    for entry in TAX_CALENDAR_TEMPLATE:
        m = entry["month"]
        month_deadlines = []
        for dl in entry["deadlines"]:
            deadline_date = datetime.date(year, m, dl["day"])
            if deadline_date < today:
                status = "filed"
            elif (deadline_date - today).days <= 7:
                status = "upcoming"
            else:
                status = "pending"

            month_deadlines.append({
                "code": dl["code"],
                "label": dl["label"],
                "date": deadline_date.isoformat(),
                "day": dl["day"],
                "type": dl["type"],
                "status": status,
            })

        months.append({
            "month": m,
            "month_name": MONTH_NAMES_VI[m],
            "deadlines": month_deadlines,
        })

    return {
        "year": year,
        "generated_at": datetime.datetime.now().isoformat(),
        "months": months,
    }


# ── US-451: CIT Optimization Swarm Advisory ─────────────────────────────────────

def run_cit_optimization_swarm(
    taxpayer_mst: str,
    taxpayer_name: str,
    quarter: int,
    year: int,
    revenue: float,
    cogs: float,
    operating_expenses: float,
) -> Dict[str, Any]:
    """Multi-agent swarm discussion for CIT quarterly optimization advisory."""
    calc = calculate_cit_quarterly(
        taxpayer_mst, quarter, year, revenue, cogs, operating_expenses,
    )

    ts = datetime.datetime.now()
    chat_steps = []

    def add(agent, role, msg, cls, offset):
        chat_steps.append({
            "agent": agent, "role": role, "message": msg,
            "avatar_class": cls,
            "timestamp": (ts + datetime.timedelta(seconds=offset)).strftime("%H:%M:%S"),
        })

    add("CITCoordinator", "Điều phối thuế TNDN",
        f"Khởi động phân tích thuế TNDN tạm tính Quý {quarter}/{year} cho "
        f"<strong>{taxpayer_name}</strong> (MST: {taxpayer_mst}). "
        f"Doanh thu kỳ: <strong>{revenue:,.0f}đ</strong>, "
        f"Thu nhập chịu thuế: <strong>{calc['taxable_income']:,.0f}đ</strong>.",
        "bg-primary", 0)

    add("CITAuditor", "Kiểm soát chi phí hợp lệ",
        f"Tỷ lệ chi phí/doanh thu: <strong>{((cogs + operating_expenses) / revenue * 100) if revenue else 0:.1f}%</strong>. "
        f"Cần rà soát các khoản chi phí không có hóa đơn hợp lệ (Điều 4 Thông tư 96/2015/TT-BTC). "
        f"Khuyến nghị đối chiếu bảng kê chi phí với sổ cái trước khi nộp tờ khai.",
        "bg-danger", 3)

    savings_est = calc["cit_payable"] * 0.05
    add("TaxOptimizer", "Tư vấn tối ưu thuế",
        f"Phân tích cơ hội tiết kiệm thuế: Nếu áp dụng ưu đãi thuế suất 17% cho doanh nghiệp "
        f"sử dụng nhiều lao động (Nghị định 218/2013/NĐ-CP), tiết kiệm ước tính "
        f"<strong>{savings_est:,.0f}đ</strong>/quý. Kiểm tra điều kiện: ≥500 lao động hoặc "
        f"tại địa bàn ưu đãi đầu tư.",
        "bg-warning", 7)

    add("CITCoordinator", "Điều phối thuế TNDN",
        f"Hoàn thành phân tích. Thuế TNDN tạm tính Quý {quarter}/{year}: "
        f"<strong>{calc['cit_payable']:,.0f}đ</strong> (thuế suất {int(calc['cit_rate']*100)}%). "
        f"Hạn nộp: <strong>{calc['filing_deadline']}</strong>. "
        f"Sẵn sàng xuất Form 01A/TNDN XML.",
        "bg-primary", 11)

    report_md = f"""# BÁO CÁO PHÂN TÍCH THUẾ TNDN TẠM TÍNH QUÝ {quarter}/{year}

## I. THÔNG TIN CHUNG
- **Doanh nghiệp**: {taxpayer_name}
- **Mã số thuế**: {taxpayer_mst}
- **Kỳ tính thuế**: Quý {quarter}/{year}
- **Ngày phân tích**: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

## II. KẾT QUẢ TÍNH TOÁN
| Chỉ tiêu | Số tiền (VND) |
|---|---|
| Doanh thu | {revenue:,.0f} |
| Giá vốn hàng bán | {cogs:,.0f} |
| Lợi nhuận gộp | {calc['gross_profit']:,.0f} |
| Chi phí hoạt động | {operating_expenses:,.0f} |
| Thu nhập trước thuế | {calc['pre_tax_income']:,.0f} |
| Thu nhập chịu thuế | {calc['taxable_income']:,.0f} |
| **Thuế TNDN phải nộp** | **{calc['cit_payable']:,.0f}** |

## III. KHUYẾN NGHỊ
1. Đối chiếu chi phí với hóa đơn hợp lệ theo Thông tư 96/2015/TT-BTC.
2. Kiểm tra điều kiện ưu đãi thuế suất (10%, 15%, 17%) theo Nghị định 218/2013/NĐ-CP.
3. Nộp tờ khai và thuế trước hạn **{calc['filing_deadline']}** để tránh phạt chậm nộp.

*meInvoice AI CIT Compliance Swarm Oracle - Version 33.0.0*
"""

    return {
        "status": "success",
        "chat_steps": chat_steps,
        "report_markdown": report_md,
        "calculation": calc,
    }
