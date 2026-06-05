"""Version 26.0.0 Advanced Compliance Services.

Includes:
- Social Insurance (BHXH/BHYT/BHTN) Reconciliation & Auditing Engine (US-380)
- PIT Finalization & Insurance Reconciliation Reporting (US-381)
- Electronic Tax Ledger (Sổ thuế điện tử) Sync & Reconciliation (US-382)
- VietQR Dynamic Tax Payment Slip Generator & Status Tracker (US-383)
- Vietnamese Tax Law Knowledge Graph & Vector Store Indexer (US-384)
- Dynamic Audit Defense Document Composer & Socratic Adviser (US-385)
"""

from __future__ import annotations
import csv
import io
import math
import uuid
import datetime
from extensions import db

# ── US-380 & US-381: Social Insurance & PIT Reconciliation ─────────────────────

DEFAULT_BASIC_SALARY = 2340000.0  # VND (applicable from July 2024 onwards)
SI_CAP_MULTIPLIER = 20

# Statutory Contribution Rates
EMPLOYER_RATES = {
    "BHXH": 0.175,
    "BHYT": 0.03,
    "BHTN": 0.01
}
EMPLOYEE_RATES = {
    "BHXH": 0.08,
    "BHYT": 0.015,
    "BHTN": 0.01
}

def calculate_statutory_insurance(gross_salary: float, basic_salary: float = DEFAULT_BASIC_SALARY) -> dict:
    """Calculate statutory social insurance contributions under capped limits."""
    cap_wage = basic_salary * SI_CAP_MULTIPLIER
    # SI & HI cap at 20x basic salary
    si_hi_base = min(gross_salary, cap_wage)
    # UI caps at 20x regional minimum salary (for simplicity, we cap UI using same cap_wage or base)
    ui_base = min(gross_salary, cap_wage)
    
    employer_contributions = {
        "BHXH": si_hi_base * EMPLOYER_RATES["BHXH"],
        "BHYT": si_hi_base * EMPLOYER_RATES["BHYT"],
        "BHTN": ui_base * EMPLOYER_RATES["BHTN"]
    }
    employee_contributions = {
        "BHXH": si_hi_base * EMPLOYEE_RATES["BHXH"],
        "BHYT": si_hi_base * EMPLOYEE_RATES["BHYT"],
        "BHTN": ui_base * EMPLOYEE_RATES["BHTN"]
    }
    
    total_employer = sum(employer_contributions.values())
    total_employee = sum(employee_contributions.values())
    
    return {
        "si_hi_base": si_hi_base,
        "employer": employer_contributions,
        "employee": employee_contributions,
        "total_employer": total_employer,
        "total_employee": total_employee,
        "is_capped": gross_salary > cap_wage
    }

def audit_social_insurance(payroll_records: list[dict], basic_salary: float = DEFAULT_BASIC_SALARY) -> dict:
    """Compare local employee payroll deductions against statutory insurance contributions."""
    audited_employees = []
    discrepancies = []
    total_payroll_insurance = 0.0
    total_statutory_insurance = 0.0
    total_employer_insurance = 0.0
    
    for emp in payroll_records:
        emp_id = emp.get("id") or str(uuid.uuid4())
        name = emp.get("name", "N/A")
        gross = emp.get("gross_salary", 0.0)
        withheld_ins = emp.get("withheld_insurance", 0.0)
        
        stat = calculate_statutory_insurance(gross, basic_salary)
        diff = withheld_ins - stat["total_employee"]
        
        status = "compliant"
        issues = []
        if abs(diff) > 10.0:  # 10 VND variance tolerance
            status = "flagged"
            issues.append(f"Chênh lệch bảo hiểm khấu trừ: {diff:,.0f} VND")
            discrepancies.append({
                "employee_id": emp_id,
                "employee_name": name,
                "type": "SI_MISMATCH",
                "message": f"Dự phòng khấu trừ BH: {withheld_ins:,.0f} VND vs Luật định: {stat['total_employee']:,.0f} VND (Chênh lệch: {diff:,.0f} VND)"
            })
            
        audited_employees.append({
            "id": emp_id,
            "name": name,
            "gross_salary": gross,
            "withheld_insurance": withheld_ins,
            "statutory_employee": stat["total_employee"],
            "statutory_employer": stat["total_employer"],
            "variance": diff,
            "status": status,
            "issues": issues,
            "breakdown": stat
        })
        
        total_payroll_insurance += withheld_ins
        total_statutory_insurance += stat["total_employee"]
        total_employer_insurance += stat["total_employer"]
        
    compliance_score = 100
    if payroll_records:
        failures = len(discrepancies)
        compliance_score = max(0, int(((len(payroll_records) - failures) / len(payroll_records)) * 100))
        
    return {
        "audited_employees": audited_employees,
        "discrepancies": discrepancies,
        "total_payroll_insurance": total_payroll_insurance,
        "total_statutory_insurance": total_statutory_insurance,
        "total_employer_insurance": total_employer_insurance,
        "compliance_score": compliance_score,
        "status": "success" if compliance_score == 100 else "flagged"
    }

def export_si_reconciliation_csv(audit_result: dict) -> str:
    """Export the social insurance reconciliation report as a formatted CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers
    writer.writerow(["BÁO CÁO ĐỐI CHIẾU TRÍCH ĐÓNG BẢO HIỂM XÃ HỘI (BHXH/BHYT/BHTN)"])
    writer.writerow([f"Ngày báo cáo: {datetime.datetime.now().strftime('%d/%m/%Y')}"])
    writer.writerow([])
    writer.writerow([
        "Mã Nhân Viên", "Họ Tên", "Lương Gross", "Khấu Trừ Thực Tế (NV)", 
        "Khấu Trừ Luật Định (NV)", "Trích Đóng Doanh Nghiệp", "Chênh Lệch", "Trạng Thái"
    ])
    
    for emp in audit_result.get("audited_employees", []):
        writer.writerow([
            emp["id"],
            emp["name"],
            f"{emp['gross_salary']:.0f}",
            f"{emp['withheld_insurance']:.0f}",
            f"{emp['statutory_employee']:.0f}",
            f"{emp['statutory_employer']:.0f}",
            f"{emp['variance']:.0f}",
            emp["status"].upper()
        ])
        
    writer.writerow([])
    writer.writerow([
        "TỔNG CỘNG", "", "",
        f"{audit_result.get('total_payroll_insurance', 0):.0f}",
        f"{audit_result.get('total_statutory_insurance', 0):.0f}",
        f"{audit_result.get('total_employer_insurance', 0):.0f}",
        f"{audit_result.get('total_payroll_insurance', 0) - audit_result.get('total_statutory_insurance', 0):.0f}",
        audit_result.get("status").upper()
    ])
    
    return output.getvalue()


# ── US-382: Electronic Tax Ledger Sync & Reconciliation ────────────────────────

def get_mock_etax_ledger(mst: str) -> dict:
    """Mock fetching the electronic tax ledger (Sổ thuế điện tử) from GDT portal."""
    return {
        "mst": mst,
        "taxpayer_name": "Công ty TNHH Giải pháp Phần mềm Ánh Sáng",
        "last_sync": datetime.datetime.now().isoformat(),
        "balances": [
            {"tax_type": "VAT", "obligation": 85000000.0, "paid": 80000000.0, "late_fee": 120000.0, "credit": 0.0},
            {"tax_type": "CIT", "obligation": 120000000.0, "paid": 120000000.0, "late_fee": 0.0, "credit": 5000000.0},
            {"tax_type": "PIT", "obligation": 15000000.0, "paid": 12000000.0, "late_fee": 45000.0, "credit": 0.0},
            {"tax_type": "FCT", "obligation": 0.0, "paid": 0.0, "late_fee": 0.0, "credit": 0.0}
        ]
    }

def reconcile_tax_ledger(mst: str, local_tax_payments: list[dict]) -> dict:
    """Reconcile dynamic local tax payment journal vouchers against the eTax ledger."""
    ledger = get_mock_etax_ledger(mst)
    reconciled_balances = []
    discrepancies = []
    
    for balance in ledger["balances"]:
        tax_type = balance["tax_type"]
        etax_paid = balance["paid"]
        
        # Sum local payments matching tax_type
        local_paid = sum(p.get("amount", 0.0) for p in local_tax_payments if p.get("tax_type") == tax_type)
        diff = local_paid - etax_paid
        
        status = "matched"
        if abs(diff) > 1.0:
            status = "mismatched"
            discrepancies.append({
                "tax_type": tax_type,
                "message": f"Mất cân đối sổ thuế {tax_type}: Ghi nhận local={local_paid:,.0f} VND vs e-Tax nộp={etax_paid:,.0f} VND (Chênh lệch: {diff:,.0f} VND)"
            })
            
        reconciled_balances.append({
            "tax_type": tax_type,
            "obligation": balance["obligation"],
            "etax_paid": etax_paid,
            "local_paid": local_paid,
            "late_fee": balance["late_fee"],
            "credit": balance["credit"],
            "variance": diff,
            "status": status
        })
        
    return {
        "mst": mst,
        "reconciled_balances": reconciled_balances,
        "discrepancies": discrepancies,
        "reconciliation_time": datetime.datetime.now().isoformat(),
        "status": "success" if not discrepancies else "flagged"
    }


# ── US-383: VietQR Payment Slip Generator ─────────────────────────────────────

def generate_napas_vietqr_payload(
    tax_type: str,
    amount: float,
    mst: str,
    account_number: str = "1130009999",
    bank_bin: str = "970415",  # VietinBank BIN
    receiver_name: str = "KHO BAC NHA NUOC"
) -> dict:
    """Scaffold a Napas 247 dynamic VietQR code string based on EMVCo specifications."""
    # VietQR format requires tag-length-value (TLV) structuring
    # Payload format indicator: tag 00, value '01'
    # Point of initiation method: tag 01, value '12' (dynamic QR)
    # Merchant account information: tag 38 (VietQR template)
    #   Subtag 00: Guid (A000000727)
    #   Subtag 01: Napas Consumer (Bank Bin + Account number)
    #   Subtag 02: Service Code ('QRIBFTTA')
    
    guid = "A000000727"
    napas_data = f"00{len(bank_bin):02d}{bank_bin}01{len(account_number):02d}{account_number}"
    service = "0208QRIBFTTA"
    sub_tag_38 = f"00{len(guid):02d}{guid}01{len(napas_data):02d}{napas_data}{service}"
    tag_38 = f"38{len(sub_tag_38):02d}{sub_tag_38}"
    
    # Currency Code: tag 53, value '704' (VND)
    tag_53 = "5303704"
    # Amount: tag 54
    amt_str = f"{amount:.0f}"
    tag_54 = f"54{len(amt_str):02d}{amt_str}"
    # Country Code: tag 58, value 'VN'
    tag_58 = "5802VN"
    # Merchant Name: tag 59
    tag_59 = f"59{len(receiver_name):02d}{receiver_name}"
    # Transaction Message: tag 62 (contains reference/billing info)
    msg = f"NOP THUE {tax_type} MST {mst}"
    sub_tag_62 = f"08{len(msg):02d}{msg}"
    tag_62 = f"62{len(sub_tag_62):02d}{sub_tag_62}"
    
    qr_base = f"000201010212{tag_38}{tag_53}{tag_54}{tag_58}{tag_59}{tag_62}6304"
    
    # Calculate CRC16 checksum (simple polynomial implementation)
    crc = 0xFFFF
    for char in qr_base:
        crc ^= ord(char) << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    
    crc_hex = f"{crc:04X}"
    vietqr_string = qr_base + crc_hex
    
    # Create a dynamic mock transaction in-memory/database
    tx_id = f"TAX-PAY-{uuid.uuid4().hex[:8].upper()}"
    
    return {
        "transaction_id": tx_id,
        "vietqr_string": vietqr_string,
        "amount": amount,
        "beneficiary": receiver_name,
        "account": account_number,
        "bank_bin": bank_bin,
        "payment_msg": msg,
        "status": "pending",
        "created_at": datetime.datetime.now().isoformat()
    }


# ── US-384: Tax Law Knowledge Graph ───────────────────────────────────────────

class TaxLawKnowledgeGraph:
    """Constructs a structural node-linked Knowledge Graph of Vietnamese tax regulations."""
    
    def __init__(self):
        self.nodes = {}
        self.vector_index = []
        self._build_graph()
        
    def _build_graph(self):
        # Index key provisions of Decree 123, Circular 80, Decree 132
        laws = [
            {
                "id": "D123-A15",
                "document": "Decree 123/2020/NĐ-CP",
                "article": "Article 15",
                "content": "Thời điểm ký số trên hóa đơn điện tử là thời điểm người bán, người mua ký số trên hóa đơn điện tử được hiển thị theo định dạng ngày, tháng, năm. Trường hợp hóa đơn điện tử đã lập có thời điểm ký số khác thời điểm lập hóa đơn thì thời điểm khai thuế là thời điểm lập hóa đơn.",
                "keywords": ["ký số", "thời điểm", "khai thuế", "lập hóa đơn", "signing time", "invoice date"],
                "links": ["C80-A8"]
            },
            {
                "id": "C80-A8",
                "document": "Circular 80/2021/TT-BTC",
                "article": "Article 8",
                "content": "Hóa đơn điện tử không có mã của cơ quan thuế hoặc có mã của cơ quan thuế phải đảm bảo đầy đủ các điều kiện về chữ ký số, định dạng dữ liệu truyền nhận, đối chiếu số liệu và phương thức thanh toán không dùng tiền mặt đối với các hóa đơn có giá trị lớn.",
                "keywords": ["chữ ký số", "không dùng tiền mặt", "hóa đơn lớn", "nộp thuế", "cashless"],
                "links": ["D123-A15", "C80-A4"]
            },
            {
                "id": "C80-A4",
                "document": "Circular 80/2021/TT-BTC",
                "article": "Article 4",
                "content": "Giao dịch thanh toán mua bán hàng hóa dịch vụ từ 20 triệu đồng trở lên phải có chứng từ thanh toán không dùng tiền mặt (chuyển khoản ngân hàng, đối trừ công nợ, ủy quyền thanh toán) để được khấu trừ thuế GTGT đầu vào và tính vào chi phí được trừ khi xác định thuế TNDN.",
                "keywords": ["20 triệu", "chuyển khoản", "khấu trừ", "chi phí được trừ", "tiền mặt", "cash limit"],
                "links": ["C80-A8"]
            },
            {
                "id": "D132-A8",
                "document": "Decree 132/2020/NĐ-CP",
                "article": "Article 8",
                "content": "Quy định khống chế chi phí lãi tiền vay được trừ khi xác định thu nhập chịu thuế TNDN đối với doanh nghiệp có giao dịch liên kết không vượt quá 30% tổng chi phí lãi vay ròng phát sinh cộng EBITDA trong kỳ.",
                "keywords": ["giao dịch liên kết", "chi phí lãi vay", "30% EBITDA", "liên kết", "related party", "ebitda"],
                "links": ["D132-A5"]
            },
            {
                "id": "D132-A5",
                "document": "Decree 132/2020/NĐ-CP",
                "article": "Article 5",
                "content": "Xác định các bên có quan hệ liên kết dựa trên tỷ lệ sở hữu vốn (tối thiểu 25% đối với công ty cổ phần, 35% đối với công ty trách nhiệm hữu hạn), hoặc sự kiểm soát trực tiếp/gián tiếp điều hành chỉ đạo sản xuất kinh doanh.",
                "keywords": ["quan hệ liên kết", "sở hữu vốn", "kiểm soát", "vốn góp", "control", "capital"],
                "links": ["D132-A8"]
            }
        ]
        
        for law in laws:
            self.nodes[law["id"]] = law
            self.vector_index.append(law)
            
    def keyword_search(self, query: str) -> list[dict]:
        """Simple TF-IDF keyword overlap similarity query mapper."""
        query_words = set(query.lower().split())
        results = []
        
        for node in self.vector_index:
            score = 0
            # Check content matching
            for kw in node["keywords"]:
                if kw.lower() in query.lower():
                    score += 3
            for word in query_words:
                if word in node["content"].lower():
                    score += 1
            if score > 0:
                results.append((score, node))
                
        # Sort by score descending
        results.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in results]

    def get_related_citations(self, node_id: str) -> list[dict]:
        """Retrieve cross-referenced citation nodes linked in the knowledge graph."""
        node = self.nodes.get(node_id)
        if not node:
            return []
        return [self.nodes[link_id] for link_id in node["links"] if link_id in self.nodes]


# ── US-385: Dynamic Audit Defense Document Composer ─────────────────────────

def compose_audit_defense_letter(
    taxpayer_profile: dict,
    audit_warning_type: str,
    context_answers: dict
) -> str:
    """Generate a custom, professional, GDT-formatted compliance explanation/defense letter."""
    kg = TaxLawKnowledgeGraph()
    citations = []
    argument = ""
    
    # Build customized arguments based on Socratic fact questionnaire answers
    if audit_warning_type == "LATE_SIGNING":
        nodes = kg.keyword_search("ký số thời điểm lập hóa đơn")
        citations = [nodes[0]] if nodes else []
        
        declaration_period = context_answers.get("declaration_period", "thời điểm lập hóa đơn")
        argument = f"""Thời điểm ký số trên hóa đơn trễ hơn thời điểm lập hóa đơn. Tuy nhiên, căn cứ theo <b>Nghị định 123/2020/NĐ-CP Điều 15 Khoản 9</b>, thời điểm khai thuế đối với bên bán và bên mua vẫn được xác định thống nhất theo <u>thời điểm lập hóa đơn</u> ({declaration_period}). Đơn vị đã kê khai và nộp thuế GTGT đầy đủ đúng kỳ hạn lập hóa đơn nên không phát sinh hành vi trốn thuế hay nộp chậm tiền thuế."""
        
    elif audit_warning_type == "CASH_PAYMENT_LIMIT":
        nodes = kg.keyword_search("20 triệu chuyển khoản khấu trừ")
        citations = [nodes[0]] if nodes else []
        
        has_voucher = context_answers.get("bank_voucher", False)
        if has_voucher:
            argument = """Mặc dù hóa đơn gốc thể hiện phương thức thanh toán là tiền mặt (TM), đơn vị đã thực hiện thanh toán chuyển khoản qua ngân hàng thương mại và có đầy đủ ủy nhiệm chi/chứng từ chuyển tiền tài khoản ngân hàng của người mua sang tài khoản người bán. Giao dịch đáp ứng hoàn toàn điều kiện khấu trừ thuế GTGT và chi phí hợp lệ theo <b>Thông tư 80/2021/TT-BTC</b>."""
        else:
            agreement_date = context_answers.get("payment_agreement_date", "thỏa thuận trả chậm")
            argument = f"""Giao dịch có giá trị trên 20 triệu đồng hiện tại chưa thực hiện thanh toán chuyển khoản do đang áp dụng điều khoản trả chậm theo hợp đồng mua bán số {context_answers.get('contract_no', 'N/A')} ký ngày {agreement_date}. Tại thời điểm quyết toán, đơn vị chưa thanh toán bằng tiền mặt trực tiếp nên vẫn đủ điều kiện tạm khấu trừ thuế GTGT đầu vào."""
            
    elif audit_warning_type == "RELATED_PARTY_EBITDA":
        nodes = kg.keyword_search("giao dịch liên kết chi phí lãi vay 30% ebitda")
        citations = [nodes[0]] if nodes else []
        
        ebitda = context_answers.get("ebitda_amount", 0.0)
        net_interest = context_answers.get("net_interest_expense", 0.0)
        allowed_cap = ebitda * 0.30
        excess = max(0.0, net_interest - allowed_cap)
        
        argument = f"""Đơn vị có phát sinh giao dịch liên kết thuộc phạm vi điều chỉnh của Nghị định 132/2020/NĐ-CP. Tổng chi phí lãi vay ròng phát sinh là {net_interest:,.0f} VND. Chỉ số EBITDA năm tài chính là {ebitda:,.0f} VND. Hạn mức chi phí lãi vay được trừ theo mức trần 30% là {allowed_cap:,.0f} VND. Phần chi phí lãi vay vượt mức trần là {excess:,.0f} VND đã được đơn vị tự giác loại trừ khỏi tờ khai quyết toán thuế TNDN (Mẫu 01/TNDN) hoặc chuyển kỳ sau theo đúng quy định tại <b>Điều 8 Nghị định 132</b>."""
        
    else:
        argument = "Đơn vị giải trình giao dịch mua bán hàng hóa, dịch vụ được thực hiện thực tế, đầy đủ hóa đơn, chứng từ hợp pháp, hạch toán đúng tài khoản và tuân thủ đầy đủ quy định pháp luật về thuế hiện hành."

    # Combine into standard template
    citation_block = ""
    for cit in citations:
        citation_block += f"""
        <div class="citation-node" style="margin-top: 15px; padding: 12px; background: rgba(255,255,255,0.05); border-left: 3px solid #3b82f6; border-radius: 4px;">
            <strong>Căn cứ pháp lý: {cit['document']} ({cit['article']})</strong>
            <p style="margin: 5px 0 0 0; font-size: 0.9em; line-height: 1.4; color: var(--text-muted, #94a3b8);">{cit['content']}</p>
        </div>
        """

    letter_html = f"""
    <div class="defense-letter-container" style="font-family: 'Outfit', 'Inter', sans-serif; padding: 30px; max-width: 800px; margin: auto; background: var(--card-bg, #1e293b); color: var(--text-main, #f8fafc); border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.3);">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 20px;">
            <div>
                <h4 style="margin: 0; color: #3b82f6; text-transform: uppercase;">CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM</h4>
                <small style="display: block; text-align: center; font-weight: bold; margin-top: 3px;">Độc lập - Tự do - Hạnh phúc</small>
            </div>
            <div style="text-align: right;">
                <small>Mã số thuế: {taxpayer_profile.get('mst', '0102030405')}</small><br>
                <small>Số: DF-{uuid.uuid4().hex[:6].upper()}/2026</small>
            </div>
        </div>
        
        <h3 style="text-align: center; margin-top: 30px; margin-bottom: 25px; text-transform: uppercase; letter-spacing: 0.5px;">V/v: GIẢI TRÌNH, BIỆN HỘ COMPLIANCE AUDIT</h3>
        
        <p><strong>Kính gửi:</strong> Chi cục Thuế / Đoàn kiểm tra thuế {taxpayer_profile.get('district', 'Nội bộ')}</p>
        
        <p style="text-indent: 30px; line-height: 1.6;">
            Công ty {taxpayer_profile.get('company_name', 'TNHH Giải pháp Phần mềm Ánh Sáng')} xin kính trình giải trình liên quan đến cảnh báo kiểm soát nội bộ (Mã cảnh báo: {audit_warning_type}) như sau:
        </p>
        
        <div class="defense-argument-body" style="padding: 15px; background: rgba(59, 130, 246, 0.08); border-radius: 8px; line-height: 1.6; margin-bottom: 20px;">
            {argument}
        </div>
        
        {citation_block}
        
        <p style="margin-top: 35px; line-height: 1.6;">
            Công ty cam kết các thông tin giải trình trên hoàn toàn trung thực, khách quan và chịu trách nhiệm trước pháp luật về tính chính xác của tài liệu giải trình đính kèm.
        </p>
        
        <div style="margin-top: 40px; display: flex; justify-content: space-between; align-items: flex-end;">
            <div>
                <p style="margin: 0; font-size: 0.85em; color: var(--text-muted, #94a3b8);">Tài liệu đính kèm:</p>
                <ul style="margin: 5px 0 0 0; padding-left: 20px; font-size: 0.85em; color: var(--text-muted, #94a3b8);">
                    <li>Bảng đối chiếu hạch toán kế toán</li>
                    <li>Chứng từ thanh toán chuyển khoản ngân hàng</li>
                </ul>
            </div>
            <div style="text-align: center; width: 250px;">
                <strong>Đại diện người nộp thuế</strong><br>
                <small style="color: var(--text-muted, #94a3b8); font-style: italic;">(Ký, ghi rõ họ tên và đóng dấu)</small>
                <div style="height: 60px;"></div>
                <strong>{taxpayer_profile.get('representative', 'Giám Đốc')}</strong>
            </div>
        </div>
    </div>
    """
    return letter_html
