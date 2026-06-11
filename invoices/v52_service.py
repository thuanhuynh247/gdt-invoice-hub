"""Special Consumption Tax (SCT) Law No. 66/2025/QH15 Compliance Engine (v52.0.0).

Implements the Special Consumption Tax calculations and audits covering:
- Sugary beverages tax classification and rate roadmap (2026-2028).
- Air conditioner capacity (BTU) audit threshold.
- Inland sales into non-tariff areas (excluding cars under 24 seats).
- Taxable price adjustments for promotional goods based on identical/equivalent prices.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional
from invoices.multitenant_service import get_tenant_db_path


class V52ComplianceService:
    """Special Consumption Tax (SCT) Law No. 66/2025/QH15 compliance engine."""

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
            CREATE TABLE IF NOT EXISTS sugary_beverage_sct_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                drink_name TEXT NOT NULL,
                sugar_content REAL NOT NULL,
                category TEXT NOT NULL,
                year INTEGER NOT NULL,
                price_before_tax REAL NOT NULL,
                sct_rate REAL NOT NULL,
                sct_amount REAL NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS air_conditioner_sct_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name TEXT NOT NULL,
                capacity_btu REAL NOT NULL,
                price_before_tax REAL NOT NULL,
                sct_rate REAL NOT NULL,
                sct_amount REAL NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS nontariff_sct_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT NOT NULL,
                destination TEXT NOT NULL,
                is_car_under_24_seats BOOLEAN NOT NULL,
                price_before_tax REAL NOT NULL,
                sct_rate REAL NOT NULL,
                sct_amount REAL NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS promotion_sct_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT NOT NULL,
                promo_price REAL NOT NULL,
                equivalent_price REAL NOT NULL,
                quantity INTEGER NOT NULL,
                sct_rate REAL NOT NULL,
                sct_amount REAL NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        return conn

    # ───────────────────── Pillar 1: Sugary Beverages SCT ──────────────────
    def calculate_sugary_beverage_sct(
        self, mst: str, drink_name: str, sugar_content: float, category: str, year: int, price_before_tax: float
    ) -> Dict[str, Any]:
        """Calculate SCT for sugary beverages under the Law 66 roadmap (2026-2028)."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        # Exclude milk, dairy products, 100% fruit juice, coconut water, mineral water, nectar
        excluded_categories = ["milk", "dairy", "100% fruit juice", "coconut water", "mineral water", "nectar"]
        is_excluded = any(ex_cat in category.lower() for ex_cat in excluded_categories)

        sct_rate = 0.0
        if is_excluded:
            notes = f"Exempt: '{drink_name}' categorized as '{category}' is excluded from sugary beverage SCT."
        elif sugar_content <= 5.0:
            notes = f"Compliant: Sugar content ({sugar_content}g/100ml) is within the <= 5g/100ml exemption limit."
        else:
            # Sugar content > 5g/100ml: Apply tax roadmap
            if year <= 2026:
                sct_rate = 0.0
                notes = f"Roadmap 2026: Tax rate is 0% for sugar content > 5g/100ml ({sugar_content}g/100ml)."
            elif year == 2027:
                sct_rate = 0.08
                notes = f"Roadmap 2027: Tax rate is 8% for sugar content > 5g/100ml ({sugar_content}g/100ml)."
            else:
                sct_rate = 0.10
                notes = f"Roadmap 2028+: Tax rate is 10% for sugar content > 5g/100ml ({sugar_content}g/100ml)."

        sct_amount = price_before_tax * sct_rate

        cur.execute("""
            INSERT INTO sugary_beverage_sct_logs
                (drink_name, sugar_content, category, year, price_before_tax, sct_rate, sct_amount, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (drink_name, sugar_content, category, year, price_before_tax, sct_rate, sct_amount, notes))

        conn.commit()
        conn.close()

        return {
            "drink_name": drink_name,
            "sugar_content": sugar_content,
            "category": category,
            "year": year,
            "price_before_tax": price_before_tax,
            "sct_rate": sct_rate,
            "sct_amount": sct_amount,
            "notes": notes
        }

    # ───────────────────── Pillar 1: Air Conditioner SCT ──────────────────
    def calculate_air_conditioner_sct(
        self, mst: str, model_name: str, capacity_btu: float, price_before_tax: float
    ) -> Dict[str, Any]:
        """Classify and calculate SCT for air conditioners based on BTU capacity."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        # Air conditioners > 24,000 BTU and <= 90,000 BTU are subject to SCT at 10%
        if 24000.0 < capacity_btu <= 90000.0:
            sct_rate = 0.10
            notes = f"Taxable: Capacity ({capacity_btu:,.0f} BTU) is within taxable range (24,000 - 90,000 BTU). Rate: 10%."
        else:
            sct_rate = 0.0
            notes = f"Exempt: Capacity ({capacity_btu:,.0f} BTU) is outside taxable range (24,000 - 90,000 BTU)."

        sct_amount = price_before_tax * sct_rate

        cur.execute("""
            INSERT INTO air_conditioner_sct_logs
                (model_name, capacity_btu, price_before_tax, sct_rate, sct_amount, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (model_name, capacity_btu, price_before_tax, sct_rate, sct_amount, notes))

        conn.commit()
        conn.close()

        return {
            "model_name": model_name,
            "capacity_btu": capacity_btu,
            "price_before_tax": price_before_tax,
            "sct_rate": sct_rate,
            "sct_amount": sct_amount,
            "notes": notes
        }

    # ───────────────────── Pillar 2: Inland to Non-Tariff Area ──────────────────
    def calculate_nontariff_sct(
        self, mst: str, item_name: str, destination: str, is_car_under_24_seats: bool, price_before_tax: float
    ) -> Dict[str, Any]:
        """Audit inland transactions sold to non-tariff zones for SCT liability."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        # Under Law 66, inland sales to non-tariff areas are subject to SCT,
        # EXCEPT for cars with fewer than 24 seats (to avoid duplicate SCT structures).
        if is_car_under_24_seats:
            sct_rate = 0.0
            notes = f"Exempt under Non-Tariff Rule: '{item_name}' is a passenger car with < 24 seats (subject to separate inland SCT)."
        else:
            sct_rate = 0.10  # Standard generic SCT rate for non-tariff sale audit
            notes = f"Taxable under Non-Tariff Rule: '{item_name}' sold from inland to non-tariff zone '{destination}' is subject to SCT."

        sct_amount = price_before_tax * sct_rate

        cur.execute("""
            INSERT INTO nontariff_sct_logs
                (item_name, destination, is_car_under_24_seats, price_before_tax, sct_rate, sct_amount, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (item_name, destination, is_car_under_24_seats, price_before_tax, sct_rate, sct_amount, notes))

        conn.commit()
        conn.close()

        return {
            "item_name": item_name,
            "destination": destination,
            "is_car_under_24_seats": is_car_under_24_seats,
            "price_before_tax": price_before_tax,
            "sct_rate": sct_rate,
            "sct_amount": sct_amount,
            "notes": notes
        }

    # ───────────────────── Pillar 2: Promotion Price Auditor ──────────────────
    def calculate_promotion_sct(
        self, mst: str, item_name: str, promo_price: float, equivalent_price: float, quantity: int, sct_rate: float = 0.10
    ) -> Dict[str, Any]:
        """Compute SCT for promotional goods using identical/equivalent market values under Law 66."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        # Under Law 66, taxable price of promotional/ad products is equivalent product value
        tax_base_per_unit = equivalent_price
        total_tax_base = tax_base_per_unit * quantity
        sct_amount = total_tax_base * sct_rate

        notes = (
            f"Tax Base Adjusted: Promotion price is {promo_price:,.0f} VND. "
            f"SCT calculated on equivalent market price {equivalent_price:,.0f} VND "
            f"for qty {quantity} (Total Base: {total_tax_base:,.0f} VND, Rate: {sct_rate * 100:.1f}%)."
        )

        cur.execute("""
            INSERT INTO promotion_sct_logs
                (item_name, promo_price, equivalent_price, quantity, sct_rate, sct_amount, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (item_name, promo_price, equivalent_price, quantity, sct_rate, sct_amount, notes))

        conn.commit()
        conn.close()

        return {
            "item_name": item_name,
            "promo_price": promo_price,
            "equivalent_price": equivalent_price,
            "quantity": quantity,
            "sct_rate": sct_rate,
            "sct_amount": sct_amount,
            "notes": notes
        }
