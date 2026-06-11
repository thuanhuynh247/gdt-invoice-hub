"""Enterprise CIT Incentives & Transfer Pricing Safe Harbor Optimizer Service (v45.0.0).

Handles dynamic calculations for Circular 80 preferential CIT rates,
tax holidays allocation, and Decree 132 Transfer Pricing Safe Harbor assessments.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, List
from invoices.multitenant_service import get_tenant_db_path

class V45ComplianceService:
    def __init__(self, base_data_dir: str | None = None):
        self.base_data_dir = base_data_dir

    def get_tenant_connection(self, mst: str) -> sqlite3.Connection:
        """Returns an isolated sqlite3 connection to the specific tenant database."""
        db_path = get_tenant_db_path(mst, self.base_data_dir)
        conn = sqlite3.connect(db_path)
        conn.text_factory = lambda x: x.decode('utf-8', errors='replace') if isinstance(x, bytes) else x
        conn.row_factory = sqlite3.Row
        
        # Ensure our custom v45 tables exist in this tenant DB
        cur = conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS cit_preferential_ledger (
                fiscal_year INTEGER PRIMARY KEY,
                total_taxable_income REAL NOT NULL,
                preferential_income REAL NOT NULL,
                preferential_rate REAL NOT NULL,
                holiday_start_year INTEGER NOT NULL,
                exemption_years INTEGER DEFAULT 0,
                reduction_years INTEGER DEFAULT 0,
                cit_standard_liability REAL DEFAULT 0.0,
                cit_preferential_liability REAL DEFAULT 0.0,
                cit_total_due REAL DEFAULT 0.0,
                cit_savings REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS tp_safe_harbor_assessments (
                fiscal_year INTEGER PRIMARY KEY,
                total_revenue REAL NOT NULL,
                related_party_txn_value REAL NOT NULL,
                net_profit_margin REAL NOT NULL,
                activity_type TEXT NOT NULL, -- 'trading', 'manufacturing', 'service'
                safe_harbor_eligible INTEGER DEFAULT 0,
                exemption_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS apa_margin_compliance (
                fiscal_year INTEGER PRIMARY KEY,
                lower_bound REAL NOT NULL,
                upper_bound REAL NOT NULL,
                actual_margin REAL NOT NULL,
                status TEXT NOT NULL, -- 'Compliant', 'Non-Compliant'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        return conn

    def simulate_preferential_cit(
        self, mst: str, year: int, total_taxable_income: float, preferential_income: float,
        preferential_rate: float, holiday_start_year: int, exemption_years: int, reduction_years: int
    ) -> Dict[str, Any]:
        """Calculates CIT liabilities under Circular 80 preferential rules and tax holidays."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        # Enforce rate caps (preferential rate cannot exceed standard 20%)
        pref_rate = min(0.20, max(0.0, preferential_rate))
        pref_income = min(total_taxable_income, max(0.0, preferential_income))
        std_income = total_taxable_income - pref_income

        # Calculate tax holiday status based on years since start
        years_since_start = year - holiday_start_year
        reduction_ratio = 0.0
        holiday_status = "No Incentive Applied"

        if years_since_start >= 0:
            if years_since_start < exemption_years:
                reduction_ratio = 1.0  # 100% tax exemption
                holiday_status = f"Tax Exemption (Year {years_since_start + 1} of {exemption_years})"
            elif years_since_start < (exemption_years + reduction_years):
                reduction_ratio = 0.5  # 50% tax reduction
                holiday_status = f"50% Tax Reduction (Year {years_since_start - exemption_years + 1} of {reduction_years})"
            else:
                holiday_status = "Holidays Expired"

        # Liabilities
        cit_standard_liability = std_income * 0.20
        cit_pref_before_holiday = pref_income * pref_rate
        cit_preferential_liability = cit_pref_before_holiday * (1.0 - reduction_ratio)

        cit_total_due = cit_standard_liability + cit_preferential_liability
        cit_without_incentive = total_taxable_income * 0.20
        cit_savings = max(0.0, cit_without_incentive - cit_total_due)

        # Persist to tenant ledger
        cur.execute("""
            INSERT OR REPLACE INTO cit_preferential_ledger (
                fiscal_year, total_taxable_income, preferential_income, preferential_rate,
                holiday_start_year, exemption_years, reduction_years,
                cit_standard_liability, cit_preferential_liability, cit_total_due, cit_savings
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            year, total_taxable_income, pref_income, pref_rate,
            holiday_start_year, exemption_years, reduction_years,
            cit_standard_liability, cit_preferential_liability, cit_total_due, cit_savings
        ))
        
        conn.commit()
        conn.close()

        return {
            "fiscal_year": year,
            "total_taxable_income": round(total_taxable_income, 2),
            "preferential_income": round(pref_income, 2),
            "standard_income": round(std_income, 2),
            "preferential_rate": pref_rate,
            "holiday_status": holiday_status,
            "reduction_ratio": reduction_ratio,
            "cit_standard_liability": round(cit_standard_liability, 2),
            "cit_preferential_liability": round(cit_preferential_liability, 2),
            "cit_total_due": round(cit_total_due, 2),
            "cit_savings": round(cit_savings, 2)
        }

    def evaluate_tp_safe_harbors(
        self, mst: str, year: int, total_revenue: float, related_party_txn_value: float,
        net_profit_margin: float, activity_type: str, apa_lower: float | None = None,
        apa_upper: float | None = None, actual_margin: float | None = None
    ) -> Dict[str, Any]:
        """Evaluates Decree 132 Transfer Pricing Safe Harbor rules and APA margins."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        # Condition 1: Revenue < 50 billion VND and related-party transaction value < 30 billion VND
        sh_eligible = 0
        reason = "Does not meet transfer pricing safe harbor criteria."

        if total_revenue < 50000000000.0 and related_party_txn_value < 30000000000.0:
            sh_eligible = 1
            reason = "Revenue under 50B VND and Related-Party Transactions under 30B VND."
        else:
            # Condition 2: Revenue < 200 billion VND and Net Profit Margin (NPM) exceeds minimum threshold
            if total_revenue < 200000000000.0:
                # Minimum margins by activity
                thresholds = {
                    "trading": 0.02,        # 2%
                    "manufacturing": 0.10,  # 10%
                    "service": 0.15         # 15%
                }
                min_threshold = thresholds.get(activity_type.lower(), 0.15)
                if net_profit_margin >= min_threshold:
                    sh_eligible = 1
                    reason = f"Revenue under 200B VND and NPM {net_profit_margin*100:.1f}% meets {activity_type} limit of {min_threshold*100:.1f}%."

        # Insert Safe Harbor record
        cur.execute("""
            INSERT OR REPLACE INTO tp_safe_harbor_assessments (
                fiscal_year, total_revenue, related_party_txn_value, net_profit_margin, activity_type, safe_harbor_eligible, exemption_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (year, total_revenue, related_party_txn_value, net_profit_margin, activity_type, sh_eligible, reason))

        # Check APA compliance if terms are provided
        apa_status = "N/A"
        if apa_lower is not None and apa_upper is not None and actual_margin is not None:
            if apa_lower <= actual_margin <= apa_upper:
                apa_status = "Compliant"
            else:
                apa_status = "Non-Compliant"

            cur.execute("""
                INSERT OR REPLACE INTO apa_margin_compliance (
                    fiscal_year, lower_bound, upper_bound, actual_margin, status
                ) VALUES (?, ?, ?, ?, ?)
            """, (year, apa_lower, apa_upper, actual_margin, apa_status))

        conn.commit()
        conn.close()

        return {
            "fiscal_year": year,
            "total_revenue": round(total_revenue, 2),
            "related_party_txn_value": round(related_party_txn_value, 2),
            "net_profit_margin": net_profit_margin,
            "activity_type": activity_type,
            "safe_harbor_eligible": bool(sh_eligible),
            "exemption_reason": reason,
            "apa_status": apa_status
        }
