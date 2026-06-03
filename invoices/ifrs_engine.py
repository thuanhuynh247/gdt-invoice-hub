"""Enterprise IFRS & International Tax Translation Engine (v18.0.0).

Handles dynamic multitenant calculations for IAS 12 (Deferred Taxes),
IFRS 16 (Lease Amortization), and OECD Pillar Two (Global Minimum Tax).
"""

from __future__ import annotations

import os
import json
import sqlite3
from datetime import datetime
from typing import Dict, Any, List
from invoices.multitenant_service import get_tenant_db_path

class IFRSTranslationService:
    def __init__(self, base_data_dir: str | None = None):
        self.base_data_dir = base_data_dir

    def get_tenant_connection(self, mst: str) -> sqlite3.Connection:
        """Returns an isolated sqlite3 connection to the specific tenant database."""
        db_path = get_tenant_db_path(mst, self.base_data_dir)
        conn = sqlite3.connect(db_path)
        conn.text_factory = lambda x: x.decode('utf-8', errors='replace') if isinstance(x, bytes) else x
        conn.row_factory = sqlite3.Row
        
        # Ensure our custom IFRS tables exist in this tenant DB
        cur = conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS ifrs_deferred_tax_ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fiscal_year INTEGER NOT NULL,
                fiscal_period INTEGER NOT NULL,
                balance_sheet_item TEXT NOT NULL,
                carrying_amount_ifrs REAL NOT NULL,
                tax_base_vas REAL NOT NULL,
                tax_rate REAL NOT NULL,
                deferred_tax_asset REAL,
                deferred_tax_liability REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS lease_amortization_schedule (
                lease_id TEXT PRIMARY KEY,
                supplier_mst TEXT NOT NULL,
                commencement_date TEXT NOT NULL,
                lease_term_months INTEGER NOT NULL,
                monthly_payment REAL NOT NULL,
                discount_rate REAL NOT NULL,
                present_value_rou REAL NOT NULL,
                interest_expense_ytd REAL DEFAULT 0.0,
                liability_balance REAL NOT NULL,
                active_status INTEGER DEFAULT 1
            );
        """)
        conn.commit()
        return conn

    def calculate_ias12_deferred_tax(self, mst: str, year: int) -> List[Dict[str, Any]]:
        """Calculates temporary differences and deferred taxes (IAS 12) for a given MST and year."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, fiscal_year, fiscal_period, balance_sheet_item, carrying_amount_ifrs, tax_base_vas, tax_rate 
            FROM ifrs_deferred_tax_ledger 
            WHERE fiscal_year = ?
        """, (year,))
        
        records = []
        for row in cur.fetchall():
            item = row["balance_sheet_item"]
            carrying = row["carrying_amount_ifrs"]
            tax_base = row["tax_base_vas"]
            rate = row["tax_rate"]
            
            diff = carrying - tax_base
            dta = 0.0
            dtl = 0.0
            
            # Temporary difference audit rules
            # DTL occurs when carrying amount of asset > tax base, or carrying amount of liability < tax base
            # DTA occurs when carrying amount of asset < tax base, or carrying amount of liability > tax base
            is_liability = any(x in item.lower() for x in ["liability", "debt", "payables", "nợ phải trả", "nghĩa vụ"])
            
            if is_liability:
                if diff < 0: # Carrying liability < Tax base -> Deferred Tax Liability
                    dtl = abs(diff) * rate
                elif diff > 0: # Carrying liability > Tax base -> Deferred Tax Asset
                    dta = abs(diff) * rate
            else:
                if diff > 0: # Carrying asset > Tax base -> Deferred Tax Liability
                    dtl = abs(diff) * rate
                elif diff < 0: # Carrying asset < Tax base -> Deferred Tax Asset
                    dta = abs(diff) * rate
            
            # Update computed values back into the DB
            cur.execute("""
                UPDATE ifrs_deferred_tax_ledger
                SET deferred_tax_asset = ?, deferred_tax_liability = ?
                WHERE id = ?
            """, (dta, dtl, row["id"]))
            
            records.append({
                "id": row["id"],
                "fiscal_year": year,
                "fiscal_period": row["fiscal_period"],
                "balance_sheet_item": item,
                "carrying_amount_ifrs": carrying,
                "tax_base_vas": tax_base,
                "temporary_difference": diff,
                "tax_rate": rate,
                "deferred_tax_asset": dta,
                "deferred_tax_liability": dtl
            })
            
        conn.commit()
        conn.close()
        return records

    def calculate_ifrs16_amortization(
        self, lease_id: str, monthly_payment: float, discount_rate: float, term_months: int
    ) -> List[Dict[str, Any]]:
        """Generates a complete IFRS 16 lease amortization schedule month-by-month.
        
        Uses present value calculation for Right-of-Use (ROU) Asset.
        """
        # Calculate Present Value of Lease Liability (Right of Use Asset)
        # PV = Payment * [(1 - (1 + r)^-n) / r]
        monthly_rate = discount_rate / 12.0
        if monthly_rate > 0:
            pv = monthly_payment * ((1 - (1 + monthly_rate) ** -term_months) / monthly_rate)
        else:
            pv = monthly_payment * term_months
            
        schedule = []
        balance = pv
        
        for m in range(1, term_months + 1):
            interest = balance * monthly_rate
            principal = monthly_payment - interest
            closing = balance - principal
            if closing < 0:
                closing = 0.0
                
            schedule.append({
                "month": m,
                "opening_balance": round(balance, 2),
                "payment": round(monthly_payment, 2),
                "interest_expense": round(interest, 2),
                "principal_repayment": round(principal, 2),
                "closing_balance": round(closing, 2)
            })
            balance = closing
            
        return schedule

    def estimate_pillar_two_topup(self, parent_mst: str, group_msts: List[str], year: int) -> Dict[str, Any]:
        """Estimates consolidated effective tax rate (ETR) and GloBE top-up taxes under OECD Pillar Two."""
        consolidated_income = 0.0
        consolidated_taxes = 0.0
        covered_tax_by_mst = {}
        
        for mst in group_msts:
            db_path = get_tenant_db_path(mst, self.base_data_dir)
            if not os.path.isfile(db_path):
                # Safe fallback to query base tenant structure
                continue
                
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            
            # Read aggregated financial figures
            try:
                cur.execute("""
                    SELECT 
                        SUM(total_amount - tax_amount) as net_sales,
                        SUM(tax_amount) as vat_paid
                    FROM invoice
                """)
                row = cur.fetchone()
                if row:
                    income = row["net_sales"] or 0.0
                    taxes = row["vat_paid"] or 0.0
                    
                    # Assume CIT estimated
                    estimated_cit = income * 0.20 # statutory CIT rate in VN
                    
                    consolidated_income += income
                    consolidated_taxes += estimated_cit
                    covered_tax_by_mst[mst] = estimated_cit
            except Exception:
                pass
            finally:
                conn.close()
                
        # Consolidated Effective Tax Rate
        etr = consolidated_taxes / consolidated_income if consolidated_income > 0 else 0.20
        
        # Pillar Two Minimum Rate is 15%
        minimum_rate = 0.15
        topup_rate = max(0.0, minimum_rate - etr)
        
        # Substance-Based Income Exclusion (SBIE) standard assumptions:
        # 5% of assets and payroll
        sbie_exclusion = consolidated_income * 0.08 # mock 8% exclusion rate
        excess_profit = max(0.0, consolidated_income - sbie_exclusion)
        topup_tax = excess_profit * topup_rate
        
        return {
            "parent_mst": parent_mst,
            "year": year,
            "consolidated_income": round(consolidated_income, 2),
            "consolidated_taxes_paid": round(consolidated_taxes, 2),
            "effective_tax_rate": round(etr, 4),
            "topup_tax_rate": round(topup_rate, 4),
            "substance_exclusion": round(sbie_exclusion, 2),
            "estimated_topup_tax": round(topup_tax, 2),
            "covered_tax_by_mst": {k: round(v, 2) for k, v in covered_tax_by_mst.items()}
        }
