"""Agricultural Land Use Tax (ALUT) Compliance Engine (v60.0.0).

Implements Agricultural Land Use Tax (Thuế sử dụng đất nông nghiệp) calculations,
rates, and exemptions under Law on Agricultural Land Use Tax 1993 and
Resolutions 55/2010/QH12, 107/2015/QH13, and 117/2020/QH14.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional
from invoices.multitenant_service import get_tenant_db_path

# Standard rates in kg of paddy rice per hectare per year
ANNUAL_CROP_RATES = {
    1: 550.0,
    2: 460.0,
    3: 370.0,
    4: 280.0,
    5: 180.0,
    6: 50.0
}

PERENNIAL_CROP_RATES = {
    1: 650.0,
    2: 550.0,
    3: 400.0,
    4: 300.0,
    5: 200.0
}

class V60ComplianceService:
    """Agricultural Land Use Tax (Thuế sử dụng đất nông nghiệp) compliance engine."""

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
            CREATE TABLE IF NOT EXISTS alut_calculations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                land_description TEXT NOT NULL,
                land_grade INTEGER NOT NULL,
                crop_type TEXT NOT NULL,
                area_ha REAL NOT NULL,
                rice_price_per_kg REAL NOT NULL DEFAULT 8000,
                standard_rice_rate_kg REAL NOT NULL,
                tax_amount_rice REAL NOT NULL,
                tax_amount_vnd REAL NOT NULL,
                effective_amount_vnd REAL NOT NULL,
                is_exempt BOOLEAN NOT NULL DEFAULT 0,
                exemption_reason TEXT,
                producer_type TEXT NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        return conn

    def calculate_alut(
        self,
        mst: str,
        land_description: str,
        land_grade: int,
        crop_type: str,
        area_ha: float,
        producer_type: str = "household",  # household, cooperative, research, state_org, general_org
        rice_price_per_kg: float = 8000.0
    ) -> Dict[str, Any]:
        """Calculate Agricultural Land Use Tax based on land grade, crop type, and producer category."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        # Sanitize crop type
        ct = crop_type.lower().strip()
        if "perennial" in ct:
            ct = "perennial"
            rate_table = PERENNIAL_CROP_RATES
            # Bound grade for perennials
            grade = max(1, min(land_grade, 5))
        else:
            ct = "annual"
            rate_table = ANNUAL_CROP_RATES
            grade = max(1, min(land_grade, 6))

        # Get rate in kg of rice per hectare
        standard_rice_rate_kg = rate_table.get(grade, 0.0)
        tax_amount_rice = standard_rice_rate_kg * area_ha
        tax_amount_vnd = tax_amount_rice * rice_price_per_kg

        # Evaluate exemptions under Resolution 117/2020/QH14 extending to 2025
        is_exempt = False
        exemption_reason = ""
        effective_amount_vnd = tax_amount_vnd

        pt = producer_type.lower().strip()
        if pt in ["household", "individual", "farmer"]:
            is_exempt = True
            effective_amount_vnd = 0.0
            exemption_reason = "100% Exemption for households and individual farmers under Resolution 117/2020/QH14."
        elif pt in ["cooperative", "agricultural_cooperative"]:
            is_exempt = True
            effective_amount_vnd = 0.0
            exemption_reason = "100% Exemption for agricultural cooperatives under Resolution 117/2020/QH14."
        elif pt in ["research", "education", "experimental_farm"]:
            is_exempt = True
            effective_amount_vnd = 0.0
            exemption_reason = "100% Exemption for educational, research, and experimental farms."
        elif pt in ["state_org", "state_enterprise"]:
            # 50% reduction for certain state agricultural enterprises
            is_exempt = True
            effective_amount_vnd = tax_amount_vnd * 0.50
            exemption_reason = "50% Reduction for State-owned agricultural enterprises using land for approved research/production."
        else:
            # General organizations using agricultural land for other purposes
            is_exempt = False
            effective_amount_vnd = tax_amount_vnd
            exemption_reason = "No waiver: General organization subject to standard rates."

        notes = (
            f"ALUT Calc: '{land_description}' ({ct} crop land, Grade {grade}). Area: {area_ha:.2f} ha. "
            f"Rate: {standard_rice_rate_kg:.0f} kg rice/ha at {rice_price_per_kg:,.0f} VND/kg. "
            f"Standard tax: {tax_amount_vnd:,.0f} VND. Effective tax: {effective_amount_vnd:,.0f} VND. "
            f"Exempt: {is_exempt} ({pt})."
        )
        if exemption_reason:
            notes += f" Reason: {exemption_reason}"

        cur.execute("""
            INSERT INTO alut_calculations
                (land_description, land_grade, crop_type, area_ha, rice_price_per_kg,
                 standard_rice_rate_kg, tax_amount_rice, tax_amount_vnd, effective_amount_vnd,
                 is_exempt, exemption_reason, producer_type, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (land_description, grade, ct, area_ha, rice_price_per_kg,
              standard_rice_rate_kg, tax_amount_rice, tax_amount_vnd, effective_amount_vnd,
              is_exempt, exemption_reason, producer_type, notes))
        conn.commit()

        last_id = cur.lastrowid
        conn.close()

        return {
            "id": last_id,
            "land_description": land_description,
            "land_grade": grade,
            "crop_type": ct,
            "area_ha": area_ha,
            "rice_price_per_kg": rice_price_per_kg,
            "standard_rice_rate_kg": standard_rice_rate_kg,
            "tax_amount_rice": tax_amount_rice,
            "tax_amount_vnd": tax_amount_vnd,
            "effective_amount_vnd": effective_amount_vnd,
            "is_exempt": is_exempt,
            "exemption_reason": exemption_reason,
            "producer_type": producer_type,
            "notes": notes
        }

    def get_history(self, mst: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Return historical calculation logs for this tenant."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()
        cur.execute("""
            SELECT id, land_description, land_grade, crop_type, area_ha, rice_price_per_kg,
                   standard_rice_rate_kg, tax_amount_rice, tax_amount_vnd, effective_amount_vnd,
                   is_exempt, exemption_reason, producer_type, notes, created_at
            FROM alut_calculations
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        conn.close()

        return [dict(r) for r in rows]
