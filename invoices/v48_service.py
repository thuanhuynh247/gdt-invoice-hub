"""VAT Law Amendments 149/2025/QH15 Compliance Engine (v48.0.0).

Implements the 2025 amendments to the Vietnamese VAT Law covering:
- Revenue threshold reclassification (200M → 500M VND/year)
- Agricultural product VAT exemption updates (enterprise-to-enterprise)
- Waste/scrap tax rate revisions
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional
from invoices.multitenant_service import get_tenant_db_path


class V48ComplianceService:
    """VAT Law Amendments 149/2025/QH15 compliance engine."""

    # New threshold per Law 149 amendment to Article 5.25
    NEW_THRESHOLD_VND = 500_000_000
    OLD_THRESHOLD_VND = 200_000_000

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
            CREATE TABLE IF NOT EXISTS threshold_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_name TEXT NOT NULL,
                annual_revenue REAL NOT NULL,
                old_status TEXT NOT NULL,
                new_status TEXT NOT NULL,
                pit_impact TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS agri_product_classifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_description TEXT NOT NULL,
                seller_type TEXT NOT NULL,
                buyer_type TEXT NOT NULL,
                old_vat_treatment TEXT NOT NULL,
                new_vat_treatment TEXT NOT NULL,
                input_credit_deductible INTEGER DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS waste_scrap_rate_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_description TEXT NOT NULL,
                source_product TEXT NOT NULL,
                old_rate TEXT NOT NULL,
                new_rate TEXT NOT NULL,
                amount REAL DEFAULT 0,
                vat_computed REAL DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        return conn

    # ───────────────────── Pillar 1: Revenue Threshold ──────────────────
    def evaluate_threshold(
        self, mst: str, business_name: str, annual_revenue: float
    ) -> Dict[str, Any]:
        """Evaluate household/individual business VAT status under new 500M threshold."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        # Old status under Law 48 Article 5.25 (200M threshold)
        old_exempt = annual_revenue <= self.OLD_THRESHOLD_VND
        old_status = "NON_TAXABLE" if old_exempt else "TAXABLE"

        # New status under Law 149 amendment (500M threshold)
        new_exempt = annual_revenue <= self.NEW_THRESHOLD_VND
        new_status = "NON_TAXABLE" if new_exempt else "TAXABLE"

        # PIT impact: under Article 17 amendment, income below threshold
        # is excluded from PIT taxable income
        pit_impact = None
        if new_exempt and not old_exempt:
            pit_impact = (
                f"RECLASSIFIED: Revenue {annual_revenue:,.0f} VND was TAXABLE under old 200M threshold "
                f"but is now NON_TAXABLE under new 500M threshold. PIT Article 3 exclusion applies."
            )
        elif new_exempt and old_exempt:
            pit_impact = "NO_CHANGE: Already exempt under both old and new thresholds."
        else:
            pit_impact = (
                f"STILL_TAXABLE: Revenue {annual_revenue:,.0f} VND exceeds both old (200M) "
                f"and new (500M) thresholds."
            )

        notes = None
        if new_exempt != old_exempt:
            notes = "STATUS_CHANGE per Law 149/2025/QH15 effective 01/01/2026"

        cur.execute("""
            INSERT INTO threshold_audit_log
                (business_name, annual_revenue, old_status, new_status, pit_impact, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (business_name, annual_revenue, old_status, new_status, pit_impact, notes))

        conn.commit()
        conn.close()

        return {
            "business_name": business_name,
            "annual_revenue": annual_revenue,
            "old_threshold": self.OLD_THRESHOLD_VND,
            "new_threshold": self.NEW_THRESHOLD_VND,
            "old_status": old_status,
            "new_status": new_status,
            "status_changed": old_status != new_status,
            "pit_impact": pit_impact,
        }

    # ──────────── Pillar 2: Agricultural Product Classification ──────────
    def classify_agri_product(
        self, mst: str, product_description: str,
        seller_type: str, buyer_type: str
    ) -> Dict[str, Any]:
        """Classify agricultural product VAT treatment under Law 149 amendments."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        is_enterprise_trade = (
            seller_type.lower() in ("enterprise", "doanh nghiệp", "cooperative", "hợp tác xã") and
            buyer_type.lower() in ("enterprise", "doanh nghiệp", "cooperative", "hợp tác xã")
        )

        # Old treatment: non-taxable per Article 5.1 (no input credit)
        old_treatment = "NON_TAXABLE_NO_CREDIT"

        # New treatment under Law 149:
        # Enterprise-to-enterprise trades of unprocessed agri products
        # → "no declaration required" but input credits ARE deductible
        if is_enterprise_trade:
            new_treatment = "NO_DECLARATION_REQUIRED_WITH_CREDIT"
            input_credit_deductible = True
            notes = (
                "Under Law 149 amendment to Article 5.1: Unprocessed agricultural products "
                "traded between enterprises/cooperatives are reclassified. Input VAT credits "
                "on related purchases remain deductible (unlike standard non-taxable items)."
            )
        else:
            new_treatment = "NON_TAXABLE_NO_CREDIT"
            input_credit_deductible = False
            notes = (
                "Standard non-taxable treatment applies. Seller is not enterprise/cooperative "
                "or buyer is not enterprise/cooperative."
            )

        cur.execute("""
            INSERT INTO agri_product_classifications
                (product_description, seller_type, buyer_type, old_vat_treatment,
                 new_vat_treatment, input_credit_deductible, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (product_description, seller_type, buyer_type, old_treatment,
              new_treatment, 1 if input_credit_deductible else 0, notes))

        conn.commit()
        conn.close()

        return {
            "product_description": product_description,
            "seller_type": seller_type,
            "buyer_type": buyer_type,
            "old_vat_treatment": old_treatment,
            "new_vat_treatment": new_treatment,
            "input_credit_deductible": input_credit_deductible,
            "treatment_changed": old_treatment != new_treatment,
        }

    # ──────────── Pillar 2: Waste/Scrap Rate Engine ──────────
    def compute_waste_scrap_rate(
        self, mst: str, item_description: str,
        source_product: str, waste_rate_pct: float,
        source_rate_pct: float, amount: float
    ) -> Dict[str, Any]:
        """Apply amended waste/scrap VAT rate rules per Law 149 Article 9.5."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        old_rate = f"{source_rate_pct}%"
        new_rate = f"{waste_rate_pct}%"

        # Compute VAT on waste using the NEW rate (waste item's own rate)
        vat_computed = amount * (waste_rate_pct / 100.0)

        # Old computation would have used source product rate
        old_vat = amount * (source_rate_pct / 100.0)

        notes = None
        if waste_rate_pct != source_rate_pct:
            savings = old_vat - vat_computed
            notes = (
                f"RATE_CHANGE per Law 149 Article 9.5: Waste/scrap now taxed at its own rate "
                f"({waste_rate_pct}%) instead of source product rate ({source_rate_pct}%). "
                f"VAT difference: {savings:,.0f} VND"
            )
        else:
            notes = "No rate difference — waste rate equals source product rate."

        cur.execute("""
            INSERT INTO waste_scrap_rate_log
                (item_description, source_product, old_rate, new_rate, amount, vat_computed, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (item_description, source_product, old_rate, new_rate, amount, vat_computed, notes))

        conn.commit()
        conn.close()

        return {
            "item_description": item_description,
            "source_product": source_product,
            "old_rate": old_rate,
            "new_rate": new_rate,
            "amount": amount,
            "vat_old": old_vat,
            "vat_new": vat_computed,
            "rate_changed": waste_rate_pct != source_rate_pct,
        }
