"""VAT Law 48/2024/QH15 Compliance Engine (v47.0.0).

Implements VAT rate classification (Articles 5 & 9), input tax credit
eligibility validation (Article 14), and refund threshold computation
(Article 15) from the new Vietnamese VAT Law effective July 1, 2025.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional
from invoices.multitenant_service import get_tenant_db_path


# ────────────────────────────────────────────────────────────────
# Static Data: Article 5 Non-Taxable Categories (27 categories)
# ────────────────────────────────────────────────────────────────
NON_TAXABLE_CATEGORIES: List[Dict[str, str]] = [
    {"code": "ART5_01", "name": "Sản phẩm nông nghiệp chưa chế biến", "desc": "Raw agricultural/forestry/aquaculture products (Article 5.1)"},
    {"code": "ART5_02", "name": "Giống vật nuôi, vật liệu nhân giống", "desc": "Animal breeds and plant propagation materials (Article 5.2)"},
    {"code": "ART5_03", "name": "Thức ăn chăn nuôi, thủy sản", "desc": "Animal feed and aquaculture feed (Article 5.3)"},
    {"code": "ART5_04", "name": "Muối", "desc": "Salt products (NaCl-based) (Article 5.4)"},
    {"code": "ART5_05", "name": "Nhà ở công bán cho người thuê", "desc": "Public housing sold to tenants (Article 5.5)"},
    {"code": "ART5_06", "name": "Dịch vụ nông nghiệp", "desc": "Agricultural irrigation, plowing, harvesting services (Article 5.6)"},
    {"code": "ART5_07", "name": "Chuyển quyền sử dụng đất", "desc": "Land use rights transfer (Article 5.7)"},
    {"code": "ART5_08", "name": "Bảo hiểm nhân thọ, sức khỏe", "desc": "Life/health/agricultural insurance (Article 5.8)"},
    {"code": "ART5_09", "name": "Dịch vụ tài chính, ngân hàng", "desc": "Financial/banking/securities services (Article 5.9)"},
    {"code": "ART5_10", "name": "Dịch vụ y tế, thú y", "desc": "Healthcare and veterinary services (Article 5.10)"},
    {"code": "ART5_11", "name": "Dịch vụ tang lễ", "desc": "Funeral services (Article 5.11)"},
    {"code": "ART5_12", "name": "Duy tu di tích lịch sử", "desc": "Historical/cultural monument maintenance with >50% public donations (Article 5.12)"},
    {"code": "ART5_13", "name": "Giáo dục, đào tạo", "desc": "Education and vocational training (Article 5.13)"},
    {"code": "ART5_14", "name": "Phát sóng truyền hình NSNN", "desc": "State-budget broadcasting (Article 5.14)"},
    {"code": "ART5_15", "name": "Sách, báo chí", "desc": "Political/textbook/legal books, newspapers (Article 5.15)"},
    {"code": "ART5_16", "name": "Vận chuyển công cộng", "desc": "Public bus, tram, inland waterway transport (Article 5.16)"},
    {"code": "ART5_17", "name": "Máy móc R&D nhập khẩu", "desc": "Imported machinery for R&D, oil exploration (Article 5.17)"},
    {"code": "ART5_18", "name": "Sản phẩm quốc phòng, an ninh", "desc": "Defense and security products (Article 5.18)"},
    {"code": "ART5_19", "name": "Viện trợ nhân đạo", "desc": "Humanitarian aid goods (Article 5.19)"},
    {"code": "ART5_20", "name": "Hàng quá cảnh, tạm nhập tái xuất", "desc": "Transit, temp import/re-export, processing for export (Article 5.20)"},
    {"code": "ART5_21", "name": "Chuyển giao công nghệ, phần mềm", "desc": "Technology transfer, IP rights, software (Article 5.21)"},
    {"code": "ART5_22", "name": "Vàng thỏi chưa chế tác", "desc": "Unprocessed gold bars/ingots at import stage (Article 5.22)"},
    {"code": "ART5_23", "name": "Tài nguyên khoáng sản xuất khẩu thô", "desc": "Exported raw/unprocessed natural resources (Article 5.23)"},
    {"code": "ART5_24", "name": "Sản phẩm nhân tạo thay thế cơ thể", "desc": "Prosthetics, implants, disability aids (Article 5.24)"},
    {"code": "ART5_25", "name": "Hộ kinh doanh ≤200 triệu/năm", "desc": "Household businesses with revenue ≤200M VND/year (Article 5.25)"},
    {"code": "ART5_26", "name": "Hàng nhập khẩu đặc biệt", "desc": "Diplomatic gifts, duty-free luggage, disaster relief imports (Article 5.26)"},
    {"code": "ART5_27", "name": "Quy định chung: không khấu trừ", "desc": "General rule: non-taxable items cannot claim input credits (Article 5.27)"},
]

# ────────────────────────────────────────────────────────────────
# Static Data: Article 9 VAT Rate Categories
# ────────────────────────────────────────────────────────────────
FIVE_PERCENT_KEYWORDS = [
    "nước sạch", "phân bón", "thuốc bảo vệ thực vật", "thức ăn chăn nuôi",
    "thiết bị y tế", "thuốc chữa bệnh", "dược liệu", "dụng cụ giảng dạy",
    "đồ chơi trẻ em", "sách", "dịch vụ khoa học công nghệ", "nhà ở xã hội",
    "nông sản sơ chế", "mủ cao su", "lưới đánh cá", "tàu khai thác thủy sản",
    "nghệ thuật biểu diễn", "máy nông nghiệp",
]


class V47ComplianceService:
    """VAT Law 48/2024/QH15 compliance engine."""

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
            CREATE TABLE IF NOT EXISTS vat_rate_classifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_description TEXT NOT NULL,
                classified_rate TEXT NOT NULL,  -- '0%', '5%', '10%', 'NON_TAXABLE'
                article_reference TEXT,
                exemption_code TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS input_credit_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_number TEXT NOT NULL,
                invoice_amount REAL NOT NULL,
                has_vat_invoice INTEGER DEFAULT 0,
                has_bank_payment INTEGER DEFAULT 0,
                seller_declared INTEGER DEFAULT 0,
                is_eligible INTEGER DEFAULT 0,
                rejection_reasons TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS vat_refund_estimates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period_label TEXT NOT NULL,
                total_output_vat REAL NOT NULL DEFAULT 0,
                total_input_vat REAL NOT NULL DEFAULT 0,
                uncredited_balance REAL NOT NULL DEFAULT 0,
                export_revenue REAL DEFAULT 0,
                refund_eligible INTEGER DEFAULT 0,
                estimated_refund REAL DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        return conn

    # ───────────────────── Pillar 1: Rate Classification ──────────────────
    def classify_vat_rate(
        self, mst: str, item_description: str
    ) -> Dict[str, Any]:
        """Classify an item/service into the correct VAT rate tier."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        desc_lower = item_description.lower()

        # Step 1: Check non-taxable categories (Article 5)
        for cat in NON_TAXABLE_CATEGORIES:
            if cat["code"].lower() in desc_lower or cat["name"].lower() in desc_lower:
                result = {
                    "item_description": item_description,
                    "classified_rate": "NON_TAXABLE",
                    "article_reference": "Điều 5 Luật 48/2024/QH15",
                    "exemption_code": cat["code"],
                    "notes": cat["desc"],
                }
                cur.execute("""
                    INSERT INTO vat_rate_classifications
                        (item_description, classified_rate, article_reference, exemption_code, notes)
                    VALUES (?, ?, ?, ?, ?)
                """, (result["item_description"], result["classified_rate"],
                      result["article_reference"], result["exemption_code"], result["notes"]))
                conn.commit()
                conn.close()
                return result

        # Step 2: Check 0% rate keywords (Article 9.1)
        zero_pct_keywords = ["xuất khẩu", "export", "vận tải quốc tế", "international transport",
                             "khu phi thuế quan", "duty-free", "cửa hàng miễn thuế"]
        for kw in zero_pct_keywords:
            if kw in desc_lower:
                result = {
                    "item_description": item_description,
                    "classified_rate": "0%",
                    "article_reference": "Điều 9.1 Luật 48/2024/QH15",
                    "exemption_code": None,
                    "notes": "Zero-rated export/international service",
                }
                cur.execute("""
                    INSERT INTO vat_rate_classifications
                        (item_description, classified_rate, article_reference, exemption_code, notes)
                    VALUES (?, ?, ?, ?, ?)
                """, (result["item_description"], result["classified_rate"],
                      result["article_reference"], result["exemption_code"], result["notes"]))
                conn.commit()
                conn.close()
                return result

        # Step 3: Check 5% rate keywords (Article 9.2)
        for kw in FIVE_PERCENT_KEYWORDS:
            if kw in desc_lower:
                result = {
                    "item_description": item_description,
                    "classified_rate": "5%",
                    "article_reference": "Điều 9.2 Luật 48/2024/QH15",
                    "exemption_code": None,
                    "notes": f"Reduced rate item matching: {kw}",
                }
                cur.execute("""
                    INSERT INTO vat_rate_classifications
                        (item_description, classified_rate, article_reference, exemption_code, notes)
                    VALUES (?, ?, ?, ?, ?)
                """, (result["item_description"], result["classified_rate"],
                      result["article_reference"], result["exemption_code"], result["notes"]))
                conn.commit()
                conn.close()
                return result

        # Step 4: Default 10% (Article 9.3)
        result = {
            "item_description": item_description,
            "classified_rate": "10%",
            "article_reference": "Điều 9.3 Luật 48/2024/QH15",
            "exemption_code": None,
            "notes": "Standard rate — all goods/services not classified elsewhere",
        }
        cur.execute("""
            INSERT INTO vat_rate_classifications
                (item_description, classified_rate, article_reference, exemption_code, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (result["item_description"], result["classified_rate"],
              result["article_reference"], result["exemption_code"], result["notes"]))
        conn.commit()
        conn.close()
        return result

    # ───────────────────── Pillar 2: Input Credit Check ──────────────────
    def check_input_credit_eligibility(
        self, mst: str, invoice_number: str, invoice_amount: float,
        has_vat_invoice: bool, has_bank_payment: bool, seller_declared: bool
    ) -> Dict[str, Any]:
        """Validate input VAT credit eligibility per Article 14."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        rejection_reasons = []

        if not has_vat_invoice:
            rejection_reasons.append("MISSING_VAT_INVOICE: Không có hóa đơn GTGT hợp lệ (Điều 14.2a)")
        if not has_bank_payment:
            rejection_reasons.append("MISSING_BANK_PAYMENT: Thiếu chứng từ thanh toán không dùng tiền mặt (Điều 14.2b)")
        if not seller_declared:
            rejection_reasons.append("SELLER_NOT_DECLARED: Người bán chưa kê khai, nộp thuế GTGT (Điều 15.9c)")

        is_eligible = len(rejection_reasons) == 0

        cur.execute("""
            INSERT INTO input_credit_checks
                (invoice_number, invoice_amount, has_vat_invoice, has_bank_payment,
                 seller_declared, is_eligible, rejection_reasons)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (invoice_number, invoice_amount,
              1 if has_vat_invoice else 0,
              1 if has_bank_payment else 0,
              1 if seller_declared else 0,
              1 if is_eligible else 0,
              "; ".join(rejection_reasons) if rejection_reasons else None))

        conn.commit()
        conn.close()

        return {
            "invoice_number": invoice_number,
            "invoice_amount": invoice_amount,
            "is_eligible": is_eligible,
            "rejection_reasons": rejection_reasons,
        }

    # ───────────────────── Pillar 2: Refund Estimator ──────────────────
    def estimate_vat_refund(
        self, mst: str, period_label: str,
        total_output_vat: float, total_input_vat: float,
        export_revenue: float = 0.0
    ) -> Dict[str, Any]:
        """Compute VAT refund eligibility per Article 15."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()

        uncredited = total_input_vat - total_output_vat
        if uncredited < 0:
            uncredited = 0.0

        refund_eligible = uncredited >= 300_000_000
        estimated_refund = 0.0

        if refund_eligible and export_revenue > 0:
            # Refund cap = 10% of export revenue (Article 15.1b)
            cap = export_revenue * 0.10
            estimated_refund = min(uncredited, cap)
        elif refund_eligible:
            estimated_refund = uncredited

        notes = None
        if not refund_eligible:
            notes = f"Uncredited balance {uncredited:,.0f} VND < 300,000,000 VND threshold"
        elif export_revenue > 0 and estimated_refund < uncredited:
            notes = f"Refund capped at 10% of export revenue ({export_revenue:,.0f} × 10% = {export_revenue * 0.10:,.0f})"

        cur.execute("""
            INSERT INTO vat_refund_estimates
                (period_label, total_output_vat, total_input_vat, uncredited_balance,
                 export_revenue, refund_eligible, estimated_refund, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (period_label, total_output_vat, total_input_vat, uncredited,
              export_revenue, 1 if refund_eligible else 0, estimated_refund, notes))

        conn.commit()
        conn.close()

        return {
            "period_label": period_label,
            "total_output_vat": total_output_vat,
            "total_input_vat": total_input_vat,
            "uncredited_balance": uncredited,
            "export_revenue": export_revenue,
            "refund_eligible": refund_eligible,
            "estimated_refund": estimated_refund,
            "notes": notes,
        }
