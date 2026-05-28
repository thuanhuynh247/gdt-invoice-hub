"""Tests for Automated VAT Declaration Engine (US-100, US-101)."""

from __future__ import annotations

import pytest
from invoices.vat_declaration_engine import (
    compute_vat_declaration,
    get_period_months,
    filter_invoices_by_period,
    render_declaration_form,
    VATDeclarationResult,
)


def _sample_invoices():
    """A representative set of mixed input/output invoices for MST 0109998887."""
    return [
        {
            "id": "OUT-001", "seller_mst": "0109998887", "buyer_mst": "0112223334",
            "amount_before_tax": 50_000_000, "tax_amount": 5_000_000, "total_amount": 55_000_000,
            "payment_method": "Chuyển khoản", "has_signature": True, "date": "2026-05-05",
        },
        {
            "id": "OUT-002", "seller_mst": "0109998887", "buyer_mst": "0199887766",
            "amount_before_tax": 30_000_000, "tax_amount": 3_000_000, "total_amount": 33_000_000,
            "payment_method": "Chuyển khoản", "has_signature": True, "date": "2026-05-10",
        },
        {
            "id": "IN-001", "seller_mst": "0112223334", "buyer_mst": "0109998887",
            "amount_before_tax": 20_000_000, "tax_amount": 2_000_000, "total_amount": 22_000_000,
            "payment_method": "Chuyển khoản", "has_signature": True, "date": "2026-05-12",
        },
        {
            "id": "IN-002", "seller_mst": "0199887766", "buyer_mst": "0109998887",
            "amount_before_tax": 25_000_000, "tax_amount": 2_500_000, "total_amount": 27_500_000,
            "payment_method": "Tiền mặt", "has_signature": True, "date": "2026-05-15",
        },
        {
            "id": "IN-003", "seller_mst": "0100000001", "buyer_mst": "0109998887",
            "amount_before_tax": 10_000_000, "tax_amount": 1_000_000, "total_amount": 11_000_000,
            "payment_method": "Chuyển khoản", "has_signature": False, "date": "2026-05-20",
        },
    ]


class TestVATDeclarationComputation:
    """US-100: VAT Declaration Computation Engine."""

    def test_compute_monthly_vat_declaration(self):
        """Total output/input VAT should be computed correctly for a month."""
        decl = compute_vat_declaration(
            taxpayer_mst="0109998887",
            period_type="monthly",
            period_label="2026-05",
            invoices=_sample_invoices(),
        )

        # Output: OUT-001 (5M) + OUT-002 (3M) = 8M
        assert decl.total_output_vat == 8_000_000.0
        assert decl.output_invoice_count == 2

        # Input: IN-001 (2M) + IN-002 (2.5M) + IN-003 (1M) = 5.5M total
        assert decl.total_input_vat == 5_500_000.0
        assert decl.input_invoice_count == 3

    def test_non_deductible_cash_payment(self):
        """Cash payments >= 20M VND should NOT be deductible."""
        decl = compute_vat_declaration(
            taxpayer_mst="0109998887",
            period_type="monthly",
            period_label="2026-05",
            invoices=_sample_invoices(),
        )

        # IN-002: 27.5M cash -> NOT deductible (2.5M)
        # IN-003: unsigned -> NOT deductible (1M)
        # Only IN-001 is deductible: 2M
        assert decl.total_deductible_input_vat == 2_000_000.0

    def test_non_deductible_unsigned_invoice(self):
        """Invoices without digital signatures should NOT be deductible."""
        decl = compute_vat_declaration(
            taxpayer_mst="0109998887",
            period_type="monthly",
            period_label="2026-05",
            invoices=_sample_invoices(),
        )

        # Check line details for IN-003
        in003 = [d for d in decl.line_details if d["invoice_id"] == "IN-003"]
        assert len(in003) == 1
        assert in003[0]["deductible"] is False
        assert "chữ ký số" in in003[0]["reason"]

    def test_vat_payable_positive(self):
        """VAT payable = output VAT - deductible input VAT."""
        decl = compute_vat_declaration(
            taxpayer_mst="0109998887",
            period_type="monthly",
            period_label="2026-05",
            invoices=_sample_invoices(),
        )

        # 8M output - 2M deductible = 6M payable
        assert decl.vat_payable == 6_000_000.0

    def test_negative_vat_means_refund(self):
        """If deductible input > output, VAT payable should be negative (refundable)."""
        invoices = [
            {
                "id": "OUT-SMALL", "seller_mst": "0109998887", "buyer_mst": "BUYER",
                "amount_before_tax": 1_000_000, "tax_amount": 100_000, "total_amount": 1_100_000,
                "payment_method": "CK", "has_signature": True, "date": "2026-05-01",
            },
            {
                "id": "IN-BIG", "seller_mst": "SUPPLIER", "buyer_mst": "0109998887",
                "amount_before_tax": 50_000_000, "tax_amount": 5_000_000, "total_amount": 55_000_000,
                "payment_method": "Chuyển khoản", "has_signature": True, "date": "2026-05-05",
            },
        ]
        decl = compute_vat_declaration("0109998887", "monthly", "2026-05", invoices)
        assert decl.vat_payable < 0  # Negative = refundable

    def test_declaration_id_format(self):
        """Declaration ID should follow DECL-{MST}-{period} format."""
        decl = compute_vat_declaration("0109998887", "monthly", "2026-05", [])
        assert decl.id == "DECL-0109998887-2026-05"

    def test_invalid_period_type_raises(self):
        """Invalid period type should raise ValueError."""
        with pytest.raises(ValueError, match="period_type"):
            compute_vat_declaration("0109998887", "weekly", "2026-W22", [])

    def test_quarterly_period_months(self):
        """get_period_months should correctly expand Q1 to 3 months."""
        months = get_period_months("2026-Q1", "quarterly")
        assert months == ["2026-01", "2026-02", "2026-03"]

    def test_quarterly_q4(self):
        """Q4 should map to Oct/Nov/Dec."""
        months = get_period_months("2026-Q4", "quarterly")
        assert months == ["2026-10", "2026-11", "2026-12"]

    def test_filter_invoices_by_period(self):
        """Only invoices within the target period should be included."""
        invoices = _sample_invoices() + [{
            "id": "OUTSIDE", "seller_mst": "0109998887", "buyer_mst": "X",
            "amount_before_tax": 1000, "tax_amount": 100, "total_amount": 1100,
            "payment_method": "CK", "has_signature": True, "date": "2026-04-30",
        }]
        filtered = filter_invoices_by_period(invoices, ["2026-05"])
        ids = [inv["id"] for inv in filtered]
        assert "OUTSIDE" not in ids
        assert len(filtered) == 5

    def test_declaration_finalization_locks_data(self):
        """Finalized declarations should have correct status."""
        decl = compute_vat_declaration("0109998887", "monthly", "2026-05", _sample_invoices())
        assert decl.status == "draft"
        decl.status = "finalized"
        assert decl.status == "finalized"


class TestDeclarationFormRenderer:
    """US-101: Declaration Form Template Renderer."""

    def test_render_form_contains_header(self):
        """Rendered form should contain Vietnamese government header."""
        decl = compute_vat_declaration("0109998887", "monthly", "2026-05", _sample_invoices())
        form = render_declaration_form(decl)
        assert "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM" in form
        assert "MẪU 01/GTGT" in form

    def test_render_form_contains_mst(self):
        """Rendered form should contain the taxpayer MST."""
        decl = compute_vat_declaration("0109998887", "monthly", "2026-05", _sample_invoices())
        form = render_declaration_form(decl)
        assert "0109998887" in form

    def test_render_form_shows_payable(self):
        """Positive VAT payable should show as THUẾ GTGT PHẢI NỘP."""
        decl = compute_vat_declaration("0109998887", "monthly", "2026-05", _sample_invoices())
        form = render_declaration_form(decl)
        assert "THUẾ GTGT PHẢI NỘP" in form

    def test_render_form_shows_refund_when_negative(self):
        """Negative VAT should show as CÒN ĐƯỢC KHẤU TRỪ."""
        decl = VATDeclarationResult(
            id="TEST", taxpayer_mst="0109998887", period_type="monthly",
            period_label="2026-05", vat_payable=-500_000,
        )
        form = render_declaration_form(decl)
        assert "CÒN ĐƯỢC KHẤU TRỪ" in form
