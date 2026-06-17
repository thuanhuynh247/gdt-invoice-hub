"""Environment Protection Fee for Solid Waste (EPFSW) Compliance Engine (v64.0.0).

Implements solid waste protection fee calculations, waste categories, and exemptions
under Decree 164/2016/NĐ-CP.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional
from invoices.multitenant_service import get_tenant_db_path

# Standard fee rates per solid waste type under Decree 164/2016/NĐ-CP (VND/tonne)
SOLID_WASTE_RATES_EPFSW = {
    "hazardous_waste": 100000.0,
    "ordinary_waste_industry": 40000.0,
    "ordinary_waste_construction": 30000.0,
    "ordinary_waste_others": 20000.0
}

class V64ComplianceService:
    """Environment Protection Fee for Solid Waste (EPFSW) compliance engine."""

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
            CREATE TABLE IF NOT EXISTS epfsw_calculations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                waste_description TEXT NOT NULL,
                waste_type TEXT NOT NULL,
                volume_tonnes REAL NOT NULL,
                base_rate REAL NOT NULL,
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

    def calculate_epfsw(
        self,
        mst: str,
        waste_description: str,
        waste_type: str,  # hazardous_waste, ordinary_waste_industry, ordinary_waste_construction, ordinary_waste_others
        volume_tonnes: float,
        exemption_category: str = "none"  # none, self_recycled, agricultural_byproduct, domestic_rural
    ) -> Dict[str, Any]:
        """Calculate Environment Protection Fee for Solid Waste under Decree 164/2016/NĐ-CP."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        wt = waste_type.lower().strip()
        ec = exemption_category.lower().strip()

        # 1. Look up base rate
        base_rate = SOLID_WASTE_RATES_EPFSW.get(wt, 0.0)
        total_fee_vnd = volume_tonnes * base_rate

        # 2. Evaluate Exemption Status
        is_exempt = False
        exemption_reason = ""
        effective_fee_vnd = total_fee_vnd

        if ec == "self_recycled":
            is_exempt = True
            effective_fee_vnd = 0.0
            exemption_reason = "100% Exemption: Solid waste recycled or reused directly within the generating facility's production cycle."
        elif ec == "agricultural_byproduct":
            is_exempt = True
            effective_fee_vnd = 0.0
            exemption_reason = "100% Exemption: Agricultural byproducts used in farming, livestock feed, or composting."
        elif ec == "domestic_rural":
            is_exempt = True
            effective_fee_vnd = 0.0
            exemption_reason = "100% Exemption: Domestic waste from certified rural households."

        notes = (
            f"EPFSW Calc: '{waste_description}' ({wt}, volume: {volume_tonnes:.2f} tonnes). "
            f"Base Rate: {base_rate:,.0f} VND/tonne. "
            f"Total: {total_fee_vnd:,.0f} VND. Effective: {effective_fee_vnd:,.0f} VND. "
            f"Exempt: {is_exempt}."
        )
        if exemption_reason:
            notes += f" Reason: {exemption_reason}"

        cur.execute("""
            INSERT INTO epfsw_calculations
                (waste_description, waste_type, volume_tonnes, base_rate,
                 total_fee_vnd, effective_fee_vnd, is_exempt, exemption_reason, exemption_category, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (waste_description, wt, volume_tonnes, base_rate,
              total_fee_vnd, effective_fee_vnd, 1 if is_exempt else 0, exemption_reason, ec, notes))
        conn.commit()

        last_id = cur.lastrowid
        conn.close()

        return {
            "id": last_id,
            "waste_description": waste_description,
            "waste_type": wt,
            "volume_tonnes": volume_tonnes,
            "base_rate": base_rate,
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
            SELECT id, waste_description, waste_type, volume_tonnes, base_rate,
                   total_fee_vnd, effective_fee_vnd, is_exempt, exemption_reason, exemption_category, notes, created_at
            FROM epfsw_calculations
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        conn.close()

        return [dict(r) for r in rows]
