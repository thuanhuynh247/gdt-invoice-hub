"""Automated VAT Declaration Engine (US-100, US-101).

Computes monthly/quarterly VAT declarations (Mẫu 01/GTGT) from invoice data,
including output VAT, deductible input VAT, and net VAT payable/refundable.
Also renders declarations into structured form templates for PDF/Excel export.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict


@dataclass
class VATDeclarationResult:
    """Result of a VAT declaration computation."""
    id: str
    taxpayer_mst: str
    period_type: str          # 'monthly' or 'quarterly'
    period_label: str         # '2026-05' or '2026-Q2'
    total_output_vat: float = 0.0
    total_input_vat: float = 0.0
    total_deductible_input_vat: float = 0.0
    vat_payable: float = 0.0  # positive = pay, negative = refundable
    output_invoice_count: int = 0
    input_invoice_count: int = 0
    total_revenue: float = 0.0
    total_purchases: float = 0.0
    status: str = "draft"
    generated_at: str = ""
    line_details: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def compute_vat_declaration(
    taxpayer_mst: str,
    period_type: str,
    period_label: str,
    invoices: list[dict],
) -> VATDeclarationResult:
    """Compute a VAT declaration from a list of invoice dicts.

    Each invoice dict should have:
      - seller_mst, buyer_mst: str
      - amount_before_tax, tax_amount, total_amount: float
      - payment_method: str (for deductibility check)
      - has_signature: bool
      - date: str (YYYY-MM-DD)

    The taxpayer_mst determines whether an invoice is output (seller) or input (buyer).
    """
    if period_type not in ("monthly", "quarterly"):
        raise ValueError(f"period_type must be 'monthly' or 'quarterly', got '{period_type}'")

    decl_id = f"DECL-{taxpayer_mst}-{period_label}"
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    total_output_vat = 0.0
    total_input_vat = 0.0
    total_deductible_input = 0.0
    total_revenue = 0.0
    total_purchases = 0.0
    output_count = 0
    input_count = 0
    line_details = []

    for inv in invoices:
        tax_amt = float(inv.get("tax_amount", 0))
        before_tax = float(inv.get("amount_before_tax", 0))
        total_amt = float(inv.get("total_amount", 0))
        seller_mst = inv.get("seller_mst", "")
        buyer_mst = inv.get("buyer_mst", "")
        payment = inv.get("payment_method", "").lower()
        has_sig = inv.get("has_signature", True)

        if seller_mst == taxpayer_mst:
            # Output invoice — we collected VAT
            total_output_vat += tax_amt
            total_revenue += before_tax
            output_count += 1
            line_details.append({
                "invoice_id": inv.get("id", ""),
                "direction": "output",
                "vat_amount": tax_amt,
                "deductible": False,
                "reason": "Thuế GTGT đầu ra (thu hộ Nhà nước)",
            })
        elif buyer_mst == taxpayer_mst:
            # Input invoice — we paid VAT
            total_input_vat += tax_amt
            total_purchases += before_tax
            input_count += 1

            # Check deductibility rules
            is_deductible = True
            reason = "Thuế GTGT đầu vào được khấu trừ"

            # Rule: Cash payments >= 20M VND are NOT deductible
            if payment in ("tiền mặt", "tien mat", "cash", "tm") and total_amt >= 20_000_000:
                is_deductible = False
                reason = "Không được khấu trừ: thanh toán tiền mặt >= 20 triệu VND"

            # Rule: Unsigned invoices are NOT deductible
            if not has_sig:
                is_deductible = False
                reason = "Không được khấu trừ: hóa đơn thiếu chữ ký số"

            if is_deductible:
                total_deductible_input += tax_amt

            line_details.append({
                "invoice_id": inv.get("id", ""),
                "direction": "input",
                "vat_amount": tax_amt,
                "deductible": is_deductible,
                "reason": reason,
            })

    vat_payable = total_output_vat - total_deductible_input

    return VATDeclarationResult(
        id=decl_id,
        taxpayer_mst=taxpayer_mst,
        period_type=period_type,
        period_label=period_label,
        total_output_vat=round(total_output_vat, 2),
        total_input_vat=round(total_input_vat, 2),
        total_deductible_input_vat=round(total_deductible_input, 2),
        vat_payable=round(vat_payable, 2),
        output_invoice_count=output_count,
        input_invoice_count=input_count,
        total_revenue=round(total_revenue, 2),
        total_purchases=round(total_purchases, 2),
        status="draft",
        generated_at=now,
        line_details=line_details,
    )


def get_period_months(period_label: str, period_type: str) -> list[str]:
    """Convert a period label into a list of YYYY-MM month strings."""
    if period_type == "monthly":
        return [period_label]  # e.g. '2026-05'
    elif period_type == "quarterly":
        # e.g. '2026-Q1' -> ['2026-01', '2026-02', '2026-03']
        parts = period_label.split("-Q")
        if len(parts) != 2:
            raise ValueError(f"Invalid quarterly label: {period_label}")
        year = int(parts[0])
        quarter = int(parts[1])
        start_month = (quarter - 1) * 3 + 1
        return [f"{year}-{m:02d}" for m in range(start_month, start_month + 3)]
    else:
        raise ValueError(f"Unknown period_type: {period_type}")


def filter_invoices_by_period(invoices: list[dict], months: list[str]) -> list[dict]:
    """Filter invoices whose date falls within the given month strings."""
    result = []
    for inv in invoices:
        date_str = inv.get("date", "")
        if date_str and len(date_str) >= 7:
            inv_month = date_str[:7]  # 'YYYY-MM'
            if inv_month in months:
                result.append(inv)
    return result


# ── US-101: Declaration Form Template Renderer ────────────────────

def render_declaration_form(decl: VATDeclarationResult) -> str:
    """Render a VAT declaration into a structured text template (Mẫu 01/GTGT)."""
    lines = [
        "═══════════════════════════════════════════════════════════════",
        "       CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM",
        "            Độc lập – Tự do – Hạnh phúc",
        "═══════════════════════════════════════════════════════════════",
        "",
        f"           TỜ KHAI THUẾ GIÁ TRỊ GIA TĂNG (MẪU 01/GTGT)",
        f"           Kỳ tính thuế: {decl.period_label} ({decl.period_type})",
        "",
        f"  Mã số thuế (MST): {decl.taxpayer_mst}",
        f"  Mã tờ khai: {decl.id}",
        f"  Ngày lập: {decl.generated_at}",
        "",
        "───────────────────────────────────────────────────────────────",
        "  CHỈ TIÊU                                          SỐ TIỀN",
        "───────────────────────────────────────────────────────────────",
        f"  [21] Tổng doanh thu bán hàng:            {decl.total_revenue:>15,.0f} VND",
        f"  [22] Tổng thuế GTGT đầu ra:              {decl.total_output_vat:>15,.0f} VND",
        f"       (Số hóa đơn đầu ra: {decl.output_invoice_count})",
        "",
        f"  [23] Tổng giá trị mua hàng:              {decl.total_purchases:>15,.0f} VND",
        f"  [24] Tổng thuế GTGT đầu vào:             {decl.total_input_vat:>15,.0f} VND",
        f"  [25] Thuế GTGT đầu vào được khấu trừ:    {decl.total_deductible_input_vat:>15,.0f} VND",
        f"       (Số hóa đơn đầu vào: {decl.input_invoice_count})",
        "",
        "───────────────────────────────────────────────────────────────",
    ]

    if decl.vat_payable >= 0:
        lines.append(f"  [40] THUẾ GTGT PHẢI NỘP:                 {decl.vat_payable:>15,.0f} VND")
    else:
        lines.append(f"  [43] THUẾ GTGT CÒN ĐƯỢC KHẤU TRỪ:       {abs(decl.vat_payable):>15,.0f} VND")

    lines.extend([
        "───────────────────────────────────────────────────────────────",
        f"  Trạng thái: {decl.status.upper()}",
        "═══════════════════════════════════════════════════════════════",
        "",
    ])

    return "\n".join(lines)
