"""Natural Resources Tax (NRT) Compliance Engine (v58.0.0).

Implements Natural Resources Tax (Thuế tài nguyên) calculations and exemptions under
Law on Natural Resources Tax No. 45/2009/QH12 and Decree 50/2010/NĐ-CP covering:
- Metallic minerals: iron (12%), copper (13%), gold (15%), tin (10%).
- Non-metallic minerals: granite/marble (10%), sand/gravel (7%).
- Crude oil: 6%-10% sliding scale by daily output.
- Natural gas: 2%.
- Coal: open-pit (7%), underground (5%).
- Natural water: industrial use (3%).
- Timber: hardwood (25%), softwood (15%).
- Marine products: natural catch (2%).
- Exemptions for agricultural water, hydroelectric water, defense resources.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional
from invoices.multitenant_service import get_tenant_db_path


# Rate schedule lookup
NRT_RATES = {
    "iron_ore": 12.0,
    "copper_ore": 13.0,
    "gold_ore": 15.0,
    "tin_ore": 10.0,
    "metallic_other": 10.0,
    "granite": 10.0,
    "marble": 10.0,
    "sand": 7.0,
    "gravel": 7.0,
    "non_metallic_other": 8.0,
    "crude_oil_low": 6.0,     # daily output <= 20,000 barrels
    "crude_oil_high": 10.0,   # daily output > 20,000 barrels
    "natural_gas": 2.0,
    "coal_open_pit": 7.0,
    "coal_underground": 5.0,
    "natural_water": 3.0,
    "timber_hardwood": 25.0,
    "timber_softwood": 15.0,
    "marine_products": 2.0,
}


class V58ComplianceService:
    """Natural Resources Tax (Thuế tài nguyên) Law 45/2009/QH12 compliance engine."""

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
            CREATE TABLE IF NOT EXISTS nrt_calculations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resource_description TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_subtype TEXT NOT NULL DEFAULT '',
                extraction_value REAL NOT NULL,
                daily_output REAL NOT NULL DEFAULT 0,
                rate_pct REAL NOT NULL,
                nrt_amount REAL NOT NULL,
                is_exempt BOOLEAN NOT NULL DEFAULT 0,
                exemption_reason TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        return conn

    def _resolve_rate(self, resource_type: str, resource_subtype: str, daily_output: float) -> float:
        """Resolve tax rate percentage from resource type and subtype."""
        rt = resource_type.lower().strip()
        rs = resource_subtype.lower().strip()

        if rt == "metallic":
            return NRT_RATES.get(rs, NRT_RATES["metallic_other"])
        elif rt == "non_metallic":
            return NRT_RATES.get(rs, NRT_RATES["non_metallic_other"])
        elif rt == "crude_oil":
            if daily_output > 20000:
                return NRT_RATES["crude_oil_high"]
            return NRT_RATES["crude_oil_low"]
        elif rt == "natural_gas":
            return NRT_RATES["natural_gas"]
        elif rt == "coal":
            if rs == "underground":
                return NRT_RATES["coal_underground"]
            return NRT_RATES["coal_open_pit"]
        elif rt == "water":
            return NRT_RATES["natural_water"]
        elif rt == "timber":
            if rs == "softwood":
                return NRT_RATES["timber_softwood"]
            return NRT_RATES["timber_hardwood"]
        elif rt == "marine":
            return NRT_RATES["marine_products"]
        else:
            return 5.0  # fallback

    def calculate_nrt(
        self,
        mst: str,
        resource_description: str,
        resource_type: str,
        resource_subtype: str = "",
        extraction_value: float = 0.0,
        daily_output: float = 0.0,
        is_agri_water: bool = False,
        is_hydro_water: bool = False,
        is_defense: bool = False,
    ) -> Dict[str, Any]:
        """Calculate Natural Resources Tax based on resource type and extraction value."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        rate_pct = self._resolve_rate(resource_type, resource_subtype, daily_output)
        nrt_amount = extraction_value * (rate_pct / 100.0)

        # Evaluate exemptions
        is_exempt = False
        exemption_reason = ""

        if is_agri_water and resource_type.lower().strip() == "water":
            is_exempt = True
            exemption_reason = "Natural water for agriculture, aquaculture, or salt production (Law 45/2009/QH12, Art. 9)"
        elif is_hydro_water and resource_type.lower().strip() == "water":
            is_exempt = True
            exemption_reason = "Natural water for hydroelectric power generation (Law 45/2009/QH12, Art. 9)"
        elif is_defense:
            is_exempt = True
            exemption_reason = "Resources extracted for national defense/security purposes (Law 45/2009/QH12, Art. 9)"

        effective_amount = 0.0 if is_exempt else nrt_amount

        notes = (
            f"Resource: '{resource_description}' ({resource_type}/{resource_subtype}). "
            f"Value: {extraction_value:,.0f} VND. Daily Output: {daily_output:,.0f}. "
            f"Rate: {rate_pct}%. NRT: {nrt_amount:,.0f} VND. "
            f"Effective: {effective_amount:,.0f} VND. Exempt: {is_exempt}."
        )
        if is_exempt:
            notes += f" Reason: {exemption_reason}"

        cur.execute("""
            INSERT INTO nrt_calculations
                (resource_description, resource_type, resource_subtype, extraction_value,
                 daily_output, rate_pct, nrt_amount, is_exempt, exemption_reason, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (resource_description, resource_type, resource_subtype, extraction_value,
              daily_output, rate_pct, effective_amount, is_exempt, exemption_reason, notes))
        conn.commit()

        last_id = cur.lastrowid
        conn.close()

        return {
            "id": last_id,
            "resource_description": resource_description,
            "resource_type": resource_type,
            "resource_subtype": resource_subtype,
            "extraction_value": extraction_value,
            "daily_output": daily_output,
            "rate_pct": rate_pct,
            "nrt_amount": nrt_amount,
            "effective_amount": effective_amount,
            "is_exempt": is_exempt,
            "exemption_reason": exemption_reason,
            "notes": notes
        }

    def get_history(self, mst: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Return historical calculation logs for this tenant."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()
        cur.execute("""
            SELECT id, resource_description, resource_type, resource_subtype, extraction_value,
                   daily_output, rate_pct, nrt_amount, is_exempt, exemption_reason, notes, created_at
            FROM nrt_calculations
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        conn.close()

        return [dict(r) for r in rows]
