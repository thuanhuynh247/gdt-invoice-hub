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

    def get_cumulative_annual_weight(self, mst: str, year: int | None = None) -> float:
        """Returns cumulative ODS weight imported in the given calendar year (default current year)."""
        if year is None:
            year = datetime.now().year
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()
        try:
            # Under SQLite, check if strftime('%Y', created_at) matches the year
            cur.execute("""
                SELECT SUM(weight_kg) FROM ods_quota_logs
                WHERE strftime('%Y', created_at) = ? AND is_exempt = 0
            """, (str(year),))
            row = cur.fetchone()
            total = row[0] if row and row[0] is not None else 0.0
        except Exception:
            total = 0.0
        finally:
            conn.close()
        return total

    def calculate_ods(
        self, mst: str, substance_name: str, substance_group: str,
        weight_kg: float, exemption_category: str = "none", save_to_db: bool = True
    ) -> Dict[str, Any]:
        """Calculate ODS quota fee using weight and ODP equivalent, verify exemptions, check cumulative annual limits, and log transaction."""
        group_key = substance_group.lower().strip()
        is_exempt = False
        notes_list = []
        warning_msg = None

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

        # 1. Fetch cumulative annual imports to verify the low-volume threshold
        current_year = datetime.now().year
        prev_cumulative = self.get_cumulative_annual_weight(mst, current_year)
        total_cumulative = prev_cumulative + weight_kg

        # Exemption checks
        if exemption_category in ["laboratory_research", "medical_use", "research_study"]:
            is_exempt = True
            final_fee = 0.0
            notes_list.append(f"Exempt: Import of {weight_kg:.2f} kg of {substance_name} certified for laboratory/medical application under Article 24.")
        elif exemption_category == "low_volume_waiver" or exemption_category == "small_allocation" or (weight_kg < 50.0 and exemption_category == "none"):
            # Check cumulative threshold! If the cumulative total for the year exceeds 50.0 kg, the low-volume exemption is denied.
            if prev_cumulative >= 50.0:
                is_exempt = False
                final_fee = weight_kg * charge_rate
                notes_list.append(f"Exemption Denied: Cumulative annual imports ({prev_cumulative:.2f} kg) already exceed the 50 kg threshold.")
                notes_list.append(f"Charged at standard rate: {final_fee:,.0f} VND.")
                warning_msg = f"Cumulative limit exceeded! Annual imports ({prev_cumulative:.2f} kg) exceed the 50 kg waiver threshold."
            elif total_cumulative > 50.0:
                # Part is below 50, part is above, charge the portion that exceeds 50 kg
                exempt_portion = max(0.0, 50.0 - prev_cumulative)
                chargeable_portion = total_cumulative - 50.0
                is_exempt = False
                final_fee = chargeable_portion * charge_rate
                notes_list.append(f"Partial Exemption: First {exempt_portion:.2f} kg is exempt (reaches 50 kg limit).")
                notes_list.append(f"Charged {chargeable_portion:.2f} kg at standard rate. Total fee: {final_fee:,.0f} VND.")
                warning_msg = f"Partial waiver applied. Cumulative imports ({total_cumulative:.2f} kg) have crossed the 50 kg threshold."
            else:
                is_exempt = True
                final_fee = 0.0
                notes_list.append(f"Exempt: Low-volume ODS allocation ({weight_kg:.2f} kg). Cumulative annual imports ({total_cumulative:.2f} kg) remain under the 50 kg threshold.")
        else:
            final_fee = weight_kg * charge_rate
            notes_list.append(f"Quota fee calculated: Group '{substance_group}', substance '{substance_name}' with net weight {weight_kg:.2f} kg.")
            notes_list.append(f"ODP factor: {odp_factor:.3f} (ODP weight equivalent: {odp_weight_eq:.3f} ODP-kg).")
            notes_list.append(f"Licensing charge rate: {charge_rate:,.0f} VND/kg. Total fee: {final_fee:,.0f} VND.")

        notes = " ".join(notes_list)

        if save_to_db:
            conn = self.get_tenant_connection(mst)
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO ods_quota_logs
                    (substance_name, substance_group, weight_kg, odp_factor, odp_weight_eq, license_charge_rate, final_fee, is_exempt, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (substance_name, substance_group, weight_kg, odp_factor, odp_weight_eq, charge_rate, final_fee, is_exempt, notes))
            conn.commit()
            conn.close()

        # Build comprehensive response containing both original keys (for test cases) and mapped keys (for frontend)
        return {
            "substance_name": substance_name,
            "substance_group": substance_group,
            "weight_kg": weight_kg,
            "odp_factor": odp_factor,
            "odp_weight_eq": odp_weight_eq,
            "odp_equivalent_kg": odp_weight_eq,        # frontend key
            "license_charge_rate": charge_rate,
            "base_rate_per_kg": charge_rate,            # frontend key
            "final_fee": final_fee,
            "effective_fee_vnd": final_fee,             # frontend key
            "is_exempt": is_exempt,
            "notes": notes,
            "exemption_reason": notes,                  # frontend key
            "exemption_category": exemption_category,   # frontend key
            "cumulative_annual_weight": total_cumulative,
            "warning": warning_msg
        }

    def get_history(self, mst: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent ODS quota logs with mapped keys for frontend compatibility."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()
        cur.execute("SELECT * FROM ods_quota_logs ORDER BY id DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        conn.close()
        res_list = []
        for r in rows:
            d = dict(r)
            # Add mapped keys for frontend compatibility
            d["odp_equivalent_kg"] = d["odp_weight_eq"]
            d["base_rate_per_kg"] = d["license_charge_rate"]
            d["effective_fee_vnd"] = d["final_fee"]
            # Infer exemption category
            notes_lower = (d.get("notes") or "").lower()
            if "medical" in notes_lower:
                d["exemption_category"] = "medical_use"
            elif "laboratory" in notes_lower or "scientific" in notes_lower:
                d["exemption_category"] = "research_study"
            elif "low-volume" in notes_lower or "waiver" in notes_lower:
                d["exemption_category"] = "low_volume_waiver"
            else:
                d["exemption_category"] = "none"
            d["exemption_reason"] = d.get("notes") or "None"
            res_list.append(d)
        return res_list
