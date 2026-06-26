"""Corporate Tax Health Score Service (Axis 5) - Computes Compliance Ratings and VAT/CIT Reconciliation Matrix."""

from __future__ import annotations
import json
from datetime import datetime
from typing import Any
from extensions import db
from invoices.models import Invoice, BankTransaction, Partner
from invoices.invoice_validator import calculate_benford_distribution, _parse_date

def calculate_tax_health(taxpayer_mst: str) -> dict[str, Any]:
    """Compute tax compliance score, rating, reconciliation matrix, and financial exposure projections."""
    invoices = Invoice.query.filter_by(taxpayer_mst=taxpayer_mst).all()
    total_invoices = len(invoices)
    
    purchase_count = 0
    sales_count = 0
    cancelled_count = 0
    late_signature_count = 0
    critical_alert_count = 0
    warning_alert_count = 0
    supplier_risk_count = 0
    cash_payment_risk_count = 0
    
    purchase_vat = 0.0
    sales_vat = 0.0
    purchase_amount = 0.0
    sales_amount = 0.0
    
    amounts_for_benford = []
    
    # 1. Run single-invoice metrics and compliance checks
    for inv in invoices:
        is_purchase = inv.invoice_type == "purchase"
        if is_purchase:
            purchase_count += 1
            purchase_amount += inv.total_amount or 0.0
            purchase_vat += inv.tax_amount or 0.0
        else:
            sales_count += 1
            sales_amount += inv.total_amount or 0.0
            sales_vat += inv.tax_amount or 0.0
            
        if inv.is_cancelled:
            cancelled_count += 1
            
        amounts_for_benford.append(inv.total_amount or 0.0)
        
        # Check late signatures (> 5 days)
        dt_sign = _parse_date(inv.signing_date)
        dt_issue = _parse_date(inv.date)
        if dt_sign and dt_issue:
            days_late = (dt_sign - dt_issue).days
            if days_late > 5:
                late_signature_count += 1
                
        # Parse compliance alerts from validator
        warnings = inv.warnings
        for w in warnings:
            if isinstance(w, dict):
                sev = w.get("severity", "")
                chk = w.get("check", "")
                if sev == "Nghiêm trọng":
                    critical_alert_count += 1
                elif sev == "Cảnh báo":
                    warning_alert_count += 1
                if chk == "Rủi ro NCC":
                    supplier_risk_count += 1
            elif isinstance(w, str):
                if "NGHIÊM TRỌNG" in w.upper() or "HỦY" in w.upper():
                    critical_alert_count += 1
                else:
                    warning_alert_count += 1
                    
        # Non-cash payment check >= 20,000,000 VND (CIT & VAT compliance)
        total_amt = inv.total_amount or 0.0
        if is_purchase and total_amt >= 20000000.0:
            pay_method = (inv.payment_method or "").strip().lower()
            if not pay_method or "tiền mặt" in pay_method or pay_method == "tm":
                cash_payment_risk_count += 1
                
    # 2. Benford's Law distribution analysis
    benford_data = calculate_benford_distribution(amounts_for_benford)
    benford_status = benford_data.get("status", "Thiếu dữ liệu")
    benford_chi_square = benford_data.get("chi_square_stat", 0.0)
    
    benford_penalty = 0
    if benford_status == "Nghiêm trọng":
        benford_penalty = 15
    elif benford_status == "Cảnh báo":
        benford_penalty = 8
        
    # 3. Health Score Calculation (100-point scale)
    score = 100.0
    score -= min(30.0, critical_alert_count * 15.0)
    score -= min(15.0, warning_alert_count * 5.0)
    score -= min(30.0, supplier_risk_count * 10.0)
    score -= min(20.0, cash_payment_risk_count * 10.0)
    score -= min(10.0, late_signature_count * 2.0)
    score -= benford_penalty
    
    score = max(0.0, score)
    score = round(score, 1)
    
    # Determine Rating and Descriptions
    if score >= 95:
        rating = "A++"
        rating_desc = "Doanh nghiệp có chỉ số tuân thủ cực kỳ cao, rủi ro thanh tra thuế rất thấp."
    elif score >= 90:
        rating = "A"
        rating_desc = "Chỉ số tuân thủ tốt, rủi ro thấp. Có một vài sai lệch nhỏ cần lưu ý."
    elif score >= 80:
        rating = "B"
        rating_desc = "Mức tuân thủ trung bình. Có nhiều lỗi hóa đơn hoặc chậm ký số cần khắc phục."
    elif score >= 70:
        rating = "C"
        rating_desc = "Rủi ro thuế trung bình cao. Cần lập tức rà soát chéo chứng từ và nhà cung cấp."
    else:
        rating = "D"
        rating_desc = "Nguy cơ RỦI RO THUẾ CỰC CAO. Hệ thống khuyến nghị rà soát khẩn cấp toàn bộ dữ liệu."
        
    # Cache rating on invoices for faster list rendering
    if invoices:
        for inv in invoices:
            inv.t_score = int(score)
            inv.t_rating = rating
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()

    # 4. Bank Reconciliation Matrix
    bank_txs = BankTransaction.query.filter_by(taxpayer_mst=taxpayer_mst).all()
    total_bank_inflows = 0.0
    total_bank_outflows = 0.0
    matched_bank_inflows = 0.0
    matched_bank_outflows = 0.0
    
    unreconciled_bank_txs = []
    
    for tx in bank_txs:
        amt = tx.amount
        is_inflow = amt > 0
        if is_inflow:
            total_bank_inflows += amt
            if tx.status == "matched":
                matched_bank_inflows += amt
        else:
            total_bank_outflows += abs(amt)
            if tx.status == "matched":
                matched_bank_outflows += abs(amt)
                
        if tx.status == "unreconciled":
            unreconciled_bank_txs.append(tx.to_dict())
            
    inflow_gap = abs(sales_amount - total_bank_inflows)
    outflow_gap = abs(purchase_amount - total_bank_outflows)
    
    # 5. Tax Exposure Projections
    vat_payable = sales_vat - purchase_vat
    cit_exposure = 0.0
    vat_non_deductible_exposure = 0.0
    
    for inv in invoices:
        if inv.invoice_type == "purchase" and (inv.total_amount or 0.0) >= 20000000.0:
            pay_method = (inv.payment_method or "").strip().lower()
            if not pay_method or "tiền mặt" in pay_method or pay_method == "tm":
                cit_exposure += (inv.amount_before_tax or 0.0) * 0.20
                vat_non_deductible_exposure += (inv.tax_amount or 0.0)
                
    total_tax_exposure = cit_exposure + vat_non_deductible_exposure
    
    return {
        "taxpayer_mst": taxpayer_mst,
        "health_score": score,
        "compliance_rating": rating,
        "compliance_description": rating_desc,
        "metrics": {
            "total_invoices": total_invoices,
            "purchase_count": purchase_count,
            "sales_count": sales_count,
            "cancelled_count": cancelled_count,
            "late_signature_count": late_signature_count,
            "critical_alert_count": critical_alert_count,
            "warning_alert_count": warning_alert_count,
            "supplier_risk_count": supplier_risk_count,
            "cash_payment_risk_count": cash_payment_risk_count,
        },
        "financials": {
            "sales_amount": sales_amount,
            "sales_vat": sales_vat,
            "purchase_amount": purchase_amount,
            "purchase_vat": purchase_vat,
        },
        "benford": {
            "status": benford_status,
            "chi_square": benford_chi_square,
            "message": benford_data.get("message", ""),
            "distribution": benford_data
        },
        "reconciliation": {
            "total_bank_inflows": total_bank_inflows,
            "total_bank_outflows": total_bank_outflows,
            "matched_bank_inflows": matched_bank_inflows,
            "matched_bank_outflows": matched_bank_outflows,
            "inflow_gap": inflow_gap,
            "outflow_gap": outflow_gap,
            "unreconciled_transactions": unreconciled_bank_txs[:10],
        },
        "tax_exposure": {
            "vat_payable_projected": vat_payable,
            "cit_non_deductible_exposure": cit_exposure,
            "vat_non_deductible_exposure": vat_non_deductible_exposure,
            "total_exposure": total_tax_exposure
        }
    }
