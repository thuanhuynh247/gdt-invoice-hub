"""Non-Agricultural Land Use Tax (NALUT) Compliance Engine (v59.0.0).

Implements NALUT (Thuế sử dụng đất phi nông nghiệp) calculations and exemptions under
Law 48/2010/QH12 and Decree 53/2011/NĐ-CP covering:
- Residential land: Progressive tiered rates 0.03% (≤ quota), 0.07% (1x-3x), 0.15% (> 3x).
- Commercial/service land: Flat 0.03%.
- Non-agricultural production land: Flat 0.03%.
- Idle/unused land: Base rate + 0.02% per idle year (capped at 0.15%).
- Exemptions for public welfare, religious, and diplomatic land uses.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, List
from invoices.multitenant_service import get_tenant_db_path


class V59ComplianceService:
    """Non-Agricultural Land Use Tax Law 48/2010/QH12 compliance engine."""

    def __init__(self, base_data_dir: str | None = None):
        self.base_data_dir = base_data_dir

    def get_tenant_connection(self, mst: str) -> sqlite3.Connection:
        db_path = get_tenant_db_path(mst, self.base_data_dir)
        conn = sqlite3.connect(db_path)
        conn.text_factory = lambda x: x.decode('utf-8', errors='replace') if isinstance(x, bytes) else x
        conn.row_factory = sqlite3.Row

        cur = conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS nalut_calculations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                land_description TEXT NOT NULL,
                land_type TEXT NOT NULL,
                land_value REAL NOT NULL,
                land_area REAL NOT NULL DEFAULT 0,
                quota_area REAL NOT NULL DEFAULT 0,
                idle_years INTEGER NOT NULL DEFAULT 0,
                rate_pct REAL NOT NULL,
                tax_amount REAL NOT NULL,
                is_exempt BOOLEAN NOT NULL DEFAULT 0,
                exemption_reason TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        return conn

    def calculate_nalut(
        self,
        mst: str,
        land_description: str,
        land_type: str,
        land_value: float = 0.0,
        land_area: float = 0.0,
        quota_area: float = 0.0,
        idle_years: int = 0,
        is_public_welfare: bool = False,
        is_religious: bool = False,
        is_diplomatic: bool = False,
    ) -> Dict[str, Any]:
        """Calculate Non-Agricultural Land Use Tax based on land type and value."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        land_type = land_type.lower().strip()

        # Determine rate and tax amount
        rate_pct = 0.03
        tax_amount = 0.0

        if land_type == "residential":
            # Progressive tiered calculation
            if quota_area > 0 and land_area > 0:
                quota_value = land_value * min(land_area, quota_area) / land_area if land_area > 0 else land_value
                tier1 = quota_value * 0.03 / 100.0

                excess_1x_3x = 0.0
                excess_3x = 0.0
                if land_area > quota_area:
                    excess_area_mid = min(land_area, quota_area * 3) - quota_area
                    if excess_area_mid > 0:
                        excess_1x_3x = (land_value * excess_area_mid / land_area) * 0.07 / 100.0
                if land_area > quota_area * 3:
                    excess_area_high = land_area - quota_area * 3
                    excess_3x = (land_value * excess_area_high / land_area) * 0.15 / 100.0

                tax_amount = tier1 + excess_1x_3x + excess_3x
                rate_pct = round((tax_amount / land_value * 100) if land_value > 0 else 0.03, 4)
            else:
                rate_pct = 0.03
                tax_amount = land_value * 0.03 / 100.0

        elif land_type in ["commercial", "service"]:
            rate_pct = 0.03
            tax_amount = land_value * 0.03 / 100.0

        elif land_type == "production":
            rate_pct = 0.03
            tax_amount = land_value * 0.03 / 100.0

        elif land_type == "idle":
            surcharge = min(0.02 * idle_years, 0.12)  # capped so total max = 0.15%
            rate_pct = 0.03 + surcharge
            rate_pct = min(rate_pct, 0.15)
            tax_amount = land_value * rate_pct / 100.0

        else:
            rate_pct = 0.03
            tax_amount = land_value * 0.03 / 100.0

        # Evaluate exemptions
        is_exempt = False
        exemption_reason = ""

        if is_public_welfare:
            is_exempt = True
            exemption_reason = "Public welfare, education, or healthcare land (Law 48/2010/QH12, Art. 9)"
        elif is_religious:
            is_exempt = True
            exemption_reason = "Religious institution or pagoda land (Law 48/2010/QH12, Art. 9)"
        elif is_diplomatic:
            is_exempt = True
            exemption_reason = "Foreign diplomatic mission land (Law 48/2010/QH12, Art. 9)"

        effective_amount = 0.0 if is_exempt else tax_amount

        notes = (
            f"Land: '{land_description}' ({land_type}). Value: {land_value:,.0f} VND. "
            f"Area: {land_area:,.0f} m². Quota: {quota_area:,.0f} m². Idle: {idle_years} yrs. "
            f"Rate: {rate_pct}%. Tax: {tax_amount:,.0f} VND. Effective: {effective_amount:,.0f} VND. Exempt: {is_exempt}."
        )
        if is_exempt:
            notes += f" Reason: {exemption_reason}"

        cur.execute("""
            INSERT INTO nalut_calculations
                (land_description, land_type, land_value, land_area, quota_area,
                 idle_years, rate_pct, tax_amount, is_exempt, exemption_reason, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (land_description, land_type, land_value, land_area, quota_area,
              idle_years, rate_pct, effective_amount, is_exempt, exemption_reason, notes))
        conn.commit()

        last_id = cur.lastrowid
        conn.close()

        return {
            "id": last_id,
            "land_description": land_description,
            "land_type": land_type,
            "land_value": land_value,
            "land_area": land_area,
            "quota_area": quota_area,
            "idle_years": idle_years,
            "rate_pct": rate_pct,
            "tax_amount": tax_amount,
            "effective_amount": effective_amount,
            "is_exempt": is_exempt,
            "exemption_reason": exemption_reason,
            "notes": notes
        }

    def get_history(self, mst: str, limit: int = 50) -> List[Dict[str, Any]]:
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()
        cur.execute("""
            SELECT id, land_description, land_type, land_value, land_area, quota_area,
                   idle_years, rate_pct, tax_amount, is_exempt, exemption_reason, notes, created_at
            FROM nalut_calculations ORDER BY created_at DESC LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
