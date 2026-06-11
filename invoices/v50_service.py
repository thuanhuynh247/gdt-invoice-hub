"""PIT Law Amendments 109/2025/QH15 Compliance Engine (v50.0.0).

Implements the Personal Income Tax (PIT) amendments covering:
- Household/individual business PIT exemptions (500M VND threshold) and rate classifications.
- Monthly salary progressive PIT brackets and family/dependent deductions.
"""

from __future__ import annotations

import os
import sqlite3
from typing import Dict, Any, List, Optional
from invoices.multitenant_service import get_tenant_db_path


class V50ComplianceService:
    """PIT Law Amendments 109/2025/QH15 compliance engine."""

    HOUSEHOLD_EXEMPT_THRESHOLD_VND = 500_000_000
    PERSONAL_DEDUCTION_VND = 15_000_000
    DEPENDENT_DEDUCTION_VND = 5_500_000

    def __init__(self, base_data_dir: str | None = None):
        self.base_data_dir = base_data_dir

    def get_tenant_connection(self, mst: str) -> sqlite3.Connection:
        """Returns an isolated sqlite3 connection to the specific tenant database."""
        db_path = get_tenant_db_path(mst, self.base_data_dir)
        conn = sqlite3.connect(db_path)
        conn.text_factory = lambda x: x.decode('utf-8', errors='replace') if isinstance(x, bytes) else x
        conn.row_factory = sqlite3.Row

        cur = conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS household_pit_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_name TEXT NOT NULL,
                annual_revenue REAL NOT NULL,
                activity_type TEXT NOT NULL,
                applied_rate REAL NOT NULL,
                pit_liability REAL NOT NULL,
                is_exempt INTEGER DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS progressive_pit_ledgers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_name TEXT NOT NULL,
                monthly_salary REAL NOT NULL,
                dependent_count INTEGER DEFAULT 0,
                personal_deduction REAL NOT NULL,
                dependent_deduction REAL NOT NULL,
                total_deductions REAL NOT NULL,
                taxable_income REAL NOT NULL,
                calculated_pit REAL NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        return conn

    # ───────────────────── Pillar 1: Household Business PIT Exemption ──────────────────
    def evaluate_household_pit(
        self, mst: str, business_name: str, annual_revenue: float, activity_type: str
    ) -> Dict[str, Any]:
        """Evaluate individual/household business PIT under the Law 109 500M VND threshold."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        is_exempt = False
        rate = 0.0
        pit_liability = 0.0

        if annual_revenue <= self.HOUSEHOLD_EXEMPT_THRESHOLD_VND:
            is_exempt = True
            notes = f"Exempt: Annual revenue {annual_revenue:,.0f} VND is ≤ 500M VND threshold."
        else:
            act_lower = activity_type.lower()
            if act_lower in ["distribution", "retail"]:
                rate = 0.5
            elif act_lower in ["services", "construction_no_materials"]:
                rate = 2.0
            elif act_lower in ["manufacturing", "transport", "construction_with_materials"]:
                rate = 1.5
            else:
                rate = 1.0  # Other activity standard rate
            
            pit_liability = annual_revenue * (rate / 100.0)
            notes = (
                f"Taxable: Revenue {annual_revenue:,.0f} VND is above 500M VND threshold. "
                f"PIT rate of {rate}% applied for activity '{activity_type}'. PIT Liability: {pit_liability:,.0f} VND."
            )

        cur.execute("""
            INSERT INTO household_pit_audit_log
                (business_name, annual_revenue, activity_type, applied_rate, pit_liability, is_exempt, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (business_name, annual_revenue, activity_type, rate, pit_liability, 1 if is_exempt else 0, notes))

        conn.commit()
        conn.close()

        return {
            "business_name": business_name,
            "annual_revenue": annual_revenue,
            "activity_type": activity_type,
            "applied_rate": f"{rate}%",
            "pit_liability": pit_liability,
            "is_exempt": is_exempt,
            "notes": notes
        }

    # ───────────────────── Pillar 2: Wage progressive brackets & Deductions ──────────────────
    def calculate_wage_pit(
        self, mst: str, employee_name: str, monthly_salary: float, dependent_count: int = 0
    ) -> Dict[str, Any]:
        """Calculate monthly wage PIT with new personal and dependent deductions."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        personal_ded = self.PERSONAL_DEDUCTION_VND
        dependent_ded = dependent_count * self.DEPENDENT_DEDUCTION_VND
        total_ded = personal_ded + dependent_ded

        taxable_income = max(0.0, monthly_salary - total_ded)

        # 7-Grade progressive tax brackets
        brackets = [
            (5_000_000, 0.05),     # Grade 1: up to 5M -> 5%
            (10_000_000, 0.10),    # Grade 2: 5M to 10M -> 10%
            (18_000_000, 0.15),    # Grade 3: 10M to 18M -> 15%
            (32_000_000, 0.20),    # Grade 4: 18M to 32M -> 20%
            (52_000_000, 0.25),    # Grade 5: 32M to 52M -> 25%
            (80_000_000, 0.30),    # Grade 6: 52M to 80M -> 30%
            (float('inf'), 0.35)   # Grade 7: over 80M -> 35%
        ]

        calculated_pit = 0.0
        remaining_income = taxable_income
        previous_limit = 0.0

        for limit, rate in brackets:
            if remaining_income <= 0:
                break
            
            bracket_span = limit - previous_limit
            taxable_amount_in_bracket = min(remaining_income, bracket_span)
            calculated_pit += taxable_amount_in_bracket * rate
            remaining_income -= taxable_amount_in_bracket
            previous_limit = limit

        notes = (
            f"Monthly Salary: {monthly_salary:,.0f} VND. Total Deductions: {total_ded:,.0f} VND "
            f"(Personal: {personal_ded:,.0f}, Dependent [{dependent_count}]: {dependent_ded:,.0f}). "
            f"Taxable Income: {taxable_income:,.0f} VND. Calculated PIT: {calculated_pit:,.0f} VND."
        )

        cur.execute("""
            INSERT INTO progressive_pit_ledgers
                (employee_name, monthly_salary, dependent_count, personal_deduction, dependent_deduction,
                 total_deductions, taxable_income, calculated_pit, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (employee_name, monthly_salary, dependent_count, personal_ded, dependent_ded, total_ded, taxable_income, calculated_pit, notes))

        conn.commit()
        conn.close()

        return {
            "employee_name": employee_name,
            "monthly_salary": monthly_salary,
            "dependent_count": dependent_count,
            "personal_deduction": personal_ded,
            "dependent_deduction": dependent_ded,
            "total_deductions": total_ded,
            "taxable_income": taxable_income,
            "calculated_pit": calculated_pit,
            "notes": notes
        }
