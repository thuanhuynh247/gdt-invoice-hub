"""Version 30.0.0 Advanced Transfer Pricing (Decree 132/2020/ND-CP) & Arm's Length Compliance Suite.

Includes:
- Sector benchmark interquartile ranges (IQR).
- Profit markup analysis and compliance scoring against 35th-75th percentiles.
- Tax adjustment, CIT penalty, and late interest calculation engine.
- AI Tax Audit Prep Advisor swarm simulation.
- Formatted Transfer Pricing Audit Preparation Dossier generation.
"""

from __future__ import annotations
import datetime

# Sector Benchmark Data conforming to Decree 132 guidelines and general GDT tax practices
# Values represent Cost Plus Markup percentages (%)
SECTOR_BENCHMARKS = {
    "manufacturing": {
        "name": "Sản xuất & Gia công Công nghiệp",
        "p35": 8.0,      # 35th percentile
        "median": 12.0,  # Median (50th percentile)
        "p75": 16.5,     # 75th percentile
        "description": "Biên lợi nhuận gộp trên giá thành sản xuất (Cost Plus markup) cho ngành sản xuất gia công."
    },
    "services": {
        "name": "Dịch vụ & Tư vấn Công nghệ",
        "p35": 10.0,
        "median": 14.5,
        "p75": 20.0,
        "description": "Biên phí dịch vụ so với giá vốn nhân công và vận hành trực tiếp."
    },
    "distribution": {
        "name": "Bán buôn & Phân phối Thương mại",
        "p35": 4.5,
        "median": 6.5,
        "p75": 9.0,
        "description": "Tỷ suất lợi nhuận gộp trên giá vốn hàng bán cho ngành phân phối thương mại."
    }
}

def calculate_transfer_pricing_risk(markup_pct: float, cost_of_goods: float, sector: str) -> dict:
    """Evaluate Related-Party transaction profit markup against sector benchmarks.
    
    Returns risk classification, adjusted tax, and penalty predictions.
    """
    bench = SECTOR_BENCHMARKS.get(sector.lower())
    if not bench:
        # Fallback to manufacturing if not specified
        bench = SECTOR_BENCHMARKS["manufacturing"]
        sector = "manufacturing"

    p35 = bench["p35"]
    median = bench["median"]
    p75 = bench["p75"]

    actual_revenue = cost_of_goods * (1 + markup_pct / 100.0)
    actual_profit = actual_revenue - cost_of_goods

    status = "Compliant"
    adjustment_needed = 0.0
    cit_underpaid = 0.0
    penalty = 0.0
    late_interest = 0.0
    risk_score = 0

    if markup_pct < p35:
        # Underpriced related-party sale risk
        status = "Under-priced Risk"
        # Adjustment is computed up to the median according to Decree 132 rules
        adjusted_revenue = cost_of_goods * (1 + median / 100.0)
        adjustment_needed = adjusted_revenue - actual_revenue
        cit_underpaid = adjustment_needed * 0.20 # Standard CIT rate is 20%
        penalty = cit_underpaid * 0.20           # Underpayment penalty is 20%
        late_interest = cit_underpaid * 0.0003 * 365 # 0.03% per day for 1 year (365 days)
        
        # Calculate risk score proportionally
        diff = p35 - markup_pct
        risk_score = min(100, int(40 + (diff / p35) * 60))
    elif markup_pct > p75:
        # Overpricing / cost inflation risk
        status = "High-priced Risk"
        risk_score = 30 # Informational warning for tax audit scrutiny
    else:
        status = "Compliant"
        risk_score = 0

    total_financial_impact = cit_underpaid + penalty + late_interest

    return {
        "sector": sector,
        "sector_name": bench["name"],
        "markup_pct": markup_pct,
        "cost_of_goods": cost_of_goods,
        "actual_revenue": actual_revenue,
        "actual_profit": actual_profit,
        "p35": p35,
        "median": median,
        "p75": p75,
        "status": status,
        "risk_score": risk_score,
        "adjustment_needed": adjustment_needed,
        "cit_underpaid": cit_underpaid,
        "penalty": penalty,
        "late_interest": late_interest,
        "total_financial_impact": total_financial_impact
    }

def generate_tp_audit_dossier(taxpayer_name: str, taxpayer_mst: str, sector: str, markup_pct: float, cost_of_goods: float, risk_details: dict) -> str:
    """Generate a printable structured Transfer Pricing Audit Preparation Dossier."""
    today = datetime.datetime.now().strftime("%d/%m/%Y")
    
    dossier = f"""HỒ SƠ CHUẨN BỊ THANH TRA GIÁ GIAO DỊCH LIÊN KẾT (TRANSFER PRICING AUDIT DOSSIER)
(Theo quy định tại Nghị định 132/2020/NĐ-CP & Luật Quản lý thuế số 38)
---
Ngày lập hồ sơ: {today}
Tên người nộp thuế: {taxpayer_name}
Mã số thuế: {taxpayer_mst}
Ngành nghề phân tích: {risk_details["sector_name"]}

I. KẾT QUẢ PHÂN TÍCH TỶ SUẤT LỢI NHUẬN (ARM'S LENGTH RANGE ANALYSIS)
- Tỷ suất Cost Plus hiện tại của doanh nghiệp: {markup_pct:.2f}%
- Khoảng giao dịch độc lập chuẩn (Arm's Length Range):
  * Bách phân vị thứ 35 (Min): {risk_details["p35"]:.2f}%
  * Trung vị (Median): {risk_details["median"]:.2f}%
  * Bách phân vị thứ 75 (Max): {risk_details["p75"]:.2f}%
- Trạng thái tuân thủ: {risk_details["status"].upper()}
- Chỉ số rủi ro thanh tra: {risk_details["risk_score"]}/100

{"II. BIỆN PHÁP ĐIỀU CHỈNH THUẾ DỰ KIẾN (POTENTIAL TAX ADJUSTMENTS)" if risk_details["adjustment_needed"] > 0 else "II. ĐÁNH GIÁ CHUNG VỀ SỰ TUÂN THỦ"}
"""

    if risk_details["adjustment_needed"] > 0:
        dossier += f"""Do biên lợi nhuận của doanh nghiệp ({markup_pct:.2f}%) thấp hơn mức tối thiểu độc lập ({risk_details["p35"]:.2f}%), cơ quan thuế có quyền ấn định lợi nhuận về mức Trung vị ({risk_details["median"]:.2f}%):
- Doanh thu điều chỉnh tăng thêm: {risk_details["adjustment_needed"]:,.0f} VNĐ
- Thuế TNDN truy thu ước tính (20%): {risk_details["cit_underpaid"]:,.0f} VNĐ
- Phạt hành vi khai thiếu thuế (20%): {risk_details["penalty"]:,.0f} VNĐ
- Tiền chậm nộp dự kiến (365 ngày - 0.03%/ngày): {risk_details["late_interest"]:,.0f} VNĐ
- TỔNG ẢNH HƯỞNG TÀI CHÍNH DỰ KIẾN: {risk_details["total_financial_impact"]:,.0f} VNĐ
"""
    else:
        dossier += f"""Biên lợi nhuận của doanh nghiệp nằm trong khoảng độc lập an toàn. Doanh nghiệp tuân thủ tốt nguyên tắc giao dịch độc lập. Tuy nhiên, vẫn cần chuẩn bị đầy đủ hồ sơ xác định giá giao dịch liên kết để nộp kèm tờ khai quyết toán thuế TNDN (Mẫu số 01/132).
"""

    dossier += """
III. DANH MỤC HỒ SƠ PHÁP LÝ CẦN CHUẨN BỊ KHI ĐÓN TIẾP ĐOÀN THANH TRA:
1. Hợp đồng kinh tế ký kết giữa các bên liên kết (Kèm phụ lục giá thành chi tiết).
2. Tờ khai thông tin quan hệ liên kết và giao dịch liên kết (Mẫu 01, Mẫu 02, Mẫu 03 ban hành kèm theo Nghị định 132/2020/NĐ-CP).
3. Báo cáo phân tích so sánh tỷ suất lợi nhuận (Benchmarking study) với dữ liệu của ít nhất 3 doanh nghiệp độc lập tương đồng hoạt động tại thị trường Việt Nam.
4. Hồ sơ quốc gia (Local File) và Hồ sơ thông tin tập đoàn toàn cầu (Master File) theo quy định hiện hành.

Khuyến nghị khắc phục:
- Điều chỉnh chính sách giá giao dịch liên kết cho kỳ tiếp theo để nâng biên lợi nhuận lên trên mức bách phân vị thứ 35.
- Hoàn thiện bộ chứng từ chứng minh tính hợp lý kinh tế của giao dịch (Commercial substance).
"""
    return dossier

class SwarmV30Advisor:
    """Version 30.0.0 Multi-Agent Swarm simulating related-party pricing audit prep."""
    def __init__(self, taxpayer_mst: str):
        self.taxpayer_mst = taxpayer_mst

    def simulate_tp_defense_chat(self, sector: str, markup_pct: float, cost_of_goods: float) -> list[dict]:
        """Simulate step-by-step chat messages representing agent swarm discussion on transfer pricing."""
        now = datetime.datetime.now()
        steps = []
        risk_details = calculate_transfer_pricing_risk(markup_pct, cost_of_goods, sector)
        
        # Step 1: Coordinator alert
        steps.append({
            "agent": "JointAuditCoordinator",
            "role": "Điều phối viên chính",
            "avatar_class": "bg-primary text-white",
            "timestamp": (now - datetime.timedelta(seconds=8)).strftime("%H:%M:%S"),
            "message": f"YÊU CẦU ĐÁNH GIÁ: Đối chiếu giao dịch liên kết cho phân khúc '{risk_details['sector_name']}' với mức markup đề xuất {markup_pct}%. Bắt đầu rà soát tuân thủ Nghị định 132."
        })
        
        # Step 2: Transfer Pricing Specialist Analysis
        steps.append({
            "agent": "TransferPricingSpecialist",
            "role": "Tác tử Xác định giá Giao dịch liên kết",
            "avatar_class": "bg-purple text-white",
            "timestamp": (now - datetime.timedelta(seconds=6)).strftime("%H:%M:%S"),
            "message": f"Ngành '{sector.upper()}' có khoảng độc lập từ {risk_details['p35']}% đến {risk_details['p75']}%. Tỷ suất của ta đạt {markup_pct}%. Trạng thái: {risk_details['status']}. " + 
                       (f"Cảnh báo: Thấp hơn bách phân vị 35 ({risk_details['p35']}%). Có nguy cơ cao bị ấn định giá lên mức trung vị {risk_details['median']}%." if risk_details["adjustment_needed"] > 0 else "Biên lợi nhuận an toàn, nằm trong khoảng độc lập độc lập.")
        })
        
        # Step 3: CIT Auditor
        if risk_details["adjustment_needed"] > 0:
            steps.append({
                "agent": "CITSpecialist",
                "role": "Tác tử Kiểm toán Thuế TNDN",
                "avatar_class": "bg-danger text-white",
                "timestamp": (now - datetime.timedelta(seconds=4)).strftime("%H:%M:%S"),
                "message": f"Tính toán truy thu: Giá trị giao dịch cần tăng thêm {risk_details['adjustment_needed']:,.0f}đ. Thuế TNDN truy thu ước tính {risk_details['cit_underpaid']:,.0f}đ. Phạt hành chính và lãi chậm nộp sẽ kéo tổng ảnh hưởng tài chính lên {risk_details['total_financial_impact']:,.0f}đ. Cực kỳ rủi ro!"
            })
        else:
            steps.append({
                "agent": "CITSpecialist",
                "role": "Tác tử Kiểm toán Thuế TNDN",
                "avatar_class": "bg-success text-white",
                "timestamp": (now - datetime.timedelta(seconds=4)).strftime("%H:%M:%S"),
                "message": "Không có truy thu thuế TNDN dự kiến từ chênh lệch giá. Tuy nhiên, cần lưu ý chi phí lãi vay khống chế 30% EBITDA theo Khoản 3 Điều 9 Nghị định 132 vẫn phải được kê khai và loại trừ nếu vượt ngưỡng."
            })
            
        # Step 4: VAT Specialist
        steps.append({
            "agent": "VATSpecialist",
            "role": "Tác tử Kiểm tra Hóa đơn & GTGT",
            "avatar_class": "bg-info text-dark",
            "timestamp": (now - datetime.timedelta(seconds=2)).strftime("%H:%M:%S"),
            "message": "Kiểm tra chứng từ: Tất cả hóa đơn cho giao dịch liên kết này phải ghi rõ mã số thuế bên liên kết, có chứng từ thanh toán không dùng tiền mặt hợp chuẩn theo Nghị định 123 và Thông tư 80."
        })
        
        # Step 5: Coordinator synthesis
        steps.append({
            "agent": "JointAuditCoordinator",
            "role": "Điều phối viên chính",
            "avatar_class": "bg-primary text-white",
            "timestamp": now.strftime("%H:%M:%S"),
            "message": "Đã tổng hợp hồ sơ phân tích giá và phương án chuẩn bị thanh tra. Tôi khuyến nghị tải ngay Hồ sơ biện hộ ở phía dưới và lưu trữ đầy đủ Báo cáo Benchmarking so sánh."
        })
        
        return steps
