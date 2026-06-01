"""CIT Calculation, Form 03/TNDN Scaffolder & Visual Scenario Modeler (US-180, US-181).

Circular 200/2014/TT-BTC, Decree 132/2020/ND-CP (30% EBITDA cap), and HTKK compatible XML output generation.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
from io import BytesIO
import openpyxl
from extensions import db
from invoices.models import Invoice

def finalize_cit(balances: dict[str, dict], metadata: dict) -> dict:
    """US-180: Compile CIT Finalization and generate HTKK Form 03/TNDN XML.
    
    EBITDA Calculation under Decree 132/2020/ND-CP:
    EBITDA = Net Operating Profit + Interest Expense + Depreciation
    Cap = 30% of EBITDA
    """
    warnings = []
    
    # 1. Gather revenue & income accounts
    revenue_511 = 0.0
    financial_rev_515 = 0.0
    other_rev_711 = 0.0
    
    # 2. Gather expense accounts
    cogs_632 = 0.0
    interest_expense_635 = 0.0  # Interest expense under 635
    other_financial_exp = 0.0
    selling_exp_641 = 0.0
    admin_exp_642 = 0.0
    other_exp_811 = 0.0
    depreciation_214 = 0.0      # Depreciation movement (credit movement of 214)
    
    for k, v in balances.items():
        if k.startswith("511"):
            revenue_511 += v["credit_movement"] - v["debit_movement"]
        elif k.startswith("515"):
            financial_rev_515 += v["credit_movement"] - v["debit_movement"]
        elif k.startswith("711"):
            other_rev_711 += v["credit_movement"] - v["debit_movement"]
            
        elif k.startswith("632"):
            cogs_632 += v["debit_movement"] - v["credit_movement"]
        elif k.startswith("635"):
            # Sub-account or total 635 interest cost
            interest_expense_635 += v["debit_movement"] - v["credit_movement"]
        elif k.startswith("641"):
            selling_exp_641 += v["debit_movement"] - v["credit_movement"]
        elif k.startswith("642"):
            admin_exp_642 += v["debit_movement"] - v["credit_movement"]
        elif k.startswith("811"):
            other_exp_811 += v["debit_movement"] - v["credit_movement"]
        elif k.startswith("214"):
            depreciation_214 += v["credit_movement"] - v["debit_movement"]

    # Deduct interest from total 635 to get non-interest financial expenses
    # Typically interest expense is tracked under 6352 or inside 635.
    # If 635 interest is not separated, we treat all of 635 as interest.
    total_revenue = revenue_511 + financial_rev_515 + other_rev_711
    total_expenses = cogs_632 + interest_expense_635 + selling_exp_641 + admin_exp_642 + other_exp_811
    
    pretax_profit = total_revenue - total_expenses
    
    # 3. Related Party Transactions (Decree 132/2020/ND-CP)
    # Get user manual adjustments from metadata
    non_deductible_manual = float(metadata.get("non_deductible_manual", 0.0))
    loss_carry_forward = float(metadata.get("loss_carry_forward", 0.0))
    rd_allowance = float(metadata.get("rd_allowance", 0.0))  # R&D tax credit
    
    # Compute EBITDA
    ebitda = pretax_profit + interest_expense_635 + depreciation_214
    ebitda = max(0.0, ebitda)  # EBITDA cannot be negative for cap formula
    
    interest_cap = ebitda * 0.3
    non_deductible_interest = 0.0
    if interest_expense_635 > interest_cap:
        non_deductible_interest = interest_expense_635 - interest_cap
        warnings.append(
            f"Vượt trần chi phí lãi vay (Nghị định 132): Chi phí lãi vay ({interest_expense_635:,.0f} VND) "
            f"vượt trần 30% EBITDA ({interest_cap:,.0f} VND). Phần chi phí lãi vay không được trừ: {non_deductible_interest:,.0f} VND."
        )
    
    # Total non-deductible expenses (Chỉ tiêu B4 trong tờ khai 03/TNDN)
    total_non_deductible = non_deductible_manual + non_deductible_interest
    
    # Taxable income (Chỉ tiêu B13)
    taxable_income = pretax_profit + total_non_deductible
    
    # Assessable income (Chỉ tiêu C1)
    assessable_income = max(0.0, taxable_income - loss_carry_forward)
    
    # CIT Liability
    cit_rate = 0.20  # Standard CIT rate 20%
    cit_before_credit = assessable_income * cit_rate
    cit_payable = max(0.0, cit_before_credit - rd_allowance)
    
    # Effective Tax Rate
    effective_tax_rate = (cit_payable / pretax_profit * 100) if pretax_profit > 0 else 0.0
    
    # Standard compliance audit risk score
    risk_score = 100
    if non_deductible_interest > 0:
        risk_score -= 15
    if non_deductible_manual > (total_expenses * 0.1):  # > 10% costs are non-deductible
        risk_score -= 20
    if pretax_profit < 0:
        risk_score -= 10  # operating loss is minor risk
    risk_score = max(10, risk_score)

    # 4. Generate HTKK XML Form 03/TNDN
    root = ET.Element("HSoKhaiThue")
    header = ET.SubElement(root, "Header")
    ET.SubElement(header, "MaMST").text = metadata.get("mst", "0109998887")
    ET.SubElement(header, "TenNNT").text = metadata.get("company_name", "CONG TY TNHH MOCK")
    
    ky_tinh_thue = ET.SubElement(header, "KyTinhThue")
    ET.SubElement(ky_tinh_thue, "LoaiKy").text = "N"
    ET.SubElement(ky_tinh_thue, "Nam").text = str(metadata.get("year", 2026))
    
    ET.SubElement(header, "MauTK").text = "03/TNDN"
    
    body = ET.SubElement(root, "Body")
    cit_form = ET.SubElement(body, "ToKhaiQuyetToanTNDN")
    
    ET.SubElement(cit_form, "LoiNhuanKeToanTruocThue", {"Code": "A1"}).text = f"{pretax_profit:.0f}"
    ET.SubElement(cit_form, "DieuChinhTangDoanhThu", {"Code": "B2"}).text = "0"
    ET.SubElement(cit_form, "ChiPhiKhongDuocTru", {"Code": "B4"}).text = f"{total_non_deductible:.0f}"
    ET.SubElement(cit_form, "TongThuNhapChiuThue", {"Code": "B13"}).text = f"{taxable_income:.0f}"
    ET.SubElement(cit_form, "ThuNhapMienThue", {"Code": "C1"}).text = "0"
    ET.SubElement(cit_form, "ChuyenLoNamTruoc", {"Code": "C3"}).text = f"{loss_carry_forward:.0f}"
    ET.SubElement(cit_form, "ThuNhapTinhThue", {"Code": "C4"}).text = f"{assessable_income:.0f}"
    ET.SubElement(cit_form, "ThueSuatPhoThong", {"Code": "C7"}).text = "20"
    ET.SubElement(cit_form, "ThueTNDNPhaiNop", {"Code": "D1"}).text = f"{cit_payable:.0f}"
    ET.SubElement(cit_form, "UuDaiGiamThueRD", {"Code": "E1"}).text = f"{rd_allowance:.0f}"
    
    raw_xml = ET.tostring(root, encoding="utf-8")
    parsed = minidom.parseString(raw_xml)
    xml_str = parsed.toprettyxml(indent="  ")
    
    return {
        "status": "success" if non_deductible_interest == 0 else "warning",
        "pretax_profit": pretax_profit,
        "ebitda": ebitda,
        "interest_cap": interest_cap,
        "non_deductible_interest": non_deductible_interest,
        "total_non_deductible": total_non_deductible,
        "taxable_income": taxable_income,
        "assessable_income": assessable_income,
        "cit_payable": cit_payable,
        "effective_tax_rate": effective_tax_rate,
        "risk_score": risk_score,
        "warnings": warnings,
        "xml": xml_str
    }

def simulate_cit_scenario(base_data: dict, adjustments: dict) -> dict:
    """US-181: Simulate what-if tax scenarios based on slider adjustments.
    
    adjustments keys:
      - revenue_pct: +/- revenue change percentage
      - cost_of_goods_pct: +/- COGS change percentage
      - staff_costs: absolute salary costs change
      - interest_linked: simulated interest expense from related party
      - rd_investment: Simulated R&D investment for deduction/credits
    """
    # 1. Read base figures from base_data
    revenue = float(base_data.get("revenue", 1000000000.0))
    cogs = float(base_data.get("cogs", 500000000.0))
    salaries = float(base_data.get("salaries", 200000000.0))
    other_costs = float(base_data.get("other_costs", 100000000.0))
    depreciation = float(base_data.get("depreciation", 50000000.0))
    
    # 2. Apply adjustments
    rev_pct = float(adjustments.get("revenue_pct", 0.0)) / 100.0
    cogs_pct = float(adjustments.get("cost_of_goods_pct", 0.0)) / 100.0
    staff_change = float(adjustments.get("staff_costs", 0.0))
    sim_interest_linked = float(adjustments.get("interest_linked", 0.0))
    sim_rd_investment = float(adjustments.get("rd_investment", 0.0))
    
    sim_revenue = revenue * (1.0 + rev_pct)
    sim_cogs = cogs * (1.0 + cogs_pct)
    sim_salaries = salaries + staff_change
    sim_interest = sim_interest_linked
    sim_expenses = sim_cogs + sim_salaries + sim_interest + other_costs
    
    sim_pretax_profit = sim_revenue - sim_expenses
    
    # EBITDA simulation
    sim_ebitda = max(0.0, sim_pretax_profit + sim_interest + depreciation)
    interest_cap = sim_ebitda * 0.3
    
    non_deductible_interest = 0.0
    if sim_interest > interest_cap:
        non_deductible_interest = sim_interest - interest_cap
        
    # Welfare costs cap (Circular 96/2015/TT-BTC: welfare costs cannot exceed 1 month average salary)
    # We can mock this with a small risk warning if staff costs change drastically without matching revenue
    non_deductible_manual = 0.0
    
    # R&D tax allowance
    # Under VAS/Vietnam tax: R&D expenses can be deducted at 100%, and some initiatives get additional 50% super-deduction
    # We can model super-deduction as direct CIT deduction
    rd_super_deduction = sim_rd_investment * 0.5
    
    # Assessable income
    taxable_income = sim_pretax_profit + non_deductible_interest + non_deductible_manual
    assessable_income = max(0.0, taxable_income)
    
    cit_payable = max(0.0, assessable_income * 0.20 - rd_super_deduction)
    effective_tax_rate = (cit_payable / sim_pretax_profit * 100) if sim_pretax_profit > 0 else 0.0
    
    # Audit Risk Score simulation
    risk_score = 100
    risk_reasons = []
    
    if non_deductible_interest > 0:
        risk_score -= 15
        risk_reasons.append("Chi phí lãi vay liên kết vượt trần 30% EBITDA")
    if sim_pretax_profit < 0:
        risk_score -= 10
        risk_reasons.append("Doanh nghiệp báo lỗ hoạt động")
    if sim_interest_linked > (sim_revenue * 0.15):
        risk_score -= 20
        risk_reasons.append("Tỷ trọng chi phí lãi vay liên kết chiếm tỷ lệ quá cao trong doanh thu (>15%)")
        
    risk_score = max(10, risk_score)
    risk_level = "Cao" if risk_score < 60 else "Trung bình" if risk_score < 80 else "Thấp"
    
    return {
        "revenue": sim_revenue,
        "expenses": sim_expenses,
        "pretax_profit": sim_pretax_profit,
        "ebitda": sim_ebitda,
        "interest_cap": interest_cap,
        "non_deductible_interest": non_deductible_interest,
        "rd_credit": rd_super_deduction,
        "cit_payable": cit_payable,
        "effective_tax_rate": effective_tax_rate,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "risk_reasons": risk_reasons
    }
