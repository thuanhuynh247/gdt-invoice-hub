"""Version 29.0.0 Advanced Ghost-Company Compliance & Tax Regulations Knowledge Graph Suite.

Includes:
- Ghost-company blacklist search & transaction volume disproportion analysis.
- Ghost Company Probability Index (0-100) and statutory risk flagging.
- AI-driven Tax Audit Defense Letter & Rectification Plan generator.
- Vietnamese Tax Regulations Knowledge Graph database (ND123, TT80, ND125, ND132, TT219).
- Swarm chat simulator for ghost-company defense strategy.
"""

from __future__ import annotations
import re
import datetime

# Mocked GDT High-Risk / Inactive Business Directory (Based on Dispatch 114/TCT-TTKT & real tax warnings)
GHOST_COMPANY_BLACKLIST = {
    "0316482931": {
        "name": "Công ty TNHH Thương mại Dịch vụ Khánh An",
        "reason": "Doanh nghiệp ngừng hoạt động tại địa chỉ đăng ký nhưng không khai báo với cơ quan thuế (Bỏ địa chỉ kinh doanh).",
        "establishment_date": "2024-03-12",
        "registered_capital": 500000000.0, # 500 million VND
        "tax_status": "Ngừng hoạt động (Bỏ địa điểm kinh doanh)",
    },
    "0108924810": {
        "name": "Công ty Cổ phần Vật liệu Xây dựng Trường Thịnh",
        "reason": "Quy mô vốn đăng ký cực kỳ thấp so với doanh thu hóa đơn phát sinh đột biến (Rủi ro mua bán hóa đơn khống).",
        "establishment_date": "2025-01-15",
        "registered_capital": 100000000.0, # 100 million VND
        "tax_status": "Đang hoạt động (Diện giám sát đặc biệt)",
    },
    "0201948291": {
        "name": "Công ty TNHH Đầu tư và Xuất nhập khẩu Hoàng Hải",
        "reason": "Mới thành lập dưới 6 tháng nhưng phát sinh doanh thu hóa đơn xuất ra vượt quá 50 tỷ VNĐ trong 1 quý.",
        "establishment_date": "2026-02-10",
        "registered_capital": 2000000000.0, # 2 billion VND
        "tax_status": "Tạm ngừng kinh doanh có thời hạn",
    }
}

def check_ghost_company(seller_mst: str, seller_name: str, invoice_value: float) -> dict:
    """Assess risk of the seller being a ghost company (doanh nghiệp ma) or high-risk entity."""
    clean_mst = re.sub(r"\D", "", seller_mst)
    flags = []
    warnings = []
    
    # 1. Check blacklist match
    blacklist_match = GHOST_COMPANY_BLACKLIST.get(clean_mst)
    
    risk_score = 0
    status = "Safe"
    details = {
        "registered_name": seller_name,
        "tax_status": "Đang hoạt động",
        "registered_capital": 10000000000.0, # Default healthy 10B VND
        "establishment_date": "2020-01-01"
    }

    if blacklist_match:
        details.update(blacklist_match)
        risk_score += 60
        flags.append(f"Khớp Mã số thuế trong danh sách doanh nghiệp rủi ro cao của Tổng cục Thuế: {blacklist_match['tax_status']}.")
        warnings.append(blacklist_match["reason"])
    
    # 2. Check establishment status (newly established is higher risk)
    est_date_str = details["establishment_date"]
    try:
        est_date = datetime.datetime.strptime(est_date_str, "%Y-%m-%d")
        age_days = (datetime.datetime.now() - est_date).days
        if age_days < 180: # Under 6 months
            risk_score += 15
            flags.append("Doanh nghiệp mới thành lập dưới 6 tháng.")
    except Exception:
        pass

    # 3. Disproportion check (invoice value vs registered capital)
    reg_capital = details["registered_capital"]
    if invoice_value >= reg_capital * 0.5:
        risk_score += 20
        flags.append("Giá trị hóa đơn hiện tại vượt quá 50% tổng vốn điều lệ đăng ký của bên bán.")
        warnings.append("Giao dịch có dấu hiệu bất cân xứng tài chính nghiêm trọng so với năng lực vốn điều lệ.")

    # 4. Final classification
    if risk_score >= 75:
        status = "Critical"
    elif risk_score >= 35:
        status = "Warning"
        
    return {
        "mst": clean_mst,
        "name": details["registered_name"],
        "risk_score": min(100, risk_score),
        "status": status,
        "flags": flags,
        "warnings": warnings,
        "details": details
    }

def generate_audit_mitigation_letter(seller_mst: str, seller_name: str, invoice_value: float, payment_method: str) -> str:
    """Generate a high-quality audit explanation/mitigation letter for tax authorities in Vietnamese."""
    today = datetime.datetime.now().strftime("%d/%m/%Y")
    clean_mst = re.sub(r"\D", "", seller_mst)
    
    letter = f"""CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Độc lập - Tự do - Hạnh phúc
---
Hà Nội, ngày {today}

BẢN GIẢI TRÌNH GIAO DỊCH VÀ BIỆN PHÁP KHẮC PHỤC RỦI RO THUẾ
(V/v: Đối chiếu giao dịch với nhà cung cấp thuộc diện giám sát thuế đặc biệt)

Kính gửi: Chi cục Thuế / Cục Thuế quản lý trực tiếp doanh nghiệp

Tên doanh nghiệp giải trình: Công ty TNHH Giải pháp Phần mềm Ánh Sáng
Mã số thuế: 0109998887
Địa chỉ: Khu đô thị mới Cầu Giấy, Hà Nội

Bằng văn bản này, chúng tôi xin thực hiện giải trình chi tiết về nghiệp vụ mua hàng hóa/dịch vụ phát sinh với nhà cung cấp sau:
- Tên đơn vị bán: {seller_name}
- Mã số thuế bên bán: {clean_mst}
- Trị giá hóa đơn giao dịch: {invoice_value:,.0f} VNĐ
- Hình thức thanh toán thực tế: {payment_method}

1. Tính xác thực và thực tế của giao dịch (Chống mua bán hóa đơn khống):
Doanh nghiệp chúng tôi khẳng định giao dịch mua bán trên là HOÀN TOÀN CÓ THẬT và được thực hiện đúng quy định pháp luật. Chúng tôi lưu trữ đầy đủ hồ sơ chứng minh nghiệp vụ thực tế bao gồm:
- Hợp đồng kinh tế số: HD/MB-2026/02 ký ngày lập giao dịch.
- Phiếu xuất kho / Biên bản bàn giao hàng hóa có chữ ký xác nhận của đại diện giao nhận hai bên.
- Nhật ký vận chuyển hàng hóa & biên bản nghiệm thu nghiệm thu hoàn thành công việc.

2. Điều kiện khấu trừ thuế GTGT và Chi phí được trừ (Circular 219 & Circular 80):
- Thanh toán không dùng tiền mặt: Giao dịch được thực hiện thanh toán qua ngân hàng (Chuyển khoản - {payment_method}) từ tài khoản của doanh nghiệp sang tài khoản đăng ký chính thức của bên bán. Hóa đơn gốc được ký số hợp chuẩn.
- Tra cứu thời điểm phát sinh: Tại thời điểm phát sinh giao dịch, Mã số thuế của nhà cung cấp vẫn hiển thị trạng thái "Đang hoạt động" trên Cổng thông tin Tổng cục Thuế. Doanh nghiệp không thể biết trước các vi phạm phát sinh sau đó của bên bán.

3. Biện pháp khắc phục & Cam kết bảo vệ quyền lợi của Nhà nước:
- Chúng tôi cam kết sẽ phối hợp chặt chẽ với cơ quan quản lý thuế để cung cấp chứng từ thanh toán ngân hàng đối ứng, hóa đơn gốc chuẩn Nghị định 123.
- Nếu cơ quan điều tra kết luận bên bán xuất hóa đơn bất hợp pháp và không thể khắc phục, chúng tôi sẽ thực hiện khai điều chỉnh giảm thuế GTGT đầu vào và nộp bổ sung thuế TNDN tương ứng theo đúng quy định tại Nghị định 125/2020/NĐ-CP.

Kính đề nghị cơ quan Thuế xem xét, tạo điều kiện cho doanh nghiệp giải trình thực tế giao dịch để tiếp tục được khấu trừ thuế hợp pháp.

Đại diện hợp pháp của doanh nghiệp
(Ký, ghi rõ họ tên và đóng dấu)
"""
    return letter

def get_tax_knowledge_graph() -> dict:
    """Return Vietnamese Tax Regulations Knowledge Graph representation for visual UI rendering."""
    return {
        "nodes": [
            {"id": "ND123", "label": "Nghị định 123/2020/NĐ-CP", "group": "invoice", "val": 25, "desc": "Quy định về hóa đơn, chứng từ điện tử và phiếu xuất kho kiêm vận chuyển nội bộ."},
            {"id": "TT80", "label": "Thông tư 80/2021/TT-BTC", "group": "admin", "val": 20, "desc": "Hướng dẫn Luật Quản lý thuế, hạn mức thanh toán không dùng tiền mặt và hồ sơ hoàn thuế."},
            {"id": "ND125", "label": "Nghị định 125/2020/NĐ-CP", "group": "penalty", "val": 15, "desc": "Xử phạt vi phạm hành chính về thuế, hóa đơn, chậm nộp, trốn thuế."},
            {"id": "ND132", "label": "Nghị định 132/2020/NĐ-CP", "group": "tp", "val": 20, "desc": "Quản lý thuế đối với doanh nghiệp có giao dịch liên kết, khống chế lãi vay EBITDA 30%."},
            {"id": "TT219", "label": "Thông tư 219/2013/TT-BTC", "group": "vat", "val": 22, "desc": "Điều kiện khấu trừ thuế GTGT đầu vào và thuế suất GTGT cho các ngành nghề."},
            {"id": "LQLT38", "label": "Luật Quản lý thuế 38/2019/QH14", "group": "law", "val": 30, "desc": "Luật khung quy định nghĩa vụ, quyền lợi và quy trình kiểm tra quyết toán thuế Việt Nam."}
        ],
        "edges": [
            {"from": "LQLT38", "to": "ND123", "label": "Ủy quyền ban hành", "desc": "Luật 38 ủy quyền Chính phủ quy định chi tiết về hóa đơn điện tử."},
            {"from": "LQLT38", "to": "TT80", "label": "Ủy quyền hướng dẫn", "desc": "Luật 38 giao Bộ Tài chính hướng dẫn quy trình khai báo quản lý thuế."},
            {"from": "LQLT38", "to": "ND125", "label": "Xử phạt hành chính", "desc": "Chế tài xử phạt hành chính các hành vi vi phạm nghĩa vụ đăng ký kê khai quy định trong Luật."},
            {"from": "ND123", "to": "TT219", "label": "Điều kiện khấu trừ", "desc": "Hóa đơn điện tử hợp chuẩn theo ND123 là điều kiện bắt buộc để khấu trừ GTGT theo TT219."},
            {"from": "TT80", "to": "TT219", "label": "Chứng từ thanh toán", "desc": "TT80 hướng dẫn thanh toán qua ngân hàng để đáp ứng điều kiện khấu trừ thuế của TT219."},
            {"from": "ND132", "to": "ND125", "label": "Chế tài liên kết", "desc": "Không nộp tờ khai liên kết mẫu 01 sẽ bị xử phạt vi phạm hóa đơn chứng từ theo ND125."}
        ]
    }

class SwarmV29Advisor:
    """Version 29 Agent Swarm simulating coordination to defend high-risk invoices."""
    def __init__(self, taxpayer_mst: str):
        self.taxpayer_mst = taxpayer_mst

    def simulate_defense_chat(self, seller_mst: str, seller_name: str, invoice_value: float) -> list[dict]:
        """Simulate step-by-step chat messages representing agent swarm discussion on ghost-company risk."""
        now = datetime.datetime.now()
        steps = []
        
        # Step 1: Coordinator alert
        steps.append({
            "agent": "JointAuditCoordinator",
            "role": "Điều phối viên chính",
            "avatar_class": "bg-primary text-white",
            "timestamp": (now - datetime.timedelta(seconds=8)).strftime("%H:%M:%S"),
            "message": f"CẢNH BÁO KHẨN CẤP: Đối tác '{seller_name}' (MST: {seller_mst}) được phát hiện có rủi ro cao về thuế. Tôi yêu cầu các tác tử phân tích chuyên sâu ngay lập tức."
        })
        
        # Step 2: Risk Auditor Analysis
        risk_details = check_ghost_company(seller_mst, seller_name, invoice_value)
        steps.append({
            "agent": "RiskAuditorAgent",
            "role": "Tác tử Rà soát Danh sách đen",
            "avatar_class": "bg-danger text-white",
            "timestamp": (now - datetime.timedelta(seconds=6)).strftime("%H:%M:%S"),
            "message": f"Phân tích hoàn tất. Chỉ số rủi ro của đơn vị này đạt {risk_details['risk_score']}/100 ({risk_details['status']}). Lý do chính: {', '.join(risk_details['flags'])}. Giao dịch trị giá {invoice_value:,.0f} VNĐ này cần được phong tỏa hồ sơ để bổ sung bằng chứng thực tế."
        })
        
        # Step 3: Legal Defense Advisor
        steps.append({
            "agent": "LegalDefenseAdvisor",
            "role": "Tác tử Biện hộ & Khắc phục",
            "avatar_class": "bg-success text-white",
            "timestamp": (now - datetime.timedelta(seconds=4)).strftime("%H:%M:%S"),
            "message": "Phương án tự vệ: Chúng ta cần lập ngay hồ sơ chứng minh giao dịch có thật (Physical Substance). Cần chuẩn bị: (1) Phiếu xuất kho PXK chính chủ bên bán, (2) Lệnh chuyển tiền ngân hàng Napas trùng ngày khớp số tiền, (3) Biên bản nghiệm thu công trình/dịch vụ."
        })
        
        # Step 4: Penalty Calculator
        tax_impact = invoice_value * 0.1 # 10% GTGT
        cit_impact = invoice_value * 0.2 # 20% TNDN
        total_risk = tax_impact + cit_impact
        steps.append({
            "agent": "PenaltyForecaster",
            "role": "Tác tử Dự báo Phạt thuế",
            "avatar_class": "bg-warning text-dark",
            "timestamp": (now - datetime.timedelta(seconds=2)).strftime("%H:%M:%S"),
            "message": f"Đánh giá tài chính: Nếu bị loại chi phí, doanh nghiệp đối mặt truy thu thuế GTGT {tax_impact:,.0f}đ và thuế TNDN {cit_impact:,.0f}đ. Tổng truy thu dự kiến {total_risk:,.0f}đ, chưa tính tiền phạt chậm nộp 0.03%/ngày theo Nghị định 125."
        })
        
        # Step 5: Coordinator synthesis
        steps.append({
            "agent": "JointAuditCoordinator",
            "role": "Điều phối viên chính",
            "avatar_class": "bg-primary text-white",
            "timestamp": now.strftime("%H:%M:%S"),
            "message": "Quyết định hành động: Tôi đã tổng hợp Bản giải trình gửi cơ quan quản lý thuế và Phụ lục đính kèm bằng chứng thực tế giao dịch. Bản thảo giải trình chi tiết đã được tạo thành công bên dưới."
        })
        
        return steps
