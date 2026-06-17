"""Enterprise Decree 123 VAT Adjustments & Circular 67 Sci-Tech Fund Optimizer Service (v44.0.0).

Handles dynamic multitenant calculations for Decree 123 adjustments,
Circular 67 / Circular 05 Science & Technology Development Fund simulation,
and Welfare Fund CIT cap audits.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, List
from invoices.multitenant_service import get_tenant_db_path

class V44ComplianceService:
    def __init__(self, base_data_dir: str | None = None):
        self.base_data_dir = base_data_dir

    def get_tenant_connection(self, mst: str) -> sqlite3.Connection:
        """Returns an isolated sqlite3 connection to the specific tenant database."""
        db_path = get_tenant_db_path(mst, self.base_data_dir)
        conn = sqlite3.connect(db_path)
        conn.text_factory = lambda x: x.decode('utf-8', errors='replace') if isinstance(x, bytes) else x
        conn.row_factory = sqlite3.Row
        
        # Ensure our custom v44 tables exist in this tenant DB
        cur = conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS decree123_invoice_adjustments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_invoice_symbol TEXT NOT NULL,
                original_invoice_number TEXT NOT NULL,
                adjustment_invoice_symbol TEXT NOT NULL,
                adjustment_invoice_number TEXT NOT NULL,
                adjustment_type TEXT NOT NULL, -- 'adjustment', 'replacement', 'discount'
                amount_change REAL NOT NULL,
                vat_change REAL NOT NULL,
                tax_rate REAL NOT NULL,
                status TEXT DEFAULT 'Pending',
                mismatch_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sci_tech_fund_ledger (
                fiscal_year INTEGER PRIMARY KEY,
                taxable_income REAL NOT NULL,
                allocated_amount REAL NOT NULL,
                spent_amount REAL DEFAULT 0.0,
                welfare_expenses REAL DEFAULT 0.0,
                average_monthly_salary REAL DEFAULT 0.0,
                welfare_limit REAL DEFAULT 0.0,
                welfare_mismatch REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sci_tech_expenditures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fiscal_year INTEGER NOT NULL,
                expenditure_date TEXT NOT NULL,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                is_qualified INTEGER DEFAULT 1,
                FOREIGN KEY(fiscal_year) REFERENCES sci_tech_fund_ledger(fiscal_year)
            );
        """)
        conn.commit()
        return conn

    def reconcile_decree123_adjustments(self, mst: str) -> List[Dict[str, Any]]:
        """Reconcile and validate Decree 123 adjustment invoices against original invoices."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, original_invoice_symbol, original_invoice_number, 
                   adjustment_invoice_symbol, adjustment_invoice_number, 
                   adjustment_type, amount_change, vat_change, tax_rate
            FROM decree123_invoice_adjustments
        """)
        
        records = []
        rows = cur.fetchall()
        
        for row in rows:
            adj_id = row["id"]
            orig_symbol = row["original_invoice_symbol"]
            orig_number = row["original_invoice_number"]
            adj_type = row["adjustment_type"]
            amount_change = row["amount_change"]
            vat_change = row["vat_change"]
            tax_rate = row["tax_rate"]
            
            # Find original invoice in the tenant DB.
            # We first search by matching file metadata or symbol/number in filename, 
            # or try to match symbol/number against columns if they exist.
            # Let's search inside the 'invoice' table.
            # Since standard invoice table doesn't have symbol/number columns directly in the base schema 
            # (only id, filename, seller_mst, buyer_mst, amount_before_tax, tax_amount, total_amount, date),
            # let's find invoices where filename contains orig_number or orig_symbol.
            # Let's perform a match:
            cur.execute("""
                SELECT id, seller_mst, buyer_mst, amount_before_tax, tax_amount 
                FROM invoice 
                WHERE filename LIKE ? OR id = ? OR filename LIKE ?
            """, (f"%{orig_number}%", orig_number, f"%{orig_symbol}%"))
            
            orig_inv = cur.fetchone()
            
            status = "Linked"
            reason = None
            
            if not orig_inv:
                # Let's check the global database as fallback
                status = "Unlinked"
                reason = "Original invoice reference not found in system."
            else:
                orig_net = orig_inv["amount_before_tax"] or 0.0
                orig_vat = orig_inv["tax_amount"] or 0.0
                
                # Validation rules:
                # 1. Negative adjustments (reduction) cannot exceed original amount
                if amount_change < 0 and abs(amount_change) > orig_net:
                    status = "Mismatch"
                    reason = f"Reduction amount {abs(amount_change):,} exceed original invoice net amount {orig_net:,}."
                elif vat_change < 0 and abs(vat_change) > orig_vat:
                    status = "Mismatch"
                    reason = f"Reduction VAT {abs(vat_change):,} exceed original invoice VAT {orig_vat:,}."
                
                # 2. Enforce taxpayer MST matching logic
                # For purchase: buyer_mst must match tenant MST. For sale: seller_mst must match tenant MST.
                # Let's verify that the tenant MST matches one of the parties in the original invoice
                if mst not in (orig_inv["seller_mst"], orig_inv["buyer_mst"]):
                    status = "Mismatch"
                    reason = "Tenant MST does not match seller or buyer of original invoice."
            
            # Update the status in tenant database
            cur.execute("""
                UPDATE decree123_invoice_adjustments
                SET status = ?, mismatch_reason = ?
                WHERE id = ?
            """, (status, reason, adj_id))
            
            records.append({
                "id": adj_id,
                "original_invoice_symbol": orig_symbol,
                "original_invoice_number": orig_number,
                "adjustment_invoice_symbol": row["adjustment_invoice_symbol"],
                "adjustment_invoice_number": row["adjustment_invoice_number"],
                "adjustment_type": adj_type,
                "amount_change": amount_change,
                "vat_change": vat_change,
                "tax_rate": tax_rate,
                "status": status,
                "mismatch_reason": reason
            })
            
        conn.commit()
        conn.close()
        return records

    def simulate_sci_tech_fund(
        self, mst: str, year: int, taxable_income: float, allocation_percent: float, 
        annual_rd_spend: float, qualified_ratio: float, welfare_expenses: float, average_monthly_salary: float
    ) -> Dict[str, Any]:
        """Calculates Sci-Tech Fund optimization limits, 5-year clawbacks, and welfare fund CIT ceilings."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()
        
        # Max allocation is 10% of taxable income
        max_allocation = taxable_income * 0.10
        allocated_amount = taxable_income * (allocation_percent / 100.0)
        if allocated_amount > max_allocation:
            allocated_amount = max_allocation
            
        # Clear existing and insert or replace
        cur.execute("""
            INSERT OR REPLACE INTO sci_tech_fund_ledger (
                fiscal_year, taxable_income, allocated_amount, spent_amount, welfare_expenses, average_monthly_salary, welfare_limit, welfare_mismatch
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (year, taxable_income, allocated_amount, 0.0, welfare_expenses, average_monthly_salary, 0.0, 0.0))
        
        # Simulate 5-year timeline
        # Year 1 to Year 5
        remaining_balance = allocated_amount
        total_qualified_spent = 0.0
        yearly_projection = []
        
        # Tax finalization filing deadline is April 1st of Year+1.
        # Late interest starts running from this date for clawbacks.
        # Interest is 0.03% per day.
        interest_rate_daily = 0.0003
        
        for i in range(1, 6):
            # Each year we spend annual_rd_spend, with qualified_ratio being qualified
            year_spend = annual_rd_spend
            year_qualified = year_spend * qualified_ratio
            
            # Deduct qualified spending from the remaining fund balance
            spent_from_fund = min(remaining_balance, year_qualified)
            remaining_balance -= spent_from_fund
            total_qualified_spent += spent_from_fund
            
            yearly_projection.append({
                "year_index": i,
                "calendar_year": year + i,
                "starting_balance": round(remaining_balance + spent_from_fund, 2),
                "r_and_d_spend": round(year_spend, 2),
                "qualified_spend": round(year_qualified, 2),
                "spent_from_fund": round(spent_from_fund, 2),
                "remaining_balance": round(remaining_balance, 2)
            })
            
        # After 5 years, any unspent fund is clawed back
        unspent_amount = remaining_balance
        cit_clawback = unspent_amount * 0.20 # statutory CIT is 20%
        
        # Simulate late payment interest (lãi chậm nộp)
        # Interest is calculated for the 5-year duration (5 * 365 days)
        days_past = 5 * 365
        late_interest = cit_clawback * interest_rate_daily * days_past
        
        # Corporate Welfare Fund ceiling: 1 month's average monthly salary
        # Welfare expenses exceeding this limit are non-deductible (mismatch)
        welfare_limit = average_monthly_salary
        welfare_mismatch = max(0.0, welfare_expenses - welfare_limit)
        
        # Update the ledger with computed metrics
        cur.execute("""
            UPDATE sci_tech_fund_ledger
            SET spent_amount = ?, welfare_limit = ?, welfare_mismatch = ?
            WHERE fiscal_year = ?
        """, (total_qualified_spent, welfare_limit, welfare_mismatch, year))
        
        conn.commit()
        conn.close()
        
        return {
            "fiscal_year": year,
            "taxable_income": round(taxable_income, 2),
            "allocation_percent": allocation_percent,
            "allocated_amount": round(allocated_amount, 2),
            "max_allowable_allocation": round(max_allocation, 2),
            "total_qualified_spent": round(total_qualified_spent, 2),
            "unspent_amount": round(unspent_amount, 2),
            "cit_clawback": round(cit_clawback, 2),
            "late_interest_penalty": round(late_interest, 2),
            "welfare_expenses": round(welfare_expenses, 2),
            "welfare_limit_cap": round(welfare_limit, 2),
            "welfare_mismatch_non_deductible": round(welfare_mismatch, 2),
            "yearly_projection": yearly_projection
        }
