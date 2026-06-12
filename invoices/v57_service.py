"""Registration Fee (RF) Compliance Engine (v57.0.0).

Implements Registration Fee (Lệ phí trước bạ) calculations and exemptions under
Decree 10/2022/NĐ-CP and Decree 20/2019/NĐ-CP covering:
- Real estate (land-use rights, buildings/apartments): 0.5% of declared/appraised value.
- Motor vehicles — Cars first-time (2% standard, up to 12% Hanoi/HCMC); subsequent: 2%.
- Motorbikes — >175cc: 5%; ≤175cc: 2%.
- Yachts, motorboats, aircraft: 1% of declared value.
- Exemptions for agricultural land, diplomatic assets, merit family housing,
  and within-family agricultural transfers.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional
from invoices.multitenant_service import get_tenant_db_path


class V57ComplianceService:
    """Registration Fee (Lệ phí trước bạ) Decree 10/2022/NĐ-CP compliance engine."""

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
            CREATE TABLE IF NOT EXISTS rf_calculations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asset_description TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                asset_value REAL NOT NULL,
                province TEXT NOT NULL DEFAULT 'standard',
                is_first_registration BOOLEAN NOT NULL DEFAULT 1,
                cylinder_capacity REAL NOT NULL DEFAULT 0,
                rate_pct REAL NOT NULL,
                registration_fee REAL NOT NULL,
                is_exempt BOOLEAN NOT NULL DEFAULT 0,
                exemption_reason TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        return conn

    def calculate_registration_fee(
        self,
        mst: str,
        asset_description: str,
        asset_type: str,
        asset_value: float = 0.0,
        province: str = "standard",
        is_first_registration: bool = True,
        cylinder_capacity: float = 0.0,
        is_agricultural_land: bool = False,
        is_diplomatic: bool = False,
        is_merit_family_housing: bool = False,
        is_family_agri_transfer: bool = False,
    ) -> Dict[str, Any]:
        """Calculate Registration Fee based on asset type, value, and provincial rates."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        asset_type = asset_type.lower().strip()
        province = province.lower().strip()

        # 1. Determine rate percentage
        rate_pct = 0.0
        if asset_type in ["land", "real_estate", "building", "apartment"]:
            rate_pct = 0.5  # 0.5% for all real estate
        elif asset_type in ["car", "automobile", "vehicle"]:
            if is_first_registration:
                if province in ["hanoi", "ha noi", "hcmc", "ho chi minh", "hồ chí minh", "hà nội"]:
                    rate_pct = 12.0  # 12% first-time in Hanoi/HCMC
                else:
                    rate_pct = 2.0  # 2% standard provinces
            else:
                rate_pct = 2.0  # 2% subsequent registrations
        elif asset_type in ["motorbike", "motorcycle", "xe máy"]:
            if cylinder_capacity > 175:
                rate_pct = 5.0  # 5% for >175cc
            else:
                rate_pct = 2.0  # 2% for ≤175cc
        elif asset_type in ["yacht", "motorboat", "aircraft", "tàu thuyền", "máy bay"]:
            rate_pct = 1.0  # 1% for watercraft and aircraft
        else:
            rate_pct = 2.0  # Default fallback rate

        # 2. Calculate base registration fee
        registration_fee = asset_value * (rate_pct / 100.0)

        # 3. Evaluate Exemptions
        is_exempt = False
        exemption_reason = ""

        if is_agricultural_land and asset_type in ["land", "real_estate"]:
            is_exempt = True
            exemption_reason = "Agricultural/forestry land allocated by the State (Decree 10/2022/NĐ-CP, Art. 10)"
        elif is_diplomatic:
            is_exempt = True
            exemption_reason = "Assets of foreign diplomatic missions/international organizations (Decree 10/2022/NĐ-CP, Art. 10)"
        elif is_merit_family_housing:
            is_exempt = True
            exemption_reason = "Social-policy housing for revolutionary merit families (Decree 10/2022/NĐ-CP, Art. 10)"
        elif is_family_agri_transfer and asset_type in ["land", "real_estate"]:
            is_exempt = True
            exemption_reason = "Agricultural land transferred within the same household (Decree 10/2022/NĐ-CP, Art. 10)"

        effective_fee = 0.0 if is_exempt else registration_fee

        notes = (
            f"Asset: '{asset_description}' ({asset_type}). Value: {asset_value:,.0f} VND. "
            f"Province: {province}. First Registration: {is_first_registration}. "
            f"Cylinder Capacity: {cylinder_capacity}cc. Rate: {rate_pct}%. "
            f"Base Fee: {registration_fee:,.0f} VND. Effective Fee: {effective_fee:,.0f} VND. Exempt: {is_exempt}."
        )
        if is_exempt:
            notes += f" Reason: {exemption_reason}"

        cur.execute("""
            INSERT INTO rf_calculations
                (asset_description, asset_type, asset_value, province, is_first_registration,
                 cylinder_capacity, rate_pct, registration_fee, is_exempt, exemption_reason, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (asset_description, asset_type, asset_value, province, is_first_registration,
              cylinder_capacity, rate_pct, effective_fee, is_exempt, exemption_reason, notes))
        conn.commit()

        last_id = cur.lastrowid
        conn.close()

        return {
            "id": last_id,
            "asset_description": asset_description,
            "asset_type": asset_type,
            "asset_value": asset_value,
            "province": province,
            "is_first_registration": is_first_registration,
            "cylinder_capacity": cylinder_capacity,
            "rate_pct": rate_pct,
            "registration_fee": registration_fee,
            "effective_fee": effective_fee,
            "is_exempt": is_exempt,
            "exemption_reason": exemption_reason,
            "notes": notes
        }

    def get_history(self, mst: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Return historical calculation logs for this tenant."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()
        cur.execute("""
            SELECT id, asset_description, asset_type, asset_value, province, is_first_registration,
                   cylinder_capacity, rate_pct, registration_fee, is_exempt, exemption_reason, notes, created_at
            FROM rf_calculations
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        conn.close()

        res = []
        for r in rows:
            res.append(dict(r))
        return res
