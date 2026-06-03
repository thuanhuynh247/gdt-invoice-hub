"""Advanced Financial KPI Dashboard and Export Pipeline (US-114, US-115).

Computes core business financial metrics (Gross Margin, Tax-to-Revenue,
Average Payment Period) and exports them to standardized CSV formats.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class FinancialKPIMetrics:
    """Calculated financial health indicators."""
    total_sales: float = 0.0
    cost_of_goods_sold: float = 0.0
    gross_margin_percent: float = 0.0
    vat_payable: float = 0.0
    tax_to_revenue_percent: float = 0.0
    average_payment_period_days: float = 0.0
    invoice_count: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


def calculate_financial_kpis(
    sales_invoices: list[dict],      # Invoices we issued (output)
    purchase_invoices: list[dict],   # Invoices we paid (input/cost)
    payment_clearances: list[dict] | None = None, # Matches invoice_id to clearance dates
) -> FinancialKPIMetrics:
    """Compute financial metrics from sales and purchase invoice streams.

    Each invoice dict is expected to contain:
      - id
      - amount_before_tax
      - tax_amount
      - date (YYYY-MM-DD)
    """
    total_sales = sum(float(i.get("amount_before_tax", 0)) for i in sales_invoices)
    cogs = sum(float(i.get("amount_before_tax", 0)) for i in purchase_invoices)
    
    # Output VAT collected vs input VAT paid
    total_output_vat = sum(float(i.get("tax_amount", 0)) for i in sales_invoices)
    total_input_vat = sum(float(i.get("tax_amount", 0)) for i in purchase_invoices)
    vat_payable = total_output_vat - total_input_vat

    # Gross Margin = (Sales - COGS) / Sales
    gross_margin = 0.0
    if total_sales > 0:
        gross_margin = ((total_sales - cogs) / total_sales) * 100.0

    # Tax-to-Revenue = VAT Payable / Sales
    tax_to_rev = 0.0
    if total_sales > 0:
        tax_to_rev = (vat_payable / total_sales) * 100.0

    # Calculate average payment clearance period
    avg_days = 0.0
    valid_clearances = 0
    total_days = 0.0

    if payment_clearances:
        # Create map of invoice_id -> clearance_date
        clearance_map = {c["invoice_id"]: c["clearance_date"] for c in payment_clearances}
        
        all_invoices = sales_invoices + purchase_invoices
        for inv in all_invoices:
            inv_id = inv.get("id")
            inv_date_str = inv.get("date")
            clear_date_str = clearance_map.get(inv_id)

            if inv_date_str and clear_date_str:
                try:
                    inv_date = datetime.strptime(inv_date_str, "%Y-%m-%d")
                    clear_date = datetime.strptime(clear_date_str, "%Y-%m-%d")
                    delta = (clear_date - inv_date).days
                    if delta >= 0:
                        total_days += delta
                        valid_clearances += 1
                except ValueError:
                    pass

    if valid_clearances > 0:
        avg_days = total_days / valid_clearances

    return FinancialKPIMetrics(
        total_sales=round(total_sales, 2),
        cost_of_goods_sold=round(cogs, 2),
        gross_margin_percent=round(gross_margin, 2),
        vat_payable=round(vat_payable, 2),
        tax_to_revenue_percent=round(tax_to_rev, 2),
        average_payment_period_days=round(avg_days, 1),
        invoice_count=len(sales_invoices) + len(purchase_invoices),
    )


# ── US-115: CSV Financial Export Pipeline ─────────────────────────

def export_kpi_to_csv(
    period_metrics: dict[str, FinancialKPIMetrics],
) -> str:
    """Generate a structured CSV report summarizing financial metrics over time.

    period_metrics is a dictionary mapping a period label (e.g. '2026-05') to KPI results.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Headers
    writer.writerow([
        "Period",
        "Total Sales (VND)",
        "Cost of Goods Sold (VND)",
        "Gross Margin (%)",
        "VAT Payable (VND)",
        "Tax-to-Revenue (%)",
        "Avg Payment Clearance (Days)",
        "Total Invoices",
    ])

    for period, kpi in sorted(period_metrics.items()):
        writer.writerow([
            period,
            f"{kpi.total_sales:.2f}",
            f"{kpi.cost_of_goods_sold:.2f}",
            f"{kpi.gross_margin_percent:.2f}",
            f"{kpi.vat_payable:.2f}",
            f"{kpi.tax_to_revenue_percent:.2f}",
            f"{kpi.average_payment_period_days:.1f}",
            kpi.invoice_count,
        ])

    return output.getvalue()
