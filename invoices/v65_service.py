"""Extended Producer Responsibility (EPR) Recycling Fee Compliance Engine (v65.0.0).

Implements EPR recycling fee calculations, product categories, rates, cost coefficients,
and exemption thresholds under Decree 08/2022/NĐ-CP.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional
from invoices.multitenant_service import get_tenant_db_path

# Standard recycling rates (R) and cost coefficients (Fs - VND/kg) under Decree 08/2022/NĐ-CP
EPR_PRODUCT_CONFIGS = {
    "packaging_paper_carton": {"R": 0.15, "Fs": 2500.0},
    "packaging_plastic": {"R": 0.22, "Fs": 8000.0},
    "packaging_metal": {"R": 0.20, "Fs": 4000.0},
    "battery_lead_acid": {"R": 0.18, "Fs": 6000.0},
    "lubricant_oil": {"R": 0.10, "Fs": 5000.0},
    "electronic_appliances": {"R": 0.12, "Fs": 7000.0}
}

class V65ComplianceService:
    """Extended Producer Responsibility (EPR) compliance engine."""

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
            CREATE TABLE IF NOT EXISTS epr_calculations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_description TEXT NOT NULL,
                product_type TEXT NOT NULL,
                volume_kg REAL NOT NULL,
                recycling_rate REAL NOT NULL,
                cost_coefficient REAL NOT NULL,
                total_fee_vnd REAL NOT NULL,
                effective_fee_vnd REAL NOT NULL,
                is_exempt BOOLEAN NOT NULL DEFAULT 0,
                exemption_reason TEXT,
                exemption_category TEXT NOT NULL DEFAULT 'none',
                annual_revenue_vnd REAL NOT NULL,
                annual_import_vnd REAL NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        return conn

    def calculate_epr(
        self,
        mst: str,
        product_description: str,
        product_type: str,
        volume_kg: float,
        annual_revenue_vnd: float = 35000000000.0,
        annual_import_vnd: float = 25000000000.0,
        exemption_category: str = "none"  # none, small_scale_revenue, small_scale_import, closed_loop_recycling, export_only
    ) -> Dict[str, Any]:
        """Calculate EPR contribution under Decree 08/2022/NĐ-CP."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        pt = product_type.lower().strip()
        ec = exemption_category.lower().strip()

        # 1. Look up configurations
        cfg = EPR_PRODUCT_CONFIGS.get(pt, {"R": 0.10, "Fs": 3000.0})
        R = cfg["R"]
        Fs = cfg["Fs"]

        # 2. Formula: F = R * V * Fs
        total_fee_vnd = R * volume_kg * Fs

        # 3. Evaluate Exemption Status
        is_exempt = False
        exemption_reason = ""
        effective_fee_vnd = total_fee_vnd

        # Revenue threshold under 30 billion VND
        if annual_revenue_vnd < 30000000000.0 or ec == "small_scale_revenue":
            is_exempt = True
            effective_fee_vnd = 0.0
            exemption_reason = "100% Exemption: Small-scale enterprise with annual revenue below 30 billion VND threshold."
        # Import threshold under 20 billion VND
        elif annual_import_vnd < 20000000000.0 or ec == "small_scale_import":
            is_exempt = True
            effective_fee_vnd = 0.0
            exemption_reason = "100% Exemption: Small-scale importer with annual import value below 20 billion VND threshold."
        elif ec == "export_only":
            is_exempt = True
            effective_fee_vnd = 0.0
            exemption_reason = "100% Exemption: Products manufactured exclusively for export, exempt from domestic EPR recycling duties."
        elif ec == "closed_loop_recycling":
            is_exempt = True
            effective_fee_vnd = 0.0
            exemption_reason = "100% Exemption: Certified closed-loop self-recycling system meeting or exceeding mandatory rates."

        notes = (
            f"EPR Calc: '{product_description}' ({pt}, volume: {volume_kg:.2f} kg). "
            f"R: {R*100:.1f}%, Fs: {Fs:,.0f} VND/kg. "
            f"Total: {total_fee_vnd:,.0f} VND. Effective: {effective_fee_vnd:,.0f} VND. "
            f"Exempt: {is_exempt}."
        )
        if exemption_reason:
            notes += f" Reason: {exemption_reason}"

        cur.execute("""
            INSERT INTO epr_calculations
                (product_description, product_type, volume_kg, recycling_rate, cost_coefficient,
                 total_fee_vnd, effective_fee_vnd, is_exempt, exemption_reason, exemption_category,
                 annual_revenue_vnd, annual_import_vnd, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (product_description, pt, volume_kg, R, Fs,
              total_fee_vnd, effective_fee_vnd, 1 if is_exempt else 0, exemption_reason, ec,
              annual_revenue_vnd, annual_import_vnd, notes))
        conn.commit()

        last_id = cur.lastrowid
        conn.close()

        return {
            "id": last_id,
            "product_description": product_description,
            "product_type": pt,
            "volume_kg": volume_kg,
            "recycling_rate": R,
            "cost_coefficient": Fs,
            "total_fee_vnd": total_fee_vnd,
            "effective_fee_vnd": effective_fee_vnd,
            "is_exempt": is_exempt,
            "exemption_reason": exemption_reason,
            "exemption_category": ec,
            "annual_revenue_vnd": annual_revenue_vnd,
            "annual_import_vnd": annual_import_vnd,
            "notes": notes
        }

    def get_history(self, mst: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Return historical calculation logs for this tenant."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()
        cur.execute("""
            SELECT id, product_description, product_type, volume_kg, recycling_rate, cost_coefficient,
                   total_fee_vnd, effective_fee_vnd, is_exempt, exemption_reason, exemption_category,
                   annual_revenue_vnd, annual_import_vnd, notes, created_at
            FROM epr_calculations
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        conn.close()

        return [dict(r) for r in rows]
