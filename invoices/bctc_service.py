"""Statutory Financial Statements (BCTC) Scaffolder (US-200, US-201).

Implements account mappings under Circular 200/2014/TT-BTC,
equation integrity validation, and HTKK compatible XML output generation.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime, timezone
import openpyxl
from io import BytesIO
from extensions import db
from invoices.models import Invoice

def parse_ledger_file(file_bytes: bytes, filename: str) -> dict[str, dict]:
    """Parse General Ledger / Trial Balance Excel or CSV file.
    
    Returns a dictionary of account balances:
    {
        "111": {
            "opening_debit": float, "opening_credit": float,
            "debit_movement": float, "credit_movement": float,
            "closing_debit": float, "closing_credit": float
        }
    }
    """
    balances = {}
    
    if filename.lower().endswith(('.xlsx', '.xls')):
        wb = openpyxl.load_workbook(BytesIO(file_bytes), data_only=True)
        ws = wb.active
        
        # Read rows, locate columns dynamically based on header patterns
        # Typically: Tài khoản (Account), Số dư đầu kỳ (Opening), Phát sinh trong kỳ (Movement), Số dư cuối kỳ (Closing)
        rows = list(ws.iter_rows(values_only=True))
        account_idx = -1
        op_dr_idx = -1
        op_cr_idx = -1
        mov_dr_idx = -1
        mov_cr_idx = -1
        cl_dr_idx = -1
        cl_cr_idx = -1
        
        for i, row in enumerate(rows[:20]):
            if not row:
                continue
            row_str = [str(c).lower() if c is not None else "" for c in row]
            
            # Simple keyword search
            for idx, c in enumerate(row_str):
                if any(kw in c for kw in ["số hiệu tk", "mã tk", "tài khoản", "account"]):
                    if account_idx == -1:
                        account_idx = idx
                elif any(kw in c for kw in ["nợ đầu kỳ", "dư nợ đầu", "opening debit", "đầu kỳ nợ"]):
                    op_dr_idx = idx
                elif any(kw in c for kw in ["có đầu kỳ", "dư có đầu", "opening credit", "đầu kỳ có"]):
                    op_cr_idx = idx
                elif any(kw in c for kw in ["nợ phát sinh", "phát sinh nợ", "debit movement"]):
                    mov_dr_idx = idx
                elif any(kw in c for kw in ["có phát sinh", "phát sinh có", "credit movement"]):
                    mov_cr_idx = idx
                elif any(kw in c for kw in ["nợ cuối kỳ", "dư nợ cuối", "closing debit", "cuối kỳ nợ"]):
                    cl_dr_idx = idx
                elif any(kw in c for kw in ["có cuối kỳ", "dư có cuối", "closing credit", "cuối kỳ có"]):
                    cl_cr_idx = idx
            
            if account_idx != -1 and (cl_dr_idx != -1 or op_dr_idx != -1):
                # Found header row
                start_row = i + 1
                break
        else:
            # Fallback defaults
            account_idx = 0
            op_dr_idx = 1
            op_cr_idx = 2
            mov_dr_idx = 3
            mov_cr_idx = 4
            cl_dr_idx = 5
            cl_cr_idx = 6
            start_row = 1
            
        for r_idx in range(start_row, len(rows)):
            row = rows[r_idx]
            if not row or account_idx >= len(row):
                continue
            acc_val = str(row[account_idx]).strip()
            # Clean account code to numbers only
            acc_clean = re.sub(r'[^\d]', '', acc_val)
            if not acc_clean or len(acc_clean) < 3:
                continue
                
            def get_float(val):
                if val is None or str(val).strip() == "":
                    return 0.0
                try:
                    return float(str(val).replace(',', '').replace(' ', ''))
                except ValueError:
                    return 0.0
            
            balances[acc_clean] = {
                "opening_debit": get_float(row[op_dr_idx]) if op_dr_idx < len(row) else 0.0,
                "opening_credit": get_float(row[op_cr_idx]) if op_cr_idx < len(row) else 0.0,
                "debit_movement": get_float(row[mov_dr_idx]) if mov_dr_idx < len(row) else 0.0,
                "credit_movement": get_float(row[mov_cr_idx]) if mov_cr_idx < len(row) else 0.0,
                "closing_debit": get_float(row[cl_dr_idx]) if cl_dr_idx < len(row) else 0.0,
                "closing_credit": get_float(row[cl_cr_idx]) if cl_cr_idx < len(row) else 0.0,
            }
            
    return balances

def compile_bctc(balances: dict[str, dict], metadata: dict) -> tuple[str, list[str]]:
    """Compile BCTC B01-DN, B02-DN, and B03-DN from parsed account balances.
    
    Returns:
        (xml_output_string, warnings_list)
    """
    warnings = []
    
    # 1. Map Balance Sheet fields (B01-DN)
    # Cash & cash equivalents (Mã số 110)
    cash_debit = 0.0
    for acc in ["111", "112"]:
        for k in balances:
            if k.startswith(acc):
                cash_debit += balances[acc]["closing_debit"] - balances[acc]["closing_credit"]
    
    # Short-term receivables (Mã số 131)
    receivables_net = 0.0
    for k in balances:
        if k.startswith("131"):
            receivables_net += balances[k]["closing_debit"] - balances[k]["closing_credit"]
            
    # Short-term trade payables (Mã số 311)
    payables_net = 0.0
    for k in balances:
        if k.startswith("331"):
            payables_net += balances[k]["closing_credit"] - balances[k]["closing_debit"]
            
    # Taxes and obligations to state budget (Mã số 313)
    taxes_net = 0.0
    for k in balances:
        if k.startswith("333"):
            taxes_net += balances[k]["closing_credit"] - balances[k]["closing_debit"]
            
    # Undistributed earnings (Mã số 421)
    undist_earnings_opening = 0.0
    undist_earnings_closing = 0.0
    for k in balances:
        if k.startswith("421"):
            undist_earnings_opening += balances[k]["opening_credit"] - balances[k]["opening_debit"]
            undist_earnings_closing += balances[k]["closing_credit"] - balances[k]["closing_debit"]

    # Calculate Assets & Liabilities
    # Standard asset accounts start with 1 or 2
    total_assets = 0.0
    for k, v in balances.items():
        if k.startswith(('1', '2')):
            # Special case: 214 (Accumulated Depreciation) is a credit balance that reduces assets
            if k.startswith('214'):
                total_assets -= (v["closing_credit"] - v["closing_debit"])
            else:
                total_assets += (v["closing_debit"] - v["closing_credit"])
                
    # Standard liability/equity accounts start with 3 or 4
    total_equity_liabilities = 0.0
    for k, v in balances.items():
        if k.startswith(('3', '4')):
            total_equity_liabilities += (v["closing_credit"] - v["closing_debit"])
            
    # 2. Map Income Statement (B02-DN)
    revenue_511 = 0.0
    cogs_632 = 0.0
    financial_rev_515 = 0.0
    financial_exp_635 = 0.0
    selling_exp_641 = 0.0
    admin_exp_642 = 0.0
    other_rev_711 = 0.0
    other_exp_811 = 0.0
    cit_exp_821 = 0.0
    
    for k, v in balances.items():
        # Movements of income statement accounts are closed to 911 at year-end,
        # so we look at debit_movement or credit_movement to get the actual period figures.
        if k.startswith("511"):
            revenue_511 += v["credit_movement"] - v["debit_movement"]
        elif k.startswith("632"):
            cogs_632 += v["debit_movement"] - v["credit_movement"]
        elif k.startswith("515"):
            financial_rev_515 += v["credit_movement"] - v["debit_movement"]
        elif k.startswith("635"):
            financial_exp_635 += v["debit_movement"] - v["credit_movement"]
        elif k.startswith("641"):
            selling_exp_641 += v["debit_movement"] - v["credit_movement"]
        elif k.startswith("642"):
            admin_exp_642 += v["debit_movement"] - v["credit_movement"]
        elif k.startswith("711"):
            other_rev_711 += v["credit_movement"] - v["debit_movement"]
        elif k.startswith("811"):
            other_exp_811 += v["debit_movement"] - v["credit_movement"]
        elif k.startswith("821"):
            cit_exp_821 += v["debit_movement"] - v["credit_movement"]

    # Calculate Net Profit
    operating_profit = (revenue_511 - cogs_632) + financial_rev_515 - financial_exp_635 - selling_exp_641 - admin_exp_642
    other_profit = other_rev_711 - other_exp_811
    pretax_profit = operating_profit + other_profit
    net_profit = pretax_profit - cit_exp_821

    # 3. Map Cash Flow (B03-DN) Direct Method
    # For a simple mock Cash Flow statement, we use Cash inflows / outflows from GL cash accounts movements:
    cash_inflows = 0.0
    cash_outflows = 0.0
    for acc in ["111", "112"]:
        for k, v in balances.items():
            if k.startswith(acc):
                cash_inflows += v["debit_movement"]
                cash_outflows += v["credit_movement"]
                
    cf_net = cash_inflows - cash_outflows

    # 4. Run Financial Integrity Checks
    # Equation 1: Assets == Liabilities + Equity
    diff_assets_liabilities = abs(total_assets - total_equity_liabilities)
    if diff_assets_liabilities > 10.0:  # Allow small floating point rounding error <= 10 VND
        warnings.append(
            f"Mất cân đối Bảng cân đối kế toán: Tổng Tài sản ({total_assets:,.0f} VND) "
            f"khác Tổng Nguồn vốn ({total_equity_liabilities:,.0f} VND). Chênh lệch: {diff_assets_liabilities:,.0f} VND."
        )
        
    # Equation 2: Net Profit After Tax (Mã số 60) must match change in Undistributed Earnings (Mã số 421)
    dividends_paid = metadata.get("dividends_paid", 0.0)
    expected_change = net_profit - dividends_paid
    actual_change = undist_earnings_closing - undist_earnings_opening
    diff_earnings = abs(actual_change - expected_change)
    if diff_earnings > 10.0:
        warnings.append(
            f"Sai lệch Lợi nhuận chưa phân phối: Lợi nhuận sau thuế trên Báo cáo kết quả hoạt động kinh doanh ({net_profit:,.0f} VND) "
            f"không khớp với thay đổi Lợi nhuận chưa phân phối trên Bảng cân đối kế toán ({actual_change:,.0f} VND). "
            f"Chênh lệch: {diff_earnings:,.0f} VND."
        )

    # 5. Build HTKK XML Structure
    root = ET.Element("HSoKhaiThue")
    
    header = ET.SubElement(root, "Header")
    ET.SubElement(header, "MaMST").text = metadata.get("mst", "0000000000")
    ET.SubElement(header, "TenNNT").text = metadata.get("company_name", "CONG TY TNHH MOCK")
    
    ky_tinh_thue = ET.SubElement(header, "KyTinhThue")
    ET.SubElement(ky_tinh_thue, "LoaiKy").text = metadata.get("reporting_period_type", "N")
    ET.SubElement(ky_tinh_thue, "Nam").text = str(metadata.get("year", datetime.now().year))
    
    ET.SubElement(header, "MauBCTC").text = "B01-DN"
    
    body = ET.SubElement(root, "Body")
    
    # Balance Sheet
    b01 = ET.SubElement(body, "BangCanDoiKeToan")
    # Add standardized Balance Sheet fields
    ET.SubElement(b01, "TienVaTuongDuongTien", {"MaSo": "110"}).text = f"{cash_debit:.0f}"
    ET.SubElement(b01, "PhaiThuKhachHangNganHan", {"MaSo": "131"}).text = f"{receivables_net:.0f}"
    ET.SubElement(b01, "TongCongTaiSan", {"MaSo": "270"}).text = f"{total_assets:.0f}"
    ET.SubElement(b01, "PhaiTraNguoiBanNganHan", {"MaSo": "311"}).text = f"{payables_net:.0f}"
    ET.SubElement(b01, "ThueVaCacKhoanPhaiNopNhaNuoc", {"MaSo": "313"}).text = f"{taxes_net:.0f}"
    ET.SubElement(b01, "LoiNhuanChuaPhanPhoi", {"MaSo": "421"}).text = f"{undist_earnings_closing:.0f}"
    ET.SubElement(b01, "TongCongNguonVon", {"MaSo": "440"}).text = f"{total_equity_liabilities:.0f}"
    
    # Income Statement
    b02 = ET.SubElement(body, "BaoCaoKetQuaKinhDoanh")
    ET.SubElement(b02, "DoanhThuBanHang", {"MaSo": "01"}).text = f"{revenue_511:.0f}"
    ET.SubElement(b02, "GiaVonHangBan", {"MaSo": "11"}).text = f"{cogs_632:.0f}"
    ET.SubElement(b02, "DoanhThuTaiChinh", {"MaSo": "21"}).text = f"{financial_rev_515:.0f}"
    ET.SubElement(b02, "ChiPhiTaiChinh", {"MaSo": "22"}).text = f"{financial_exp_635:.0f}"
    ET.SubElement(b02, "ChiPhiBanHang", {"MaSo": "25"}).text = f"{selling_exp_641:.0f}"
    ET.SubElement(b02, "ChiPhiQuanLyDoanhNghiep", {"MaSo": "26"}).text = f"{admin_exp_642:.0f}"
    ET.SubElement(b02, "LoiNhuanThuan", {"MaSo": "30"}).text = f"{operating_profit:.0f}"
    ET.SubElement(b02, "ThuNhapKhac", {"MaSo": "40"}).text = f"{other_rev_711:.0f}"
    ET.SubElement(b02, "ChiPhiKhac", {"MaSo": "45"}).text = f"{other_exp_811:.0f}"
    ET.SubElement(b02, "LoiNhuanTruocThue", {"MaSo": "50"}).text = f"{pretax_profit:.0f}"
    ET.SubElement(b02, "ChiPhiThueTNDNHienHanh", {"MaSo": "51"}).text = f"{cit_exp_821:.0f}"
    ET.SubElement(b02, "LoiNhuanSauThue", {"MaSo": "60"}).text = f"{net_profit:.0f}"
    
    # Cash Flow Statement
    b03 = ET.SubElement(body, "BaoCaoLuuchuyenTienTe")
    ET.SubElement(b03, "TienThuBanHang", {"MaSo": "01"}).text = f"{cash_inflows:.0f}"
    ET.SubElement(b03, "TienChiTraNhaCungCap", {"MaSo": "02"}).text = f"{cash_outflows:.0f}"
    ET.SubElement(b03, "LuuChuyenTienThuanTuHDKD", {"MaSo": "20"}).text = f"{cf_net:.0f}"
    ET.SubElement(b03, "LuuChuyenTienThuanTrongKy", {"MaSo": "50"}).text = f"{cf_net:.0f}"
    
    # Generate pretty printed XML
    raw_xml = ET.tostring(root, encoding="utf-8")
    parsed = minidom.parseString(raw_xml)
    xml_str = parsed.toprettyxml(indent="  ")
    
    return xml_str, warnings

def audit_ledger_against_invoices(balances: dict[str, dict], taxpayer_mst: str, date_window_days: int = 30) -> dict:
    """US-201: Cross-reference General Ledger entries with e-invoices in the database.
    
    Finds:
      - missing_invoices: Transactions in ledger that have no matching XML invoice
      - missing_entries: XML invoices in database that have no matching ledger entry
      - value_mismatches: Mapped entries where amount/tax values differ.
    """
    # Fetch all invoices for active taxpayer
    invoices = Invoice.query.filter_by(taxpayer_mst=taxpayer_mst).all()
    
    missing_invoices = []
    missing_entries = []
    value_mismatches = []
    
    # To simplify ledger audit comparison, we assume the caller uploaded the ledger entries
    # or that we can generate ledger transactions from the balances mapping.
    # In a full production system, we'd receive a list of transactions.
    # Let's mock the audit integrity checker by cross-checking invoice totals against the general ledger.
    # We will generate a matching report.
    
    # Let's inspect invoices first. For each invoice in DB, check if ledger has matching amount.
    matched_invoice_ids = set()
    
    # Standard ledger accounts mapping:
    # Purchase invoices (where buyer_mst == taxpayer_mst) should correspond to debit of 152,156,642 and credit of 331/111/112.
    # Sales invoices (where seller_mst == taxpayer_mst) correspond to credit of 511 and debit of 131/111/112.
    
    # Let's run a heuristic check:
    for inv in invoices:
        # Search for a match in ledger balances
        found_match = False
        amount_match = False
        
        # Check if the invoice total corresponds to any account movements
        target_amt = inv.total_amount
        
        # Let's check ledger accounts that relate to the transaction type
        accounts_to_check = []
        if inv.invoice_type == "purchase":
            # Credited 331, or debited 156/642
            accounts_to_check = ["331", "156", "642", "111", "112"]
        else:
            # Debited 131, or credited 511
            accounts_to_check = ["131", "511", "111", "112"]
            
        for acc in accounts_to_check:
            for k, v in balances.items():
                if k.startswith(acc):
                    # Check if movement matches the invoice amount (within tolerance)
                    movement = max(v["debit_movement"], v["credit_movement"])
                    if abs(movement - target_amt) < 10.0:  # rounding tolerance 10 VND
                        found_match = True
                        amount_match = True
                        matched_invoice_ids.add(inv.id)
                        break
                    elif abs(movement - target_amt) / target_amt < 0.05:  # within 5%
                        # Possible value mismatch
                        value_mismatches.append({
                            "invoice_id": inv.id,
                            "invoice_number": inv.number,
                            "invoice_amount": inv.total_amount,
                            "ledger_account": k,
                            "ledger_amount": movement,
                            "severity": "medium",
                            "message": f"Chênh lệch số liệu: Hóa đơn {inv.number} có tổng tiền {inv.total_amount:,.0f} VND, sổ cái TK {k} ghi nhận {movement:,.0f} VND."
                        })
                        found_match = True
                        matched_invoice_ids.add(inv.id)
                        break
            if found_match:
                break
                
        if not found_match:
            # No ledger entry found for this invoice
            missing_entries.append({
                "invoice_id": inv.id,
                "invoice_number": inv.number,
                "partner_name": inv.seller_name if inv.invoice_type == "purchase" else inv.buyer_name,
                "amount": inv.total_amount,
                "date": inv.date,
                "severity": "high",
                "message": f"Thiếu bút toán sổ cái: Hóa đơn số {inv.number} của {inv.seller_name if inv.invoice_type == 'purchase' else inv.buyer_name} ({inv.total_amount:,.0f} VND) chưa được ghi nhận trên sổ cái."
            })
            
    # Now check for ledger transactions that have no matching invoice
    # For every account with significant movement, if the movement doesn't match any invoice:
    for k, v in balances.items():
        # Look for purchase or sales accounts
        if k.startswith(('156', '642', '511', '131', '331')):
            movement = max(v["debit_movement"], v["credit_movement"])
            if movement > 0:
                # Find if any invoice matches this movement
                inv_match = False
                for inv in invoices:
                    if abs(inv.total_amount - movement) < 10.0:
                        inv_match = True
                        break
                if not inv_match:
                    missing_invoices.append({
                        "ledger_account": k,
                        "amount": movement,
                        "severity": "high",
                        "message": f"Thiếu hóa đơn XML: Sổ cái tài khoản {k} ghi nhận phát sinh {movement:,.0f} VND nhưng không tìm thấy hóa đơn XML tương ứng trên hệ thống GDT."
                    })
                    
    return {
        "status": "success" if not (missing_invoices or missing_entries or value_mismatches) else "flagged",
        "missing_invoices": missing_invoices,
        "missing_entries": missing_entries,
        "value_mismatches": value_mismatches,
        "compliance_score": max(0, 100 - 15 * len(missing_invoices) - 10 * len(missing_entries) - 5 * len(value_mismatches))
    }
