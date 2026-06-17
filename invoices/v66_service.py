"""Greenhouse Gas (GHG) Emissions & Carbon Credits Compliance Engine (v66.0.0).

Implements GHG emissions calculations, GWP scaling, carbon credit offsets,
and small-scale exemptions under Decree 06/2022/NĐ-CP.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, List
from invoices.multitenant_service import get_tenant_db_path

class V66ComplianceService:
    """GHG Emissions & Carbon Credits Decree 06/2022/NĐ-CP compliance engine."""

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
            CREATE TABLE IF NOT EXISTS ghg_emissions_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                emission_description TEXT NOT NULL,
                facility_category TEXT NOT NULL,
                co2_tonnes REAL NOT NULL,
                ch4_tonnes REAL NOT NULL,
                n2o_tonnes REAL NOT NULL,
                carbon_credits_offset REAL NOT NULL,
                total_co2e REAL NOT NULL,
                taxable_co2e REAL NOT NULL,
                fee_amount REAL NOT NULL,
                is_exempt BOOLEAN NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        return conn

    def calculate_ghg(
        self, mst: str, emission_description: str, facility_category: str,
        co2_tonnes: float, ch4_tonnes: float, n2o_tonnes: float,
        carbon_credits_offset: float = 0.0, exemption_category: str = "none"
    ) -> Dict[str, Any]:
        """Calculate GHG emissions in CO2e, verify exemptions, apply credit offsets, and record transaction."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        # IPCC AR5 Global Warming Potentials (GWP)
        gwp_co2 = 1.0
        gwp_ch4 = 28.0
        gwp_n2o = 265.0

        total_co2e = (co2_tonnes * gwp_co2) + (ch4_tonnes * gwp_ch4) + (n2o_tonnes * gwp_n2o)

        # Standard Carbon price: 150,000 VND per tonne CO2e
        carbon_unit_price = 150000.0

        is_exempt = False
        notes_list = []

        # Exemption check: Small emitter under 3,000 tonnes CO2e/year
        if total_co2e < 3000.0 or exemption_category == "small_emitter":
            is_exempt = True
            taxable_co2e = 0.0
            fee_amount = 0.0
            notes_list.append(f"Exempt: Total emissions ({total_co2e:.2f} tCO2e) are below the 3,000 tCO2e small-emitter threshold under Decree 06/2022/NĐ-CP.")
        else:
            # Maximum carbon credit offset is capped at 10% of total emissions under Article 22
            max_offset = total_co2e * 0.10
            actual_offset = min(carbon_credits_offset, max_offset)
            taxable_co2e = total_co2e - actual_offset
            fee_amount = taxable_co2e * carbon_unit_price
            
            notes_list.append(f"Emissions calculated: {total_co2e:.2f} tCO2e (CO2={co2_tonnes:.1f}t, CH4={ch4_tonnes:.1f}t, N2O={n2o_tonnes:.1f}t).")
            if actual_offset > 0:
                notes_list.append(f"Carbon credit offset applied: {actual_offset:.2f} tCO2e (requested: {carbon_credits_offset:.2f} tCO2e, capped at 10% limit of {max_offset:.2f} tCO2e).")
            notes_list.append(f"Taxable CO2e: {taxable_co2e:.2f} tCO2e at {carbon_unit_price:,.0f} VND/tCO2e. Total fee: {fee_amount:,.0f} VND.")

        notes = " ".join(notes_list)

        cur.execute("""
            INSERT INTO ghg_emissions_logs
                (emission_description, facility_category, co2_tonnes, ch4_tonnes, n2o_tonnes, carbon_credits_offset, total_co2e, taxable_co2e, fee_amount, is_exempt, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (emission_description, facility_category, co2_tonnes, ch4_tonnes, n2o_tonnes, carbon_credits_offset, total_co2e, taxable_co2e, fee_amount, is_exempt, notes))

        conn.commit()
        conn.close()

        return {
            "emission_description": emission_description,
            "facility_category": facility_category,
            "co2_tonnes": co2_tonnes,
            "ch4_tonnes": ch4_tonnes,
            "n2o_tonnes": n2o_tonnes,
            "gwp_factors": {"CO2": gwp_co2, "CH4": gwp_ch4, "N2O": gwp_n2o},
            "carbon_credits_offset": carbon_credits_offset,
            "total_co2e": total_co2e,
            "taxable_co2e": taxable_co2e,
            "fee_amount": fee_amount,
            "is_exempt": is_exempt,
            "notes": notes
        }

    def get_history(self, mst: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent GHG emission logs."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()
        cur.execute("SELECT * FROM ghg_emissions_logs ORDER BY id DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
