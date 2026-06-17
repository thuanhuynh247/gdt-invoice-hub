"""Biodiversity Offset & Conservation Fee Compliance Engine (v68.0.0).

Implements biodiversity conservation fee calculations, ecosystem tier rates,
offset credits, impact multipliers, and exemptions under the Law on Biodiversity 2008.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, List
from invoices.multitenant_service import get_tenant_db_path

class V68ComplianceService:
    """Biodiversity Offset & Conservation Fee Law on Biodiversity 2008 compliance engine."""

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
            CREATE TABLE IF NOT EXISTS biodiversity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_name TEXT NOT NULL,
                ecosystem_type TEXT NOT NULL,
                impact_area_ha REAL NOT NULL,
                impact_rating TEXT NOT NULL,
                has_offset_plan BOOLEAN NOT NULL,
                base_rate_per_ha REAL NOT NULL,
                final_fee REAL NOT NULL,
                is_exempt BOOLEAN NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        return conn

    def calculate_biodiversity(
        self, mst: str, project_name: str, ecosystem_type: str,
        impact_area_ha: float, impact_rating: str = "medium",
        has_offset_plan: bool = False, exemption_category: str = "none"
    ) -> Dict[str, Any]:
        """Calculate biodiversity conservation fee, apply impact multipliers and offset reductions, and log transaction."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        eco_key = ecosystem_type.lower().strip()
        is_exempt = False
        notes_list = []

        # Standard rates per hectare
        rates = {
            "national_park": 250000000.0,
            "nature_reserve": 180000000.0,
            "species_habitat": 120000000.0,
            "landscape_protected": 80000000.0
        }
        base_rate = rates.get(eco_key, 50000000.0) # default fallback

        # Multipliers
        multiplier = 1.0
        if impact_rating.lower().strip() == "high":
            multiplier *= 1.5
        elif impact_rating.lower().strip() == "low":
            multiplier *= 0.8

        # Offset reduction
        if has_offset_plan:
            multiplier *= 0.6  # 40% discount for implementing certified offset programs

        # Exemption checks
        if exemption_category == "national_defense":
            is_exempt = True
            final_fee = 0.0
            notes_list.append("Exempt: Infrastructure project designated for national defense/security inside protected zones (exempt under Law on Biodiversity).")
        elif exemption_category == "household_agro" and impact_area_ha < 0.5:
            is_exempt = True
            final_fee = 0.0
            notes_list.append(f"Exempt: Small sustainable household forestry/agro project ({impact_area_ha:.2f} ha) under 0.5 ha threshold.")
        else:
            final_fee = impact_area_ha * base_rate * multiplier
            notes_list.append(f"Fee calculated: Ecosystem '{ecosystem_type}' with impact area {impact_area_ha:.2f} ha. Base rate: {base_rate:,.0f} VND/ha.")
            notes_list.append(f"Multiplier applied: {multiplier:.2f} (impact rating: {impact_rating}, offset plan: {has_offset_plan}).")
            notes_list.append(f"Total conservation fee: {final_fee:,.0f} VND.")

        notes = " ".join(notes_list)

        cur.execute("""
            INSERT INTO biodiversity_logs
                (project_name, ecosystem_type, impact_area_ha, impact_rating, has_offset_plan, base_rate_per_ha, final_fee, is_exempt, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (project_name, ecosystem_type, impact_area_ha, impact_rating, has_offset_plan, base_rate, final_fee, is_exempt, notes))

        conn.commit()
        conn.close()

        return {
            "project_name": project_name,
            "ecosystem_type": ecosystem_type,
            "impact_area_ha": impact_area_ha,
            "impact_rating": impact_rating,
            "has_offset_plan": has_offset_plan,
            "base_rate_per_ha": base_rate,
            "final_fee": final_fee,
            "is_exempt": is_exempt,
            "notes": notes
        }

    def get_history(self, mst: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent biodiversity conservation logs."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()
        cur.execute("SELECT * FROM biodiversity_logs ORDER BY id DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
