"""Tests for the Multi-Jurisdictional Tax Mapping Engine (US-121)."""

from __future__ import annotations

import pytest
import threading
from invoices.tax_mapping import (
    CurrencyExchangeBuffer,
    TaxMappingEngine,
)


class TestTaxMapping:
    """US-121: Multi-Jurisdictional Tax Mapping & Exchange Rate Buffer Test Suite."""

    def _sample_invoice(self) -> dict:
        return {
            "id": "INV-IFRS-888",
            "seller_name": "Oracle Global Systems Singapore",
            "seller_mst": "8024681357",  # Foreign MST
            "buyer_name": "Tập đoàn Đại Nam",
            "buyer_mst": "0312345678",
            "total_amount": 50_000_000.0,
            "items": [
                {
                    "item_name": "Oracle Cloud Subscription",
                    "amount_before_tax": 30_000_000.0,
                    "expense_category": "Software License",
                },
                {
                    "item_name": "Oracle Cloud Setup Services",
                    "amount_before_tax": 20_000_000.0,
                    "expense_category": "Dịch vụ tư vấn",
                }
            ]
        }

    def test_exchange_rate_buffer_conversions(self):
        """Verify currency conversions and custom exchange rates update correctly."""
        buffer = CurrencyExchangeBuffer()
        
        # Test default rates
        assert buffer.get_rate("USD") == 25400.0
        assert buffer.get_rate("EUR") == 27500.0
        
        # Convert VND to USD (50,800,000 / 25,400 = 2,000 USD)
        usd_amount = buffer.convert_to_reporting(50_800_000.0, "USD")
        assert usd_amount == 2000.0

        # Update rate and verify conversion changes
        buffer.set_rate("USD", 25_000.0)
        assert buffer.get_rate("USD") == 25000.0
        new_usd_amount = buffer.convert_to_reporting(50_800_000.0, "USD")
        assert new_usd_amount == 2032.0

    def test_exchange_rate_buffer_thread_safety(self):
        """Verify that concurrent read/write operations do not trigger deadlock or race conditions."""
        buffer = CurrencyExchangeBuffer()
        
        def writer_loop():
            for i in range(100):
                buffer.set_rate("USD", 25000.0 + i)

        def reader_loop():
            for _ in range(100):
                rate = buffer.get_rate("USD")
                assert rate >= 25000.0

        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=writer_loop))
            threads.append(threading.Thread(target=reader_loop))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

    def test_is_foreign_contractor_detection(self):
        """Verify the engine correctly flags foreign entities by MST formatting."""
        engine = TaxMappingEngine()
        
        # 1. Standard Vietnam MST (10 digits) -> not foreign
        assert engine.is_foreign_contractor({"seller_mst": "0109876543"}) is False

        # 2. Standard branch MST (13 digits) -> not foreign
        assert engine.is_foreign_contractor({"seller_mst": "0312345678-001"}) is False

        # 3. MST starting with 80 (standard foreign contract MST code) -> foreign
        assert engine.is_foreign_contractor({"seller_mst": "8024681357"}) is True

        # 4. Blank MST -> foreign contractor
        assert engine.is_foreign_contractor({"seller_mst": ""}) is True

        # 5. Non-standard digit count -> foreign contractor
        assert engine.is_foreign_contractor({"seller_mst": "ABC1234"}) is True

    def test_calculate_fct_liability(self):
        """Verify Foreign Contractor Tax calculations conform to standard rules."""
        engine = TaxMappingEngine()
        
        # Service category FCT: VAT = 5%, CIT = 5%
        fct = engine.calculate_fct(100_000_000.0, "services")
        assert fct.is_applicable is True
        assert fct.vat_rate == 0.05
        assert fct.vat_amount == 5_000_000.0
        assert fct.cit_rate == 0.05
        assert fct.cit_amount == 5_000_000.0
        assert fct.total_fct_liability == 10_000_000.0

        # Software License FCT: VAT = 0%, CIT = 2%
        fct_sw = engine.calculate_fct(100_000_000.0, "software_license")
        assert fct_sw.vat_rate == 0.0
        assert fct_sw.vat_amount == 0.0
        assert fct_sw.cit_rate == 0.02
        assert fct_sw.cit_amount == 2_000_000.0
        assert fct_sw.total_fct_liability == 2_000_000.0

    def test_map_to_ifrs(self):
        """Verify standard-compliant ledger translation and journal entries generation."""
        engine = TaxMappingEngine()
        invoice = self._sample_invoice()
        
        mapping = engine.map_to_ifrs(invoice, reporting_currency="USD", fct_category="software_license")
        
        assert mapping.document_number == "INV-IFRS-888"
        assert mapping.reporting_currency == "USD"
        
        # 50,000,000 / 25,400 USD = 1968.50 USD
        assert mapping.amount_in_reporting == 1968.50
        
        # Verify FCT calculations are included
        assert mapping.fct_liability.is_applicable is True
        assert mapping.fct_liability.total_fct_liability == 1_000_000.0  # 50,000,000 * 2%
        
        # Verify General Ledger entries are posted correctly
        assert len(mapping.journal_entries) == 2
        
        # Software License item GL account debit: 242, credit: 331
        item1 = mapping.journal_entries[0]
        assert item1["account_debit"] == "242"
        assert item1["account_credit"] == "331"
        assert item1["amount_base"] == 30_000_000.0
        assert item1["amount_reporting"] == 1181.10  # 30,000,000 / 25,400
        
        # Consulting service item GL account debit: 6422, credit: 331
        item2 = mapping.journal_entries[1]
        assert item2["account_debit"] == "6422"
        assert item2["account_credit"] == "331"
        assert item2["amount_base"] == 20_000_000.0
        assert item2["amount_reporting"] == 787.40
