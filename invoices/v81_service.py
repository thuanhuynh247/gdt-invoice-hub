"""V81 Compliance Hub: Personal Income Tax (PIT) Withholding, Form 08/CK-TNCN & Electronic Certificates.

Implements:
1. Circular 111/2013/TT-BTC & Circular 25/2018/TT-BTC on PIT withholding (10% freelance vs. progressive rates).
2. Form 08/CK-TNCN commitment validation (MST check, single income source condition, deduction threshold calculation).
3. Circular 78/2021/TT-BTC on Electronic PIT Withholding Certificates (Chứng từ khấu trừ thuế TNCN điện tử).
4. Multi-Tenant database persistence in SQLite, Multi-Agent advisory consensus, and Form 05/KK-TNCN XML generation.
"""

from __future__ import annotations

import sqlite3
import re
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from invoices.multitenant_service import get_tenant_db_path


class V81PITComplianceService:
    """Version 81 Personal Income Tax (PIT) Compliance & Electronic Certificate Audit Engine."""

    # Key Legal Constants under Circular 111/2013/TT-BTC & Circular 25/2018/TT-BTC
    FREELANCE_THRESHOLD_VND = 2_000_000.0  # Threshold for 10% withholding per transaction
    PERSONAL_DEDUCTION_MONTHLY = 11_000_000.0  # 11M VND / month
    DEPENDENT_DEDUCTION_MONTHLY = 4_400_000.0  # 4.4M VND / dependent / month
    ANNUAL_PERSONAL_DEDUCTION = 132_000_000.0  # 132M VND / year
    ANNUAL_DEPENDENT_DEDUCTION = 52_800_000.0  # 52.8M VND / dependent / year
    FREELANCE_WITHHOLDING_RATE = 0.10  # 10% for residents
    NON_RESIDENT_WITHHOLDING_RATE = 0.20  # 20% for non-residents

    def __init__(self, base_data_dir: str | None = None):
        self.base_data_dir = base_data_dir

    def get_tenant_connection(self, mst: str) -> sqlite3.Connection:
        """Returns isolated sqlite3 connection to tenant database."""
        db_path = get_tenant_db_path(mst, self.base_data_dir)
        conn = sqlite3.connect(db_path)
        conn.text_factory = lambda x: x.decode('utf-8', errors='replace') if isinstance(x, bytes) else x
        conn.row_factory = sqlite3.Row

        cur = conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS v81_pit_audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                person_name TEXT NOT NULL,
                personal_id_or_mst TEXT,
                contract_type TEXT NOT NULL,
                payment_amount REAL NOT NULL,
                taxable_income REAL NOT NULL,
                withholding_tax REAL NOT NULL,
                net_payment REAL NOT NULL,
                has_form_08 BOOLEAN NOT NULL DEFAULT 0,
                form_08_valid BOOLEAN NOT NULL DEFAULT 0,
                has_elec_cert BOOLEAN NOT NULL DEFAULT 0,
                cert_number TEXT,
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

    @staticmethod
    def calculate_progressive_pit(taxable_income: float) -> float:
        """Calculate progressive monthly PIT for labor contract >= 3 months."""
        if taxable_income <= 0:
            return 0.0

        brackets = [
            (5_000_000, 0.05, 0),
            (10_000_000, 0.10, 250_000),
            (18_000_000, 0.15, 750_000),
            (32_000_000, 0.20, 1_650_000),
            (52_000_000, 0.25, 3_250_000),
            (80_000_000, 0.30, 5_850_000),
            (float("inf"), 0.35, 9_850_000),
        ]

        for upper, rate, deduction in brackets:
            if taxable_income <= upper:
                return round(taxable_income * rate - deduction, 2)
        return 0.0

    def audit_pit_transaction(
        self,
        mst: str,
        person_name: str,
        payment_amount: float,
        personal_id_or_mst: str = "",
        contract_type: str = "freelance",  # 'long_term' / 'resident_contract' (>= 3 mos), 'freelance' (< 3 mos / vụ việc), 'non_resident'
        num_dependents: int = 0,
        insurance_deduction: float = 0.0,
        has_form_08: bool = False,
        estimated_annual_income: float = 0.0,
        is_sole_income_source: bool = True,
        has_elec_cert: bool = False,
        cert_number: str = "",
    ) -> Dict[str, Any]:
        """
        Audit a personal payment against Circular 111/2013/TT-BTC, Circular 25/2018/TT-BTC, and Circular 78/2021/TT-BTC.
        """
        if payment_amount < 0:
            raise ValueError("Số tiền chi trả không được là số âm.")

        violations: List[str] = []
        recommendations: List[str] = []
        risk_points = 0
        form_08_valid = False
        form_08_status = "NOT_SUBMITTED"
        withholding_tax = 0.0
        taxable_income = 0.0
        applicable_tax_rate = 0.0

        clean_id_or_mst = personal_id_or_mst.strip()
        has_valid_mst = bool(re.match(r"^\d{10}(-\d{3})?$", clean_id_or_mst))

        is_labor_contract = contract_type in ("resident_contract", "long_term")

        if is_labor_contract:
            # Hợp đồng lao động từ 3 tháng trở lên: Áp dụng biểu lũy tiến từng phần
            total_deductions = self.PERSONAL_DEDUCTION_MONTHLY + (num_dependents * self.DEPENDENT_DEDUCTION_MONTHLY) + insurance_deduction
            taxable_income = max(0.0, payment_amount - total_deductions)
            withholding_tax = self.calculate_progressive_pit(taxable_income)
            applicable_tax_rate = round((withholding_tax / taxable_income * 100), 1) if taxable_income > 0 else 0.0
            form_08_status = "NOT_APPLICABLE"
            
            if not has_valid_mst:
                risk_points += 15
                violations.append("Người lao động ký HĐLĐ chưa đăng ký Mã số thuế cá nhân chính thức.")
                recommendations.append("Đăng ký MST cá nhân cho người lao động để được hưởng đầy đủ giảm trừ gia cảnh.")

        elif contract_type == "non_resident":
            # Cá nhân không cư trú: Khấu trừ 20% toàn bộ thu nhập
            taxable_income = payment_amount
            applicable_tax_rate = 20.0
            withholding_tax = round(payment_amount * self.NON_RESIDENT_WITHHOLDING_RATE, 2)
            form_08_status = "NOT_APPLICABLE"
            if not has_elec_cert and withholding_tax > 0:
                risk_points += 20
                violations.append("Chưa cấp Chứng từ khấu trừ thuế TNCN điện tử theo Thông tư 78/2021/TT-BTC.")
                recommendations.append("Xuất chứng từ khấu trừ thuế TNCN điện tử cấp cho cá nhân không cư trú.")

        else:
            # Thu nhập vãng lai / hợp đồng dưới 3 tháng / dịch vụ vụ việc
            taxable_income = payment_amount
            
            if payment_amount < self.FREELANCE_THRESHOLD_VND:
                # Chi trả dưới 2 triệu đồng/lần: Tạm thời không bắt buộc khấu trừ 10%
                withholding_tax = 0.0
                applicable_tax_rate = 0.0
                form_08_status = "EXEMPT_UNDER_2M"
                if has_form_08:
                    recommendations.append("Chi trả dưới 2 triệu không cần lập Cam kết 08/CK-TNCN.")
            else:
                # Chi trả từ 2 triệu đồng trở lên: Khấu trừ 10% trừ khi có Cam kết 08 hợp lệ
                applicable_tax_rate = 10.0
                if has_form_08:
                    # Kiểm tra tính hợp lệ của Cam kết mẫu 08/CK-TNCN
                    max_allowed_annual = self.ANNUAL_PERSONAL_DEDUCTION + (num_dependents * self.ANNUAL_DEPENDENT_DEDUCTION)
                    
                    if not has_valid_mst:
                        risk_points += 45
                        violations.append("Cam kết 08 KHÔNG hợp lệ: Cá nhân chưa có Mã số thuế (MST cá nhân) tại thời điểm làm cam kết.")
                        recommendations.append("Cá nhân bắt buộc phải có MST trước thời điểm ký cam kết theo Thông tư 111/2013.")
                        form_08_valid = False
                        form_08_status = "INVALID"
                        withholding_tax = round(payment_amount * self.FREELANCE_WITHHOLDING_RATE, 2)
                    elif not is_sole_income_source:
                        risk_points += 40
                        violations.append("Cam kết 08 KHÔNG hợp lệ: Cá nhân có thu nhập từ 2 nơi trở lên trong năm.")
                        recommendations.append("Cá nhân có nhiều nguồn thu nhập không đủ điều kiện làm Cam kết 08, phải khấu trừ 10%.")
                        form_08_valid = False
                        form_08_status = "INVALID"
                        withholding_tax = round(payment_amount * self.FREELANCE_WITHHOLDING_RATE, 2)
                    elif estimated_annual_income > max_allowed_annual:
                        risk_points += 35
                        violations.append(f"Cam kết 08 KHÔNG hợp lệ: Ước tính thu nhập năm ({estimated_annual_income:,.0f} đ) vượt ngưỡng giảm trừ gia cảnh ({max_allowed_annual:,.0f} đ).")
                        recommendations.append(f"Thu nhập vượt mức giảm trừ ({max_allowed_annual:,.0f} đ), bắt buộc phải khấu trừ 10%.")
                        form_08_valid = False
                        form_08_status = "INVALID"
                        withholding_tax = round(payment_amount * self.FREELANCE_WITHHOLDING_RATE, 2)
                    else:
                        form_08_valid = True
                        form_08_status = "VALID"
                        applicable_tax_rate = 0.0
                        withholding_tax = 0.0
                else:
                    # Bắt buộc khấu trừ 10%
                    form_08_status = "NOT_SUBMITTED"
                    withholding_tax = round(payment_amount * self.FREELANCE_WITHHOLDING_RATE, 2)
                    if not has_elec_cert:
                        risk_points += 15
                        recommendations.append("Cấp Chứng từ khấu trừ thuế TNCN điện tử (mẫu 03/TNCN điện tử) nếu cá nhân có yêu cầu.")

        net_payment = max(0.0, payment_amount - withholding_tax)

        # Electronic Certificate validation
        elec_cert_status = "NOT_REQUIRED"
        if has_elec_cert:
            if not cert_number:
                risk_points += 10
                elec_cert_status = "MISSING_SERIAL"
                violations.append("Khai báo có Chứng từ khấu trừ điện tử nhưng chưa điền số ký hiệu chứng từ.")
                recommendations.append("Bổ sung ký hiệu và số chứng từ khấu trừ thuế TNCN điện tử theo Thông tư 78/2021.")
            else:
                elec_cert_status = "ISSUED"
        elif withholding_tax > 0:
            elec_cert_status = "PENDING_REQUEST"

        # Determine Risk Level & Compliance Score
        compliance_score = max(0.0, 100.0 - risk_points)
        if risk_points >= 40:
            risk_level = "CRITICAL"
        elif risk_points >= 20:
            risk_level = "WARNING"
        else:
            risk_level = "SAFE"

        # Build Audit Notes
        notes_parts = []
        if is_labor_contract:
            notes_parts.append(f"[HĐLĐ dài hạn] Thu nhập {payment_amount:,.0f} đ, Giảm trừ gia cảnh: {self.PERSONAL_DEDUCTION_MONTHLY + (num_dependents * self.DEPENDENT_DEDUCTION_MONTHLY):,.0f} đ.")
        elif contract_type == "non_resident":
            notes_parts.append(f"[Cá nhân không cư trú] Khấu trừ 20% trên tổng thu nhập {payment_amount:,.0f} đ.")
        else:
            if has_form_08 and form_08_valid:
                notes_parts.append(f"[Vãng lai >= 2M] Đã áp dụng Cam kết 08/CK-TNCN hợp lệ (Tạm thời không khấu trừ 10%).")
            elif has_form_08 and not form_08_valid:
                notes_parts.append(f"[Vãng lai >= 2M] Cam kết 08 KHÔNG hợp lệ -> Bắt buộc khấu trừ 10% ({withholding_tax:,.0f} đ).")
            else:
                notes_parts.append(f"[Vãng lai] Khấu trừ 10% tại nguồn ({withholding_tax:,.0f} đ).")

        if violations:
            notes_parts.append("Vi phạm: " + "; ".join(violations))
        else:
            notes_parts.append("Hồ sơ tuân thủ đúng quy định về khấu trừ và quyết toán thuế TNCN.")

        audit_notes = " ".join(notes_parts)

        # Persist to Tenant DB
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO v81_pit_audit_logs (
                person_name, personal_id_or_mst, contract_type, payment_amount,
                taxable_income, withholding_tax, net_payment, has_form_08,
                form_08_valid, has_elec_cert, cert_number, risk_level,
                compliance_score, audit_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            person_name, clean_id_or_mst, contract_type, payment_amount,
            taxable_income, withholding_tax, net_payment,
            1 if has_form_08 else 0, 1 if form_08_valid else 0,
            1 if has_elec_cert else 0, cert_number, risk_level,
            compliance_score, audit_notes
        ))
        conn.commit()
        conn.close()

        # Advisory Council Debate
        debate = [
            {
                "speaker": "PIT Tax Inspector (Cán bộ Thuế TNCN)",
                "text": (
                    f"Khoản chi trả {payment_amount:,.0f} VNĐ cho {person_name}. "
                    + (f"Phát hiện Cam kết 08 sai quy định: Bắt buộc khấu trừ ngay 10% ({withholding_tax:,.0f} VNĐ), nếu không doanh nghiệp sẽ bị truy thu và phạt chậm nộp 0.03%/ngày theo Luật Quản lý Thuế 38/2019." if (has_form_08 and not form_08_valid) else f"Thuế khấu trừ xác định: {withholding_tax:,.0f} VNĐ. Tuân thủ Thông tư 111/2013/TT-BTC.")
                )
            },
            {
                "speaker": "HR & Payroll Director (Trưởng phòng Nhân sự & Tiền lương)",
                "text": (
                    f"Thực nhận của nhân sự: {net_payment:,.0f} VNĐ. "
                    + ("Đã yêu cầu người lao động bổ sung MST cá nhân và đăng ký người phụ thuộc để bảo vệ quyền lợi khấu trừ." if not has_valid_mst else "Hồ sơ thông tin nhân sự và MST đã được xác thực trên hệ thống.")
                )
            },
            {
                "speaker": "Chief Internal Auditor (Trưởng ban Kiểm toán Nội bộ)",
                "text": (
                    f"Đánh giá điểm tuân thủ {compliance_score:.1f}/100. "
                    + ("Cần chuẩn bị xuất Chứng từ khấu trừ thuế TNCN điện tử theo định dạng TT 78/2021/TT-BTC và đồng bộ dữ liệu vào Tờ khai 05/KK-TNCN quý." if withholding_tax > 0 else "Hồ sơ đủ điều kiện giải trình thanh tra thuế.")
                )
            }
        ]

        consensus_summary = (
            f"V81 PIT Audit Kết luận: Rủi ro [{risk_level}], Điểm tuân thủ {compliance_score:.1f}%. "
            f"Thuế TNCN khấu trừ: {withholding_tax:,.0f} VNĐ, Thực nhận (Net): {net_payment:,.0f} VNĐ."
        )

        return {
            "person_name": person_name,
            "personal_id_or_mst": clean_id_or_mst,
            "contract_type": contract_type,
            "payment_amount": payment_amount,
            "taxable_income": taxable_income,
            "withholding_tax": withholding_tax,
            "net_payment": net_payment,
            "applicable_tax_rate": applicable_tax_rate,
            "has_form_08": has_form_08,
            "form_08_valid": form_08_valid,
            "form_08_status": form_08_status,
            "has_elec_cert": has_elec_cert,
            "cert_number": cert_number,
            "elec_cert_status": elec_cert_status,
            "risk_level": risk_level,
            "compliance_score": compliance_score,
            "violations": violations,
            "recommendations": recommendations,
            "audit_notes": audit_notes,
            "debate": debate,
            "consensus_summary": consensus_summary,
        }

    def generate_05kk_xml(self, mst: str, tax_period: str = "Q1/2026", org_name: str = "DOANH NGHIEP") -> str:
        """
        Generate compliant XML content for Form 05/KK-TNCN (HTKK import).
        """
        logs = self.get_history(mst, limit=100)
        
        total_people = len(logs)
        total_payment = sum(r["payment_amount"] for r in logs)
        total_tax_withheld = sum(r["withholding_tax"] for r in logs)
        freelance_count = sum(1 for r in logs if r["contract_type"] != "long_term")

        xml_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<HSoThueDTu xmlns="http://kekhaithue.gdt.gov.vn/TKhai">',
            '  <HSoKhaiThue>',
            '    <TTinChung>',
            '      <TTinTKhaiThue>',
            '        <TKhai>05/KK-TNCN</TKhai>',
            '        <MoTaTKhai>Tờ khai khấu trừ thuế thu nhập cá nhân (Áp dụng cho tổ chức, cá nhân trả thu nhập)</MoTaTKhai>',
            f'        <KyKhaiThue>{tax_period}</KyKhaiThue>',
            f'        <NgayLapTKhai>{date.today().strftime("%d/%m/%Y")}</NgayLapTKhai>',
            '      </TTinTKhaiThue>',
            '      <TTinNNT>',
            f'        <MST>{mst}</MST>',
            f'        <TenNNT>{org_name}</TenNNT>',
            '      </TTinNNT>',
            '    </TTinChung>',
            '    <CTieuTKhaiChinh>',
            f'      <CT21>{total_people}</CT21>',  # Tổng số người nhận thu nhập
            f'      <CT22>{freelance_count}</CT22>',  # Tổng số cá nhân không ký HĐLĐ hoặc HĐLĐ < 3 tháng
            f'      <CT27>{int(total_payment)}</CT27>',  # Tổng thu nhập chịu thuế trả cho cá nhân
            f'      <CT30>{int(total_tax_withheld)}</CT30>',  # Tổng số thuế TNCN đã khấu trừ
            '    </CTieuTKhaiChinh>',
            '    <BangKe_05_1BK>',
        ]

        for i, row in enumerate(logs, start=1):
            xml_lines.append(f'      <ChiTiet id="{i}">')
            xml_lines.append(f'        <HoTen>{row["person_name"]}</HoTen>')
            xml_lines.append(f'        <MST>{row["personal_id_or_mst"]}</MST>')
            xml_lines.append(f'        <LoaiHD>{row["contract_type"]}</LoaiHD>')
            xml_lines.append(f'        <ThuNhapChiTra>{int(row["payment_amount"])}</ThuNhapChiTra>')
            xml_lines.append(f'        <ThueKhauTru>{int(row["withholding_tax"])}</ThueKhauTru>')
            xml_lines.append(f'        <ThucNhan>{int(row["net_payment"])}</ThucNhan>')
            xml_lines.append(f'        <CoCamKet08>{1 if row["has_form_08"] else 0}</CoCamKet08>')
            xml_lines.append('      </ChiTiet>')

        xml_lines.extend([
            '    </BangKe_05_1BK>',
            '  </HSoKhaiThue>',
            '</HSoThueDTu>'
        ])

        return "\n".join(xml_lines)

    def get_history(self, mst: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Retrieve recent V81 PIT audit logs."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()
        cur.execute("SELECT * FROM v81_pit_audit_logs ORDER BY id DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def delete_log(self, mst: str, log_id: int) -> bool:
        """Delete an audit log entry."""
        conn = self.get_tenant_connection(mst)
        cur = conn.cursor()
        cur.execute("DELETE FROM v81_pit_audit_logs WHERE id = ?", (log_id,))
        deleted = cur.rowcount > 0
        conn.commit()
        conn.close()
        return deleted
