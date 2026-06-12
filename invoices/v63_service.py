"""Environment Protection Fee for Mineral Extraction (EPFME) Compliance Engine (v63.0.0).

Implements mineral extraction fee calculations, salvage exploitation rates, and exemptions
under Decree 27/2023/NĐ-CP.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional
from invoices.multitenant_service import get_tenant_db_path

# Standard fee rates per mineral under Decree 27/2023/NĐ-CP (VND)
MINERAL_RATES_EPFME = {
    "crude_oil": 100000.0,       # per tonne
    "natural_gas": 50.0,        # per m3
    "associated_gas": 35.0,     # per m3
    "building_stone": 7500.0,    # per m3
    "brick_clay": 2250.0        # per m3
}

class V63ComplianceService:
    """Environment Protection Fee for Mineral Extraction (EPFME) compliance engine."""

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
            CREATE TABLE IF NOT EXISTS epfme_calculations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mineral_description TEXT NOT NULL,
                mineral_type TEXT NOT NULL,
                volume REAL NOT NULL,
                is_salvage BOOLEAN NOT NULL DEFAULT 0,
                base_rate REAL NOT NULL,
                applied_rate REAL NOT NULL,
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

    def calculate_epfme(
        self,
        mst: str,
        mineral_description: str,
        mineral_type: str,  # crude_oil, natural_gas, associated_gas, building_stone, brick_clay
        volume: float,
        is_salvage: bool = False,
        exemption_category: str = "none"  # none, household_building, security_military_disaster, environmental_reclamation
    ) -> Dict[str, Any]:
        """Calculate Environment Protection Fee for Mineral Extraction under Decree 27/2023/NĐ-CP."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        mt = mineral_type.lower().strip()
        ec = exemption_category.lower().strip()

        # 1. Look up base rate
        base_rate = MINERAL_RATES_EPFME.get(mt, 0.0)

        # 2. Check salvage reduction: 60% of base rate
        applied_rate = base_rate
        if is_salvage:
            applied_rate = base_rate * 0.60

        total_fee_vnd = volume * applied_rate

        # 3. Evaluate Exemption Status
        is_exempt = False
        exemption_reason = ""
        effective_fee_vnd = total_fee_vnd

        if ec == "household_building":
            is_exempt = True
            effective_fee_vnd = 0.0
            exemption_reason = "100% Exemption: Household mineral extraction for personal residential construction on their own land."
        elif ec == "security_military_disaster":
            is_exempt = True
            effective_fee_vnd = 0.0
            exemption_reason = "100% Exemption: Soil/stone extracted for military, security, or natural disaster relief."
        elif ec == "environmental_reclamation":
            is_exempt = True
            effective_fee_vnd = 0.0
            exemption_reason = "100% Exemption: Waste/soil returned for site reclamation and environmental restoration under approved plans."

        notes = (
            f"EPFME Calc: '{mineral_description}' ({mt}, volume: {volume:.2f}, salvage: {is_salvage}). "
            f"Base Rate: {base_rate:,.0f} VND. Applied Rate: {applied_rate:,.2f} VND. "
            f"Total: {total_fee_vnd:,.0f} VND. Effective: {effective_fee_vnd:,.0f} VND. "
            f"Exempt: {is_exempt}."
        )
        if exemption_reason:
            notes += f" Reason: {exemption_reason}"

        cur.execute("""
            INSERT INTO epfme_calculations
                (mineral_description, mineral_type, volume, is_salvage, base_rate, applied_rate,
                 total_fee_vnd, effective_fee_vnd, is_exempt, exemption_reason, exemption_category, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (mineral_description, mt, volume, 1 if is_salvage else 0, base_rate, applied_rate,
              total_fee_vnd, effective_fee_vnd, 1 if is_exempt else 0, exemption_reason, ec, notes))
        conn.commit()

        last_id = cur.lastrowid
        conn.close()

        return {
            "id": last_id,
            "mineral_description": mineral_description,
            "mineral_type": mt,
            "volume": volume,
            "is_salvage": is_salvage,
            "base_rate": base_rate,
            "applied_rate": applied_rate,
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
            SELECT id, mineral_description, mineral_type, volume, is_salvage, base_rate, applied_rate,
                   total_fee_vnd, effective_fee_vnd, is_exempt, exemption_reason, exemption_category, notes, created_at
            FROM epfme_calculations
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        conn.close()

        return [dict(r) for r in rows]
