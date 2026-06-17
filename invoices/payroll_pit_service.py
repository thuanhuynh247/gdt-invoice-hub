"""Payroll & Personal Income Tax (PIT) Compliance Audit Engine (US-344, US-345).

Implements statutory PIT calculations under progressive tax rates (5% to 35%),
dependent deductions (4.4M/month), personal deductions (11M/month), 
social insurance withholding audits (10.5% employee, 21.5% employer), 
and GDT-compliant Form 05/QTT-TNCN XML generation.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime

# PIT Progressive Tax brackets table (monthly taxable income)
# 1. Up to 5M: 5%
# 2. 5M to 10M: 10% - 250k
# 3. 10M to 18M: 15% - 750k
# 4. 18M to 32M: 20% - 1.65M
# 5. 32M to 52M: 25% - 3.25M
# 6. 52M to 80M: 30% - 5.85M
# 7. Over 80M: 35% - 9.85M
def calculate_monthly_pit(taxable_income: float) -> float:
    """Calculate progressive PIT for monthly taxable income in VND."""
    if taxable_income <= 0:
        return 0.0
    elif taxable_income <= 5000000:
        return taxable_income * 0.05
    elif taxable_income <= 10000000:
        return taxable_income * 0.10 - 250000
    elif taxable_income <= 18000000:
        return taxable_income * 0.15 - 750000
    elif taxable_income <= 32000000:
        return taxable_income * 0.20 - 1650000
    elif taxable_income <= 52000000:
        return taxable_income * 0.25 - 3250000
    elif taxable_income <= 80000000:
        return taxable_income * 0.30 - 5850000
    else:
        return taxable_income * 0.35 - 9850000

def audit_payroll_register(employees: list[dict]) -> dict:
    """Audit employee payroll registries against progressive PIT and social insurance rates.
    
    Each employee in list:
      {
         "id": str,
         "name": str,
         "mst": str,
         "gross_salary": float,
         "dependents": int,
         "withheld_pit": float,
         "withheld_insurance": float
      }
    """
    personal_deduction = 11000000.0  # 11M VND per month
    dependent_deduction_rate = 4400000.0  # 4.4M VND per dependent per month
    
    total_gross = 0.0
    total_pit_calculated = 0.0
    total_pit_withheld = 0.0
    total_insurance_calculated = 0.0
    total_insurance_withheld = 0.0
    
    audited_employees = []
    compliance_issues = []
    
    for emp in employees:
        gross = emp.get("gross_salary", 0.0)
        dependents = emp.get("dependents", 0)
        w_pit = emp.get("withheld_pit", 0.0)
        w_ins = emp.get("withheld_insurance", 0.0)
        
        # Social Insurance (SI) base is capped at 20x base salary
        # Base salary in 2026 is 2,340,000 VND. Cap = 46,800,000 VND.
        si_base = min(gross, 46800000.0)
        calc_ins = si_base * 0.105  # 10.5% total employee social deductions
        calc_employer_ins = si_base * 0.215 # 21.5% employer contributions
        
        # Deductions
        dep_deduct = dependents * dependent_deduction_rate
        total_deduct = personal_deduction + dep_deduct + calc_ins
        
        # Taxable income
        taxable_inc = max(0.0, gross - total_deduct)
        calc_pit = calculate_monthly_pit(taxable_inc)
        
        # Variances
        pit_variance = w_pit - calc_pit
        ins_variance = w_ins - calc_ins
        
        status = "compliant"
        issues = []
        
        if abs(pit_variance) > 10.0:  # Allow 10 VND threshold
            status = "non_compliant"
            issues.append(f"PIT discrepancy: withheld={w_pit:,.0f} vs statutory={calc_pit:,.0f} (var={pit_variance:,.0f} VND)")
            compliance_issues.append({
                "employee_id": emp.get("id"),
                "employee_name": emp.get("name"),
                "issue_type": "PIT_DISCREPANCY",
                "message": f"Thuế TNCN khấu trừ thực tế ({w_pit:,.0f} VND) khác biệt so với thuế suất lũy tiến ({calc_pit:,.0f} VND)."
            })
            
        if abs(ins_variance) > 10.0:
            status = "non_compliant"
            issues.append(f"Insurance discrepancy: withheld={w_ins:,.0f} vs statutory={calc_ins:,.0f} (var={ins_variance:,.0f} VND)")
            compliance_issues.append({
                "employee_id": emp.get("id"),
                "employee_name": emp.get("name"),
                "issue_type": "SI_DISCREPANCY",
                "message": f"Bảo hiểm khấu trừ thực tế ({w_ins:,.0f} VND) khác biệt so với mức đóng 10.5% ({calc_ins:,.0f} VND)."
            })
            
        total_gross += gross
        total_pit_calculated += calc_pit
        total_pit_withheld += w_pit
        total_insurance_calculated += calc_ins
        total_insurance_withheld += w_ins
        
        audited_employees.append({
            "id": emp.get("id"),
            "name": emp.get("name"),
            "mst": emp.get("mst", ""),
            "gross_salary": gross,
            "dependents": dependents,
            "statutory_insurance": calc_ins,
            "employer_insurance": calc_employer_ins,
            "taxable_income": taxable_inc,
            "calculated_pit": calc_pit,
            "withheld_pit": w_pit,
            "withheld_insurance": w_ins,
            "pit_variance": pit_variance,
            "insurance_variance": ins_variance,
            "status": status,
            "issues": issues
        })
        
    # Calculate score
    total_checks = len(employees) * 2 if employees else 1
    failures = len(compliance_issues)
    compliance_score = max(0, int(((total_checks - failures) / total_checks) * 100))
    
    return {
        "employees": audited_employees,
        "compliance_issues": compliance_issues,
        "total_gross": total_gross,
        "total_pit_calculated": total_pit_calculated,
        "total_pit_withheld": total_pit_withheld,
        "total_insurance_calculated": total_insurance_calculated,
        "total_insurance_withheld": total_insurance_withheld,
        "compliance_score": compliance_score,
        "status": "success" if compliance_score == 100 else "flagged"
    }

def generate_form_05_qtt_tncn_xml(metadata: dict, employees: list[dict]) -> str:
    """Generate GDT-compliant year-end PIT finalization Form 05/QTT-TNCN XML return."""
    root = ET.Element("HSoKhaiThue")
    
    header = ET.SubElement(root, "Header")
    ET.SubElement(header, "MaMST").text = metadata.get("mst", "0000000000")
    ET.SubElement(header, "TenNNT").text = metadata.get("company_name", "Doanh nghiệp của tôi")
    
    ky_tinh_thue = ET.SubElement(header, "KyTinhThue")
    ET.SubElement(ky_tinh_thue, "LoaiKy").text = "N"
    ET.SubElement(ky_tinh_thue, "Nam").text = str(metadata.get("year", datetime.now().year))
    
    ET.SubElement(header, "MauTK").text = "05/QTT-TNCN"
    
    body = ET.SubElement(root, "Body")
    
    # 05/QTT-TNCN Core Info
    qtt = ET.SubElement(body, "ToKhai05QTT")
    
    # Tables corresponding to appendices BK05-1, BK05-2, BK05-3
    bk1 = ET.SubElement(qtt, "BangKe05_1")
    bk2 = ET.SubElement(qtt, "BangKe05_2")
    bk3 = ET.SubElement(qtt, "BangKe05_3")
    
    # Classify employees into BK05-1 (residents with labor contract >= 3 months)
    # and BK05-2 (residents without contract or contract < 3 months, flat 10% rate)
    for idx, emp in enumerate(employees):
        # Default to contract >= 3 months (resident) for testing
        is_contract_gte_3m = emp.get("contract_type", "long_term") == "long_term"
        
        gross = emp.get("gross_salary", 0.0) * 12 # Annualize for year-end finalization
        ins = emp.get("withheld_insurance", 0.0) * 12
        dependents = emp.get("dependents", 0)
        personal_deduct = 11000000.0 * 12
        dep_deduct = dependents * 4400000.0 * 12
        taxable_inc = max(0.0, gross - personal_deduct - dep_deduct - ins)
        pit = calculate_monthly_pit(taxable_inc / 12) * 12
        
        if is_contract_gte_3m:
            row = ET.SubElement(bk1, "ChiTiet")
            ET.SubElement(row, "STT").text = str(idx + 1)
            ET.SubElement(row, "TenNV").text = emp.get("name", "N/A")
            ET.SubElement(row, "MST_NV").text = emp.get("mst", "")
            ET.SubElement(row, "ThuNhapChiuThue").text = f"{gross:.0f}"
            ET.SubElement(row, "GiamTruGiaCanh").text = f"{(personal_deduct + dep_deduct):.0f}"
            ET.SubElement(row, "GiamTruBaoHiem").text = f"{ins:.0f}"
            ET.SubElement(row, "ThuNhapTinhThue").text = f"{taxable_inc:.0f}"
            ET.SubElement(row, "ThueTNCNKhauTru").text = f"{pit:.0f}"
        else:
            row = ET.SubElement(bk2, "ChiTiet")
            ET.SubElement(row, "STT").text = str(idx + 1)
            ET.SubElement(row, "TenNV").text = emp.get("name", "N/A")
            ET.SubElement(row, "MST_NV").text = emp.get("mst", "")
            # Flat rate calculations (e.g. 10%)
            flat_pit = gross * 0.10
            ET.SubElement(row, "ThuNhapChiuThue").text = f"{gross:.0f}"
            ET.SubElement(row, "ThueTNCNKhauTru").text = f"{flat_pit:.0f}"
            
    # Generate pretty printed XML
    raw_xml = ET.tostring(root, encoding="utf-8")
    parsed = minidom.parseString(raw_xml)
    xml_str = parsed.toprettyxml(indent="  ")
    
    return xml_str
