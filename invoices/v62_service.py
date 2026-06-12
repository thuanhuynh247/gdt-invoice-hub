"""Environment Protection Fee for Emissions (EPFE) Compliance Engine (v62.0.0).

Implements industrial emissions fee calculations, pollutants surcharge, and exemptions
under Decree 153/2024/NĐ-CP.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional
from invoices.multitenant_service import get_tenant_db_path

# Variable fee rates per pollutant under Decree 153/2024/NĐ-CP (VND per kg)
# Note: 800 VND/tonne = 0.8 VND/kg, 700 VND/tonne = 0.7 VND/kg, 500 VND/tonne = 0.5 VND/kg
POLLUTANT_RATES_EPFE = {
    "dust": 0.8,
    "nox": 0.8,
    "sox": 0.7,
    "co": 0.5
}

class V62ComplianceService:
    """Environment Protection Fee for Emissions (EPFE) compliance engine."""

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
            CREATE TABLE IF NOT EXISTS epfe_calculations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                emission_description TEXT NOT NULL,
                facility_type TEXT NOT NULL,
                period TEXT NOT NULL,
                is_subject_to_monitoring BOOLEAN NOT NULL DEFAULT 1,
                pollutant_dust_kg REAL DEFAULT 0,
                pollutant_nox_kg REAL DEFAULT 0,
                pollutant_sox_kg REAL DEFAULT 0,
                pollutant_co_kg REAL DEFAULT 0,
                base_fee_vnd REAL NOT NULL,
                variable_fee_vnd REAL NOT NULL,
                total_fee_vnd REAL NOT NULL,
                effective_fee_vnd REAL NOT NULL,
                is_exempt BOOLEAN NOT NULL DEFAULT 0,
                exemption_reason TEXT,
                exemption_category TEXT NOT NULL DEFAULT 'none',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        return conn

    def calculate_epfe(
        self,
        mst: str,
        emission_description: str,
        facility_type: str = "general_industrial",
        period: str = "annual",  # annual or quarterly
        is_subject_to_monitoring: bool = True,
        pollutant_dust_kg: float = 0.0,
        pollutant_nox_kg: float = 0.0,
        pollutant_sox_kg: float = 0.0,
        pollutant_co_kg: float = 0.0,
        exemption_category: str = "none",  # none, out_of_scope, zero_emissions, coop_welfare
    ) -> Dict[str, Any]:
        """Calculate Environment Protection Fee for Emissions under Decree 153/2024/NĐ-CP."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        ft = facility_type.lower().strip()
        pd = period.lower().strip()
        ec = exemption_category.lower().strip()

        # 1. Base fixed fee: 3,000,000 VND/year (or 750,000 VND/quarter)
        if pd == "quarterly" or pd == "quarter":
            base_fee_vnd = 750000.0
        else:
            base_fee_vnd = 3000000.0

        # 2. Variable fee is computed only if the facility is subject to monitoring
        variable_fee_vnd = 0.0
        if is_subject_to_monitoring:
            variable_fee_vnd += pollutant_dust_kg * POLLUTANT_RATES_EPFE["dust"]
            variable_fee_vnd += pollutant_nox_kg * POLLUTANT_RATES_EPFE["nox"]
            variable_fee_vnd += pollutant_sox_kg * POLLUTANT_RATES_EPFE["sox"]
            variable_fee_vnd += pollutant_co_kg * POLLUTANT_RATES_EPFE["co"]

        total_fee_vnd = base_fee_vnd + variable_fee_vnd

        # 3. Evaluate Exemption Status
        is_exempt = False
        exemption_reason = ""
        effective_fee_vnd = total_fee_vnd

        if ec == "out_of_scope":
            is_exempt = True
            effective_fee_vnd = 0.0
            exemption_reason = "100% Exemption: Small business/household operation out of scope of environmental permit."
        elif ec == "zero_emissions":
            is_exempt = True
            effective_fee_vnd = 0.0
            exemption_reason = "100% Exemption: Certified zero-emission clean technology implementation."
        elif ec == "coop_welfare":
            is_exempt = True
            effective_fee_vnd = 0.0
            exemption_reason = "100% Exemption: Local community public welfare facility subsidized by People's Committee."

        notes = (
            f"EPFE Calc: '{emission_description}' ({ft} facility, period: {pd}, monitoring: {is_subject_to_monitoring}). "
            f"Base: {base_fee_vnd:,.0f} VND. Variable: {variable_fee_vnd:,.0f} VND. "
            f"Total: {total_fee_vnd:,.0f} VND. Effective: {effective_fee_vnd:,.0f} VND. "
            f"Exempt: {is_exempt}."
        )
        if exemption_reason:
            notes += f" Reason: {exemption_reason}"

        cur.execute("""
            INSERT INTO epfe_calculations
                (emission_description, facility_type, period, is_subject_to_monitoring,
                 pollutant_dust_kg, pollutant_nox_kg, pollutant_sox_kg, pollutant_co_kg,
                 base_fee_vnd, variable_fee_vnd, total_fee_vnd, effective_fee_vnd,
                 is_exempt, exemption_reason, exemption_category, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (emission_description, ft, pd, 1 if is_subject_to_monitoring else 0,
              pollutant_dust_kg, pollutant_nox_kg, pollutant_sox_kg, pollutant_co_kg,
              base_fee_vnd, variable_fee_vnd, total_fee_vnd, effective_fee_vnd,
              1 if is_exempt else 0, exemption_reason, ec, notes))
        conn.commit()

        last_id = cur.lastrowid
        conn.close()

        return {
            "id": last_id,
            "emission_description": emission_description,
            "facility_type": ft,
            "period": pd,
            "is_subject_to_monitoring": is_subject_to_monitoring,
            "pollutant_dust_kg": pollutant_dust_kg,
            "pollutant_nox_kg": pollutant_nox_kg,
            "pollutant_sox_kg": pollutant_sox_kg,
            "pollutant_co_kg": pollutant_co_kg,
            "base_fee_vnd": base_fee_vnd,
            "variable_fee_vnd": variable_fee_vnd,
            "total_fee_vnd": total_fee_vnd,
            "effective_fee_vnd": effective_fee_vnd,
            "is_exempt": is_exempt,
            "exemption_reason": exemption_reason,
            "exemption_category": ec,
            "notes": notes
        }

    def get_history(self, mst: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Return historical calculation logs for this tenant."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()
        cur.execute("""
            SELECT id, emission_description, facility_type, period, is_subject_to_monitoring,
                   pollutant_dust_kg, pollutant_nox_kg, pollutant_sox_kg, pollutant_co_kg,
                   base_fee_vnd, variable_fee_vnd, total_fee_vnd, effective_fee_vnd,
                   is_exempt, exemption_reason, exemption_category, notes, created_at
            FROM epfe_calculations
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        conn.close()

        return [dict(r) for r in rows]
