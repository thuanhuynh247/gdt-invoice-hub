"""CIT Law Amendments 67/2025/QH15 Compliance Engine (v49.0.0).

Implements the 2025 amendments to the Corporate Income Tax (CIT) Law covering:
- Revenue-scaled SME CIT rates (15% / 17% / 20%)
- Real estate transfer loss offsetting against production income
- Digital platform CIT liability for foreign providers
- Tax exemptions for carbon credit transfers and green bond interest
"""

from __future__ import annotations

import os
import sqlite3
from typing import Dict, Any, List, Optional
from invoices.multitenant_service import get_tenant_db_path


class V49ComplianceService:
    """CIT Law Amendments 67/2025/QH15 compliance engine."""

    SME_THRESHOLD_1_VND = 3_000_000_000        # < 3B -> 15%
    SME_THRESHOLD_2_VND = 50_000_000_000       # 3B - 50B -> 17%

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
            CREATE TABLE IF NOT EXISTS sme_cit_classifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_name TEXT NOT NULL,
                annual_revenue REAL NOT NULL,
                has_transfer_pricing INTEGER DEFAULT 0,
                classified_rate REAL NOT NULL,
                is_sme INTEGER DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS re_loss_offset_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tax_year INTEGER NOT NULL,
                main_income REAL NOT NULL,
                re_loss REAL NOT NULL,
                offset_applied REAL NOT NULL,
                final_taxable_income REAL NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS digital_cit_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendor_name TEXT NOT NULL,
                is_foreign_platform INTEGER DEFAULT 0,
                transaction_amount REAL NOT NULL,
                component_type TEXT NOT NULL,  -- 'service' or 'trade'
                withholding_rate REAL NOT NULL,
                withholding_tax REAL NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS green_exemption_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_description TEXT NOT NULL,
                exemption_type TEXT NOT NULL,  -- 'carbon_credit' or 'green_bond' or 'none'
                amount REAL NOT NULL,
                is_exempt INTEGER DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        return conn

    # ───────────────────── Pillar 1: SME CIT Rate Classification ──────────────────
    def classify_sme_cit(
        self, mst: str, business_name: str, annual_revenue: float, has_transfer_pricing: bool = False
    ) -> Dict[str, Any]:
        """Evaluate SME corporate tax rate eligibility under the Law 67 Article 10 amendment."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        is_sme = False
        classified_rate = 20.0  # Standard CIT rate

        if has_transfer_pricing:
            notes = "Standard 20% rate applied: Company is in a transfer pricing relationship (exemption disallowed)."
        elif annual_revenue < self.SME_THRESHOLD_1_VND:
            classified_rate = 15.0
            is_sme = True
            notes = f"SME Tier 1 rate (15%) applied: Revenue {annual_revenue:,.0f} VND is under 3B VND."
        elif annual_revenue < self.SME_THRESHOLD_2_VND:
            classified_rate = 17.0
            is_sme = True
            notes = f"SME Tier 2 rate (17%) applied: Revenue {annual_revenue:,.0f} VND is between 3B and 50B VND."
        else:
            notes = f"Standard 20% rate applied: Revenue {annual_revenue:,.0f} VND is 50B VND or above."

        cur.execute("""
            INSERT INTO sme_cit_classifications
                (business_name, annual_revenue, has_transfer_pricing, classified_rate, is_sme, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (business_name, annual_revenue, 1 if has_transfer_pricing else 0, classified_rate, 1 if is_sme else 0, notes))

        conn.commit()
        conn.close()

        return {
            "business_name": business_name,
            "annual_revenue": annual_revenue,
            "has_transfer_pricing": has_transfer_pricing,
            "classified_rate": f"{classified_rate}%",
            "is_sme": is_sme,
            "notes": notes
        }

    # ───────────────────── Pillar 1: Real Estate Loss Offsetting ──────────────────
    def apply_re_loss_offset(
        self, mst: str, tax_year: int, main_income: float, re_loss: float
    ) -> Dict[str, Any]:
        """Compute the final taxable income by offsetting real estate transfer losses against main income."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        offset_applied = min(main_income, re_loss)
        final_taxable_income = max(0.0, main_income - offset_applied)

        notes = (
            f"Under Law 67/2025/QH15: Offset {offset_applied:,.0f} VND of real estate losses "
            f"directly against main income of {main_income:,.0f} VND. Remaining taxable income: {final_taxable_income:,.0f} VND."
        )

        cur.execute("""
            INSERT INTO re_loss_offset_logs
                (tax_year, main_income, re_loss, offset_applied, final_taxable_income, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (tax_year, main_income, re_loss, offset_applied, final_taxable_income, notes))

        conn.commit()
        conn.close()

        return {
            "tax_year": tax_year,
            "main_income": main_income,
            "re_loss": re_loss,
            "offset_applied": offset_applied,
            "final_taxable_income": final_taxable_income,
            "notes": notes
        }

    # ───────────────────── Pillar 2: Digital Platform CIT Liability ──────────────────
    def audit_digital_cit(
        self, mst: str, vendor_name: str, is_foreign_platform: bool, amount: float, component_type: str
    ) -> Dict[str, Any]:
        """Audit foreign digital service purchases for withholding tax under Law 67."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        if is_foreign_platform:
            # Component type check
            if component_type.lower() == "service":
                rate = 5.0  # 5% for service component
            else:
                rate = 1.0  # 1% for trade/goods component
            tax_withheld = amount * (rate / 100.0)
            notes = (
                f"Withholding liability: {rate}% CIT rate applied on {amount:,.0f} VND "
                f"purchased from foreign digital vendor {vendor_name} ({component_type} component)."
            )
        else:
            rate = 0.0
            tax_withheld = 0.0
            notes = f"No withholding liability: Vendor {vendor_name} is a local taxpayer or has permanent establishment."

        cur.execute("""
            INSERT INTO digital_cit_audit_log
                (vendor_name, is_foreign_platform, transaction_amount, component_type, withholding_rate, withholding_tax, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (vendor_name, 1 if is_foreign_platform else 0, amount, component_type, rate, tax_withheld, notes))

        conn.commit()
        conn.close()

        return {
            "vendor_name": vendor_name,
            "is_foreign_platform": is_foreign_platform,
            "transaction_amount": amount,
            "component_type": component_type,
            "withholding_rate": f"{rate}%",
            "withholding_tax": tax_withheld,
            "notes": notes
        }

    # ───────────────────── Pillar 2: Carbon Credit & Green Bond Exemption ──────────────────
    def scan_green_exemptions(
        self, mst: str, item_description: str, amount: float
    ) -> Dict[str, Any]:
        """Scan transaction for green bond/carbon credit exemptions under Law 67."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        desc_lower = item_description.lower()
        exemption_type = "none"
        is_exempt = False
        notes = "No green exemption applies."

        if "carbon" in desc_lower or "tín chỉ giảm phát thải" in desc_lower or "tín chỉ các-bon" in desc_lower:
            exemption_type = "carbon_credit"
            is_exempt = True
            notes = "Exempt: First-time transfer of carbon credits under Law 67/2025/QH15 Article 8."
        elif "green bond" in desc_lower or "trái phiếu xanh" in desc_lower:
            exemption_type = "green_bond"
            is_exempt = True
            notes = "Exempt: Green bond interest or first-time green bond transfer under Law 67/2025/QH15 Article 8."

        cur.execute("""
            INSERT INTO green_exemption_logs
                (item_description, exemption_type, amount, is_exempt, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (item_description, exemption_type, amount, 1 if is_exempt else 0, notes))

        conn.commit()
        conn.close()

        return {
            "item_description": item_description,
            "exemption_type": exemption_type,
            "amount": amount,
            "is_exempt": is_exempt,
            "notes": notes
        }
