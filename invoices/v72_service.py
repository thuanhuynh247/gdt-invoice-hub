"""Industrial Wastewater Treatment Surcharge Compliance Engine (v72.0.0).

Implements pollutant load-based and flat-rate wastewater calculations,
cooling water loops, and centralized sewer treatment exemptions under Decree 53/2020/NĐ-CP.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, List
from invoices.multitenant_service import get_tenant_db_path

class V72ComplianceService:
    """Industrial Wastewater Surcharge Decree 53/2020/NĐ-CP compliance engine."""

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
            CREATE TABLE IF NOT EXISTS wastewater_surcharge_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                volume_m3 REAL NOT NULL,
                cod_mg_l REAL NOT NULL,
                tss_mg_l REAL NOT NULL,
                pb_mg_l REAL NOT NULL,
                hg_mg_l REAL NOT NULL,
                cd_mg_l REAL NOT NULL,
                cooling_water BOOLEAN NOT NULL,
                municipal_treatment_inflow BOOLEAN NOT NULL,
                gross_fee REAL NOT NULL,
                final_fee REAL NOT NULL,
                is_exempt BOOLEAN NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        return conn

    def calculate_surcharge(
        self, mst: str, volume_m3: float, cod_mg_l: float, tss_mg_l: float,
        pb_mg_l: float = 0.0, hg_mg_l: float = 0.0, cd_mg_l: float = 0.0,
        cooling_water: bool = False, municipal_treatment_inflow: bool = False
    ) -> Dict[str, Any]:
        """Calculate quarterly wastewater fee based on pollutants and volume, apply exemptions, and log."""
        if volume_m3 < 0 or cod_mg_l < 0 or tss_mg_l < 0 or pb_mg_l < 0 or hg_mg_l < 0 or cd_mg_l < 0:
            raise ValueError("All volumes and concentration metrics must be non-negative.")

        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        is_exempt = cooling_water or municipal_treatment_inflow
        notes_list = []

        # Pricing rates (Decree 53/2020/NĐ-CP)
        # Flat quarterly charge: 375,000 VND (representing 1.5M per year for < 20 m3/day average)
        # Average daily volume = total volume / 90 days.
        daily_avg_volume = volume_m3 / 90.0

        if daily_avg_volume < 20.0:
            # Small generator flat fee
            gross_fee = 375000.0
            fee_type = "flat_rate"
            notes_list.append(f"Flat rate applied for low-discharge facility (average {daily_avg_volume:.2f} m3/day < 20 m3/day).")
        else:
            # Pollutant load calculations: load_kg = volume_m3 * concentration_mg_l / 1000
            cod_load = volume_m3 * cod_mg_l / 1000.0
            tss_load = volume_m3 * tss_mg_l / 1000.0
            pb_load = volume_m3 * pb_mg_l / 1000.0
            hg_load = volume_m3 * hg_mg_l / 1000.0
            cd_load = volume_m3 * cd_mg_l / 1000.0

            cod_fee = cod_load * 2000.0
            tss_fee = tss_load * 4000.0
            pb_fee = pb_load * 1000000.0
            hg_fee = hg_load * 20000000.0
            cd_fee = cd_load * 10000000.0

            gross_fee = cod_fee + tss_fee + pb_fee + hg_fee + cd_fee
            fee_type = "pollutant_load"
            notes_list.append(f"Load fees: COD ({cod_fee:,.0f} VND), TSS ({tss_fee:,.0f} VND), Heavy Metals ({pb_fee + hg_fee + cd_fee:,.0f} VND).")

        if is_exempt:
            final_fee = 0.0
            ex_reason = "cooling loops" if cooling_water else "centralized sewage sewer connection"
            notes_list.append(f"Exempt: Surcharge waived (Reason: {ex_reason}).")
        else:
            final_fee = gross_fee

        notes = " ".join(notes_list)

        cur.execute("""
            INSERT INTO wastewater_surcharge_logs
                (volume_m3, cod_mg_l, tss_mg_l, pb_mg_l, hg_mg_l, cd_mg_l, cooling_water, municipal_treatment_inflow, gross_fee, final_fee, is_exempt, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (volume_m3, cod_mg_l, tss_mg_l, pb_mg_l, hg_mg_l, cd_mg_l, cooling_water, municipal_treatment_inflow, gross_fee, final_fee, is_exempt, notes))

        conn.commit()
        conn.close()

        return {
            "volume_m3": volume_m3,
            "cod_mg_l": cod_mg_l,
            "tss_mg_l": tss_mg_l,
            "pb_mg_l": pb_mg_l,
            "hg_mg_l": hg_mg_l,
            "cd_mg_l": cd_mg_l,
            "cooling_water": cooling_water,
            "municipal_treatment_inflow": municipal_treatment_inflow,
            "gross_fee": gross_fee,
            "final_fee": final_fee,
            "is_exempt": is_exempt,
            "notes": notes
        }

    def get_history(self, mst: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent wastewater logs."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()
        cur.execute("SELECT * FROM wastewater_surcharge_logs ORDER BY id DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
