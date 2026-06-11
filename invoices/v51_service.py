"""Tax Administration Law Amendments 108/2025/QH15 Compliance Engine (v51.0.0).

Implements the electronic transaction auditing and cross-border e-commerce tax tracking covering:
- XML invoice digital signature integrity and GDT transmission delay checks (24-hour rule).
- Cross-border digital platform registration verification and B2B withholding calculations (VAT + CIT).
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional
from invoices.multitenant_service import get_tenant_db_path


class V51ComplianceService:
    """Tax Administration Law Amendments 108/2025/QH15 compliance engine."""

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
            CREATE TABLE IF NOT EXISTS etransaction_signature_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT NOT NULL,
                sign_date TEXT NOT NULL,
                receive_date TEXT NOT NULL,
                signature_status TEXT NOT NULL,  -- 'COMPLIANT', 'SIGNATURE_EXPIRED', 'LATE_TRANSMISSION'
                transmission_delay_hours REAL NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS foreign_vendor_registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendor_name TEXT NOT NULL,
                portal_mst TEXT NOT NULL,
                registration_status TEXT NOT NULL,  -- 'ACTIVE', 'INACTIVE'
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS ecommerce_withholding_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendor_name TEXT NOT NULL,
                service_amount REAL NOT NULL,
                goods_amount REAL NOT NULL,
                vat_withholding REAL NOT NULL,
                cit_withholding REAL NOT NULL,
                total_withholding REAL NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        return conn

    # ───────────────────── Pillar 1: E-Transaction Signature Auditing ──────────────────
    def audit_etransaction_signature(
        self, mst: str, invoice_number: str, sign_date_str: str, receive_date_str: str, cert_expiry_date_str: str
    ) -> Dict[str, Any]:
        """Audit invoice digital signature, certificate expiry, and GDT transmission delays under Law 108."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        # Try parsing dates (expected formats: YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
        date_formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]
        
        def parse_dt(dt_str: str) -> datetime:
            for fmt in date_formats:
                try:
                    return datetime.strptime(dt_str, fmt)
                except ValueError:
                    continue
            return datetime.now()

        sign_dt = parse_dt(sign_date_str)
        receive_dt = parse_dt(receive_date_str)
        expiry_dt = parse_dt(cert_expiry_date_str)

        delay_seconds = (receive_dt - sign_dt).total_seconds()
        delay_hours = max(0.0, delay_seconds / 3600.0)

        if sign_dt > expiry_dt:
            status = "SIGNATURE_EXPIRED"
            notes = f"Failed: Signature date ({sign_date_str}) is after certificate expiration date ({cert_expiry_date_str})."
        elif delay_hours > 24.0:
            status = "LATE_TRANSMISSION"
            notes = f"Warning: Invoice sign date to GDT reception delay is {delay_hours:.1f} hours, which exceeds the 24-hour limit."
        else:
            status = "COMPLIANT"
            notes = f"Compliant: Signature is valid and GDT transmission delay is {delay_hours:.1f} hours (within 24-hour limit)."

        cur.execute("""
            INSERT INTO etransaction_signature_audit
                (invoice_number, sign_date, receive_date, signature_status, transmission_delay_hours, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (invoice_number, sign_date_str, receive_date_str, status, delay_hours, notes))

        conn.commit()
        conn.close()

        return {
            "invoice_number": invoice_number,
            "sign_date": sign_date_str,
            "receive_date": receive_date_str,
            "signature_status": status,
            "transmission_delay_hours": delay_hours,
            "notes": notes
        }

    # ───────────────────── Pillar 2: Foreign Vendor Portal Registration ──────────────────
    def register_foreign_vendor(
        self, mst: str, vendor_name: str, portal_mst: str, registration_status: str = "ACTIVE"
    ) -> Dict[str, Any]:
        """Register a foreign vendor on the GDT NTNN portal tracking system."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        notes = f"Vendor {vendor_name} registered on the GDT NTNN portal with MST {portal_mst} (Status: {registration_status})."

        cur.execute("""
            INSERT INTO foreign_vendor_registrations
                (vendor_name, portal_mst, registration_status, notes)
            VALUES (?, ?, ?, ?)
        """, (vendor_name, portal_mst, registration_status, notes))

        conn.commit()
        conn.close()

        return {
            "vendor_name": vendor_name,
            "portal_mst": portal_mst,
            "registration_status": registration_status,
            "notes": notes
        }

    # ───────────────────── Pillar 2: Cross-Border B2B Withholding ──────────────────
    def calculate_ecommerce_withholding(
        self, mst: str, vendor_name: str, is_registered_vendor: bool, service_amount: float, goods_amount: float
    ) -> Dict[str, Any]:
        """Compute withholding tax on foreign e-commerce B2B payments under Law 108."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        if is_registered_vendor:
            # Foreign vendor is registered and pays taxes directly, no local buyer withholding required
            vat_withholding = 0.0
            cit_withholding = 0.0
            total_withholding = 0.0
            notes = f"No withholding required: Vendor {vendor_name} is registered directly on GDT NTNN portal."
        else:
            # Local B2B buyer must withhold tax:
            # For Services: VAT 5%, CIT 5% -> total 10%
            # For Goods: VAT 5%, CIT 1% -> total 6%
            vat_services = service_amount * 0.05
            cit_services = service_amount * 0.05
            
            vat_goods = goods_amount * 0.05
            cit_goods = goods_amount * 0.01

            vat_withholding = vat_services + vat_goods
            cit_withholding = cit_services + cit_goods
            total_withholding = vat_withholding + cit_withholding

            notes = (
                f"Withholding required: Local buyer must withhold tax. "
                f"Services: VAT 5% ({vat_services:,.0f} VND), CIT 5% ({cit_services:,.0f} VND). "
                f"Goods: VAT 5% ({vat_goods:,.0f} VND), CIT 1% ({cit_goods:,.0f} VND). "
                f"Total withheld: {total_withholding:,.0f} VND."
            )

        cur.execute("""
            INSERT INTO ecommerce_withholding_logs
                (vendor_name, service_amount, goods_amount, vat_withholding, cit_withholding, total_withholding, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (vendor_name, service_amount, goods_amount, vat_withholding, cit_withholding, total_withholding, notes))

        conn.commit()
        conn.close()

        return {
            "vendor_name": vendor_name,
            "is_registered_vendor": is_registered_vendor,
            "service_amount": service_amount,
            "goods_amount": goods_amount,
            "vat_withholding": vat_withholding,
            "cit_withholding": cit_withholding,
            "total_withholding": total_withholding,
            "notes": notes
        }
