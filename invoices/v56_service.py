"""License Fee (LF) Compliance Engine (v56.0.0).

Implements annual License Fee (Lệ phí môn bài) calculations and exemptions under Decree 139/2016/NĐ-CP
and amending Decree 22/2020/NĐ-CP covering:
- Enterprise fee brackets based on Charter Capital (> 10 Billion VND, <= 10 Billion VND).
- Branches, Representative Offices, Business Locations flat fee.
- Household and individual fee brackets based on annual revenue.
- Newly established enterprise first calendar year exemption.
- Agricultural cooperative exemptions.
- Low annual revenue exemption (<= 100M VND/year).
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional
from invoices.multitenant_service import get_tenant_db_path


class V56ComplianceService:
    """License Fee (Lệ phí môn bài) Decree 139/2016/NĐ-CP compliance engine."""

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
            CREATE TABLE IF NOT EXISTS lf_calculations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_name TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                charter_capital REAL NOT NULL,
                annual_revenue REAL NOT NULL,
                is_newly_established BOOLEAN NOT NULL,
                is_agri_cooperative BOOLEAN NOT NULL,
                standard_fee REAL NOT NULL,
                effective_fee REAL NOT NULL,
                is_exempt BOOLEAN NOT NULL,
                exemption_reason TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        return conn

    def calculate_license_fee(
        self, mst: str, entity_name: str, entity_type: str, charter_capital: float = 0.0,
        annual_revenue: float = 0.0, is_newly_established: bool = False, is_agri_cooperative: bool = False
    ) -> Dict[str, Any]:
        """Calculate License Fee based on brackets and audit for exemptions."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        entity_type = entity_type.lower().strip()

        # 1. Determine standard fee
        standard_fee = 0.0
        if entity_type in ["branch", "representative office", "ro", "location"]:
            standard_fee = 1000000.0  # 1,000,000 VND / year flat
        elif entity_type == "enterprise":
            if charter_capital > 10000000000.0:  # > 10 Billion VND
                standard_fee = 3000000.0  # 3,000,000 VND / year
            else:
                standard_fee = 2000000.0  # 2,000,000 VND / year
        elif entity_type in ["household", "individual"]:
            if annual_revenue > 500000000.0:  # > 500M
                standard_fee = 1000000.0
            elif annual_revenue > 300000000.0:  # 300M to 500M
                standard_fee = 500000.0
            elif annual_revenue > 100000000.0:  # 100M to 300M
                standard_fee = 300000.0
            else:
                standard_fee = 300000.0  # base standard fee before exemption check is triggered

        # 2. Evaluate Exemptions
        is_exempt = False
        exemption_reason = ""

        if is_newly_established:
            is_exempt = True
            exemption_reason = "First calendar year of establishment exemption under Decree 22/2020/NĐ-CP"
        elif is_agri_cooperative:
            is_exempt = True
            exemption_reason = "Agricultural cooperative exemption under Decree 139/2016/NĐ-CP"
        elif entity_type in ["household", "individual"] and annual_revenue <= 100000000.0:
            is_exempt = True
            exemption_reason = "Low annual revenue exemption (annual revenue <= 100,000,000 VND)"

        effective_fee = 0.0 if is_exempt else standard_fee

        notes = (
            f"Entity: '{entity_name}' ({entity_type}). Charter Capital: {charter_capital:,.0f} VND. "
            f"Revenue: {annual_revenue:,.0f} VND. Newly Established: {is_newly_established}. Agri Cooperative: {is_agri_cooperative}. "
            f"Standard Fee: {standard_fee:,.0f} VND. Effective Fee: {effective_fee:,.0f} VND. Exempt: {is_exempt}."
        )
        if is_exempt:
            notes += f" Reason: {exemption_reason}"

        cur.execute("""
            INSERT INTO lf_calculations
                (entity_name, entity_type, charter_capital, annual_revenue, is_newly_established,
                 is_agri_cooperative, standard_fee, effective_fee, is_exempt, exemption_reason, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (entity_name, entity_type, charter_capital, annual_revenue, is_newly_established,
              is_agri_cooperative, standard_fee, effective_fee, is_exempt, exemption_reason, notes))
        conn.commit()

        # Retrieve generated ID
        last_id = cur.lastrowid
        conn.close()

        return {
            "id": last_id,
            "entity_name": entity_name,
            "entity_type": entity_type,
            "charter_capital": charter_capital,
            "annual_revenue": annual_revenue,
            "is_newly_established": is_newly_established,
            "is_agri_cooperative": is_agri_cooperative,
            "standard_fee": standard_fee,
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
            SELECT id, entity_name, entity_type, charter_capital, annual_revenue, is_newly_established,
                   is_agri_cooperative, standard_fee, effective_fee, is_exempt, exemption_reason, notes, created_at
            FROM lf_calculations
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        rows = cur.fetchall()
        conn.close()

        res = []
        for r in rows:
            res.append(dict(r))
        return res
