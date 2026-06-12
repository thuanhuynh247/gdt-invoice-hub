"""Environment Protection Fee for Wastewater (EPFW) Compliance Engine (v61.0.0).

Implements wastewater fee calculations, pollutants surcharge, and exemptions
under Decree 53/2020/NĐ-CP.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional
from invoices.multitenant_service import get_tenant_db_path

# Variable fee rates per pollutant under Decree 53/2020/NĐ-CP (VND per kg)
POLLUTANT_RATES = {
    "cod": 2000.0,     # Chemical Oxygen Demand
    "tss": 2400.0,     # Total Suspended Solids
    "pb": 1000000.0,   # Lead
    "cd": 20000000.0,  # Cadmium
    "hg": 40000000.0,  # Mercury
    "as_metal": 20000000.0  # Arsenic
}

class V61ComplianceService:
    """Environment Protection Fee for Wastewater (EPFW) compliance engine."""

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
            CREATE TABLE IF NOT EXISTS epfw_calculations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                water_description TEXT NOT NULL,
                wastewater_type TEXT NOT NULL,
                water_volume_m3 REAL NOT NULL,
                clean_water_price_vnd REAL DEFAULT 0,
                has_heavy_metals BOOLEAN DEFAULT 0,
                pollutant_cod_kg REAL DEFAULT 0,
                pollutant_tss_kg REAL DEFAULT 0,
                pollutant_pb_kg REAL DEFAULT 0,
                pollutant_cd_kg REAL DEFAULT 0,
                pollutant_hg_kg REAL DEFAULT 0,
                pollutant_as_kg REAL DEFAULT 0,
                base_fee_vnd REAL NOT NULL,
                variable_fee_vnd REAL NOT NULL,
                total_fee_vnd REAL NOT NULL,
                effective_fee_vnd REAL NOT NULL,
                is_exempt BOOLEAN NOT NULL DEFAULT 0,
                exemption_reason TEXT,
                water_source TEXT NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        return conn

    def calculate_epfw(
        self,
        mst: str,
        water_description: str,
        wastewater_type: str,  # domestic or industrial
        water_volume_m3: float,
        clean_water_price_vnd: float = 0.0,  # only for domestic (VND per m3)
        pollutant_cod_kg: float = 0.0,
        pollutant_tss_kg: float = 0.0,
        pollutant_pb_kg: float = 0.0,
        pollutant_cd_kg: float = 0.0,
        pollutant_hg_kg: float = 0.0,
        pollutant_as_kg: float = 0.0,
        water_source: str = "central_water",  # central_water, cooling_recycling, natural_runoff, rural_domestic, hydropower
    ) -> Dict[str, Any]:
        """Calculate Environment Protection Fee for Wastewater under Decree 53/2020/NĐ-CP."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        wt = wastewater_type.lower().strip()
        ws = water_source.lower().strip()

        # Initial fee components
        base_fee_vnd = 0.0
        variable_fee_vnd = 0.0

        if wt == "domestic":
            # Domestic: 10% of clean water purchasing price before VAT
            # Total water cost = volume * price per m3
            total_water_cost = water_volume_m3 * clean_water_price_vnd
            variable_fee_vnd = total_water_cost * 0.10
            base_fee_vnd = 0.0
        else:
            # Industrial:
            # Fixed environmental protection fee is 1,500,000 VND/year.
            # Variable fee depends on pollutant load (kg)
            base_fee_vnd = 1500000.0
            # Calculate pollutant load costs
            variable_fee_vnd += pollutant_cod_kg * POLLUTANT_RATES["cod"]
            variable_fee_vnd += pollutant_tss_kg * POLLUTANT_RATES["tss"]
            variable_fee_vnd += pollutant_pb_kg * POLLUTANT_RATES["pb"]
            variable_fee_vnd += pollutant_cd_kg * POLLUTANT_RATES["cd"]
            variable_fee_vnd += pollutant_hg_kg * POLLUTANT_RATES["hg"]
            variable_fee_vnd += pollutant_as_kg * POLLUTANT_RATES["as_metal"]

        total_fee_vnd = base_fee_vnd + variable_fee_vnd

        # Evaluate Exemption Status
        is_exempt = False
        exemption_reason = ""
        effective_fee_vnd = total_fee_vnd

        if ws == "cooling_recycling":
            is_exempt = True
            effective_fee_vnd = 0.0
            exemption_reason = "100% Exemption for cooling water running through closed recycling systems with no direct chemical contact."
        elif ws == "natural_runoff":
            is_exempt = True
            effective_fee_vnd = 0.0
            exemption_reason = "100% Exemption for natural runoff and rainwater not collected inside industrial parks."
        elif ws == "rural_domestic":
            is_exempt = True
            effective_fee_vnd = 0.0
            exemption_reason = "100% Exemption for rural domestic water consumed by households where clean water is not centralized."
        elif ws == "hydropower":
            is_exempt = True
            effective_fee_vnd = 0.0
            exemption_reason = "100% Exemption for water running through hydro-power turbines for electricity generation."

        has_metals = (pollutant_pb_kg > 0 or pollutant_cd_kg > 0 or pollutant_hg_kg > 0 or pollutant_as_kg > 0)

        notes = (
            f"EPFW Calc: '{water_description}' ({wt} wastewater, source: {ws}). Volume: {water_volume_m3:.2f} m3. "
            f"Base: {base_fee_vnd:,.0f} VND. Variable: {variable_fee_vnd:,.0f} VND. "
            f"Total: {total_fee_vnd:,.0f} VND. Effective: {effective_fee_vnd:,.0f} VND. "
            f"Exempt: {is_exempt}."
        )
        if exemption_reason:
            notes += f" Reason: {exemption_reason}"

        cur.execute("""
            INSERT INTO epfw_calculations
                (water_description, wastewater_type, water_volume_m3, clean_water_price_vnd,
                 has_heavy_metals, pollutant_cod_kg, pollutant_tss_kg, pollutant_pb_kg,
                 pollutant_cd_kg, pollutant_hg_kg, pollutant_as_kg, base_fee_vnd,
                 variable_fee_vnd, total_fee_vnd, effective_fee_vnd, is_exempt,
                 exemption_reason, water_source, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (water_description, wt, water_volume_m3, clean_water_price_vnd,
              1 if has_metals else 0, pollutant_cod_kg, pollutant_tss_kg, pollutant_pb_kg,
              pollutant_cd_kg, pollutant_hg_kg, pollutant_as_kg, base_fee_vnd,
              variable_fee_vnd, total_fee_vnd, effective_fee_vnd,
              1 if is_exempt else 0, exemption_reason, ws, notes))
        conn.commit()

        last_id = cur.lastrowid
        conn.close()

        return {
            "id": last_id,
            "water_description": water_description,
            "wastewater_type": wt,
            "water_volume_m3": water_volume_m3,
            "clean_water_price_vnd": clean_water_price_vnd,
            "has_heavy_metals": has_metals,
            "pollutant_cod_kg": pollutant_cod_kg,
            "pollutant_tss_kg": pollutant_tss_kg,
            "pollutant_pb_kg": pollutant_pb_kg,
            "pollutant_cd_kg": pollutant_cd_kg,
            "pollutant_hg_kg": pollutant_hg_kg,
            "pollutant_as_kg": pollutant_as_kg,
            "base_fee_vnd": base_fee_vnd,
            "variable_fee_vnd": variable_fee_vnd,
            "total_fee_vnd": total_fee_vnd,
            "effective_fee_vnd": effective_fee_vnd,
            "is_exempt": is_exempt,
            "exemption_reason": exemption_reason,
            "water_source": ws,
            "notes": notes
        }

    def get_history(self, mst: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Return historical calculation logs for this tenant."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()
        cur.execute("""
            SELECT id, water_description, wastewater_type, water_volume_m3, clean_water_price_vnd,
                   has_heavy_metals, pollutant_cod_kg, pollutant_tss_kg, pollutant_pb_kg,
                   pollutant_cd_kg, pollutant_hg_kg, pollutant_as_kg, base_fee_vnd,
                   variable_fee_vnd, total_fee_vnd, effective_fee_vnd, is_exempt,
                   exemption_reason, water_source, notes, created_at
            FROM epfw_calculations
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        conn.close()

        return [dict(r) for r in rows]
