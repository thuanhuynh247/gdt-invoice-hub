"""Ozone-Depleting Substances (ODS) Quotas & Fees Compliance Engine (v70.0.0).

Implements ODS licensing fee calculations, ODP scaling, and research/medical
use exemptions under Decree 06/2022/NĐ-CP.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, List
from invoices.multitenant_service import get_tenant_db_path

class V70ComplianceService:
    """Ozone-Depleting Substances (ODS) Decree 06/2022/NĐ-CP compliance engine."""

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
            CREATE TABLE IF NOT EXISTS ods_quota_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                substance_name TEXT NOT NULL,
                substance_group TEXT NOT NULL,
                weight_kg REAL NOT NULL,
                odp_factor REAL NOT NULL,
                odp_weight_eq REAL NOT NULL,
                license_charge_rate REAL NOT NULL,
                final_fee REAL NOT NULL,
                is_exempt BOOLEAN NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        return conn

    def calculate_ods(
        self, mst: str, substance_name: str, substance_group: str,
        weight_kg: float, exemption_category: str = "none"
    ) -> Dict[str, Any]:
        """Calculate ODS quota fee using weight and ODP equivalent, verify exemptions, and log transaction."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        group_key = substance_group.lower().strip()
        is_exempt = False
        notes_list = []

        # ODP factors and licensing fee rates per kg based on Decree 06/2022/NĐ-CP
        odp_factors = {
            "cfc": 1.0,
            "hcfc": 0.055,
            "hfc": 0.0,
            "halon": 10.0,
            "methyl_bromide": 0.6
        }
        license_charges = {
            "cfc": 250000.0,
            "hcfc": 15000.0,
            "hfc": 8000.0,
            "halon": 2500000.0,
            "methyl_bromide": 150000.0
        }

        odp_factor = odp_factors.get(group_key, 0.1)
        charge_rate = license_charges.get(group_key, 20000.0)

        odp_weight_eq = weight_kg * odp_factor

        # Exemption checks
        if exemption_category in ["laboratory_research", "medical_use"]:
            is_exempt = True
            final_fee = 0.0
            notes_list.append(f"Exempt: Import of {weight_kg:.2f} kg of {substance_name} certified for laboratory/medical application under Article 24.")
        elif exemption_category == "small_allocation" or (weight_kg < 50.0 and exemption_category == "none"):
            is_exempt = True
            final_fee = 0.0
            notes_list.append(f"Exempt: Low-volume ODS allocation ({weight_kg:.2f} kg) below 50 kg annual threshold.")
        else:
            final_fee = weight_kg * charge_rate
            notes_list.append(f"Quota fee calculated: Group '{substance_group}', substance '{substance_name}' with net weight {weight_kg:.2f} kg.")
            notes_list.append(f"ODP factor: {odp_factor:.3f} (ODP weight equivalent: {odp_weight_eq:.3f} ODP-kg).")
            notes_list.append(f"Licensing charge rate: {charge_rate:,.0f} VND/kg. Total fee: {final_fee:,.0f} VND.")

        notes = " ".join(notes_list)

        cur.execute("""
            INSERT INTO ods_quota_logs
                (substance_name, substance_group, weight_kg, odp_factor, odp_weight_eq, license_charge_rate, final_fee, is_exempt, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (substance_name, substance_group, weight_kg, odp_factor, odp_weight_eq, charge_rate, final_fee, is_exempt, notes))

        conn.commit()
        conn.close()

        return {
            "substance_name": substance_name,
            "substance_group": substance_group,
            "weight_kg": weight_kg,
            "odp_factor": odp_factor,
            "odp_weight_eq": odp_weight_eq,
            "license_charge_rate": charge_rate,
            "final_fee": final_fee,
            "is_exempt": is_exempt,
            "notes": notes
        }

    def get_history(self, mst: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent ODS quota logs."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()
        cur.execute("SELECT * FROM ods_quota_logs ORDER BY id DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
