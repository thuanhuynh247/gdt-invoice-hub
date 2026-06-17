"""Hazardous Waste Management & Disposal Surcharge Compliance Engine (v73.0.0).

Implements licensing and category weight-based disposal fee calculations,
small generator exclusions (< 600 kg/year), and research lab exemptions under Decree 08/2022/NĐ-CP.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, List
from invoices.multitenant_service import get_tenant_db_path

class V73ComplianceService:
    """Hazardous Waste Decree 08/2022/NĐ-CP compliance engine."""

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
            CREATE TABLE IF NOT EXISTS hazardous_waste_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                waste_category TEXT NOT NULL,
                weight_kg REAL NOT NULL,
                apply_license BOOLEAN NOT NULL,
                annual_weight_kg REAL NOT NULL,
                is_research_lab BOOLEAN NOT NULL,
                license_fee REAL NOT NULL,
                disposal_fee REAL NOT NULL,
                final_fee REAL NOT NULL,
                is_exempt BOOLEAN NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        return conn

    def calculate_hazardous_waste(
        self, mst: str, waste_category: str, weight_kg: float,
        apply_license: bool = False, annual_weight_kg: float = 0.0,
        is_research_lab: bool = False
    ) -> Dict[str, Any]:
        """Calculate hazardous waste licensing and disposal fees, apply exemptions, and log."""
        if weight_kg < 0 or annual_weight_kg < 0:
            raise ValueError("Weights must be non-negative.")

        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        cat_key = waste_category.lower().strip()
        notes_list = []

        # Disposal fee rates (Decree 08/2022/NĐ-CP)
        disposal_rates = {
            "category_a": 2000.0,  # VND/kg
            "category_b": 5000.0   # VND/kg
        }

        if cat_key not in disposal_rates:
            conn.close()
            raise ValueError(f"Invalid waste category. Must be one of: {list(disposal_rates.keys())}")

        disposal_rate = disposal_rates[cat_key]
        disposal_fee = weight_kg * disposal_rate

        # Base licensing fee
        base_license_fee = 5000000.0 if apply_license else 0.0
        license_fee = base_license_fee
        is_exempt = False

        # Exemption checks for licensing fee
        if apply_license:
            if is_research_lab:
                license_fee = 0.0
                is_exempt = True
                notes_list.append("Licensing Fee Exempt: Certified academic/research laboratory waste.")
            elif annual_weight_kg > 0 and annual_weight_kg < 600.0:
                license_fee = 0.0
                is_exempt = True
                notes_list.append(f"Licensing Fee Exempt: Small generator status (annual weight {annual_weight_kg:.2f} kg < 600 kg).")

        final_fee = license_fee + disposal_fee

        notes_list.append(f"Calculated: category '{waste_category}', disposal weight {weight_kg:.2f} kg.")
        notes_list.append(f"Disposal fee: {disposal_fee:,.0f} VND (Rate: {disposal_rate:,.0f} VND/kg).")
        if apply_license:
            notes_list.append(f"Licensing fee: {license_fee:,.0f} VND (Base: {base_license_fee:,.0f} VND).")
        notes_list.append(f"Total fee: {final_fee:,.0f} VND.")

        notes = " ".join(notes_list)

        cur.execute("""
            INSERT INTO hazardous_waste_logs
                (waste_category, weight_kg, apply_license, annual_weight_kg, is_research_lab, license_fee, disposal_fee, final_fee, is_exempt, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (waste_category, weight_kg, apply_license, annual_weight_kg, is_research_lab, license_fee, disposal_fee, final_fee, is_exempt, notes))

        conn.commit()
        conn.close()

        return {
            "waste_category": waste_category,
            "weight_kg": weight_kg,
            "apply_license": apply_license,
            "annual_weight_kg": annual_weight_kg,
            "is_research_lab": is_research_lab,
            "license_fee": license_fee,
            "disposal_fee": disposal_fee,
            "final_fee": final_fee,
            "is_exempt": is_exempt,
            "notes": notes
        }

    def get_history(self, mst: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent hazardous waste logs."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()
        cur.execute("SELECT * FROM hazardous_waste_logs ORDER BY id DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
