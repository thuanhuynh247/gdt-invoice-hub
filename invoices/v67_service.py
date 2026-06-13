"""Scrap Import Environmental Deposit Compliance Engine (v67.0.0).

Implements environmental protection deposit calculations for scrap importers,
exemptions for laboratory imports, and refund logic under Decree 08/2022/NĐ-CP.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, List
from invoices.multitenant_service import get_tenant_db_path

class V67ComplianceService:
    """Scrap Import Environmental Deposit Decree 08/2022/NĐ-CP compliance engine."""

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
            CREATE TABLE IF NOT EXISTS scrap_deposit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scrap_description TEXT NOT NULL,
                scrap_type TEXT NOT NULL,
                volume_tonnes REAL NOT NULL,
                cargo_value_vnd REAL NOT NULL,
                deposit_rate REAL NOT NULL,
                deposit_amount REAL NOT NULL,
                is_exempt BOOLEAN NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        return conn

    def calculate_deposit(
        self, mst: str, scrap_description: str, scrap_type: str,
        volume_tonnes: float, cargo_value_vnd: float, exemption_category: str = "none"
    ) -> Dict[str, Any]:
        """Calculate scrap import deposit fee, check volume brackets, verify exemptions, and write transaction."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        type_key = scrap_type.lower().strip()
        deposit_rate = 0.0
        is_exempt = False
        notes_list = []

        # Bracket rate determination based on Decree 08/2022/NĐ-CP
        if type_key == "scrap_steel":
            if volume_tonnes < 500.0:
                deposit_rate = 0.10
            elif volume_tonnes <= 1000.0:
                deposit_rate = 0.15
            else:
                deposit_rate = 0.20
        elif type_key == "scrap_paper":
            if volume_tonnes < 100.0:
                deposit_rate = 0.15
            elif volume_tonnes <= 500.0:
                deposit_rate = 0.18
            else:
                deposit_rate = 0.20
        elif type_key == "scrap_plastic":
            if volume_tonnes < 100.0:
                deposit_rate = 0.18
            elif volume_tonnes <= 500.0:
                deposit_rate = 0.22
            else:
                deposit_rate = 0.25
        else:
            # Generic/other scrap types default to 20%
            deposit_rate = 0.20

        # Exemption checks
        if exemption_category == "laboratory_research" and volume_tonnes <= 5.0:
            is_exempt = True
            deposit_amount = 0.0
            notes_list.append(f"Exempt: Research institute importing {volume_tonnes:.1f} tonnes of scrap for laboratory analysis (exempt under Article 41).")
        else:
            deposit_amount = cargo_value_vnd * deposit_rate
            notes_list.append(f"Deposit calculated: Type '{scrap_type}' with volume {volume_tonnes:.1f} tonnes. Rate applied: {deposit_rate * 100:.1f}%. Cargo value: {cargo_value_vnd:,.0f} VND. Deposit: {deposit_amount:,.0f} VND.")

        notes = " ".join(notes_list)

        cur.execute("""
            INSERT INTO scrap_deposit_logs
                (scrap_description, scrap_type, volume_tonnes, cargo_value_vnd, deposit_rate, deposit_amount, is_exempt, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (scrap_description, scrap_type, volume_tonnes, cargo_value_vnd, deposit_rate, deposit_amount, is_exempt, notes))

        conn.commit()
        conn.close()

        return {
            "scrap_description": scrap_description,
            "scrap_type": scrap_type,
            "volume_tonnes": volume_tonnes,
            "cargo_value_vnd": cargo_value_vnd,
            "deposit_rate": deposit_rate,
            "deposit_amount": deposit_amount,
            "is_exempt": is_exempt,
            "notes": notes
        }

    def get_history(self, mst: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent scrap deposit logs."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()
        cur.execute("SELECT * FROM scrap_deposit_logs ORDER BY id DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
