"""Version 25.0.0 Advanced Compliance Services.

Includes:
- GDT Status Syncing Agent (US-370)
- E-Invoice Correction & Replacement XML (US-372)
- Form 04/SS-HĐĐT XML Generator (US-373)
- Corporate Tax Optimization & Scenario Modeler (US-374)
"""

from __future__ import annotations
import base64
import datetime
import uuid
import xml.etree.ElementTree as ET
import lxml.etree
from extensions import db
from invoices.models import Invoice, Partner
from invoices.v24_compliance_service import generate_hsm_mock_certificate, sign_xml_invoice, transmit_to_gdt_sandbox

# ── US-370: GDT Portal Syncing & Status Verification Crawler/Agent ─────

def sync_gdt_verification_status(invoice_ids: list[str]) -> dict:
    """Sync and verify GDT portal status for the specified invoice IDs.
    
    If the invoice status is pending/empty, simulate checking the GDT database.
    If it has a valid signature and correct fields, mark as 'approved' and assign a GDT code if missing.
    Otherwise, mark as 'rejected' with error logs.
    """
    updated_invoices = []
    status_counts = {"approved": 0, "rejected": 0, "pending": 0}
    
    for inv_id in invoice_ids:
        inv = Invoice.query.get(inv_id)
        if not inv:
            continue
            
        current_status = inv.invoice_status or "pending"
        
        # If it's already approved or rejected, count and continue
        if current_status in ["approved", "rejected"]:
            status_counts[current_status] += 1
            continue
            
        # For pending invoices, check compliance to determine status
        errors = []
        
        # Rule 1: Requires signature
        if not inv.has_signature:
            errors.append("Thiếu chữ ký số HSM.")
            
        # Rule 2: Non-cash payments check (Circular 80)
        # Invoices > 20M VND must use bank transfers (TM/CK is accepted but TM is warning)
        if inv.total_amount > 20000000.0 and inv.payment_method == "TM":
            errors.append("Hóa đơn trên 20 triệu VND thanh toán bằng tiền mặt (TM).")
            
        # Rule 3: Seller MST format validation
        if not inv.seller_mst or not inv.seller_mst.strip().isdigit() or len(inv.seller_mst) not in [10, 14]:
            errors.append(f"Mã số thuế người bán '{inv.seller_mst}' không đúng định dạng.")

        if errors:
            inv.invoice_status = "rejected"
            inv.notes = f"GDT Sync Refusal: {'; '.join(errors)}"
            status_counts["rejected"] += 1
        else:
            inv.invoice_status = "approved"
            # Assign GDT code if missing
            if not inv.notes or "GDT-" not in inv.notes:
                gdt_code = f"GDT-{uuid.uuid4().hex[:12].upper()}"
                inv.notes = f"GDT Approval Code: {gdt_code}"
            status_counts["approved"] += 1
            
        inv.updated_at = datetime.datetime.now().isoformat()
        db.session.add(inv)
        
        updated_invoices.append({
            "id": inv.id,
            "status": inv.invoice_status,
            "notes": inv.notes,
            "updated_at": inv.updated_at
        })
        
    db.session.commit()
    
    return {
        "status": "success",
        "sync_time": datetime.datetime.now().isoformat(),
        "total_checked": len(invoice_ids),
        "status_counts": status_counts,
        "updated_invoices": updated_invoices
    }


def run_portal_sync_agent() -> dict:
    """Agent execution routine to pull all pending invoices and synchronize their status."""
    pending_invoices = Invoice.query.filter(
        (Invoice.invoice_status == "pending") | (Invoice.invoice_status == None)
    ).all()
    
    ids = [inv.id for inv in pending_invoices]
    if not ids:
        return {
            "status": "no_work",
            "message": "Không có hóa đơn ở trạng thái chờ (pending) cần đồng bộ.",
            "sync_time": datetime.datetime.now().isoformat()
        }
        
    return sync_gdt_verification_status(ids)


# ── US-372: E-Invoice Correction & Replacement XML Generator ──────────

def generate_correction_or_replacement_xml(
    original_invoice: Invoice,
    new_data: dict,
    type_change: str
) -> bytes:
    """Generate a Decree 123 compliant XML for corrected (điều chỉnh) or replaced (thay thế) e-invoices.
    
    Includes referencing element mapping back to the original GDT code and transaction.
    """
    if type_change not in ["correction", "replacement"]:
        raise ValueError("Loại thay đổi phải là 'correction' hoặc 'replacement'.")
        
    number = new_data.get("number") or f"{int(original_invoice.number) + 1:08d}"
    symbol = new_data.get("symbol") or original_invoice.symbol
    template = new_data.get("template_code") or original_invoice.template_code
    date_str = new_data.get("date") or datetime.date.today().isoformat()
    
    # Retrieve original GDT code from notes or assign fallback
    orig_gdt_code = "GDT-UNKNOWN"
    if original_invoice.notes and "GDT Approval Code:" in original_invoice.notes:
        orig_gdt_code = original_invoice.notes.replace("GDT Approval Code:", "").strip()
        
    ref_type_code = "1" if type_change == "replacement" else "2"
    ref_type_desc = "Thay thế" if type_change == "replacement" else "Điều chỉnh"
    
    # Extract line items
    items_xml = ""
    items = new_data.get("items") or []
    if not items:
        # Carry over original items
        for idx, item in enumerate(original_invoice.items, 1):
            items_xml += f"""        <HHDVu>
          <STT>{idx}</STT>
          <Ten>{item.item_name}</Ten>
          <SLuong>{item.quantity}</SLuong>
          <DGia>{item.unit_price}</DGia>
          <ThTien>{item.amount_before_tax}</ThTien>
          <TSuat>{item.tax_rate}</TSuat>
          <TThue>{item.tax_amount}</TThue>
        </HHDVu>
"""
    else:
        for idx, item in enumerate(items, 1):
            items_xml += f"""        <HHDVu>
          <STT>{idx}</STT>
          <Ten>{item.get('item_name')}</Ten>
          <SLuong>{item.get('quantity', 0.0)}</SLuong>
          <DGia>{item.get('unit_price', 0.0)}</DGia>
          <ThTien>{item.get('amount_before_tax', 0.0)}</ThTien>
          <TSuat>{item.get('tax_rate', '10%')}</TSuat>
          <TThue>{item.get('tax_amount', 0.0)}</TThue>
        </HHDVu>
"""

    amount_before_tax = new_data.get("amount_before_tax", original_invoice.amount_before_tax)
    tax_amount = new_data.get("tax_amount", original_invoice.tax_amount)
    total_amount = new_data.get("total_amount", original_invoice.total_amount)

    xml_content = f"""<HDon>
  <DLHDon Id="HD_{number}">
    <TTChung>
      <THDon>Hóa đơn giá trị gia tăng ({ref_type_desc})</THDon>
      <KHMSHDon>{template}</KHMSHDon>
      <KHHDon>{symbol}</KHHDon>
      <SHDon>{number}</SHDon>
      <NLap>{date_str}</NLap>
      <DVTTe>VND</DVTTe>
      <HTTToan>{new_data.get('payment_method') or original_invoice.payment_method or 'TM/CK'}</HTTToan>
      <LHDon>{ref_type_code}</LHDon>
      <LHDGoc>
        <SHDonGoc>{original_invoice.number}</SHDonGoc>
        <NLapGoc>{original_invoice.date}</NLapGoc>
        <KHHDonGoc>{original_invoice.symbol}</KHHDonGoc>
        <KHMSHDonGoc>{original_invoice.template_code}</KHMSHDonGoc>
        <MaGoc>{orig_gdt_code}</MaGoc>
      </LHDGoc>
    </TTChung>
    <NDHDon>
      <NBan>
        <Ten>{original_invoice.seller_name}</Ten>
        <MST>{original_invoice.seller_mst}</MST>
        <DChi>{original_invoice.seller_address or 'Dia chi nguoi ban'}</DChi>
      </NBan>
      <NMua>
        <Ten>{original_invoice.buyer_name}</Ten>
        <MST>{original_invoice.buyer_mst}</MST>
        <DChi>{original_invoice.buyer_address or 'Dia chi nguoi mua'}</DChi>
      </NMua>
      <DSDVu>
{items_xml}      </DSDVu>
    </NDHDon>
    <TToan>
      <TgTCThue>{amount_before_tax}</TgTCThue>
      <TgTThue>{tax_amount}</TgTThue>
      <TgTTTBSo>{total_amount}</TgTTTBSo>
    </TToan>
  </DLHDon>
</HDon>"""
    return xml_content.encode("utf-8")


# ── US-373: Form 04/SS-HĐĐT XML Generator & GDT Transmission Wizard ────

def generate_form_04_ss_xml(
    taxpayer_mst: str,
    company_name: str,
    bad_invoices: list[dict]
) -> bytes:
    """Generate standard Form 04/SS-HĐĐT XML reporting list of incorrect invoices to GDT."""
    today = datetime.date.today().isoformat()
    list_items_xml = ""
    
    for idx, item in enumerate(bad_invoices, 1):
        num = item.get("original_number") or "00000001"
        symbol = item.get("original_symbol") or "C26TBA"
        tpl = item.get("original_template") or "1"
        date_str = item.get("original_date") or today
        gdt_code = item.get("gdt_code") or "GDT-UNKNOWN"
        reason = item.get("reason") or "Sai sot thong tin"
        err_type = item.get("error_type") or "2" # 1: Huy, 2: Dieu chinh, 3: Thay the, 4: Giai trinh
        
        list_items_xml += f"""      <HDSSSot>
        <STT>{idx}</STT>
        <KHMSHDon>{tpl}</KHMSHDon>
        <KHHDon>{symbol}</KHHDon>
        <SHDon>{num}</SHDon>
        <NLap>{date_str}</NLap>
        <MCQuanThue>{gdt_code}</MCQuanThue>
        <LSSSot>{err_type}</LSSSot>
        <LDo>{reason}</LDo>
      </HDSSSot>
"""

    xml_content = f"""<TBao xmlns="http://hoadondientu.gdt.gov.vn/schema">
  <DLTBao Id="TB_04SS_{taxpayer_mst}">
    <TTChung>
      <MCQuan>Cục Thuế Thành Phố Hà Nội</MCQuan>
      <TenNNT>{company_name}</TenNNT>
      <MST>{taxpayer_mst}</MST>
      <NLap>{today}</NLap>
      <DDanh>Hà Nội</DDanh>
    </TTChung>
    <NDTBao>
      <DSHDSSSot>
{list_items_xml}      </DSHDSSSot>
    </NDTBao>
  </DLTBao>
</TBao>"""
    return xml_content.encode("utf-8")


# ── US-374: Corporate Tax Optimization & Scenario Modeler Engine ───────

def calculate_corporate_tax_optimization(taxpayer_mst: str, scenarios_config: list[dict]) -> dict:
    """Perform tax forecasts and simulations based on tax configuration scenarios.
    
    Models:
    - Standard CIT rate (20%) vs preferential rates (10%, 15%)
    - Tax holidays (exemption years, reduction years)
    - Interest expense EBITDA cap (30%)
    - Non-deductible expense estimations (e.g. welfare benefits capped at 1-month average salary)
    """
    # 1. Gather historical baseline from DB (if any)
    invoices = Invoice.query.filter(Invoice.taxpayer_mst == taxpayer_mst).all()
    
    # Calculate baseline revenue and COGS
    sales_total = sum(inv.amount_before_tax for inv in invoices if inv.seller_mst == taxpayer_mst)
    purchase_total = sum(inv.amount_before_tax for inv in invoices if inv.buyer_mst == taxpayer_mst)
    
    # Safe fallback if baseline is zero
    if sales_total == 0.0:
        sales_total = 200000000000.0  # 200B VND
    if purchase_total == 0.0:
        purchase_total = 140000000000.0  # 140B VND

    ebitda_baseline = sales_total - purchase_total
    loan_interest_baseline = 15000000000.0  # 15B VND loan interest fallback
    employee_count_baseline = 100
    avg_salary_baseline = 20000000.0 # 20M VND
    total_welfare_w_cash_baseline = 3500000000.0 # 3.5B VND welfare (over limit of 2B VND)
    
    # Calculate non-deductible parts
    ebitda_limit_interest = ebitda_baseline * 0.3
    non_deductible_interest = max(0.0, loan_interest_baseline - ebitda_limit_interest)
    
    welfare_limit = avg_salary_baseline * employee_count_baseline
    non_deductible_welfare = max(0.0, total_welfare_w_cash_baseline - welfare_limit)
    
    # Other non-deductible items: invoices > 20M paid in cash
    non_deductible_cash_invoices = sum(
        inv.amount_before_tax for inv in invoices 
        if inv.buyer_mst == taxpayer_mst and inv.total_amount > 20000000.0 and inv.payment_method == "TM"
    )
    
    total_non_deductible = non_deductible_interest + non_deductible_welfare + non_deductible_cash_invoices
    taxable_income_baseline = ebitda_baseline - loan_interest_baseline + total_non_deductible
    
    baseline_cit = taxable_income_baseline * 0.20
    
    scenarios_results = []
    
    # 2. Simulate scenarios
    for idx, sc in enumerate(scenarios_config, 1):
        name = sc.get("name") or f"Kịch bản {idx}"
        pref_rate = float(sc.get("preferential_rate") or 0.20)
        holiday_exempt_years = int(sc.get("holiday_exempt_years") or 0)
        holiday_reduce_years = int(sc.get("holiday_reduce_years") or 0)
        interest_reduction = sc.get("reduce_loan_interest", False)
        cash_reduction = sc.get("enforce_bank_transfer", False)
        
        # Adjust loan interest if optimization is enabled
        sim_loan_interest = loan_interest_baseline
        if interest_reduction:
            # Re-finance or optimize loan structure to drop below the cap
            sim_loan_interest = min(loan_interest_baseline, ebitda_limit_interest)
            
        # Adjust cash invoices if optimization is enabled
        sim_non_deductible_cash = non_deductible_cash_invoices
        if cash_reduction:
            sim_non_deductible_cash = 0.0
            
        sim_non_deductible = (
            max(0.0, sim_loan_interest - ebitda_limit_interest) + 
            non_deductible_welfare + 
            sim_non_deductible_cash
        )
        
        sim_taxable_income = ebitda_baseline - sim_loan_interest + sim_non_deductible
        
        # Calculate CIT rate factor based on holiday phase
        rate_factor = pref_rate
        holiday_status = "Đang áp dụng thuế suất thường"
        if holiday_exempt_years > 0:
            rate_factor = 0.0
            holiday_status = "Miễn thuế 100%"
        elif holiday_reduce_years > 0:
            rate_factor = pref_rate * 0.5
            holiday_status = "Giảm thuế 50%"
            
        sim_cit = sim_taxable_income * rate_factor
        tax_savings = baseline_cit - sim_cit
        
        scenarios_results.append({
            "scenario_name": name,
            "preferential_rate": pref_rate,
            "holiday_status": holiday_status,
            "taxable_income": sim_taxable_income,
            "cit_liability": sim_cit,
            "tax_savings": tax_savings,
            "interest_cap_breached": sim_loan_interest > ebitda_limit_interest
        })
        
    return {
        "taxpayer_mst": taxpayer_mst,
        "baseline": {
            "revenue": sales_total,
            "cogs": purchase_total,
            "ebitda": ebitda_baseline,
            "loan_interest": loan_interest_baseline,
            "non_deductible_interest": non_deductible_interest,
            "non_deductible_welfare": non_deductible_welfare,
            "non_deductible_cash_invoices": non_deductible_cash_invoices,
            "total_non_deductible": total_non_deductible,
            "taxable_income": taxable_income_baseline,
            "cit_liability": baseline_cit
        },
        "scenarios": scenarios_results,
        "best_scenario": max(scenarios_results, key=lambda x: x["tax_savings"]) if scenarios_results else None
    }
