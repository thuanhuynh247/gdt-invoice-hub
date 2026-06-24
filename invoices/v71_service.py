"""E-Waste EPR Recycling & Disposal Fee Compliance Engine (v71.0.0).

Implements electronics, batteries, and solar panels recycling fee calculations,
export exclusions, and small-scale importer exemptions under Decree 08/2022/NĐ-CP.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, List
from invoices.multitenant_service import get_tenant_db_path

class V71ComplianceService:
    """E-Waste EPR Decree 08/2022/NĐ-CP compliance engine."""

    def __init__(self, base_data_dir: str | None = None):
        self.base_data_dir = base_data_dir

    def get_tenant_connection(self, mst: str) -> sqlite3.Connection:
        """Returns isolated sqlite3 connection to tenant database."""
        db_path = get_tenant_db_path(mst, self.base_data_dir)
        conn = sqlite3.connect(db_path)
        conn.text_factory = lambda x: x.decode('utf-8', errors='replace') if isinstance(x, bytes) else x
        conn.row_factory = sqlite3.Row

        cur = conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS ewaste_epr_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_category TEXT NOT NULL,
                quantity REAL NOT NULL,
                is_export BOOLEAN NOT NULL,
                preceding_year_revenue REAL NOT NULL,
                preceding_year_import_value REAL NOT NULL,
                charge_rate REAL NOT NULL,
                gross_fee REAL NOT NULL,
                final_fee REAL NOT NULL,
                is_exempt BOOLEAN NOT NULL,
                exemption_type TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        return conn

    def calculate_epr(
        self, mst: str, product_category: str, quantity: float,
        is_export: bool = False, preceding_year_revenue: float = 0.0,
        preceding_year_import_value: float = 0.0, save_to_db: bool = True
    ) -> Dict[str, Any]:
        """Calculate EPR recycling fee, verify exemptions, and log transaction."""
        if quantity < 0:
            raise ValueError("Quantity/Weight must be non-negative.")
        if preceding_year_revenue < 0 or preceding_year_import_value < 0:
            raise ValueError("Revenue and import values must be non-negative.")

        cat_key = product_category.lower().strip()
        is_exempt = False
        exemption_type = "none"
        notes_list = []

        # EPR charge rates based on Decree 08/2022/NĐ-CP
        rates = {
            "laptop": 20000.0,      # VND/unit
            "tv_monitor": 30000.0,  # VND/unit
            "phone": 5000.0,        # VND/unit
            "battery": 50000.0,      # VND/kg
            "solar_panel": 15000.0   # VND/kg
        }

        if cat_key not in rates:
            raise ValueError(f"Invalid product category. Must be one of: {list(rates.keys())}")

        charge_rate = rates[cat_key]
        gross_fee = quantity * charge_rate

        # Exemption checks
        if is_export:
            is_exempt = True
            exemption_type = "export_exemption"
            final_fee = 0.0
            notes_list.append(f"Exempt: Direct export of {quantity:.2f} units/kg of {product_category} (EPR waived).")
        elif preceding_year_revenue > 0 and preceding_year_revenue < 30000000000.0:
            is_exempt = True
            exemption_type = "small_scale_revenue_exemption"
            final_fee = 0.0
            notes_list.append(f"Exempt: Importer/Producer revenue from preceding year ({preceding_year_revenue:,.0f} VND) is below the 30B VND threshold.")
        elif preceding_year_import_value > 0 and preceding_year_import_value < 3000000000.0:
            is_exempt = True
            exemption_type = "small_scale_import_exemption"
            final_fee = 0.0
            notes_list.append(f"Exempt: Total import value of goods from preceding year ({preceding_year_import_value:,.0f} VND) is below the 3B VND threshold.")
        else:
            final_fee = gross_fee
            notes_list.append(f"Recycling fee calculated: Category '{product_category}', quantity/weight {quantity:.2f}.")
            notes_list.append(f"EPR charge rate: {charge_rate:,.0f} VND per unit/kg. Total fee: {final_fee:,.0f} VND.")

        notes = " ".join(notes_list)

        breakdown = {
            "laptop": rates["laptop"] * quantity,
            "tv_monitor": rates["tv_monitor"] * quantity,
            "phone": rates["phone"] * quantity,
            "battery": rates["battery"] * quantity,
            "solar_panel": rates["solar_panel"] * quantity,
        }

        if save_to_db:
            conn = self.get_tenant_connection(mst)
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO ewaste_epr_logs
                    (product_category, quantity, is_export, preceding_year_revenue, preceding_year_import_value, charge_rate, gross_fee, final_fee, is_exempt, exemption_type, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (product_category, quantity, is_export, preceding_year_revenue, preceding_year_import_value, charge_rate, gross_fee, final_fee, is_exempt, exemption_type, notes))
            conn.commit()
            conn.close()

        return {
            "product_category": product_category,
            "quantity": quantity,
            "is_export": is_export,
            "preceding_year_revenue": preceding_year_revenue,
            "preceding_year_import_value": preceding_year_import_value,
            "charge_rate": charge_rate,
            "gross_fee": gross_fee,
            "final_fee": final_fee,
            "is_exempt": is_exempt,
            "exemption_type": exemption_type,
            "breakdown": breakdown,
            "notes": notes
        }

    def get_history(self, mst: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent EPR logs."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()
        cur.execute("SELECT * FROM ewaste_epr_logs ORDER BY id DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def delete_log(self, mst: str, log_id: int) -> bool:
        """Delete an EPR log entry by ID (for audit corrections)."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()
        cur.execute("DELETE FROM ewaste_epr_logs WHERE id = ?", (log_id,))
        deleted = cur.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    def get_annual_summary(self, mst: str, year: int | None = None) -> Dict[str, Any]:
        """Returns a summary of all E-Waste EPR activity for the given calendar year."""
        if year is None:
            year = datetime.now().year
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()
        
        # Default empty summary
        summary = {
            "year": year,
            "total_shipments": 0,
            "total_quantity": 0.0,
            "total_gross_fee": 0.0,
            "total_final_fee": 0.0,
            "total_exempt_fee": 0.0,
            "exempt_count": 0,
            "charged_count": 0,
            "category_distribution": {},
            "exemption_distribution": {}
        }
        
        try:
            cur.execute("""
                SELECT product_category, quantity, gross_fee, final_fee, is_exempt, exemption_type
                FROM ewaste_epr_logs
                WHERE strftime('%Y', created_at) = ?
            """, (str(year),))
            rows = cur.fetchall()
            
            for row in rows:
                r_cat = row["product_category"]
                r_qty = row["quantity"]
                r_gross = row["gross_fee"]
                r_final = row["final_fee"]
                r_exempt = bool(row["is_exempt"])
                r_ex_type = row["exemption_type"] or "none"
                
                summary["total_shipments"] += 1
                summary["total_quantity"] += r_qty
                summary["total_gross_fee"] += r_gross
                summary["total_final_fee"] += r_final
                
                if r_exempt:
                    summary["exempt_count"] += 1
                else:
                    summary["charged_count"] += 1
                
                # Category breakdown
                if r_cat not in summary["category_distribution"]:
                    summary["category_distribution"][r_cat] = {"count": 0, "quantity": 0.0, "final_fee": 0.0}
                summary["category_distribution"][r_cat]["count"] += 1
                summary["category_distribution"][r_cat]["quantity"] += r_qty
                summary["category_distribution"][r_cat]["final_fee"] += r_final
                
                # Exemption type breakdown
                if r_ex_type not in summary["exemption_distribution"]:
                    summary["exemption_distribution"][r_ex_type] = 0
                summary["exemption_distribution"][r_ex_type] += 1
                
            summary["total_exempt_fee"] = max(0.0, summary["total_gross_fee"] - summary["total_final_fee"])
        except Exception:
            pass
        finally:
            conn.close()
            
        return summary
