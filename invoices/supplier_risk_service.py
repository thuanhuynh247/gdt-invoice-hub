"""Dynamic GDT Supplier Risk & Shell Company Detection Service."""

from __future__ import annotations

import json
from datetime import datetime
from collections import defaultdict
from sqlalchemy import and_
from extensions import db
from invoices.models import Invoice, Partner, BlacklistedMST, LineItem, AIAuditResult
from invoices.mst_service import (
    check_mst_status,
    STATUS_ACTIVE,
    STATUS_SUSPENDED,
    STATUS_CLOSED,
    STATUS_NOT_FOUND,
)

def calculate_supplier_risk(seller_mst: str, taxpayer_mst: str) -> dict:
    """Analyze all invoices and GDT status of a supplier to calculate an AI-powered trust rating.
    
    Returns a dict with:
        - supplier_mst
        - supplier_name
        - invoice_count
        - risk_score: 0 to 100
        - trust_rating: A++ to F
        - flags: list of matched risk flags
        - total_value
        - gdt_status
        - details: dictionary with individual penalty components
    """
    # Force SQLAlchemy to expire the session identity map and fetch fresh data from database
    db.session.expire_all()
    
    # 1. Base initialization
    score = 100
    flags = []
    penalties = {}
    
    # 2. Fetch GDT Tax status & Blacklist check
    blacklisted = BlacklistedMST.query.filter_by(mst=seller_mst).first()
    is_blacklisted = False
    if blacklisted:
        is_blacklisted = True
        flags.append("BLACKLISTED")
        penalties["blacklist"] = 100
        
    # Get partner info for name and address
    partner = Partner.query.filter_by(mst=seller_mst).first()
    if is_blacklisted:
        supplier_name = "BLACKLISTED SUPPLIER"
    else:
        supplier_name = partner.name if partner and partner.name else "Nhà cung cấp chưa đặt tên"
    
    # Resolve GDT status
    if is_blacklisted:
        gdt_status = "BLACKLISTED"
    else:
        gdt_info = check_mst_status(seller_mst)
        gdt_status = gdt_info.get("status") or STATUS_ACTIVE
        
        if gdt_status == STATUS_SUSPENDED:
            score -= 25
            flags.append("GDT_STATUS_SUSPENDED")
            penalties["gdt_status"] = 25
        elif gdt_status == STATUS_CLOSED:
            score -= 50
            flags.append("GDT_STATUS_CLOSED")
            penalties["gdt_status"] = 50
        elif gdt_status == STATUS_NOT_FOUND:
            score -= 75
            flags.append("GDT_STATUS_NOT_FOUND")
            penalties["gdt_status"] = 75

    # Fetch all invoices from this supplier for the current taxpayer profile
    invoices = Invoice.query.filter(
        and_(
            Invoice.seller_mst == seller_mst,
            Invoice.taxpayer_mst == taxpayer_mst
        )
    ).all()
    
    invoice_count = len(invoices)
    total_value = sum(inv.total_amount for inv in invoices)
    
    if invoice_count == 0:
        # Capped score if no transaction history but has active status
        final_score = max(0, score)
        if is_blacklisted:
            final_score = 0
            trust_rating = "F"
        else:
            trust_rating = "A++" if final_score >= 95 else ("A" if final_score >= 85 else "B")
            
        return {
            "supplier_mst": seller_mst,
            "supplier_name": supplier_name,
            "invoice_count": 0,
            "risk_score": final_score,
            "trust_rating": trust_rating,
            "flags": flags,
            "total_value": 0.0,
            "gdt_status": gdt_status,
            "details": penalties
        }
        
    if not partner or not partner.name:
        # Use seller_name from first invoice if partner record is incomplete
        supplier_name = invoices[0].seller_name or "Nhà cung cấp chưa đặt tên"

    # 3. Monthly statistics for Velocity/Volume Spikes & Cash Splitting
    monthly_totals = defaultdict(float)
    monthly_cash_splitting_count = defaultdict(int)
    
    # Track months with historical invoices
    for inv in invoices:
        date_str = inv.date or ""
        # Try extracting YYYY-MM
        month_key = date_str[:7] if len(date_str) >= 7 else "unknown"
        if month_key != "unknown":
            monthly_totals[month_key] += inv.total_amount
            
            # Cash Splitting check
            pay_method = (inv.payment_method or "").upper()
            is_cash = any(x in pay_method for x in ["TM", "TIỀN MẶT", "CASH"])
            if is_cash and 19000000.0 <= inv.total_amount < 20000000.0:
                monthly_cash_splitting_count[month_key] += 1

    # Evaluate Volume Spike
    months_count = len(monthly_totals)
    if months_count >= 3:
        # Calculate monthly average
        all_sums = list(monthly_totals.values())
        avg_monthly = sum(all_sums) / months_count
        has_volume_spike = any(m_sum > 3.0 * avg_monthly for m_sum in all_sums)
        if has_volume_spike:
            score -= 20
            flags.append("VOLUME_SPIKE")
            penalties["volume_spike"] = 20
    else:
        # For new suppliers, flag if any single month has total amount > 500 million VND
        has_large_new_volume = any(m_sum > 500000000.0 for m_sum in monthly_totals.values())
        if has_large_new_volume:
            score -= 20
            flags.append("VOLUME_SPIKE")
            penalties["volume_spike"] = 20

    # Evaluate Cash Splitting & Direct Cash Violations
    has_cash_splitting = any(count >= 2 for count in monthly_cash_splitting_count.values())
    has_direct_cash_violation = any(
        inv.total_amount >= 20000000.0 and any(x in (inv.payment_method or "").upper() for x in ["TM", "TIỀN MẶT", "CASH"])
        for inv in invoices
    )
    if has_cash_splitting or has_direct_cash_violation:
        score -= 15
        flags.append("CASH_SPLITTING")
        penalties["cash_splitting"] = 15

    # 4. Late Digital Signing check
    late_signing_count = 0
    for inv in invoices:
        if not inv.has_signature:
            late_signing_count += 1
            continue
        try:
            inv_date = datetime.strptime(inv.date[:10], "%Y-%m-%d")
            sig_date = datetime.strptime(inv.signing_date[:10], "%Y-%m-%d")
            delta_days = (sig_date - inv_date).days
            if delta_days > 3:
                late_signing_count += 1
        except Exception:
            # Fallback if date strings are not perfectly matching %Y-%m-%d
            pass
            
    late_signing_ratio = late_signing_count / invoice_count if invoice_count > 0 else 0.0
    if late_signing_ratio > 0.20:
        score -= 15
        flags.append("LATE_SIGNING")
        penalties["late_signing"] = 15

    # 5. Suspicious Item Text Scan
    suspicious_keywords = [
        "dịch vụ tư vấn",
        "tư vấn quản lý",
        "chi phí hỗ trợ",
        "dịch vụ tiếp khách",
        "dịch vụ ăn uống",
        "quảng cáo không rõ nội dung",
        "khảo sát thị trường",
    ]
    
    suspicious_invoices = set()
    for inv in invoices:
        for item in inv.items:
            item_name_lower = (item.item_name or "").lower()
            if any(kw in item_name_lower for kw in suspicious_keywords):
                suspicious_invoices.add(inv)
                break
                
    if len(suspicious_invoices) > 0:
        avg_suspicious_value = sum(i.total_amount for i in suspicious_invoices) / len(suspicious_invoices)
        if avg_suspicious_value > 50000000.0:
            score -= 15
            flags.append("SUSPICIOUS_ITEMS")
            penalties["suspicious_items"] = 15

    # 6. AI Compliance Warnings from AIAuditResult
    ai_warning_count = 0
    for inv in invoices:
        ai_warning_count += len(inv.ai_audit_results)
        
    if ai_warning_count > 0:
        deduction = min(30, ai_warning_count * 15)
        score -= deduction
        flags.append("AI_WARNING")
        penalties["ai_warning"] = deduction

    # Capping score
    final_score = max(0, score)
    if is_blacklisted:
        final_score = 0
    
    # 7. Trust Rating Assignment
    if is_blacklisted:
        trust_rating = "F"
    elif final_score >= 95:
        trust_rating = "A++"
    elif final_score >= 85:
        trust_rating = "A"
    elif final_score >= 70:
        trust_rating = "B"
    elif final_score >= 50:
        trust_rating = "C"
    elif final_score >= 30:
        trust_rating = "D"
    else:
        trust_rating = "F"
        
    return {
        "supplier_mst": seller_mst,
        "supplier_name": supplier_name,
        "invoice_count": invoice_count,
        "risk_score": final_score,
        "trust_rating": trust_rating,
        "flags": flags,
        "total_value": total_value,
        "gdt_status": gdt_status,
        "details": penalties
    }

def get_all_suppliers_risk_radar(taxpayer_mst: str) -> dict:
    """Retrieve all suppliers and summarize the risk radar statistics."""
    # Find all supplier MSTs from invoices
    raw_sellers = db.session.query(Invoice.seller_mst, Invoice.seller_name).filter(
        Invoice.taxpayer_mst == taxpayer_mst
    ).all()
    
    # Extract unique MSTs in Python to avoid PostgreSQL-specific DISTINCT ON deprecation warnings
    seen_msts = set()
    unique_sellers = []
    for mst, name in raw_sellers:
        if mst and mst not in seen_msts:
            seen_msts.add(mst)
            unique_sellers.append((mst, name))
    
    suppliers_radar = []
    total_value_at_risk = 0.0
    high_risk_count = 0  # Rating D or F
    
    # Set of blacklist to also count blacklisted ones even if no invoices exist
    blacklisted_records = BlacklistedMST.query.all()
    blacklisted_msts = {b.mst for b in blacklisted_records}
    
    # Combine unique sellers from invoices + blacklisted ones
    seller_msts = {s[0] for s in unique_sellers if s[0]}
    all_msts = seller_msts.union(blacklisted_msts)
    
    for mst in all_msts:
        res = calculate_supplier_risk(mst, taxpayer_mst)
        suppliers_radar.append(res)
        
        if res["trust_rating"] in ("D", "F"):
            high_risk_count += 1
            total_value_at_risk += res["total_value"]
            
    # Sort: risk_score ascending (highest risk first), then total_value descending
    suppliers_radar.sort(key=lambda x: (x["risk_score"], -x["total_value"]))
    
    # Filter the summary counts
    blacklist_warnings_count = sum(1 for s in suppliers_radar if "BLACKLISTED" in s["flags"])
    signature_violations_count = sum(1 for s in suppliers_radar if "LATE_SIGNING" in s["flags"])
    payment_type_flags_count = sum(1 for s in suppliers_radar if "CASH_SPLITTING" in s["flags"])
    
    return {
        "status": "success",
        "summary": {
            "total_analyzed": len(suppliers_radar),
            "total_with_warnings": high_risk_count,
            "total_value_at_risk": total_value_at_risk,
            "blacklist_warnings_count": blacklist_warnings_count,
            "signature_violations_count": signature_violations_count,
            "payment_type_flags_count": payment_type_flags_count
        },
        "suppliers": suppliers_radar
    }
