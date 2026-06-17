"""Environmental Protection (EP) Tax Compliance Engine (v53.0.0).

Implements Environmental Protection Tax calculations and audits under Law 57/2010/QH12 covering:
- Petrol, Diesel oil, Kerosene rate calculations.
- Lignite, Anthracite, and Other coal rate calculations.
- Plastic bags and HCFC chemical rate calculations.
- Exemption rules for biodegradable plastics, coal for electricity or export, and re-export fuels.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional
from invoices.multitenant_service import get_tenant_db_path


class V53ComplianceService:
    """Environmental Protection (EP) Tax Law No. 57/2010/QH12 compliance engine."""

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
            CREATE TABLE IF NOT EXISTS ep_tax_fuel_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fuel_type TEXT NOT NULL,
                quantity_litres REAL NOT NULL,
                price_before_tax REAL NOT NULL,
                ep_tax_rate REAL NOT NULL,
                ep_tax_amount REAL NOT NULL,
                is_exempt BOOLEAN NOT NULL,
                exemption_reason TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS ep_tax_coal_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                coal_type TEXT NOT NULL,
                quantity_tonnes REAL NOT NULL,
                price_before_tax REAL NOT NULL,
                ep_tax_rate REAL NOT NULL,
                ep_tax_amount REAL NOT NULL,
                is_exempt BOOLEAN NOT NULL,
                exemption_reason TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS ep_tax_plastic_bag_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bag_name TEXT NOT NULL,
                weight_kg REAL NOT NULL,
                price_before_tax REAL NOT NULL,
                is_certified_biodegradable BOOLEAN NOT NULL,
                ep_tax_rate REAL NOT NULL,
                ep_tax_amount REAL NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS ep_tax_chemical_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chemical_name TEXT NOT NULL,
                weight_kg REAL NOT NULL,
                price_before_tax REAL NOT NULL,
                ep_tax_rate REAL NOT NULL,
                ep_tax_amount REAL NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        return conn

    # ───────────────────── US-650 & US-651: Fuel EP Tax Calculation ──────────────────
    def calculate_fuel_ep_tax(
        self, mst: str, fuel_type: str, quantity_litres: float, price_before_tax: float, is_transit_or_reexport: bool = False
    ) -> Dict[str, Any]:
        """Calculate EP tax for petrol, diesel, and kerosene with transit/re-export exemptions."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        # Rates lookup
        rates = {
            "petrol": 2000.0,
            "diesel": 1000.0,
            "kerosene": 600.0
        }
        
        fuel_key = fuel_type.lower().strip()
        ep_tax_rate = rates.get(fuel_key, 0.0)
        
        is_exempt = False
        exemption_reason = ""
        
        if is_transit_or_reexport:
            is_exempt = True
            ep_tax_amount = 0.0
            exemption_reason = "Transit/Re-export"
            notes = f"Exempt: Fuel '{fuel_type}' was temporarily imported for transit/re-export. EP tax rate of {ep_tax_rate:,.0f} VND/l waived."
        else:
            ep_tax_amount = quantity_litres * ep_tax_rate
            notes = f"Calculated: Fuel '{fuel_type}' (Qty: {quantity_litres:,.1f}l) taxed at absolute rate {ep_tax_rate:,.0f} VND/l. Total EP Tax: {ep_tax_amount:,.0f} VND."

        cur.execute("""
            INSERT INTO ep_tax_fuel_logs
                (fuel_type, quantity_litres, price_before_tax, ep_tax_rate, ep_tax_amount, is_exempt, exemption_reason, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (fuel_type, quantity_litres, price_before_tax, ep_tax_rate, ep_tax_amount, is_exempt, exemption_reason, notes))

        conn.commit()
        conn.close()

        return {
            "fuel_type": fuel_type,
            "quantity_litres": quantity_litres,
            "price_before_tax": price_before_tax,
            "ep_tax_rate": ep_tax_rate,
            "ep_tax_amount": ep_tax_amount,
            "is_exempt": is_exempt,
            "exemption_reason": exemption_reason,
            "notes": notes
        }

    # ───────────────────── US-650 & US-651: Coal EP Tax Calculation ──────────────────
    def calculate_coal_ep_tax(
        self, mst: str, coal_type: str, quantity_tonnes: float, price_before_tax: float, usage: str = "other"
    ) -> Dict[str, Any]:
        """Calculate coal EP tax by type (lignite/sub-bituminous, anthracite, other) with electricity/export exemptions."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        # Rates lookup
        rates = {
            "anthracite": 30000.0,
            "lignite": 20000.0,
            "sub-bituminous": 20000.0,
            "other": 15000.0
        }
        
        coal_key = coal_type.lower().strip()
        # Find matching rate
        ep_tax_rate = rates.get("other")
        for key, rate in rates.items():
            if key in coal_key:
                ep_tax_rate = rate
                break
                
        is_exempt = False
        exemption_reason = ""
        
        usage_key = usage.lower().strip()
        if usage_key in ["electricity_generation", "electricity", "export"]:
            is_exempt = True
            ep_tax_amount = 0.0
            exemption_reason = "Electricity Generation" if "elect" in usage_key else "Export"
            notes = f"Exempt: Coal '{coal_type}' utilized for {exemption_reason.lower()}. EP tax rate of {ep_tax_rate:,.0f} VND/tonne waived."
        else:
            ep_tax_amount = quantity_tonnes * ep_tax_rate
            notes = f"Calculated: Coal '{coal_type}' (Qty: {quantity_tonnes:,.1f} tonnes) taxed at absolute rate {ep_tax_rate:,.0f} VND/tonne. Total EP Tax: {ep_tax_amount:,.0f} VND."

        cur.execute("""
            INSERT INTO ep_tax_coal_logs
                (coal_type, quantity_tonnes, price_before_tax, ep_tax_rate, ep_tax_amount, is_exempt, exemption_reason, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (coal_type, quantity_tonnes, price_before_tax, ep_tax_rate, ep_tax_amount, is_exempt, exemption_reason, notes))

        conn.commit()
        conn.close()

        return {
            "coal_type": coal_type,
            "quantity_tonnes": quantity_tonnes,
            "price_before_tax": price_before_tax,
            "ep_tax_rate": ep_tax_rate,
            "ep_tax_amount": ep_tax_amount,
            "is_exempt": is_exempt,
            "exemption_reason": exemption_reason,
            "notes": notes
        }

    # ───────────────────── US-650 & US-651: Plastic Bag EP Tax Calculation ──────────
    def calculate_plastic_bag_ep_tax(
        self, mst: str, bag_name: str, weight_kg: float, price_before_tax: float, is_certified_biodegradable: bool = False
    ) -> Dict[str, Any]:
        """Calculate EP tax for plastic bags (50,000 VND/kg) with 100% biodegradable exemption."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        ep_tax_rate = 50000.0
        
        if is_certified_biodegradable:
            ep_tax_amount = 0.0
            notes = f"Exempt: Plastic bag '{bag_name}' is certified biodegradable. EP tax rate of {ep_tax_rate:,.0f} VND/kg waived."
        else:
            ep_tax_amount = weight_kg * ep_tax_rate
            notes = f"Calculated: Non-biodegradable bag '{bag_name}' (Weight: {weight_kg:,.2f} kg) taxed at absolute rate {ep_tax_rate:,.0f} VND/kg. Total EP Tax: {ep_tax_amount:,.0f} VND."

        cur.execute("""
            INSERT INTO ep_tax_plastic_bag_logs
                (bag_name, weight_kg, price_before_tax, is_certified_biodegradable, ep_tax_rate, ep_tax_amount, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (bag_name, weight_kg, price_before_tax, is_certified_biodegradable, ep_tax_rate, ep_tax_amount, notes))

        conn.commit()
        conn.close()

        return {
            "bag_name": bag_name,
            "weight_kg": weight_kg,
            "price_before_tax": price_before_tax,
            "is_certified_biodegradable": is_certified_biodegradable,
            "ep_tax_rate": ep_tax_rate,
            "ep_tax_amount": ep_tax_amount,
            "notes": notes
        }

    # ───────────────────── US-650: Chemical EP Tax Calculation ──────────────────
    def calculate_chemical_ep_tax(
        self, mst: str, chemical_name: str, weight_kg: float, price_before_tax: float
    ) -> Dict[str, Any]:
        """Calculate EP tax for chemicals (HCFC: 5,000 VND/kg, others 0.0 or custom if not HCFC)."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        chem_key = chemical_name.lower().strip()
        if "hcfc" in chem_key:
            ep_tax_rate = 5000.0
            ep_tax_amount = weight_kg * ep_tax_rate
            notes = f"Calculated: HCFC chemical '{chemical_name}' (Weight: {weight_kg:,.2f} kg) taxed at absolute rate {ep_tax_rate:,.0f} VND/kg. Total EP Tax: {ep_tax_amount:,.0f} VND."
        else:
            ep_tax_rate = 0.0
            ep_tax_amount = 0.0
            notes = f"Compliant: Chemical '{chemical_name}' is not classified under taxable HCFC compounds."

        cur.execute("""
            INSERT INTO ep_tax_chemical_logs
                (chemical_name, weight_kg, price_before_tax, ep_tax_rate, ep_tax_amount, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (chemical_name, weight_kg, price_before_tax, ep_tax_rate, ep_tax_amount, notes))

        conn.commit()
        conn.close()

        return {
            "chemical_name": chemical_name,
            "weight_kg": weight_kg,
            "price_before_tax": price_before_tax,
            "ep_tax_rate": ep_tax_rate,
            "ep_tax_amount": ep_tax_amount,
            "notes": notes
        }
