"""Natural Resources Tax (NRT) Compliance Engine (v54.0.0).

Implements Natural Resources Tax calculations and audits under Luật Thuế tài nguyên
45/2009/QH12 as amended by Luật 71/2014/QH13 covering:
- Metallic ore extraction (iron, copper, gold, tin).
- Non-metallic minerals (granite, sand, marble, limestone).
- Water resources (surface water, groundwater) with agricultural and hydropower exemptions.
- Natural timber and plantation timber.
- Marine products (aquatic products, pearls/coral).
- Self-consumed resource rate adjustments (70% of standard rate).
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional
from invoices.multitenant_service import get_tenant_db_path


class V54ComplianceService:
    """Natural Resources Tax Law 45/2009/QH12 compliance engine."""

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
            CREATE TABLE IF NOT EXISTS nrt_mineral_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mineral_name TEXT NOT NULL,
                mineral_category TEXT NOT NULL,
                quantity REAL NOT NULL,
                unit_price REAL NOT NULL,
                nrt_rate REAL NOT NULL,
                nrt_amount REAL NOT NULL,
                is_self_consumed BOOLEAN NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS nrt_water_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                water_source TEXT NOT NULL,
                usage_purpose TEXT NOT NULL,
                volume_m3 REAL NOT NULL,
                unit_price REAL NOT NULL,
                nrt_rate REAL NOT NULL,
                nrt_amount REAL NOT NULL,
                is_exempt BOOLEAN NOT NULL,
                exemption_reason TEXT,
                hydropower_capacity_mw REAL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS nrt_timber_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timber_name TEXT NOT NULL,
                timber_source TEXT NOT NULL,
                volume_m3 REAL NOT NULL,
                unit_price REAL NOT NULL,
                nrt_rate REAL NOT NULL,
                nrt_amount REAL NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS nrt_marine_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT NOT NULL,
                product_category TEXT NOT NULL,
                quantity_kg REAL NOT NULL,
                unit_price REAL NOT NULL,
                nrt_rate REAL NOT NULL,
                nrt_amount REAL NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        return conn

    # ───────────────────── US-660 & US-661: Mineral NRT Calculation ──────────────────
    def calculate_mineral_nrt(
        self, mst: str, mineral_name: str, mineral_category: str, quantity: float,
        unit_price: float, is_self_consumed: bool = False
    ) -> Dict[str, Any]:
        """Calculate NRT for metallic ores and non-metallic minerals with self-consumption adjustment."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        # Rate tables
        metallic_rates = {
            "iron": 0.12,
            "copper": 0.13,
            "gold": 0.15,
            "tin": 0.20
        }
        nonmetallic_rates = {
            "granite": 0.08,
            "sand": 0.07,
            "marble": 0.09,
            "limestone": 0.05
        }

        cat_key = mineral_category.lower().strip()
        mineral_key = mineral_name.lower().strip()

        # Determine rate
        if cat_key == "metallic" or cat_key == "metal":
            nrt_rate = metallic_rates.get("iron")  # default
            for key, rate in metallic_rates.items():
                if key in mineral_key:
                    nrt_rate = rate
                    break
        else:
            nrt_rate = nonmetallic_rates.get("granite")  # default
            for key, rate in nonmetallic_rates.items():
                if key in mineral_key:
                    nrt_rate = rate
                    break

        # Self-consumed resources: 70% of the standard rate
        effective_rate = nrt_rate
        if is_self_consumed:
            effective_rate = nrt_rate * 0.70

        taxable_value = quantity * unit_price
        nrt_amount = taxable_value * effective_rate

        if is_self_consumed:
            notes = f"Self-consumed: Mineral '{mineral_name}' ({cat_key}) taxed at 70% of standard rate ({nrt_rate*100:.0f}% → {effective_rate*100:.1f}%). Taxable value: {taxable_value:,.0f} VND. NRT: {nrt_amount:,.0f} VND."
        else:
            notes = f"Calculated: Mineral '{mineral_name}' ({cat_key}) taxed at {nrt_rate*100:.0f}%. Taxable value: {taxable_value:,.0f} VND. NRT: {nrt_amount:,.0f} VND."

        cur.execute("""
            INSERT INTO nrt_mineral_logs
                (mineral_name, mineral_category, quantity, unit_price, nrt_rate, nrt_amount, is_self_consumed, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (mineral_name, mineral_category, quantity, unit_price, effective_rate, nrt_amount, is_self_consumed, notes))

        conn.commit()
        conn.close()

        return {
            "mineral_name": mineral_name,
            "mineral_category": mineral_category,
            "quantity": quantity,
            "unit_price": unit_price,
            "nrt_rate": effective_rate,
            "standard_rate": nrt_rate,
            "nrt_amount": nrt_amount,
            "is_self_consumed": is_self_consumed,
            "notes": notes
        }

    # ───────────────────── US-660 & US-661: Water NRT Calculation ──────────────────
    def calculate_water_nrt(
        self, mst: str, water_source: str, usage_purpose: str, volume_m3: float,
        unit_price: float, hydropower_capacity_mw: float = 0.0
    ) -> Dict[str, Any]:
        """Calculate NRT for water resources with agricultural and hydropower exemptions."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        source_key = water_source.lower().strip()
        usage_key = usage_purpose.lower().strip()

        # Rate lookup
        if "ground" in source_key:
            nrt_rate = 0.04  # Groundwater default 4%
        else:
            nrt_rate = 0.02  # Surface water default 2%

        is_exempt = False
        exemption_reason = ""

        # Exemption: Agricultural water
        if usage_key in ["agriculture", "forestry", "fishery", "salt_production", "agricultural"]:
            is_exempt = True
            nrt_amount = 0.0
            exemption_reason = "Agricultural/Forestry/Fishery"
            notes = f"Exempt: Water from '{water_source}' used for {usage_purpose}. NRT rate of {nrt_rate*100:.0f}% waived under Article 9.1 (agricultural use)."
        # Exemption: Small-scale hydropower ≤ 2MW
        elif usage_key in ["hydropower", "hydro"] and hydropower_capacity_mw <= 2.0:
            is_exempt = True
            nrt_amount = 0.0
            exemption_reason = f"Small-Scale Hydropower (≤ 2MW, actual: {hydropower_capacity_mw:.1f}MW)"
            notes = f"Exempt: Hydropower station (capacity {hydropower_capacity_mw:.1f}MW ≤ 2MW threshold). NRT rate of {nrt_rate*100:.0f}% waived under Article 9.3."
        else:
            taxable_value = volume_m3 * unit_price
            nrt_amount = taxable_value * nrt_rate
            notes = f"Calculated: Water from '{water_source}' for {usage_purpose} ({volume_m3:,.0f} m³) taxed at {nrt_rate*100:.0f}%. Taxable value: {taxable_value:,.0f} VND. NRT: {nrt_amount:,.0f} VND."

        cur.execute("""
            INSERT INTO nrt_water_logs
                (water_source, usage_purpose, volume_m3, unit_price, nrt_rate, nrt_amount, is_exempt, exemption_reason, hydropower_capacity_mw, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (water_source, usage_purpose, volume_m3, unit_price, nrt_rate, nrt_amount, is_exempt, exemption_reason, hydropower_capacity_mw, notes))

        conn.commit()
        conn.close()

        return {
            "water_source": water_source,
            "usage_purpose": usage_purpose,
            "volume_m3": volume_m3,
            "unit_price": unit_price,
            "nrt_rate": nrt_rate,
            "nrt_amount": nrt_amount,
            "is_exempt": is_exempt,
            "exemption_reason": exemption_reason,
            "hydropower_capacity_mw": hydropower_capacity_mw,
            "notes": notes
        }

    # ───────────────────── US-660: Timber NRT Calculation ──────────────────
    def calculate_timber_nrt(
        self, mst: str, timber_name: str, timber_source: str, volume_m3: float,
        unit_price: float
    ) -> Dict[str, Any]:
        """Calculate NRT for natural forest timber and plantation timber."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        source_key = timber_source.lower().strip()

        if "natural" in source_key or "forest" in source_key:
            nrt_rate = 0.25  # Natural forest hardwood default 25%
        elif "plantation" in source_key or "planted" in source_key:
            nrt_rate = 0.03  # Plantation timber default 3%
        else:
            nrt_rate = 0.10  # Generic timber default 10%

        taxable_value = volume_m3 * unit_price
        nrt_amount = taxable_value * nrt_rate

        notes = f"Calculated: Timber '{timber_name}' (source: {timber_source}, {volume_m3:,.1f} m³) taxed at {nrt_rate*100:.0f}%. Taxable value: {taxable_value:,.0f} VND. NRT: {nrt_amount:,.0f} VND."

        cur.execute("""
            INSERT INTO nrt_timber_logs
                (timber_name, timber_source, volume_m3, unit_price, nrt_rate, nrt_amount, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (timber_name, timber_source, volume_m3, unit_price, nrt_rate, nrt_amount, notes))

        conn.commit()
        conn.close()

        return {
            "timber_name": timber_name,
            "timber_source": timber_source,
            "volume_m3": volume_m3,
            "unit_price": unit_price,
            "nrt_rate": nrt_rate,
            "nrt_amount": nrt_amount,
            "notes": notes
        }

    # ───────────────────── US-660: Marine Products NRT Calculation ──────────────────
    def calculate_marine_nrt(
        self, mst: str, product_name: str, product_category: str, quantity_kg: float,
        unit_price: float
    ) -> Dict[str, Any]:
        """Calculate NRT for natural aquatic products and pearls/coral."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        cat_key = product_category.lower().strip()

        if "pearl" in cat_key or "coral" in cat_key:
            nrt_rate = 0.08  # Pearls/Coral default 8%
        else:
            nrt_rate = 0.02  # Natural aquatic products default 2%

        taxable_value = quantity_kg * unit_price
        nrt_amount = taxable_value * nrt_rate

        notes = f"Calculated: Marine product '{product_name}' ({cat_key}, {quantity_kg:,.1f} kg) taxed at {nrt_rate*100:.0f}%. Taxable value: {taxable_value:,.0f} VND. NRT: {nrt_amount:,.0f} VND."

        cur.execute("""
            INSERT INTO nrt_marine_logs
                (product_name, product_category, quantity_kg, unit_price, nrt_rate, nrt_amount, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (product_name, product_category, quantity_kg, unit_price, nrt_rate, nrt_amount, notes))

        conn.commit()
        conn.close()

        return {
            "product_name": product_name,
            "product_category": product_category,
            "quantity_kg": quantity_kg,
            "unit_price": unit_price,
            "nrt_rate": nrt_rate,
            "nrt_amount": nrt_amount,
            "notes": notes
        }
