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

            CREATE TABLE IF NOT EXISTS ifrs15_revenue_contracts (
                contract_id TEXT PRIMARY KEY,
                customer_name TEXT NOT NULL,
                contract_date TEXT NOT NULL,
                total_transaction_price REAL NOT NULL,
                deferred_revenue REAL DEFAULT 0.0,
                recognized_revenue REAL DEFAULT 0.0,
                status TEXT DEFAULT 'Active'
            );

            CREATE TABLE IF NOT EXISTS ifrs15_performance_obligations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                contract_id TEXT NOT NULL,
                obligation_name TEXT NOT NULL,
                standalone_selling_price REAL NOT NULL,
                allocated_price REAL,
                is_satisfied INTEGER DEFAULT 0,
                satisfied_date TEXT,
                FOREIGN KEY(contract_id) REFERENCES ifrs15_revenue_contracts(contract_id)
            );

            CREATE TABLE IF NOT EXISTS ifrs_fixed_assets (
                asset_id TEXT PRIMARY KEY,
                asset_name TEXT NOT NULL,
                asset_category TEXT NOT NULL,
                acquisition_date TEXT NOT NULL,
                historical_cost REAL NOT NULL,
                ifrs_useful_life_years REAL NOT NULL,
                vas_useful_life_years REAL NOT NULL,
                ifrs_accumulated_depreciation REAL DEFAULT 0.0,
                vas_accumulated_depreciation REAL DEFAULT 0.0,
                is_revalued INTEGER DEFAULT 0,
                revaluation_surplus REAL DEFAULT 0.0
            );

            CREATE TABLE IF NOT EXISTS ifrs_forex_valuation (
                item_id TEXT PRIMARY KEY,
                account_name TEXT NOT NULL,
                currency TEXT NOT NULL,
                foreign_amount REAL NOT NULL,
                book_rate REAL NOT NULL,
                year_end_rate REAL NOT NULL,
                asset_or_liability TEXT NOT NULL
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

    def calculate_ifrs16_amortization_table(self, mst: str, lease_id: str) -> List[Dict[str, Any]]:
        """Retrieves lease details from the tenant database and generates a complete amortization table."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()
        cur.execute("""
            SELECT monthly_payment, discount_rate, lease_term_months 
            FROM lease_amortization_schedule 
            WHERE lease_id = ?
        """, (lease_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return []
        return self.calculate_ifrs16_amortization(
            lease_id, row["monthly_payment"], row["discount_rate"], row["lease_term_months"]
        )

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

    def allocate_ifrs15_transaction_price(
        self, mst: str, contract_id: str, customer_name: str, contract_date: str, total_price: float, obligations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Allocates contract price based on relative Standalone Selling Prices (SSP) under IFRS 15."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()
        
        # Save contract record
        cur.execute("""
            INSERT OR REPLACE INTO ifrs15_revenue_contracts (contract_id, customer_name, contract_date, total_transaction_price, deferred_revenue, recognized_revenue)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (contract_id, customer_name, contract_date, total_price, total_price, 0.0))
        
        # Remove old performance obligations for this contract
        cur.execute("DELETE FROM ifrs15_performance_obligations WHERE contract_id = ?", (contract_id,))
        
        # Sum up Standalone Selling Prices
        total_ssp = sum(float(ob.get("standalone_selling_price", 0.0)) for ob in obligations)
        
        allocated_obligations = []
        for ob in obligations:
            ssp = float(ob.get("standalone_selling_price", 0.0))
            name = ob.get("obligation_name")
            
            allocated_price = 0.0
            if total_ssp > 0:
                allocated_price = total_price * (ssp / total_ssp)
            else:
                allocated_price = total_price / len(obligations)
                
            cur.execute("""
                INSERT INTO ifrs15_performance_obligations (contract_id, obligation_name, standalone_selling_price, allocated_price, is_satisfied)
                VALUES (?, ?, ?, ?, 0)
            """, (contract_id, name, ssp, allocated_price))
            
            allocated_obligations.append({
                "obligation_name": name,
                "standalone_selling_price": ssp,
                "allocated_price": round(allocated_price, 2)
            })
            
        conn.commit()
        conn.close()
        return allocated_obligations

    def recognize_ifrs15_revenue(self, mst: str, contract_id: str, satisfied_names: List[str], satisfied_date: str) -> Dict[str, Any]:
        """Marks specific obligations as satisfied and updates recognized and deferred revenue in tenant DB under IFRS 15."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()
        
        # Update satisfied status for specific obligations
        for name in satisfied_names:
            cur.execute("""
                UPDATE ifrs15_performance_obligations
                SET is_satisfied = 1, satisfied_date = ?
                WHERE contract_id = ? AND obligation_name = ?
            """, (satisfied_date, contract_id, name))
            
        # Sum up satisfied obligations allocated prices
        cur.execute("""
            SELECT SUM(allocated_price) 
            FROM ifrs15_performance_obligations
            WHERE contract_id = ? AND is_satisfied = 1
        """, (contract_id,))
        recognized = cur.fetchone()[0] or 0.0
        
        # Get total transaction price
        cur.execute("""
            SELECT total_transaction_price 
            FROM ifrs15_revenue_contracts
            WHERE contract_id = ?
        """, (contract_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return {"error": f"Contract {contract_id} not found"}
        
        total_price = row[0]
        deferred = total_price - recognized
        if deferred < 0:
            deferred = 0.0
            
        # Update contract totals
        cur.execute("""
            UPDATE ifrs15_revenue_contracts
            SET recognized_revenue = ?, deferred_revenue = ?
            WHERE contract_id = ?
        """, (recognized, deferred, contract_id))
        
        conn.commit()
        conn.close()
        
        return {
            "contract_id": contract_id,
            "total_transaction_price": round(total_price, 2),
            "recognized_revenue": round(recognized, 2),
            "deferred_revenue": round(deferred, 2)
        }

    def calculate_vietnam_tax_reconciliation(
        self,
        mst: str,
        year: int,
        vas_profit_before_tax: float = 500000000.0,
        total_interest_expense: float = 120000000.0,
        ebitda: float = 300000000.0
    ) -> Dict[str, Any]:
        """Calculates adjustments between IFRS/VAS and Vietnamese corporate income tax (CIT) rules.
        
        Incorporates:
        - Decree 132/2020/ND-CP 30% EBITDA interest cap (temporary carry-forward DTA).
        - Circular 78 cash settlement CIT non-deductibility (permanent difference for high-value cash invoices >= 20M).
        - Invoice T-score compliance audits (permanent difference for t-score < 70).
        - IFRS 16 Lease differences vs. VAS cash-basis operating lease deductions.
        - Useful life depreciation check (Circular 45/2013/TT-BTC limits vs IAS 16 management estimation).
        - Revaluation depreciation disallowed (historical cost vs IFRS revaluation model).
        - Foreign exchange differences (IAS 21 revaluation recognized in P&L vs Circular 200/2014/TT-BTC cash/receivables exclusion).
        - Employee benefits (IAS 19 post-employment benefit accruals vs actual paid deduction).
        - 5-year statutory limitation rule on DTA recoverability assessment.
        - IFRS 15 revenue vs. physical GDT invoicing timing gaps (Decree 123).
        - Full mapping to Form 03-1A/TNDN CIT Return.
        """
        conn = self.get_tenant_connection(mst)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        # 1. Permanent differences from input invoice audits
        # Input invoices: buyer_mst = mst (taxpayer is the buyer)
        # Any invoice with t_score < 70 is flagged as illegal/high-risk -> permanent non-deductible
        cur.execute("""
            SELECT COALESCE(SUM(total_amount), 0.0) 
            FROM invoice 
            WHERE buyer_mst = ? AND t_score < 70
        """, (mst,))
        high_risk_non_deductible = float(cur.fetchone()[0])
        
        # Invoices with amount >= 20M VND: must be paid via bank transfer to be deductible
        # We flag them as Circular 78 cash payment risk
        cur.execute("""
            SELECT COALESCE(SUM(total_amount), 0.0) 
            FROM invoice 
            WHERE buyer_mst = ? AND total_amount >= 20000000.0
        """, (mst,))
        bank_transfer_required_sum = float(cur.fetchone()[0])
        
        # 2. Decree 132/2020/ND-CP EBITDA Interest Expense Cap
        ebitda_limit = max(0.0, ebitda * 0.30)
        disallowed_interest = 0.0
        if total_interest_expense > ebitda_limit:
            disallowed_interest = total_interest_expense - ebitda_limit
            
        dta_interest_carryforward = disallowed_interest * 0.20
        
        # 3. IFRS 16 vs VAS Operating Lease timing differences
        # Get active leases
        cur.execute("""
            SELECT lease_id, commencement_date, lease_term_months, monthly_payment, discount_rate, present_value_rou
            FROM lease_amortization_schedule
            WHERE active_status = 1
        """)
        leases = cur.fetchall()
        
        ifrs16_expenses_ytd = 0.0
        vas_cash_deductions_ytd = 0.0
        lease_dta = 0.0
        
        for lease in leases:
            lid = lease["lease_id"]
            monthly_pmt = lease["monthly_payment"]
            term = lease["lease_term_months"]
            rate = lease["discount_rate"]
            pv = lease["present_value_rou"]
            
            # Straight-line depreciation of ROU asset YTD (assuming 12 months)
            months_active = min(12, term)
            depreciation = (pv / term) * months_active
            
            # Interest expense YTD
            schedule = self.calculate_ifrs16_amortization(lid, monthly_pmt, rate, term)
            interest = sum(row["interest_expense"] for row in schedule[:months_active])
            
            ifrs16_expenses_ytd += (depreciation + interest)
            vas_cash_deductions_ytd += (monthly_pmt * months_active)
            
            # Lease Liability vs ROU asset balance at month 12 (or end of active)
            closing_liability = schedule[months_active - 1]["closing_balance"] if months_active <= len(schedule) else 0.0
            closing_rou = max(0.0, pv - depreciation)
            # Temporary difference = Lease Liability - ROU Asset
            temp_diff = closing_liability - closing_rou
            if temp_diff > 0:
                lease_dta += temp_diff * 0.20
                
        lease_timing_adjustment = ifrs16_expenses_ytd - vas_cash_deductions_ytd
        
        # 4. Provisions DTA from Ledger
        cur.execute("""
            SELECT COALESCE(SUM(carrying_amount_ifrs - tax_base_vas), 0.0)
            FROM ifrs_deferred_tax_ledger
            WHERE fiscal_year = ? AND balance_sheet_item LIKE '%Provision%' AND balance_sheet_item NOT LIKE '%Benefit%' AND balance_sheet_item NOT LIKE '%Severance%'
        """, (year,))
        provisions_diff = float(cur.fetchone()[0])
        provisions_dta = max(0.0, provisions_diff * 0.20)
        
        # 5. IFRS 15 Revenue vs GDT Invoiced Revenue Audit
        # Calculate recognized revenue under IFRS 15
        cur.execute("SELECT COALESCE(SUM(recognized_revenue), 0.0) FROM ifrs15_revenue_contracts")
        ifrs15_revenue = float(cur.fetchone()[0])
        
        # Calculate GDT Invoiced Revenue (sales invoices: seller_mst = mst)
        cur.execute("""
            SELECT COALESCE(SUM(amount_before_tax), 0.0)
            FROM invoice
            WHERE seller_mst = ?
        """, (mst,))
        gdt_invoiced_revenue = float(cur.fetchone()[0])
        
        revenue_gap = ifrs15_revenue - gdt_invoiced_revenue

        # 6. FIXED ASSETS: Useful lives & Revaluation Audits (Circular 45 vs IAS 16)
        cur.execute("""
            SELECT asset_id, asset_name, asset_category, historical_cost, 
                   ifrs_useful_life_years, vas_useful_life_years, is_revalued, revaluation_surplus 
            FROM ifrs_fixed_assets
        """)
        fixed_assets = cur.fetchall()
        excess_depreciation_sum = 0.0
        revaluation_depreciation_disallowed = 0.0
        fixed_assets_details = []
        for asset in fixed_assets:
            cost = asset["historical_cost"]
            ifrs_life = asset["ifrs_useful_life_years"]
            vas_life = asset["vas_useful_life_years"]
            is_rev = asset["is_revalued"]
            rev_surplus = asset["revaluation_surplus"]
            
            ifrs_dep = cost / ifrs_life if ifrs_life > 0 else 0.0
            vas_dep = cost / vas_life if vas_life > 0 else 0.0
            
            # Excess useful life depreciation is added back for taxation
            excess_dep = max(0.0, ifrs_dep - vas_dep)
            excess_depreciation_sum += excess_dep
            
            rev_dep = 0.0
            if is_rev and rev_surplus > 0:
                rev_dep = rev_surplus / ifrs_life if ifrs_life > 0 else 0.0
                revaluation_depreciation_disallowed += rev_dep
                
            fixed_assets_details.append({
                "asset_id": asset["asset_id"],
                "asset_name": asset["asset_name"],
                "asset_category": asset["asset_category"],
                "historical_cost": cost,
                "ifrs_depreciation": round(ifrs_dep, 2),
                "vas_depreciation": round(vas_dep, 2),
                "excess_depreciation": round(excess_dep, 2),
                "revaluation_depreciation_disallowed": round(rev_dep, 2)
            })

        # 7. FOREX: Unrealized differences revaluation audits (IAS 21 vs Circular 200)
        cur.execute("""
            SELECT item_id, account_name, currency, foreign_amount, book_rate, year_end_rate, asset_or_liability 
            FROM ifrs_forex_valuation
        """)
        forex_valuations = cur.fetchall()
        unrealized_forex_gain_non_taxable = 0.0
        unrealized_forex_loss_non_deductible = 0.0
        forex_details = []
        for item in forex_valuations:
            f_amt = item["foreign_amount"]
            b_rate = item["book_rate"]
            ye_rate = item["year_end_rate"]
            type_al = item["asset_or_liability"]
            
            diff = f_amt * (ye_rate - b_rate)
            gain = 0.0
            loss = 0.0
            
            if type_al == "ASSET":
                if diff > 0:
                    gain = diff
                    unrealized_forex_gain_non_taxable += gain
                else:
                    loss = abs(diff)
                    unrealized_forex_loss_non_deductible += loss
            else: # LIABILITY
                if ye_rate > b_rate:
                    loss = f_amt * (ye_rate - b_rate)
                else:
                    gain = f_amt * (b_rate - ye_rate)
                    
            forex_details.append({
                "item_id": item["item_id"],
                "account_name": item["account_name"],
                "currency": item["currency"],
                "foreign_amount": f_amt,
                "book_amount": round(f_amt * b_rate, 2),
                "year_end_amount": round(f_amt * ye_rate, 2),
                "gain": round(gain, 2),
                "loss": round(loss, 2),
                "cit_status": "Non-taxable Gain" if (type_al == "ASSET" and gain > 0) else ("Non-deductible Loss" if (type_al == "ASSET" and loss > 0) else "CIT Compliant")
            })

        # 8. Employee Benefits Accruals (IAS 19 vs Vietnam Realized Deductions)
        cur.execute("""
            SELECT COALESCE(SUM(carrying_amount_ifrs - tax_base_vas), 0.0)
            FROM ifrs_deferred_tax_ledger
            WHERE fiscal_year = ? AND (balance_sheet_item LIKE '%Benefit%' OR balance_sheet_item LIKE '%Severance%')
        """, (year,))
        employee_benefits_diff = float(cur.fetchone()[0])
        employee_benefits_dta = max(0.0, employee_benefits_diff * 0.20)
        
        # Close connection
        conn.close()
        
        # 9. Reconcile to Taxable Profit (VN CIT Form 03-1A/TNDN Bridge)
        # B1: Net profit before tax (VAS base)
        b1 = vas_profit_before_tax
        
        # B2: Revenue timing additions (IFRS 15 Recognized Revenue > GDT Invoiced Revenue)
        b2 = max(0.0, revenue_gap)
        
        # B3: Expenses disallowed by CIT Law (Permanent and Temporary addbacks)
        b3 = (high_risk_non_deductible + disallowed_interest + excess_depreciation_sum + 
              revaluation_depreciation_disallowed + provisions_diff + employee_benefits_diff)
              
        # B4: Unrealized forex loss from cash/receivables (non-deductible)
        b4 = unrealized_forex_loss_non_deductible
        
        # B11: Unrealized forex gain from cash/receivables (non-taxable)
        b11 = unrealized_forex_gain_non_taxable
        
        # B12: Decreasing revenue adjustments (IFRS 15 Recognized Revenue < GDT Invoiced Revenue)
        b12 = max(0.0, -revenue_gap)
        
        taxable_profit = b1 + b2 + b3 + b4 - b11 - b12
        current_cit_rate = 0.20
        estimated_current_cit = max(0.0, taxable_profit * current_cit_rate)
        
        # 10. Total DTA
        total_dta = dta_interest_carryforward + lease_dta + provisions_dta + employee_benefits_dta + (excess_depreciation_sum * 0.20)
        
        # 11. DTA 5-year recoverability risk assessment
        dta_recovery_years = total_dta / (estimated_current_cit + 1.0)
        dta_recovery_risk = False
        warning_msg = None
        if dta_recovery_years > 5.0 or taxable_profit <= 0:
            dta_recovery_risk = True
            warning_msg = "WARNING: Deferred Tax Assets (DTA) may expire. Under Vietnamese CIT Law (Circular 78), tax losses and interest carry-forwards are strictly capped at a 5-year carry-forward limit. Current taxable profit projections are insufficient for full utilization."
            
        return {
            "mst": mst,
            "fiscal_year": year,
            "vas_profit_before_tax": vas_profit_before_tax,
            "total_interest_expense": total_interest_expense,
            "ebitda": ebitda,
            "high_risk_non_deductible": round(high_risk_non_deductible, 2),
            "bank_transfer_required_sum": round(bank_transfer_required_sum, 2),
            "decree132_ebitda_limit": round(ebitda_limit, 2),
            "decree132_disallowed_interest": round(disallowed_interest, 2),
            "decree132_dta_carryforward": round(dta_interest_carryforward, 2),
            "ifrs16_expenses_ytd": round(ifrs16_expenses_ytd, 2),
            "vas_lease_cash_deductions_ytd": round(vas_cash_deductions_ytd, 2),
            "lease_timing_adjustment": round(lease_timing_adjustment, 2),
            "lease_dta": round(lease_dta, 2),
            "provisions_timing_difference": round(provisions_diff, 2),
            "provisions_dta": round(provisions_dta, 2),
            "ifrs15_recognized_revenue": round(ifrs15_revenue, 2),
            "gdt_invoiced_revenue": round(gdt_invoiced_revenue, 2),
            "revenue_gap_ifrs15_vs_gdt": round(revenue_gap, 2),
            "fixed_assets_details": fixed_assets_details,
            "excess_depreciation_sum": round(excess_depreciation_sum, 2),
            "revaluation_depreciation_disallowed": round(revaluation_depreciation_disallowed, 2),
            "forex_details": forex_details,
            "unrealized_forex_gain_non_taxable": round(unrealized_forex_gain_non_taxable, 2),
            "unrealized_forex_loss_non_deductible": round(unrealized_forex_loss_non_deductible, 2),
            "employee_benefits_diff": round(employee_benefits_diff, 2),
            "employee_benefits_dta": round(employee_benefits_dta, 2),
            "permanent_addbacks": round(high_risk_non_deductible + revaluation_depreciation_disallowed, 2),
            "temporary_adjustments": round(disallowed_interest + lease_timing_adjustment + provisions_diff + employee_benefits_diff + excess_depreciation_sum, 2),
            "taxable_profit": round(taxable_profit, 2),
            "estimated_current_cit": round(estimated_current_cit, 2),
            "total_deferred_tax_assets": round(total_dta, 2),
            "dta_recovery_risk": dta_recovery_risk,
            "dta_recovery_warning": warning_msg,
            "effective_tax_rate": round(estimated_current_cit / vas_profit_before_tax, 4) if vas_profit_before_tax > 0 else 0.20,
            "form_03_1a": {
                "B1": round(b1, 2),
                "B2": round(b2, 2),
                "B3": round(b3, 2),
                "B4": round(b4, 2),
                "B11": round(b11, 2),
                "B12": round(b12, 2),
                "taxable_income": round(taxable_profit, 2),
                "estimated_cit": round(estimated_current_cit, 2)
            }
        }


