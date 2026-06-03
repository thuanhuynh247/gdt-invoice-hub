"""Multi-Jurisdictional Tax Mapping Engine (US-121).

Translates local Vietnamese GDT tax structure into international standards (IFRS),
computes Foreign Contractor Tax (FCT) liability matrix,
and integrates a thread-safe exchange rate buffering layer (VND -> USD/EUR).
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class FCTLiability:
    """Detailed breakdown of Foreign Contractor Tax (FCT) liability."""
    is_applicable: bool = False
    contractor_category: str = "N/A"
    vat_rate: float = 0.0
    vat_amount: float = 0.0
    cit_rate: float = 0.0
    cit_amount: float = 0.0
    total_fct_rate: float = 0.0
    total_fct_liability: float = 0.0


@dataclass
class IFRSInvoiceMapping:
    """IFRS & Multi-Currency compliant representation of a local invoice."""
    document_number: str
    supplier_name: str
    supplier_tax_id: str
    customer_name: str
    customer_tax_id: str
    posting_date: str
    base_currency: str = "VND"
    reporting_currency: str = "USD"
    exchange_rate: float = 1.0
    amount_in_base: float = 0.0
    amount_in_reporting: float = 0.0
    fct_liability: FCTLiability = field(default_factory=FCTLiability)
    journal_entries: list[dict] = field(default_factory=list)


class CurrencyExchangeBuffer:
    """Thread-safe buffer holding currency exchange rates (VND to USD/EUR)."""

    def __init__(self):
        self._lock = threading.Lock()
        # Default fallback exchange rates (VND to 1 unit of foreign currency)
        # E.g., 1 USD = 25,400 VND -> rate VND to USD is 1/25400
        self._rates = {
            "USD": 25400.0,
            "EUR": 27500.0,
            "JPY": 162.0,
        }
        self.last_updated = datetime.now(timezone.utc).isoformat()

    def get_rate(self, currency: str) -> float:
        """Get exchange rate for target currency (units of VND per 1 unit of currency)."""
        with self._lock:
            return self._rates.get(currency.upper(), 1.0)

    def set_rate(self, currency: str, rate_in_vnd: float):
        """Set or update exchange rate in a thread-safe manner."""
        if rate_in_vnd <= 0:
            raise ValueError("Exchange rate must be positive.")
        with self._lock:
            self._rates[currency.upper()] = rate_in_vnd
            self.last_updated = datetime.now(timezone.utc).isoformat()

    def convert_to_reporting(self, amount_vnd: float, target_currency: str) -> float:
        """Convert VND amount into reporting currency."""
        rate = self.get_rate(target_currency)
        if rate == 0:
            return 0.0
        return round(amount_vnd / rate, 2)


class TaxMappingEngine:
    """Translates GDT local compliance invoices to IFRS & calculates FCT liabilities."""

    # FCT rates in Vietnam based on Circular 103/2014/TT-BTC
    FCT_MATRIX = {
        "services": {"vat": 0.05, "cit": 0.05},
        "services_with_goods": {"vat": 0.03, "cit": 0.02},
        "goods_supply": {"vat": 0.0, "cit": 0.01},  # CIT 1% only
        "software_license": {"vat": 0.0, "cit": 0.02},  # Software is VAT exempt, CIT 2%
        "interest": {"vat": 0.0, "cit": 0.05},
        "royalties": {"vat": 0.0, "cit": 0.10},
    }

    # Chart of Accounts General Ledger mapping
    GL_MAPPING = {
        "Thiết bị IT": {"debit": "1561", "credit": "331"},
        "Vật tư phụ": {"debit": "1542", "credit": "331"},
        "Dịch vụ tư vấn": {"debit": "6422", "credit": "331"},
        "Software License": {"debit": "242", "credit": "331"},  # Deferred Expense
        "default": {"debit": "642", "credit": "331"},
    }

    def __init__(self, buffer: CurrencyExchangeBuffer | None = None):
        self.exchange_buffer = buffer or CurrencyExchangeBuffer()

    def is_foreign_contractor(self, invoice: dict) -> bool:
        """Determine if the supplier is a foreign contractor.
        
        Typically foreign contractors do not have a standard Vietnamese taxpayer MST 
        (or have specific foreign MST patterns starting with 80 or not 10 digits).
        """
        mst = invoice.get("seller_mst", "").strip()
        # If MST is missing or foreign formatting (like non-digit or 80... range)
        if not mst:
            return True
        if mst.startswith("80"):
            return True
        # Standard Vietnamese MST is either 10 digits or 13 digits (for branches)
        clean_mst = "".join(filter(str.isdigit, mst))
        if len(clean_mst) != 10 and len(clean_mst) != 13:
            return True
        return False

    def calculate_fct(self, amount_vnd: float, category: str) -> FCTLiability:
        """Calculate FCT (Value Added Tax & Corporate Income Tax liabilities)."""
        rules = self.FCT_MATRIX.get(category.lower())
        if not rules:
            return FCTLiability()

        vat_rate = rules["vat"]
        cit_rate = rules["cit"]

        # Circular 103 FCT formula:
        # 1. VAT revenue = Taxable Revenue / (1 - VAT Rate) [if net contract]
        # For simplicity, we assume gross contract revenue model:
        vat_amount = round(amount_vnd * vat_rate, 2)
        cit_amount = round(amount_vnd * cit_rate, 2)
        total_fct = vat_amount + cit_amount

        return FCTLiability(
            is_applicable=True,
            contractor_category=category,
            vat_rate=vat_rate,
            vat_amount=vat_amount,
            cit_rate=cit_rate,
            cit_amount=cit_amount,
            total_fct_rate=vat_rate + cit_rate,
            total_fct_liability=total_fct,
        )

    def map_to_ifrs(self, invoice: dict, reporting_currency: str = "USD", fct_category: str | None = None) -> IFRSInvoiceMapping:
        """Convert a local GDT XML structure to IFRS Multi-Currency Mapping."""
        amount_vnd = float(invoice.get("total_amount", 0.0))
        rate = self.exchange_buffer.get_rate(reporting_currency)
        amount_reporting = self.exchange_buffer.convert_to_reporting(amount_vnd, reporting_currency)

        # FCT check
        fct = FCTLiability()
        if self.is_foreign_contractor(invoice) and fct_category:
            fct = self.calculate_fct(amount_vnd, fct_category)

        # Build journal entries based on line items
        journal_entries = []
        items = invoice.get("items", [])
        
        for item in items:
            category = item.get("expense_category", "default")
            item_amount = float(item.get("amount_before_tax", 0.0))
            item_amount_reporting = self.exchange_buffer.convert_to_reporting(item_amount, reporting_currency)
            
            gl = self.GL_MAPPING.get(category, self.GL_MAPPING["default"])
            
            journal_entries.append({
                "account_debit": gl["debit"],
                "account_credit": gl["credit"],
                "amount_base": item_amount,
                "amount_reporting": item_amount_reporting,
                "description": f"Post item {item.get('item_name', 'N/A')} to General Ledger",
            })

        return IFRSInvoiceMapping(
            document_number=invoice.get("id", "N/A"),
            supplier_name=invoice.get("seller_name", "N/A"),
            supplier_tax_id=invoice.get("seller_mst", "N/A"),
            customer_name=invoice.get("buyer_name", "N/A"),
            customer_tax_id=invoice.get("buyer_mst", "N/A"),
            posting_date=invoice.get("imported_at") or invoice.get("date") or datetime.now(timezone.utc).isoformat(),
            base_currency="VND",
            reporting_currency=reporting_currency.upper(),
            exchange_rate=rate,
            amount_in_base=amount_vnd,
            amount_in_reporting=amount_reporting,
            fct_liability=fct,
            journal_entries=journal_entries,
        )
