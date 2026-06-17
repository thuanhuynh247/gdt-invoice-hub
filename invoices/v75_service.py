"""Single-Use Plastics & Ocean Pollution Levy Compliance Engine (v75.0.0).

Implements single-use plastic bags, cosmetics microbeads, and food packaging levy calculations,
biodegradable certifications, and medical containment packaging exemptions under Decree 08/2022/NĐ-CP.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, List
from invoices.multitenant_service import get_tenant_db_path

class V75ComplianceService:
    """Single-Use Plastics Decree 08/2022/NĐ-CP compliance engine."""

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
            CREATE TABLE IF NOT EXISTS plastics_levy_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plastic_category TEXT NOT NULL,
                quantity_kg REAL NOT NULL,
                biodegradable_certified BOOLEAN NOT NULL,
                medical_containment BOOLEAN NOT NULL,
                charge_rate REAL NOT NULL,
                gross_fee REAL NOT NULL,
                final_fee REAL NOT NULL,
                is_exempt BOOLEAN NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        return conn

    def calculate_levy(
        self, mst: str, plastic_category: str, quantity_kg: float,
        biodegradable_certified: bool = False, medical_containment: bool = False
    ) -> Dict[str, Any]:
        """Calculate single-use plastics levy, verify exemptions, and log transaction."""
        if quantity_kg < 0:
            raise ValueError("Quantity in kg must be non-negative.")

        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        cat_key = plastic_category.lower().strip()
        is_exempt = biodegradable_certified or medical_containment
        notes_list = []

        # Pricing rates (Decree 08/2022/NĐ-CP)
        rates = {
            "microbeads_cosmetics": 150000.0,
            "plastic_bags": 50000.0,
            "plastic_packaging": 30000.0
        }

        if cat_key not in rates:
            conn.close()
            raise ValueError(f"Invalid plastic category. Must be one of: {list(rates.keys())}")

        charge_rate = rates[cat_key]
        gross_fee = quantity_kg * charge_rate

        if is_exempt:
            final_fee = 0.0
            reasons = []
            if biodegradable_certified:
                reasons.append("certified biodegradable material status")
            if medical_containment:
                reasons.append("medical containment packaging standard compliance")
            notes_list.append(f"Exempt: Levy waived (Reason: {', '.join(reasons)}).")
        else:
            final_fee = gross_fee
            notes_list.append(f"Plastics levy calculated: Category '{plastic_category}', quantity {quantity_kg:.2f} kg.")
            notes_list.append(f"Levy charge rate: {charge_rate:,.0f} VND/kg. Total levy: {final_fee:,.0f} VND.")

        notes = " ".join(notes_list)

        cur.execute("""
            INSERT INTO plastics_levy_logs
                (plastic_category, quantity_kg, biodegradable_certified, medical_containment, charge_rate, gross_fee, final_fee, is_exempt, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (plastic_category, quantity_kg, biodegradable_certified, medical_containment, charge_rate, gross_fee, final_fee, is_exempt, notes))

        conn.commit()
        conn.close()

        return {
            "plastic_category": plastic_category,
            "quantity_kg": quantity_kg,
            "biodegradable_certified": biodegradable_certified,
            "medical_containment": medical_containment,
            "charge_rate": charge_rate,
            "gross_fee": gross_fee,
            "final_fee": final_fee,
            "is_exempt": is_exempt,
            "notes": notes
        }

    def get_history(self, mst: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent plastics levy logs."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()
        cur.execute("SELECT * FROM plastics_levy_logs ORDER BY id DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
