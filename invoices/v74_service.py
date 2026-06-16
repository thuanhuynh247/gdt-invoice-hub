"""Noise & Vibration Surcharge Compliance Engine (v74.0.0).

Implements noise exceedance dBA and vibration exceedance m/s2 surcharge calculations,
shift factors (1.5x night multiplier), and public works/emergency/festival exemptions under Law on EP 2020.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, List
from invoices.multitenant_service import get_tenant_db_path

class V74ComplianceService:
    """Noise & Vibration Law on EP 2020 compliance engine."""

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
            CREATE TABLE IF NOT EXISTS noise_vibration_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                noise_db REAL NOT NULL,
                vibration_m_s2 REAL NOT NULL,
                shift TEXT NOT NULL,
                public_infrastructure BOOLEAN NOT NULL,
                emergency_relief BOOLEAN NOT NULL,
                traditional_festival BOOLEAN NOT NULL,
                noise_surcharge REAL NOT NULL,
                vibration_surcharge REAL NOT NULL,
                gross_fee REAL NOT NULL,
                final_fee REAL NOT NULL,
                is_exempt BOOLEAN NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        return conn

    def calculate_surcharge(
        self, mst: str, noise_db: float, vibration_m_s2: float, shift: str = "day",
        public_infrastructure: bool = False, emergency_relief: bool = False,
        traditional_festival: bool = False
    ) -> Dict[str, Any]:
        """Calculate noise and vibration surcharges, apply day/night shift factors and exemptions, and log."""
        if noise_db < 0 or vibration_m_s2 < 0:
            raise ValueError("Noise and vibration levels must be non-negative.")

        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        shift_key = shift.lower().strip()
        is_exempt = public_infrastructure or emergency_relief or traditional_festival
        notes_list = []

        # Statutory limits
        noise_limit = 70.0 if shift_key == "day" else 55.0
        vibration_limit = 0.055

        # Exceedance
        noise_exceed = max(0.0, noise_db - noise_limit)
        vibration_exceed = max(0.0, vibration_m_s2 - vibration_limit)

        # Base surcharge calculations
        noise_surcharge = noise_exceed * 100000.0  # 100,000 VND / dBA
        vibration_surcharge = round((vibration_exceed / 0.01) * 5000000.0, 2)


        shift_multiplier = 1.5 if shift_key == "night" else 1.0
        gross_fee = (noise_surcharge + vibration_surcharge) * shift_multiplier

        if is_exempt:
            final_fee = 0.0
            ex_reasons = []
            if public_infrastructure:
                ex_reasons.append("public transport/utility infrastructure works")
            if emergency_relief:
                ex_reasons.append("emergency relief sirens/alarms")
            if traditional_festival:
                ex_reasons.append("traditional cultural festival")
            notes_list.append(f"Exempt: Waiver applied due to {', '.join(ex_reasons)}.")
        else:
            final_fee = gross_fee

        notes_list.append(f"Noise measured: {noise_db:.1f} dBA (limit: {noise_limit:.1f} dBA).")
        notes_list.append(f"Vibration measured: {vibration_m_s2:.4f} m/s² (limit: {vibration_limit:.4f} m/s²).")
        notes_list.append(f"Surcharge subtotal: Noise ({noise_surcharge:,.0f} VND), Vibration ({vibration_surcharge:,.0f} VND).")
        if shift_key == "night":
            notes_list.append("Night shift multiplier 1.5x applied.")
        notes_list.append(f"Total surcharge: {final_fee:,.0f} VND.")

        notes = " ".join(notes_list)

        cur.execute("""
            INSERT INTO noise_vibration_logs
                (noise_db, vibration_m_s2, shift, public_infrastructure, emergency_relief, traditional_festival, noise_surcharge, vibration_surcharge, gross_fee, final_fee, is_exempt, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (noise_db, vibration_m_s2, shift, public_infrastructure, emergency_relief, traditional_festival, noise_surcharge, vibration_surcharge, gross_fee, final_fee, is_exempt, notes))

        conn.commit()
        conn.close()

        return {
            "noise_db": noise_db,
            "vibration_m_s2": vibration_m_s2,
            "shift": shift,
            "public_infrastructure": public_infrastructure,
            "emergency_relief": emergency_relief,
            "traditional_festival": traditional_festival,
            "noise_surcharge": noise_surcharge,
            "vibration_surcharge": vibration_surcharge,
            "gross_fee": gross_fee,
            "final_fee": final_fee,
            "is_exempt": is_exempt,
            "notes": notes
        }

    def get_history(self, mst: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent noise/vibration logs."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()
        cur.execute("SELECT * FROM noise_vibration_logs ORDER BY id DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
