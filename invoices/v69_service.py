"""Oil Spill Response & Risk Fee Compliance Engine (v69.0.0).

Implements oil spill risk management fee calculations, capacity charges,
double-hull transport discounts, and military exemptions under Decision 12/2021/QĐ-TTg.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, List
from invoices.multitenant_service import get_tenant_db_path

class V69ComplianceService:
    """Oil Spill Response & Risk Fee Decision 12/2021/QĐ-TTg compliance engine."""

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
            CREATE TABLE IF NOT EXISTS oil_spill_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                facility_name TEXT NOT NULL,
                facility_type TEXT NOT NULL,
                capacity_m3 REAL NOT NULL,
                has_double_hull BOOLEAN NOT NULL,
                base_fee REAL NOT NULL,
                capacity_charge REAL NOT NULL,
                discount_applied REAL NOT NULL,
                final_fee REAL NOT NULL,
                is_exempt BOOLEAN NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        return conn

    def calculate_spill_fee(
        self, mst: str, facility_name: str, facility_type: str,
        capacity_m3: float, has_double_hull: bool = False, exemption_category: str = "none"
    ) -> Dict[str, Any]:
        """Calculate oil spill risk fee based on facility type, capacity, apply mitigation discounts, and log transaction."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        type_key = facility_type.lower().strip()
        is_exempt = False
        notes_list = []

        # Base fee rates per quarter
        base_rates = {
            "refinery_or_extraction": 50000000.0,
            "storage_terminal": 30000000.0,
            "transport_fleet": 20000000.0,
            "fuel_station": 2000000.0
        }
        base_fee = base_rates.get(type_key, 10000000.0)

        # Capacity charges (500 VND per m3 of fuel capacity)
        capacity_charge = capacity_m3 * 500.0

        # Mitigation discounts: 30% for double-hull tankers/double-walled storage
        discount_rate = 0.30 if has_double_hull else 0.0

        # Exemption checks
        if exemption_category == "military_petroleum":
            is_exempt = True
            final_fee = 0.0
            notes_list.append("Exempt: National defense petroleum storage terminal and military fleet (exempt under Decision 12/2021/QĐ-TTg).")
        elif type_key == "fuel_station" and capacity_m3 < 5.0:
            is_exempt = True
            final_fee = 0.0
            notes_list.append(f"Exempt: Small rural fuel station with storage capacity ({capacity_m3:.2f} m3) under 5 m3 threshold.")
        else:
            gross_fee = base_fee + capacity_charge
            discount_applied = gross_fee * discount_rate
            final_fee = gross_fee - discount_applied
            notes_list.append(f"Spill fee calculated: Type '{facility_type}' with base fee {base_fee:,.0f} VND.")
            notes_list.append(f"Capacity charge: {capacity_charge:,.0f} VND (capacity: {capacity_m3:.1f} m3).")
            if has_double_hull:
                notes_list.append(f"Double-hull/wall mitigation discount of 30% applied (-{discount_applied:,.0f} VND).")
            notes_list.append(f"Total quarterly risk fee: {final_fee:,.0f} VND.")

        notes = " ".join(notes_list)
        discount_amount = gross_fee * discount_rate if not is_exempt else 0.0

        cur.execute("""
            INSERT INTO oil_spill_logs
                (facility_name, facility_type, capacity_m3, has_double_hull, base_fee, capacity_charge, discount_applied, final_fee, is_exempt, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (facility_name, facility_type, capacity_m3, has_double_hull, base_fee, capacity_charge, discount_amount, final_fee, is_exempt, notes))

        conn.commit()
        conn.close()

        return {
            "facility_name": facility_name,
            "facility_type": facility_type,
            "capacity_m3": capacity_m3,
            "has_double_hull": has_double_hull,
            "base_fee": base_fee,
            "capacity_charge": capacity_charge,
            "discount_applied": discount_amount,
            "final_fee": final_fee,
            "is_exempt": is_exempt,
            "notes": notes
        }

    def get_history(self, mst: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent oil spill logs."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()
        cur.execute("SELECT * FROM oil_spill_logs ORDER BY id DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
