"""Import-Export Tax (IET) Compliance Engine (v55.0.0).

Implements Import-Export Tax calculations and exemption audits under Law 107/2016/QH13:
- Import duties (Preferential MFN, Ordinary, Special Preferential FTA).
- Export duties (Standard, Mineral, Wood/Timber chip).
- Exemptions for goods under processing contracts (hàng gia công xuất khẩu).
- Exemptions for temporary import and re-export (tạm nhập tái xuất).
- Low-value gift/sample exemption thresholds (<= 2,000,000 VND).
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional
from invoices.multitenant_service import get_tenant_db_path


class V55ComplianceService:
    """Import-Export Tax Law 107/2016/QH13 compliance engine."""

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
            CREATE TABLE IF NOT EXISTS iet_calculations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cargo_name TEXT NOT NULL,
                cargo_type TEXT NOT NULL,
                quantity REAL NOT NULL,
                unit_price REAL NOT NULL,
                tariff_type TEXT NOT NULL,
                goods_purpose TEXT NOT NULL,
                standard_rate REAL NOT NULL,
                effective_rate REAL NOT NULL,
                duty_amount REAL NOT NULL,
                is_exempt BOOLEAN NOT NULL,
                exemption_reason TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        return conn

    def calculate_import_export_duty(
        self, mst: str, cargo_name: str, cargo_type: str, quantity: float,
        unit_price: float, tariff_type: str = "preferential", goods_purpose: str = "commercial"
    ) -> Dict[str, Any]:
        """Calculate IET with standard rates and verify processing/temporary/low-value exemptions."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        cargo_type = cargo_type.lower().strip()
        tariff_type = tariff_type.lower().strip()
        goods_purpose = goods_purpose.lower().strip()
        cargo_name_lower = cargo_name.lower().strip()

        # 1. Base Tax Rate determination
        standard_rate = 0.0
        if cargo_type == "export":
            # Standard export rate: 5% (0.05)
            # Minerals/Ores: 10% (0.10)
            # Wood chips/timber: 2% (0.02)
            if "mineral" in cargo_name_lower or "ore" in cargo_name_lower or "coal" in cargo_name_lower:
                standard_rate = 0.10
            elif "wood" in cargo_name_lower or "timber" in cargo_name_lower or "chip" in cargo_name_lower:
                standard_rate = 0.02
            else:
                standard_rate = 0.05
        else:
            # Import tariff rates:
            # Preferential MFN: 10% (0.10)
            # Ordinary: 15% (0.15)
            # Special (FTAs): 5% (0.05)
            if tariff_type in ["ordinary", "standard"]:
                standard_rate = 0.15
            elif tariff_type in ["special", "fta", "evfta", "cptpp"]:
                standard_rate = 0.05
            else:
                standard_rate = 0.10  # default to preferential MFN

        # 2. Evaluate Exemptions
        is_exempt = False
        exemption_reason = ""
        effective_rate = standard_rate
        total_value = quantity * unit_price

        if goods_purpose == "processing contract" or goods_purpose == "processing":
            is_exempt = True
            exemption_reason = "Goods imported for processing contract under Law 107/2016/QH13"
            effective_rate = 0.0
        elif goods_purpose == "temporary import" or goods_purpose == "temporary":
            is_exempt = True
            exemption_reason = "Goods temporarily imported for re-export under Law 107/2016/QH13"
            effective_rate = 0.0
        elif goods_purpose == "gift" or goods_purpose == "sample":
            if total_value <= 2000000.0:
                is_exempt = True
                exemption_reason = f"Low-value gift/sample exemption (VND {total_value:,.0f} <= 2,000,000)"
                effective_rate = 0.0
            else:
                is_exempt = False
                exemption_reason = f"Gift value (VND {total_value:,.0f}) exceeds exemption threshold (2,000,000)"

        duty_amount = total_value * effective_rate

        notes = (
            f"Cargo: '{cargo_name}' ({cargo_type}). Quantity: {quantity:,.2f}, Unit Price: {unit_price:,.0f} VND. "
            f"Tariff: {tariff_type}, Purpose: {goods_purpose}. "
            f"Standard Rate: {standard_rate*100:.1f}%. Effective Rate: {effective_rate*100:.1f}%. "
            f"Calculated Duty: {duty_amount:,.0f} VND. Exempt: {is_exempt}."
        )
        if is_exempt:
            notes += f" Reason: {exemption_reason}"

        cur.execute("""
            INSERT INTO iet_calculations
                (cargo_name, cargo_type, quantity, unit_price, tariff_type, goods_purpose,
                 standard_rate, effective_rate, duty_amount, is_exempt, exemption_reason, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (cargo_name, cargo_type, quantity, unit_price, tariff_type, goods_purpose,
              standard_rate, effective_rate, duty_amount, is_exempt, exemption_reason, notes))
        conn.commit()

        # Retrieve the generated ID
        last_id = cur.lastrowid
        conn.close()

        return {
            "id": last_id,
            "cargo_name": cargo_name,
            "cargo_type": cargo_type,
            "quantity": quantity,
            "unit_price": unit_price,
            "total_value": total_value,
            "tariff_type": tariff_type,
            "goods_purpose": goods_purpose,
            "standard_rate": standard_rate,
            "effective_rate": effective_rate,
            "duty_amount": duty_amount,
            "is_exempt": is_exempt,
            "exemption_reason": exemption_reason,
            "notes": notes
        }

    def get_history(self, mst: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Return historical calculation logs for this tenant."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()
        cur.execute("""
            SELECT id, cargo_name, cargo_type, quantity, unit_price, tariff_type, goods_purpose,
                   standard_rate, effective_rate, duty_amount, is_exempt, exemption_reason, notes, created_at
            FROM iet_calculations
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        conn.close()

        res = []
        for r in rows:
            res.append(dict(r))
        return res
