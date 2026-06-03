"""Cash flow projection and scenario simulation engine (US-150, US-151).

Provides rolling 30/60/90-day cash-flow forecasting by combining pending
invoice receivables, payables, and projected VAT liabilities. Also supports
stateless scenario simulation with adjustable payment delay and rejection
parameters for financial stress-testing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional


@dataclass
class CashFlowProjection:
    """Result of a cash-flow projection over a time horizon."""

    horizon_days: int
    start_date: str
    end_date: str
    total_receivables: float
    total_payables: float
    projected_vat_liability: float
    net_cash_flow: float
    daily_timeline: list[dict]


@dataclass
class ScenarioParams:
    """Parameters for what-if scenario simulation (US-151)."""

    delay_days: int = 0           # Extra days delay on receivables
    rejection_rate: float = 0.0   # % of receivables forfeited (0.0–1.0)
    vat_adjustment: float = 0.0   # Increase/decrease in projected VAT liability


def calculate_cashflow_projection(
    taxpayer_mst: Optional[str] = None,
    as_of: Optional[date] = None,
    scenario: Optional[ScenarioParams] = None,
) -> dict:
    """Calculate rolling 30/60/90-day cash-flow projections.

    Returns a dict with 3 projection horizons and a unified daily timeline.
    """
    from extensions import db
    from invoices.models import Invoice

    if as_of is None:
        as_of = date.today()

    if scenario is None:
        scenario = ScenarioParams()

    # Fetch active (non-cancelled) invoices for the taxpayer
    query = Invoice.query.filter(Invoice.is_cancelled == False)
    if taxpayer_mst:
        query = query.filter(Invoice.taxpayer_mst == taxpayer_mst)
    invoices = query.all()

    # Classify invoices into receivables (bán ra) vs payables (mua vào)
    receivables = []  # Invoices where we are the seller → money coming IN
    payables = []     # Invoices where we are the buyer → money going OUT

    for inv in invoices:
        inv_date = _parse_date(inv.date)
        due = _parse_date(inv.due_date) if inv.due_date else (inv_date + timedelta(days=30) if inv_date else None)
        paid = _parse_date(inv.paid_date) if inv.paid_date else None

        entry = {
            "id": inv.id,
            "date": inv.date,
            "due_date": due.isoformat() if due else None,
            "paid_date": paid.isoformat() if paid else None,
            "amount": inv.total_amount,
            "tax_amount": inv.tax_amount,
            "seller_name": inv.seller_name or "",
            "buyer_name": inv.buyer_name or "",
            "seller_mst": inv.seller_mst or "",
            "buyer_mst": inv.buyer_mst or "",
        }

        # Determine direction: if our MST matches seller_mst → we sold it (receivable)
        # If our MST matches buyer_mst → we bought it (payable)
        if taxpayer_mst and inv.seller_mst == taxpayer_mst:
            receivables.append(entry)
        elif taxpayer_mst and inv.buyer_mst == taxpayer_mst:
            payables.append(entry)
        else:
            # Without MST context, use buyer_mst presence as heuristic
            # Invoices with buyer_mst = our profile are purchases (payables)
            payables.append(entry)

    # Build projections for 30/60/90 day horizons
    projections = {}
    for horizon in [30, 60, 90]:
        proj = _project_horizon(
            as_of, horizon, receivables, payables, scenario
        )
        projections[f"{horizon}d"] = {
            "horizon_days": horizon,
            "start_date": as_of.isoformat(),
            "end_date": (as_of + timedelta(days=horizon)).isoformat(),
            "total_receivables": proj["total_receivables"],
            "total_payables": proj["total_payables"],
            "projected_vat_liability": proj["vat_liability"],
            "net_cash_flow": proj["net_cash_flow"],
        }

    # Build daily timeline for chart (90-day view)
    daily_timeline = _build_daily_timeline(
        as_of, 90, receivables, payables, scenario
    )

    # Summary statistics
    total_receivable_count = len(receivables)
    total_payable_count = len(payables)
    overdue_receivables = sum(
        1 for r in receivables
        if r["due_date"] and _parse_date(r["due_date"])
        and _parse_date(r["due_date"]) < as_of
        and not r["paid_date"]
    )

    return {
        "as_of": as_of.isoformat(),
        "taxpayer_mst": taxpayer_mst,
        "projections": projections,
        "daily_timeline": daily_timeline,
        "summary": {
            "total_invoices": total_receivable_count + total_payable_count,
            "receivable_count": total_receivable_count,
            "payable_count": total_payable_count,
            "overdue_receivables": overdue_receivables,
        },
        "scenario_applied": {
            "delay_days": scenario.delay_days,
            "rejection_rate": scenario.rejection_rate,
            "vat_adjustment": scenario.vat_adjustment,
        },
    }


def simulate_scenario(
    taxpayer_mst: Optional[str] = None,
    delay_days: int = 0,
    rejection_rate: float = 0.0,
    vat_adjustment: float = 0.0,
    as_of: Optional[date] = None,
) -> dict:
    """Stateless scenario simulation (US-151).

    Recalculates cash-flow projections with adjusted parameters.
    Does NOT modify any database records.
    """
    scenario = ScenarioParams(
        delay_days=delay_days,
        rejection_rate=max(0.0, min(1.0, rejection_rate)),
        vat_adjustment=vat_adjustment,
    )
    return calculate_cashflow_projection(
        taxpayer_mst=taxpayer_mst,
        as_of=as_of,
        scenario=scenario,
    )


def _project_horizon(
    as_of: date,
    days: int,
    receivables: list[dict],
    payables: list[dict],
    scenario: ScenarioParams,
) -> dict:
    """Project totals for a specific horizon window."""
    end_date = as_of + timedelta(days=days)

    # Receivables due within horizon
    total_recv = 0.0
    for r in receivables:
        if r["paid_date"]:
            continue  # Already paid
        due = _parse_date(r["due_date"]) if r["due_date"] else None
        if due is None:
            continue
        # Apply scenario delay
        adjusted_due = due + timedelta(days=scenario.delay_days)
        if adjusted_due <= end_date:
            total_recv += r["amount"]

    # Apply rejection rate (portion of receivables lost)
    effective_recv = total_recv * (1.0 - scenario.rejection_rate)

    # Payables due within horizon
    total_pay = 0.0
    for p in payables:
        if p["paid_date"]:
            continue  # Already paid
        due = _parse_date(p["due_date"]) if p["due_date"] else None
        if due is None:
            continue
        if due <= end_date:
            total_pay += p["amount"]

    # VAT liability estimate: ~10% of total payable amounts (input VAT credit)
    # minus output VAT on receivables, filtered by horizon window
    output_vat = 0.0
    for r in receivables:
        if r["paid_date"]:
            continue
        due = _parse_date(r["due_date"]) if r["due_date"] else None
        if due:
            adjusted_due = due + timedelta(days=scenario.delay_days)
            if adjusted_due <= end_date:
                output_vat += r["tax_amount"]

    input_vat = 0.0
    for p in payables:
        if p["paid_date"]:
            continue
        due = _parse_date(p["due_date"]) if p["due_date"] else None
        if due and due <= end_date:
            input_vat += p["tax_amount"]

    vat_liability = max(0.0, output_vat - input_vat) + scenario.vat_adjustment

    net = effective_recv - total_pay - vat_liability

    return {
        "total_receivables": round(effective_recv, 2),
        "total_payables": round(total_pay, 2),
        "vat_liability": round(vat_liability, 2),
        "net_cash_flow": round(net, 2),
    }


def _build_daily_timeline(
    as_of: date,
    days: int,
    receivables: list[dict],
    payables: list[dict],
    scenario: ScenarioParams,
) -> list[dict]:
    """Build a day-by-day cash-flow timeline for charting."""
    timeline = []
    running_balance = 0.0

    for day_offset in range(days + 1):
        current_date = as_of + timedelta(days=day_offset)
        day_inflow = 0.0
        day_outflow = 0.0

        # Check receivables due on this day
        for r in receivables:
            if r["paid_date"]:
                continue
            due = _parse_date(r["due_date"]) if r["due_date"] else None
            if due is None:
                continue
            adjusted_due = due + timedelta(days=scenario.delay_days)
            if adjusted_due == current_date:
                day_inflow += r["amount"] * (1.0 - scenario.rejection_rate)

        # Check payables due on this day
        for p in payables:
            if p["paid_date"]:
                continue
            due = _parse_date(p["due_date"]) if p["due_date"] else None
            if due is None:
                continue
            if due == current_date:
                day_outflow += p["amount"]

        running_balance += day_inflow - day_outflow
        timeline.append({
            "date": current_date.isoformat(),
            "inflow": round(day_inflow, 2),
            "outflow": round(day_outflow, 2),
            "net": round(day_inflow - day_outflow, 2),
            "balance": round(running_balance, 2),
        })

    return timeline


def _parse_date(date_str: Optional[str]) -> Optional[date]:
    """Safely parse a YYYY-MM-DD date string."""
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str[:10])
    except (ValueError, TypeError):
        return None
