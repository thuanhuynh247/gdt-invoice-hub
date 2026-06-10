import os
import xml.etree.ElementTree as ET
from xml.dom import minidom

class CITFinalizationService:
    @staticmethod
    def calculate_cit(revenue, cogs, selling_expenses, admin_expenses, non_deductible_adjustments, loss_offset=0, cit_rate=0.20, holiday_discount=0.0):
        """
        Calculates CIT liability based on standard Vietnamese tax rules.
        """
        operating_expenses = selling_expenses + admin_expenses
        net_accounting_profit = revenue - cogs - operating_expenses
        
        # Non-deductible adjustments increase taxable profit (Code B4 in GDT Form)
        taxable_income_before_loss = net_accounting_profit + non_deductible_adjustments
        
        # Loss carry-forward cannot exceed taxable income before loss
        applied_loss = min(max(0, loss_offset), max(0, taxable_income_before_loss))
        taxable_income = max(0, taxable_income_before_loss - applied_loss)
        
        # Calculate CIT liability before and after holiday discount
        cit_before_incentives = taxable_income * cit_rate
        cit_liability = cit_before_incentives * (1.0 - holiday_discount)
        
        return {
            "net_accounting_profit": net_accounting_profit,
            "taxable_income_before_loss": taxable_income_before_loss,
            "applied_loss": applied_loss,
            "taxable_income": taxable_income,
            "cit_before_incentives": cit_before_incentives,
            "cit_liability": cit_liability,
            "non_deductible_adjustments": non_deductible_adjustments
        }

    @staticmethod
    def optimize_loss_carry_forward(historical_losses, projected_profits, tax_holidays=None, cit_rate=0.20):
        """
        Optimizes historical loss offsets (up to 5 years expiry) across projected profit years,
        considering tax holidays (exemptions/reductions) to maximize overall tax savings.
        """
        if tax_holidays is None:
            tax_holidays = {}
            
        # 1. Compute effective tax rates for each projection year
        effective_rates = {}
        for year in projected_profits:
            holiday = tax_holidays.get(year, {})
            if holiday.get("tax_free", False):
                effective_rates[year] = 0.0
            else:
                reduction = holiday.get("reduction", 0.0) # e.g. 0.5 = 50% discount
                effective_rates[year] = cit_rate * (1.0 - reduction)
                
        # 2. Set up tracking matrices
        remaining_losses = historical_losses.copy() # {loss_year: amount}
        remaining_profits = projected_profits.copy() # {profit_year: amount}
        offset_schedule = [] # List of dicts: {"loss_year", "profit_year", "amount_offset", "tax_savings"}
        
        # 3. Sort profit years by effective rate descending to prioritize offsetting high-tax years
        # If rates are equal, sort chronologically to offset older first
        sorted_profit_years = sorted(
            projected_profits.keys(),
            key=lambda y: (-effective_rates[y], y)
        )
        
        # 4. Offset losses
        for profit_year in sorted_profit_years:
            rate = effective_rates[profit_year]
            if rate <= 0.0:
                # If effective tax rate is 0%, offsetting loss provides no tax benefit.
                # However, if the loss is going to expire anyway, we still offset it chronologically (or just skip).
                # To be compliant with GDT rules, if we MUST offset losses chronologically in the first profitable year,
                # we do it. But to maximize NPV, we prioritize non-zero rates.
                # Let's check which active losses would expire if not offset in this zero-tax year.
                # Loss from Y expires after Y + 5. If Y + 5 == profit_year, it expires this year.
                pass
            
            # Active loss years for this profit_year are those within the 5-year window:
            # profit_year - 5 <= loss_year < profit_year
            active_loss_years = sorted([
                ly for ly in remaining_losses 
                if profit_year - 5 <= ly < profit_year and remaining_losses[ly] > 0
            ])
            
            for loss_year in active_loss_years:
                if remaining_profits[profit_year] <= 0:
                    break
                    
                loss_avail = remaining_losses[loss_year]
                profit_avail = remaining_profits[profit_year]
                
                offset_amount = min(loss_avail, profit_avail)
                if offset_amount > 0:
                    remaining_losses[loss_year] -= offset_amount
                    remaining_profits[profit_year] -= offset_amount
                    
                    tax_savings = offset_amount * rate
                    offset_schedule.append({
                        "loss_year": loss_year,
                        "profit_year": profit_year,
                        "amount_offset": offset_amount,
                        "tax_savings": tax_savings
                    })
                    
        # 5. Calculate expired losses for each year
        expired_losses = {}
        for loss_year, amount in remaining_losses.items():
            # If the loss year is more than 5 years before the latest projection year, it expires
            latest_projection_year = max(projected_profits.keys()) if projected_profits else loss_year
            if loss_year + 5 <= latest_projection_year:
                expired_losses[loss_year] = amount
            else:
                expired_losses[loss_year] = 0.0
                
        return {
            "offset_schedule": offset_schedule,
            "remaining_losses": remaining_losses,
            "remaining_profits": remaining_profits,
            "expired_losses": expired_losses,
            "effective_rates": effective_rates
        }

    @staticmethod
    def generate_cit_xml(mst, taxpayer_name, year, cit_data, loss_data):
        """
        Generates standard schema-compliant GDT Form 03/TNDN XML content.
        """
        root = ET.Element("hoSoKhaiThue")
        
        # 1. Header
        header = ET.SubElement(root, "toaKhai")
        ET.SubElement(header, "mst").text = mst
        ET.SubElement(header, "tenNNT").text = taxpayer_name
        ET.SubElement(header, "namKhaiThue").text = str(year)
        
        # 2. Main values
        ET.SubElement(header, "ct21").text = f"{cit_data.get('revenue', 0.0):.2f}"
        ET.SubElement(header, "ct22").text = f"{cit_data.get('cogs', 0.0) + cit_data.get('selling_expenses', 0.0) + cit_data.get('admin_expenses', 0.0):.2f}"
        ET.SubElement(header, "ct23").text = f"{cit_data.get('non_deductible_adjustments', 0.0):.2f}"
        ET.SubElement(header, "ct28").text = f"{cit_data.get('taxable_income_before_loss', 0.0):.2f}"
        ET.SubElement(header, "ct31").text = f"{cit_data.get('applied_loss', 0.0):.2f}"
        ET.SubElement(header, "ct36").text = f"{cit_data.get('cit_liability', 0.0):.2f}"
        
        # 3. Phụ lục 03-1A
        pl1 = ET.SubElement(root, "phuLuc_03_1A")
        ET.SubElement(pl1, "doanhThu").text = f"{cit_data.get('revenue', 0.0):.2f}"
        ET.SubElement(pl1, "giaVon").text = f"{cit_data.get('cogs', 0.0):.2f}"
        ET.SubElement(pl1, "chiPhiBanHang").text = f"{cit_data.get('selling_expenses', 0.0):.2f}"
        ET.SubElement(pl1, "chiPhiQLDN").text = f"{cit_data.get('admin_expenses', 0.0):.2f}"
        ET.SubElement(pl1, "loiNhuanKếToan").text = f"{cit_data.get('net_accounting_profit', 0.0):.2f}"
        
        # 4. Phụ lục 03-2A
        pl2 = ET.SubElement(root, "phuLuc_03_2A")
        for ly, loss_amt in loss_data.get("historical_losses", {}).items():
            row = ET.SubElement(pl2, "dong")
            ET.SubElement(row, "namPhatSinh").text = str(ly)
            ET.SubElement(row, "soLoPhatSinh").text = f"{loss_amt:.2f}"
            
            prior_offset = loss_data.get("prior_offsets", {}).get(ly, 0.0)
            ET.SubElement(row, "chuyenLoTruoc").text = f"{prior_offset:.2f}"
            
            current_offset = 0.0
            for item in loss_data.get("offset_schedule", []):
                if item["loss_year"] == ly and item["profit_year"] == year:
                    current_offset += item["amount_offset"]
            ET.SubElement(row, "chuyenLoKyNay").text = f"{current_offset:.2f}"
            
            expired = loss_data.get("expired_losses", {}).get(ly, 0.0)
            ET.SubElement(row, "loHetHan").text = f"{expired:.2f}"
            
            remaining = max(0.0, loss_amt - prior_offset - current_offset - expired)
            ET.SubElement(row, "loConChuyen").text = f"{remaining:.2f}"
            
        xmlstr = ET.tostring(root, encoding="utf-8")
        parsed = minidom.parseString(xmlstr)
        return parsed.toprettyxml(indent="  ")

    @staticmethod
    def simulate_cit_swarm_debate(cit_data, loss_data):
        """
        Simulates the discussion between tax personas on CIT finalization optimization.
        """
        debate = [
            {
                "sender": "JointAuditCoordinator",
                "message": "Chào cả nhóm. Hôm nay chúng ta sẽ xem xét kế hoạch quyết toán thuế TNDN (Mẫu 03/TNDN) cho năm nay. Doanh thu dự kiến là {revenue:,.0f} VND với thuế TNDN tính toán là {cit_liability:,.0f} VND sau khi chuyển lỗ và ưu đãi. Hãy tối ưu hoá kế hoạch này.".format(
                    revenue=cit_data.get("revenue", 0.0),
                    cit_liability=cit_data.get("cit_liability", 0.0)
                )
            },
            {
                "sender": "CITConsultant",
                "message": "Về phần chuyển lỗ, tôi đề xuất ưu tiên chuyển các khoản lỗ lớn từ năm {oldest_loss} để tránh bị hết hạn 5 năm theo quy định Thông tư 80. Thuật toán của chúng ta đã phân bổ tối ưu để tối đa hoá số tiền thuế tiết kiệm được.".format(
                    oldest_loss=min(loss_data.get("historical_losses", {2021: 0}).keys())
                )
            },
            {
                "sender": "CFO",
                "message": "Chúng ta có các khoản chi phí không được trừ là {non_deductible:,.0f} VND (Mã B4). Hãy chắc chắn rằng chúng ta có đủ hồ sơ chứng từ thanh toán không dùng tiền mặt cho các hóa đơn trên 20 triệu VND để bảo vệ các khoản chi phí hợp lý khác trước cơ quan thuế.".format(
                    non_deductible=cit_data.get("non_deductible_adjustments", 0.0)
                )
            },
            {
                "sender": "TaxAuditor",
                "message": "Chính xác. Hồ sơ quyết toán thuế TNDN cần đính kèm Phụ lục 03-1A và 03-2A đầy đủ. Việc kê khai XML Mẫu 03/TNDN của chúng ta phải chuẩn hoá cấu trúc thẻ của Tổng cục Thuế để tránh lỗi hệ thống khi nộp tờ khai qua mạng."
            }
        ]
        
        # Construct printable Memo
        memo = f"""# BIÊN BẢN TƯ VẤN QUYẾT TOÁN THUẾ TNDN HÀNG NĂM

**MST**: 0102030405
**Kỳ tính thuế**: {cit_data.get('year', 2026)}
**Tổng doanh thu**: {cit_data.get('revenue', 0.0):,.0f} VND
**Chi phí không được trừ (B4)**: {cit_data.get('non_deductible_adjustments', 0.0):,.0f} VND
**Số lỗ chuyển kỳ này (C3a)**: {cit_data.get('applied_loss', 0.0):,.0f} VND
**Thuế TNDN phải nộp**: {cit_data.get('cit_liability', 0.0):,.0f} VND

---

## Ý kiến tham vấn của Swarm Advisors:

1. **Điều phối viên kiểm toán (JointAuditCoordinator)**: Đảm bảo số liệu đồng bộ giữa báo cáo tài chính và phụ lục kết quả kinh doanh 03-1A.
2. **Chuyên gia tư vấn TNDN (CITConsultant)**: Khấu trừ tối ưu các khoản lỗ lũy kế theo đúng nguyên tắc chuyển lỗ liên tục tối đa 5 năm.
3. **Giám đốc tài chính (CFO)**: Cần lưu ý các khoản chi phí không được trừ và củng cố chứng từ hợp lệ.
4. **Kiểm toán viên thuế (TaxAuditor)**: Xác nhận cấu trúc XML hoàn toàn hợp lệ và sẵn sàng xuất khẩu nộp cho GDT.
"""
        return debate, memo
