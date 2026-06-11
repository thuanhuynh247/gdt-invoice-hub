"""Enterprise E-Invoice Incident Logs & Converted Bill Audit Service (v46.0.0).

Handles GDT Form 04/SS-HĐĐT incident reporting status reconciliation
and Circular 78 legacy conversion double-deduction auditor checks.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, List
from invoices.multitenant_service import get_tenant_db_path

class V46ComplianceService:
    def __init__(self, base_data_dir: str | None = None):
        self.base_data_dir = base_data_dir

    def get_tenant_connection(self, mst: str) -> sqlite3.Connection:
        """Returns an isolated sqlite3 connection to the specific tenant database."""
        db_path = get_tenant_db_path(mst, self.base_data_dir)
        conn = sqlite3.connect(db_path)
        conn.text_factory = lambda x: x.decode('utf-8', errors='replace') if isinstance(x, bytes) else x
        conn.row_factory = sqlite3.Row
        
        # Ensure our custom v46 tables exist in this tenant DB
        cur = conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS form_04_ss_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_invoice_symbol TEXT NOT NULL,
                original_invoice_number TEXT NOT NULL,
                invoice_date TEXT NOT NULL,
                filing_date TEXT NOT NULL,
                gdt_status_code INTEGER DEFAULT 0, -- 0: Pending, 1: Accepted, 2: Rejected
                submission_delay_days INTEGER DEFAULT 0,
                deadline_warning TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS invoice_conversion_prints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_symbol TEXT NOT NULL,
                invoice_number TEXT NOT NULL,
                print_date TEXT NOT NULL,
                print_count INTEGER DEFAULT 1,
                converted_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS conversion_reconciliation_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT NOT NULL,
                invoice_amount REAL NOT NULL,
                alert_type TEXT NOT NULL, -- 'MULTIPLE_CONVERSION_PRINTS_ALERT', 'DUPLICATE_CONVERSION_CLAIM'
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        return conn

    def process_form_04_ss(
        self, mst: str, original_invoice_symbol: str, original_invoice_number: str,
        invoice_date_str: str, filing_date_str: str, gdt_status_code: int
    ) -> Dict[str, Any]:
        """Ingests and validates Form 04/SS-HĐĐT filing deadlines and response codes."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        # Parse dates
        fmt = "%Y-%m-%d"
        inv_dt = datetime.strptime(invoice_date_str, fmt)
        fil_dt = datetime.strptime(filing_date_str, fmt)

        # Calculate difference in days
        delay_days = (fil_dt - inv_dt).days
        warning = None
        
        # Decree 123: Form 04/SS should be filed in the month/quarter of the incident.
        # We flag a warning if the filing date is after the last day of the subsequent month.
        # As a simplified safe rule: if filing is more than 30 days after the invoice date, flag it.
        if delay_days > 30:
            warning = "LATE_FILING_WARNING: Form 04/SS filed more than 30 days after invoice date."

        # Insert Form 04/SS log
        cur.execute("""
            INSERT INTO form_04_ss_logs (
                original_invoice_symbol, original_invoice_number, invoice_date, filing_date, gdt_status_code, submission_delay_days, deadline_warning
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (original_invoice_symbol, original_invoice_number, invoice_date_str, filing_date_str, gdt_status_code, delay_days, warning))
        
        conn.commit()
        conn.close()

        status_map = {0: "Pending", 1: "Accepted", 2: "Rejected"}

        return {
            "original_invoice_symbol": original_invoice_symbol,
            "original_invoice_number": original_invoice_number,
            "invoice_date": invoice_date_str,
            "filing_date": filing_date_str,
            "gdt_status": status_map.get(gdt_status_code, "Unknown"),
            "submission_delay_days": delay_days,
            "deadline_warning": warning
        }

    def audit_conversion_prints(
        self, mst: str, invoice_symbol: str, invoice_number: str,
        print_date_str: str, print_count: int, converted_by: str, invoice_amount: float
    ) -> Dict[str, Any]:
        """Audits paper conversions of e-invoices and checks for double-deduction risks."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        # Insert print log
        cur.execute("""
            INSERT INTO invoice_conversion_prints (
                invoice_symbol, invoice_number, print_date, print_count, converted_by
            ) VALUES (?, ?, ?, ?, ?)
        """, (invoice_symbol, invoice_number, print_date_str, print_count, converted_by))

        alerts = []
        
        # Alert 1: Check multiple prints
        if print_count > 1:
            alert_type = "MULTIPLE_CONVERSION_PRINTS_ALERT"
            details = f"E-invoice {invoice_number} has been printed as conversion {print_count} times by {converted_by}."
            alerts.append({"type": alert_type, "details": details})
            
            cur.execute("""
                INSERT INTO conversion_reconciliation_alerts (invoice_number, invoice_amount, alert_type, details)
                VALUES (?, ?, ?, ?)
            """, (invoice_number, invoice_amount, alert_type, details))

        # Alert 2: Search original purchases in local ledger for double claims.
        # If there is another invoice/expense with the exact same number and amount, flag duplicate.
        cur.execute("""
            SELECT count(*) FROM invoice
            WHERE id = ? AND total_amount = ?
        """, (invoice_number, invoice_amount))
        
        existing_claims = cur.fetchone()[0]
        if existing_claims > 0:
            alert_type = "DUPLICATE_CONVERSION_CLAIM"
            details = f"Warning: Invoice {invoice_number} with amount {invoice_amount:,.2f} is already recorded in the system ledger. Duplicate CIT deduction risk detected."
            alerts.append({"type": alert_type, "details": details})

            cur.execute("""
                INSERT INTO conversion_reconciliation_alerts (invoice_number, invoice_amount, alert_type, details)
                VALUES (?, ?, ?, ?)
            """, (invoice_number, invoice_amount, alert_type, details))

        conn.commit()
        conn.close()

        return {
            "invoice_symbol": invoice_symbol,
            "invoice_number": invoice_number,
            "print_count": print_count,
            "converted_by": converted_by,
            "alerts": alerts
        }
