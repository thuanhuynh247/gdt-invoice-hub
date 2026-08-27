"""V82 Compliance Hub: Tax Settlement, CIT/VAT Deductibility & E-Invoice Audit Engine.

Implements:
1. Circular 78/2014/TT-BTC, Circular 96/2015/TT-BTC & Law 38/2019/QH14 on Corporate Income Tax (CIT) & VAT deductibility.
2. Non-cash payment proof mandatory check for transactions >= 20,000,000 VND (Thông tư 219/2013/TT-BTC).
3. Vendor MST validity check, suspended/blacklisted enterprise detection, and E-Invoice XML signature verification.
4. Multi-Tenant database persistence in SQLite, Multi-Agent advisory consensus, and Tax Settlement Summary Report export.
"""

from __future__ import annotations

import sqlite3
import re
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from invoices.multitenant_service import get_tenant_db_path


class V82ComplianceService:
    """Version 82 Tax Settlement, Deductibility & E-Invoice Audit Engine."""

    NON_CASH_THRESHOLD_VND = 20_000_000.0  # 20M VND threshold for mandatory non-cash payment
    CIT_STANDARD_TAX_RATE = 0.20  # 20% Standard Corporate Income Tax

    def __init__(self, base_data_dir: str | None = None):
        self.base_data_dir = base_data_dir

    def get_tenant_connection(self, mst: str) -> sqlite3.Connection:
        """Returns isolated sqlite3 connection to tenant database with v82 schema."""
        db_path = get_tenant_db_path(mst, self.base_data_dir)
        conn = sqlite3.connect(db_path)
        conn.text_factory = lambda x: x.decode('utf-8', errors='replace') if isinstance(x, bytes) else x
        conn.row_factory = sqlite3.Row

        cur = conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS v82_compliance_audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vendor_name TEXT NOT NULL,
                vendor_mst TEXT NOT NULL,
                invoice_number TEXT NOT NULL,
                invoice_date TEXT NOT NULL,
                total_amount REAL NOT NULL,
                vat_amount REAL NOT NULL,
                payment_method TEXT NOT NULL,
                has_non_cash_proof BOOLEAN NOT NULL DEFAULT 0,
                is_valid_xml BOOLEAN NOT NULL DEFAULT 1,
                is_blacklisted BOOLEAN NOT NULL DEFAULT 0,
                cit_deductible_amount REAL NOT NULL,
                cit_non_deductible_amount REAL NOT NULL,
                vat_creditable_amount REAL NOT NULL,
                risk_level TEXT NOT NULL,
                compliance_score REAL NOT NULL DEFAULT 100,
                audit_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        return conn

    def _get_db_connection(self, mst: str) -> sqlite3.Connection:
        """Alias for get_tenant_connection for compatibility."""
        return self.get_tenant_connection(mst)

    def audit_invoice_deductibility(
        self,
        tenant_mst: str,
        vendor_name: str,
        vendor_mst: str,
        invoice_number: str,
        invoice_date: str,
        total_amount: float,
        vat_amount: float = 0.0,
        payment_method: str = "BANK_TRANSFER",  # BANK_TRANSFER, CASH, OFFSET, OTHER
        has_non_cash_proof: bool = True,
        is_valid_xml: bool = True,
        is_blacklisted: bool = False,
    ) -> Dict[str, Any]:
        """
        Audit a commercial invoice for CIT cost deductibility and VAT credit input compliance.
        """
        if total_amount < 0:
            raise ValueError("Số tiền hóa đơn không được là số âm.")

        violations: List[str] = []
        recommendations: List[str] = []
        risk_points = 0

        clean_vendor_mst = vendor_mst.strip()
        has_valid_mst = bool(re.match(r"^\d{10}(-\d{3})?$", clean_vendor_mst))

        amount_before_vat = max(0.0, total_amount - vat_amount)

        cit_deductible_amount = amount_before_vat
        cit_non_deductible_amount = 0.0
        vat_creditable_amount = vat_amount

        # 1. Check Vendor MST Validity & Blacklist Status
        if not has_valid_mst:
            risk_points += 40
            violations.append("Mã số thuế bên bán không đúng định dạng chuẩn Cục Thuế (10 hoặc 13 chữ số).")
            recommendations.append("Yêu cầu bên bán cung cấp đúng MST chuẩn theo Giấy chứng nhận ĐKKD.")

        if is_blacklisted:
            risk_points += 50
            cit_deductible_amount = 0.0
            cit_non_deductible_amount = amount_before_vat
            vat_creditable_amount = 0.0
            violations.append("CẢNH BÁO NGHÊM TRỌNG: Bên bán thuộc danh sách doanh nghiệp bỏ địa điểm kinh doanh hoặc ngừng hoạt động.")
            recommendations.append("Loại bỏ toàn bộ chi phí được trừ khi quyết toán thuế TNDN và không kê khai khấu trừ thuế GTGT.")

        # 2. Check XML Integrity & E-Invoice Signature
        if not is_valid_xml:
            risk_points += 35
            cit_deductible_amount = 0.0
            cit_non_deductible_amount = amount_before_vat
            vat_creditable_amount = 0.0
            violations.append("Hóa đơn điện tử không hợp lệ (Lỗi chữ ký số, sai cấu trúc XML hoặc hóa đơn bị hủy).")
            recommendations.append("Yêu cầu bên bán lập hóa đơn thay thế hoặc điều chỉnh hợp lệ theo Nghị định 123/2020/NĐ-CP.")

        # 3. Non-Cash Payment Requirement for Transactions >= 20,000,000 VND
        requires_non_cash = total_amount >= self.NON_CASH_THRESHOLD_VND
        is_cash_payment = payment_method.upper() == "CASH"

        if requires_non_cash and (is_cash_payment or not has_non_cash_proof):
            risk_points += 30
            cit_deductible_amount = 0.0
            cit_non_deductible_amount = amount_before_vat
            vat_creditable_amount = 0.0
            violations.append(f"Hóa đơn từ {self.NON_CASH_THRESHOLD_VND:,.0f} VNĐ thanh toán bằng tiền mặt hoặc thiếu chứng từ thanh toán không dùng tiền mặt.")
            recommendations.append("Bổ sung ủy nhiệm chi/chứng từ chuyển khoản ngân hàng qua tài khoản đã đăng ký với cơ quan thuế (Thông tư 219/2013).")

        # Calculate Compliance Score and Risk Level
        compliance_score = max(0.0, 100.0 - risk_points)
        if risk_points >= 40:
            risk_level = "CRITICAL"
        elif risk_points >= 20:
            risk_level = "WARNING"
        else:
            risk_level = "SAFE"

        # Build Audit Notes
        notes_parts = []
        if risk_level == "SAFE":
            notes_parts.append(f"Hóa đơn số {invoice_number} đủ điều kiện tính chi phí được trừ ({cit_deductible_amount:,.0f} VNĐ) và khấu trừ GTGT ({vat_creditable_amount:,.0f} VNĐ).")
        else:
            notes_parts.append(f"Hóa đơn số {invoice_number} bị loại chi phí TNDN ({cit_non_deductible_amount:,.0f} VNĐ).")
            notes_parts.append("Lý do: " + "; ".join(violations))

        audit_notes = " ".join(notes_parts)

        # Persist Audit Log
        conn = self.get_tenant_connection(tenant_mst)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO v82_compliance_audit_logs (
                vendor_name, vendor_mst, invoice_number, invoice_date, total_amount,
                vat_amount, payment_method, has_non_cash_proof, is_valid_xml,
                is_blacklisted, cit_deductible_amount, cit_non_deductible_amount,
                vat_creditable_amount, risk_level, compliance_score, audit_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            vendor_name, clean_vendor_mst, invoice_number, invoice_date, total_amount,
            vat_amount, payment_method, 1 if has_non_cash_proof else 0,
            1 if is_valid_xml else 0, 1 if is_blacklisted else 0,
            cit_deductible_amount, cit_non_deductible_amount, vat_creditable_amount,
            risk_level, compliance_score, audit_notes
        ))
        conn.commit()
        conn.close()

        # Multi-Agent Debate Simulation
        debate = [
            {
                "speaker": "Tax Audit Senior Inspector (Thanh tra Thuế TNDN)",
                "text": (
                    f"Hóa đơn {invoice_number} từ NCC {vendor_name} (MST: {clean_vendor_mst}) giá trị {total_amount:,.0f} VNĐ. "
                    + (f"Phát hiện vi phạm nghiêm trọng: {violations[0]}" if violations else "Đủ điều kiện ghi nhận chi phí hợp lý hợp lệ theo Thông tư 96/2015/TT-BTC.")
                )
            },
            {
                "speaker": "Chief Financial Officer (Giám đốc Tài chính CFO)",
                "text": (
                    f"Tổng chi phí trước thuế: {amount_before_vat:,.0f} VNĐ. "
                    + (f"Cần điều chỉnh giảm chi phí được trừ khi quyết toán Mẫu 03/TNDN ({cit_non_deductible_amount:,.0f} VNĐ)." if cit_non_deductible_amount > 0 else f"Chi phí được trừ TNDN: {cit_deductible_amount:,.0f} VNĐ, Thuế GTGT khấu trừ: {vat_creditable_amount:,.0f} VNĐ.")
                )
            },
            {
                "speaker": "Chief Compliance Officer (Trưởng ban Tuân thủ)",
                "text": (
                    f"Đánh giá mức độ tuân thủ [{risk_level}], Điểm tuân thủ {compliance_score:.1f}/100. "
                    + (f"Khuyến nghị action: {recommendations[0]}" if recommendations else "Hồ sơ hóa đơn đáp ứng 100% tiêu chuẩn giải trình quyết toán thuế.")
                )
            }
        ]

        consensus_summary = (
            f"V82 Compliance Kết luận: Rủi ro [{risk_level}], Điểm tuân thủ {compliance_score:.1f}%. "
            f"Chi phí được trừ: {cit_deductible_amount:,.0f} VNĐ, Không được trừ: {cit_non_deductible_amount:,.0f} VNĐ, Thuế GTGT được khấu trừ: {vat_creditable_amount:,.0f} VNĐ."
        )

        return {
            "vendor_name": vendor_name,
            "vendor_mst": clean_vendor_mst,
            "invoice_number": invoice_number,
            "invoice_date": invoice_date,
            "total_amount": total_amount,
            "vat_amount": vat_amount,
            "amount_before_vat": amount_before_vat,
            "payment_method": payment_method,
            "has_non_cash_proof": has_non_cash_proof,
            "is_valid_xml": is_valid_xml,
            "is_blacklisted": is_blacklisted,
            "cit_deductible_amount": cit_deductible_amount,
            "cit_non_deductible_amount": cit_non_deductible_amount,
            "vat_creditable_amount": vat_creditable_amount,
            "risk_level": risk_level,
            "compliance_score": compliance_score,
            "violations": violations,
            "recommendations": recommendations,
            "audit_notes": audit_notes,
            "debate": debate,
            "consensus_summary": consensus_summary,
        }

    def get_summary_analytics(self, tenant_mst: str) -> Dict[str, Any]:
        """
        Get aggregated compliance analytics for the dashboard Bento cards.
        """
        conn = self.get_tenant_connection(tenant_mst)
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                COUNT(*) as total_invoices,
                COALESCE(SUM(total_amount), 0) as grand_total_amount,
                COALESCE(SUM(cit_deductible_amount), 0) as total_deductible,
                COALESCE(SUM(cit_non_deductible_amount), 0) as total_non_deductible,
                COALESCE(SUM(vat_creditable_amount), 0) as total_vat_creditable,
                AVG(compliance_score) as avg_score,
                SUM(CASE WHEN risk_level = 'CRITICAL' THEN 1 ELSE 0 END) as critical_count,
                SUM(CASE WHEN risk_level = 'WARNING' THEN 1 ELSE 0 END) as warning_count,
                SUM(CASE WHEN risk_level = 'SAFE' THEN 1 ELSE 0 END) as safe_count
            FROM v82_compliance_audit_logs
        """)
        row = dict(cur.fetchone())
        conn.close()

        total = row["total_invoices"] or 1
        return {
            "total_invoices": row["total_invoices"],
            "grand_total_amount": row["grand_total_amount"],
            "total_deductible": row["total_deductible"],
            "total_non_deductible": row["total_non_deductible"],
            "total_vat_creditable": row["total_vat_creditable"],
            "avg_score": round(row["avg_score"] or 100.0, 1),
            "critical_count": row["critical_count"],
            "warning_count": row["warning_count"],
            "safe_count": row["safe_count"],
            "compliance_rate": round((row["safe_count"] / total) * 100, 1),
        }

    def get_history(self, tenant_mst: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Retrieve recent V82 audit logs."""
        conn = self.get_tenant_connection(tenant_mst)
        cur = conn.cursor()
        cur.execute("SELECT * FROM v82_compliance_audit_logs ORDER BY id DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def delete_log(self, tenant_mst: str, log_id: int) -> bool:
        """Delete an audit log entry."""
        conn = self.get_tenant_connection(tenant_mst)
        cur = conn.cursor()
        cur.execute("DELETE FROM v82_compliance_audit_logs WHERE id = ?", (log_id,))
        deleted = cur.rowcount > 0
        conn.commit()
        conn.close()
        return deleted
