"""Intelligent Tax Penalty Predictor & Audit Explanation Builder (US-340, US-341).

Implements statutory tax penalty calculations under Decree 125/2020/NĐ-CP, 
daily late payment interest (0.03% per day), and automated corporate defense letter drafting.
"""

from __future__ import annotations

from datetime import datetime, date

def calculate_audit_penalties(
    underpaid_tax: float,
    due_date: str | date,
    payment_date: str | date,
    evasion_multiplier: float = 0.0,
    has_mitigating_factors: bool = False
) -> dict:
    """Calculate potential GDT tax penalties and late payment interest.
    
    Rules (Decree 125/2020/NĐ-CP & Luật Quản lý thuế 38/2019/QH14):
      - Under-declaration fine: 20% of underpaid tax.
      - Late payment interest: 0.03% per day, starting from due_date + 1.
      - Evasion penalty: ranges from 1.0x to 3.0x (default 0.0 meaning not evasion).
    """
    if isinstance(due_date, str):
        d_due = datetime.strptime(due_date, "%Y-%m-%d").date()
    else:
        d_due = due_date

    if isinstance(payment_date, str):
        d_pay = datetime.strptime(payment_date, "%Y-%m-%d").date()
    else:
        d_pay = payment_date

    # Calculate late days
    late_days = max(0, (d_pay - d_due).days)
    
    # 1. Under-declaration fine (20%)
    under_declaration_fine = float(round(underpaid_tax * 0.20)) if evasion_multiplier == 0.0 else 0.0
    
    # 2. Late interest (0.03% per day)
    late_interest = float(round(underpaid_tax * 0.0003 * late_days))
    
    # 3. Evasion fine (1x to 3x)
    evasion_fine = float(round(underpaid_tax * evasion_multiplier))
    
    # Adjust for mitigating factors
    if has_mitigating_factors:
        under_declaration_fine = max(0.0, float(round(under_declaration_fine * 0.8))) # 20% reduction
        evasion_fine = max(0.0, float(round(evasion_fine * 0.8)))
        
    total_penalties = under_declaration_fine + late_interest + evasion_fine
    total_liability = underpaid_tax + total_penalties
    
    return {
        "underpaid_tax": underpaid_tax,
        "late_days": late_days,
        "under_declaration_fine": under_declaration_fine,
        "late_interest": late_interest,
        "evasion_fine": evasion_fine,
        "total_penalties": total_penalties,
        "total_liability": total_liability,
        "decree_reference": "Nghị định 125/2020/NĐ-CP & Thông tư 80/2021/TT-BTC"
    }

def generate_audit_defense_letter(
    risk_type: str,
    taxpayer_name: str,
    taxpayer_mst: str,
    details: dict
) -> str:
    """Generate a formal Vietnamese explanation & defense letter responding to tax audit findings."""
    now_str = datetime.now().strftime("ngày %d tháng %m năm %Y")
    
    letter_header = f"""CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Độc lập - Tự do - Hạnh phúc
----------------

Số: ......./GT-CV
V/v: Giải trình số liệu kiểm toán thuế

                                Hà Nội, {now_str}

                KÍNH GỬI: CHI CỤC THUẾ / CỤC THUẾ ........................
"""

    letter_body = ""
    
    if risk_type.upper() == "RELATED_PARTY_EBITDA":
        ebitda_limit = details.get("ebitda_limit", "30%")
        actual_interest = details.get("actual_interest", 0)
        allowable_interest = details.get("allowable_interest", 0)
        variance = details.get("variance", 0)
        
        letter_body = f"""Căn cứ vào Nghị định 132/2020/NĐ-CP của Chính phủ về quản lý thuế đối với doanh nghiệp có giao dịch liên kết.
Doanh nghiệp chúng tôi: {taxpayer_name} (MST: {taxpayer_mst}) xin giải trình về việc chi phí lãi vay vượt mức khống chế 30% EBITDA như sau:

1. Trong năm quyết toán, tổng chi phí lãi vay phát sinh của doanh nghiệp là {actual_interest:,.0f} VND. Chi phí lãi vay được trừ theo khống chế 30% EBITDA là {allowable_interest:,.0f} VND. Phần chi phí lãi vay không được trừ tạm thời ghi nhận là {variance:,.0f} VND.
2. Nguyên nhân phát sinh chi phí lãi vay cao do doanh nghiệp đang trong giai đoạn đầu đầu tư xây dựng dự án trọng điểm, chưa có doanh thu tương xứng để tối ưu EBITDA.
3. Căn cứ khoản 3 Điều 15 Nghị định 132/2020/NĐ-CP, doanh nghiệp sẽ tiến hành chuyển phần chi phí lãi vay chưa được trừ này vào chi phí sản xuất kinh doanh của các năm tiếp theo (thời gian chuyển không quá 05 năm liên tục).

Do đó, doanh nghiệp đề xuất phương án bảo lưu và kết chuyển chi phí lãi vay theo đúng quy định pháp luật và cam kết điều chỉnh bổ sung tờ khai quyết toán thuế TNDN."""

    elif risk_type.upper() == "FCT_WITHHOLDING":
        contractor_name = details.get("contractor_name", "Google Asia Pacific Pte. Ltd.")
        revenue = details.get("revenue", 0)
        calculated_fct = details.get("calculated_fct", 0)
        
        letter_body = f"""Căn cứ vào Thông tư 103/2014/TT-BTC hướng dẫn thực hiện nghĩa vụ thuế áp dụng đối với tổ chức, cá nhân nước ngoài kinh doanh tại Việt Nam.
Doanh nghiệp chúng tôi: {taxpayer_name} (MST: {taxpayer_mst}) xin giải trình về nghĩa vụ Thuế nhà thầu nước ngoài (FCT) liên quan đến giao dịch với {contractor_name}:

1. Tổng giá trị thanh toán cho nhà thầu nước ngoài trong kỳ là {revenue:,.0f} VND.
2. Thuế nhà thầu khấu trừ ước tính là {calculated_fct:,.0f} VND (Bao gồm VAT nhà thầu và TNDN nhà thầu).
3. Giao dịch này thuộc loại hình cung cấp dịch vụ trực tuyến qua nền tảng số. Doanh nghiệp đã tiến hành kê khai theo phương pháp trực tiếp (tỷ lệ % trên doanh thu tính thuế).

Chúng tôi xin gửi kèm hồ sơ hợp đồng, chứng từ thanh toán và biên lai nộp thuế nhà thầu của các đợt phát sinh tương ứng để phục vụ công tác đối chiếu của cơ quan thuế."""

    elif risk_type.upper() == "CUSTOMS_VAT_VARIANCE":
        customs_declaration = details.get("customs_declaration", "N/A")
        variance_amount = details.get("variance_amount", 0)
        
        letter_body = f"""Căn cứ theo Luật Thuế giá trị gia tăng và các quy định về đối chiếu tờ khai hải quan VNACCS/VCIS.
Doanh nghiệp chúng tôi: {taxpayer_name} (MST: {taxpayer_mst}) giải trình về sự chênh lệch thuế GTGT hàng nhập khẩu liên quan đến Tờ khai Hải quan số {customs_declaration}:

1. Số thuế GTGT hàng nhập khẩu ghi nhận theo tờ khai hải quan và số liệu hải quan là {details.get('customs_vat', 0):,.0f} VND.
2. Số thuế GTGT được khấu trừ thực tế ghi nhận trên sổ sách doanh nghiệp là {details.get('invoice_vat', 0):,.0f} VND.
3. Chênh lệch phát sinh là {variance_amount:,.0f} VND. Chênh lệch này xuất phát từ tỷ giá tính thuế hải quan tại thời điểm mở tờ khai hải quan khác biệt so với tỷ giá quy đổi hóa đơn mua hàng tại ngày nhận hàng, hoặc do phân bổ chi phí vận chuyển quốc tế.

Doanh nghiệp khẳng định số thuế GTGT hàng nhập khẩu kê khai khấu trừ hoàn toàn khớp với biên lai nộp thuế GTGT khâu nhập khẩu và chứng từ nộp ngân sách nhà nước đi kèm."""

    elif risk_type.upper() == "CIRCULAR_20_RISK":
        invoice_id = details.get("invoice_id", "N/A")
        total_amount = details.get("total_amount", 0)
        
        letter_body = f"""Căn cứ theo Thông tư 20/2026/TT-BTC quy định về chứng từ thanh toán không dùng tiền mặt đối với các khoản mua hàng ủy quyền qua thẻ cá nhân.
Doanh nghiệp chúng tôi: {taxpayer_name} (MST: {taxpayer_mst}) xin giải trình về chứng từ thanh toán của hóa đơn số {invoice_id} trị giá {total_amount:,.0f} VND:

1. Giao dịch được thực hiện qua hình thức nhân viên công ty dùng thẻ cá nhân để thanh toán trực tiếp, sau đó công ty thực hiện hoàn ứng cho nhân viên.
2. Công ty đã chuẩn bị đầy đủ: Quy chế tài chính cho phép ủy quyền thanh toán, Giấy ủy quyền cho nhân viên thanh toán, Chứng từ chuyển khoản hoàn ứng từ tài khoản công ty sang tài khoản nhân viên, kèm sao kê ngân hàng xác nhận thanh toán của cá nhân cho nhà cung cấp.

Doanh nghiệp đảm bảo tính hợp lý hợp lệ của chi phí và đề nghị cơ quan thuế chấp thuận khấu trừ thuế GTGT đầu vào và chi phí được trừ khi tính thuế TNDN."""

    else:
        letter_body = f"""Doanh nghiệp chúng tôi: {taxpayer_name} (MST: {taxpayer_mst}) xin giải trình về các nội dung chênh lệch phát hiện trong kỳ thanh tra kiểm tra thuế.
Chúng tôi cam kết số liệu kế toán phản ánh đúng thực tế hoạt động sản xuất kinh doanh và luôn chấp hành đầy đủ các nghĩa vụ thuế đối với ngân sách nhà nước."""

    letter_footer = f"""
Chúng tôi kính mong Cơ quan Thuế xem xét và tạo điều kiện hỗ trợ doanh nghiệp.
Xin trân trọng cảm ơn./.

                                ĐẠI DIỆN THEO PHÁP LUẬT
                                (Ký, ghi rõ họ tên và đóng dấu)
"""

    return letter_header + "\n" + letter_body + "\n" + letter_footer


def calculate_fct_tax(
    contract_value: float,
    contract_type: str,  # "net" or "gross"
    industry_type: str   # "services", "goods_with_services", "construction_with_materials", "construction_no_materials", "transport_other", "royalties", "aircraft_vessel_lease", "loan_interest", "securities_transfer"
) -> dict:
    """Calculate Foreign Contractor Tax (FCT) in Vietnam under Circular 103/2014/TT-BTC.
    
    Returns details of FCT VAT, FCT CIT, grossed-up values, net values, and legal bases.
    """
    # Industry mappings: (VAT_rate, CIT_rate, description)
    industry_rates = {
        "services": (0.05, 0.05, "Dịch vụ, cho thuê máy móc thiết bị, bảo hiểm"),
        "goods_with_services": (0.03, 0.01, "Cung cấp hàng hóa kèm dịch vụ lắp đặt, bảo hành, bảo dưỡng"),
        "construction_with_materials": (0.03, 0.02, "Xây dựng, lắp đặt có bao thầu nguyên vật liệu"),
        "construction_no_materials": (0.05, 0.02, "Xây dựng, lắp đặt không bao thầu nguyên vật liệu"),
        "transport_other": (0.02, 0.02, "Kinh doanh vận tải, nhà hàng, khách sạn, hoạt động khác"),
        "royalties": (0.00, 0.10, "Bản quyền, chuyển giao công nghệ, quyền sở hữu trí tuệ"),
        "aircraft_vessel_lease": (0.00, 0.02, "Cho thuê tàu bay, động cơ tàu bay, tàu biển"),
        "loan_interest": (0.00, 0.05, "Lãi tiền vay cung cấp cho doanh nghiệp Việt Nam"),
        "securities_transfer": (0.00, 0.001, "Chuyển nhượng chứng khoán, chứng chỉ quỹ")
    }
    
    if industry_type not in industry_rates:
        raise ValueError(f"Loại hình kinh doanh không hợp lệ: {industry_type}")
        
    vat_rate, cit_rate, desc = industry_rates[industry_type]
    
    if contract_type == "net":
        # Grossing up from net paid to foreign contractor
        # CIT Taxable revenue = Net / (1 - CIT_Rate)
        cit_revenue = float(round(contract_value / (1.0 - cit_rate)))
        # Gross revenue = CIT Taxable revenue / (1 - VAT_Rate)
        gross_revenue = float(round(cit_revenue / (1.0 - vat_rate)))
        
        fct_cit = float(round(cit_revenue * cit_rate))
        fct_vat = float(round(gross_revenue * vat_rate))
        total_fct = fct_cit + fct_vat
        net_value = contract_value
    else:
        # Starting with Gross contract value (including FCT)
        gross_revenue = contract_value
        fct_vat = float(round(gross_revenue * vat_rate))
        cit_revenue = gross_revenue - fct_vat
        fct_cit = float(round(cit_revenue * cit_rate))
        total_fct = fct_vat + fct_cit
        net_value = gross_revenue - total_fct
        
    return {
        "contract_value": contract_value,
        "contract_type": contract_type,
        "industry_type": industry_type,
        "industry_description": desc,
        "vat_rate": vat_rate,
        "cit_rate": cit_rate,
        "gross_revenue": gross_revenue,
        "cit_revenue": cit_revenue,
        "fct_vat": fct_vat,
        "fct_cit": fct_cit,
        "total_fct": total_fct,
        "net_value": net_value,
        "circular_reference": "Thông tư 103/2014/TT-BTC hướng dẫn nghĩa vụ thuế nhà thầu nước ngoài"
    }


def calculate_pit_tax(
    monthly_income: float,
    dependents: int = 0
) -> dict:
    """Calculate Vietnamese Personal Income Tax (PIT) on salary.
    
    Rules (Nghị quyết 954/2020/UBTVQH14 & Luật Thuế TNCN):
      - Self deduction (giảm trừ bản thân): 11,000,000 VND / month
      - Dependent deduction (giảm trừ người phụ thuộc): 4,400,000 VND / month per person
    """
    personal_deduction = 11000000.0
    dependent_deduction = dependents * 4400000.0
    total_deductions = personal_deduction + dependent_deduction
    
    taxable_income = max(0.0, monthly_income - total_deductions)
    
    # Calculate tax based on progressive tiers
    brackets = [
        (5000000.0, 0.05, 0.0),
        (10000000.0, 0.10, 250000.0),
        (18000000.0, 0.15, 750000.0),
        (32000000.0, 0.20, 1650000.0),
        (52000000.0, 0.25, 3250000.0),
        (80000000.0, 0.30, 5850000.0),
        (float('inf'), 0.35, 9850000.0)
    ]
    
    active_bracket_idx = 0
    for i, (limit, rate, subtract) in enumerate(brackets):
        prev_limit = brackets[i-1][0] if i > 0 else 0.0
        if taxable_income > prev_limit:
            active_bracket_idx = i
            
    # Calculate total tax using the shortcut formulas
    limit, rate, subtract = brackets[active_bracket_idx]
    tax = float(round(taxable_income * rate - subtract))
    tax = max(0.0, tax)
    
    net_income = monthly_income - tax
    
    return {
        "monthly_income": monthly_income,
        "dependents": dependents,
        "personal_deduction": personal_deduction,
        "dependent_deduction": dependent_deduction,
        "total_deductions": total_deductions,
        "taxable_income": taxable_income,
        "tax_rate": rate,
        "pit_tax": tax,
        "net_income": net_income,
        "active_tier": active_bracket_idx + 1,
        "legal_reference": "Nghị quyết 954/2020/UBTVQH14 & Thông tư 111/2013/TT-BTC"
    }


