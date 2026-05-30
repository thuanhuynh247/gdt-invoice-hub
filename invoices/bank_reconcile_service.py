"""Service layer for US-080/US-081 bank statement ingestion and AI fuzzy matching."""

from __future__ import annotations

import csv
import os
import re
from datetime import datetime
from extensions import db
from invoices.models import Invoice, BankTransaction, TaxpayerProfile

try:
    import openpyxl
except ImportError:
    openpyxl = None


def remove_vietnamese_diacritics(text: str) -> str:
    """Remove Vietnamese tone marks and accents for standard string matching."""
    if not text:
        return ""
    
    # Mapping of accented characters
    diacritics_map = {
        'a': 'áàảãạăắằẳẵặâấầẩẫậ',
        'A': 'ÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬ',
        'd': 'đ',
        'D': 'Đ',
        'e': 'éèẻẽẹêếềểễệ',
        'E': 'ÉÈẺẼẸÊẾỀỂỄỆ',
        'i': 'íìỉĩị',
        'I': 'ÍÌỈĨỊ',
        'o': 'óòỏõọôốồổỗộơớờởỡợ',
        'O': 'ÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢ',
        'u': 'úùủũụưứừửữự',
        'U': 'ÚÙỦŨỤƯỨỪỬỮỰ',
        'y': 'ýỳỷỹỵ',
        'Y': 'ÝỲỶỸỴ'
    }
    
    res = text
    for char, accented_chars in diacritics_map.items():
        for accented_char in accented_chars:
            res = res.replace(accented_char, char)
    return res


def clean_vietnamese_text(text: str) -> str:
    """Normalize text, remove diacritics, and convert to uppercase."""
    no_diacritics = remove_vietnamese_diacritics(text)
    # Remove special characters except alphanumeric and basic spacing
    cleaned = re.sub(r'[^a-zA-Z0-9\s-]', '', no_diacritics)
    return " ".join(cleaned.upper().split())


def clean_company_name_tokens(name: str) -> list[str]:
    """Clean company names and extract significant naming keywords/tokens."""
    cleaned = clean_vietnamese_text(name)
    # Common corporate designations to drop for core matching
    drop_words = {
        "CONG TY", "CO PHAN", "TNHH", "TRACH NHIEM HUU HAN",
        "MTV", "MOT THANH VIEN", "TMDV", "THUONG MAI DICH VU",
        "INVESTMENT", "HOLDINGS", "GROUP", "GLOBAL", "TOAN CAU",
        "VIET NAM", "VIETNAM", "MOCK", "SAMPLE", "TEST"
    }
    
    tokens = cleaned.split()
    core_tokens = [t for t in tokens if t not in drop_words and len(t) > 1]
    
    # Fallback to full cleaned split if all words were dropped
    return core_tokens if core_tokens else [t for t in tokens if len(t) > 1]


def parse_bank_statement(file_path: str, bank_name: str | None = None) -> list[dict]:
    """Parse bank statement spreadsheet (Excel or CSV) and extract transactions."""
    transactions = []
    
    # 1. Parse CSV Format
    if file_path.lower().endswith('.csv'):
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        # Simple dynamic column matching based on header labels
        headers = []
        start_row = 0
        for i, row in enumerate(rows[:10]):
            row_str = [cell.lower() for cell in row]
            if any("ngày" in cell or "date" in cell or "nội dung" in cell or "remark" in cell for cell in row_str):
                headers = row_str
                start_row = i + 1
                break
        
        if not headers and rows:
            headers = [cell.lower() for cell in rows[0]]
            start_row = 1
            
        for i in range(start_row, len(rows)):
            row = rows[i]
            if not row or len(row) < len(headers):
                continue
            
            # Map values dynamically
            tx = _map_row_to_tx_dict(row, headers, bank_name or "Generic")
            if tx:
                transactions.append(tx)
                
    # 2. Parse Excel Format using openpyxl
    elif openpyxl is not None:
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        sheet = wb.active
        
        rows = []
        for r in sheet.iter_rows(values_only=True):
            rows.append(r)
            
        headers = []
        start_row = 0
        for i, row in enumerate(rows[:15]):
            if not row:
                continue
            row_str = [str(cell).lower() if cell is not None else "" for cell in row]
            if any("ngày" in cell or "date" in cell or "nội dung" in cell or "remark" in cell for cell in row_str):
                headers = row_str
                start_row = i + 1
                break
                
        if not headers and rows:
            first_row = rows[0]
            if first_row:
                headers = [str(cell).lower() if cell is not None else "" for cell in first_row]
                start_row = 1
            
        for i in range(start_row, len(rows)):
            row = rows[i]
            if not row or all(cell is None for cell in row):
                continue
            
            row_str = [str(cell) if cell is not None else "" for cell in row]
            tx = _map_row_to_tx_dict(row_str, headers, bank_name or "Generic")
            if tx:
                transactions.append(tx)
                
    else:
        # Fallback to direct raw parsing if openpyxl is missing (should not happen in this env)
        raise ImportError("openpyxl is required to parse Excel statements.")
        
    return transactions


def _map_row_to_tx_dict(row: list[str], headers: list[str], bank: str) -> dict | None:
    """Helper to map a parsed row into a standardized transaction dictionary."""
    # Find matching indexes
    date_idx, desc_idx, amt_idx, ref_idx = -1, -1, -1, -1
    debit_idx, credit_idx = -1, -1
    
    for idx, h in enumerate(headers):
        if not h:
            continue
        if any(k in h for k in ["ngày", "date", "time"]):
            if date_idx == -1:
                date_idx = idx
        elif any(k in h for k in ["nội dung", "mô tả", "description", "remark", "diễn giải"]):
            desc_idx = idx
        elif any(k in h for k in ["số gd", "ref", "mã giao dịch", "mã gd", "chứng từ"]):
            ref_idx = idx
        elif any(k in h for k in ["ghi nợ", "nợ", "debit", "rút"]):
            debit_idx = idx
        elif any(k in h for k in ["ghi có", "có", "credit", "nộp"]):
            credit_idx = idx
        elif any(k in h for k in ["số tiền", "amount", "giá trị"]):
            amt_idx = idx
            
    # Parse transaction date
    tx_date = datetime.now().strftime("%Y-%m-%d")
    if date_idx != -1 and date_idx < len(row) and row[date_idx]:
        raw_date = row[date_idx].strip()
        # Extract YYYY-MM-DD or standard formats
        match = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', raw_date)
        if match:
            tx_date = f"{match.group(1)}-{int(match.group(2)):02d}-{int(match.group(3)):02d}"
        else:
            match_vi = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', raw_date)
            if match_vi:
                tx_date = f"{match_vi.group(3)}-{int(match_vi.group(2)):02d}-{int(match_vi.group(1)):02d}"
                
    # Parse description
    desc = ""
    if desc_idx != -1 and desc_idx < len(row):
        desc = row[desc_idx].strip()
        
    if not desc:
        return None  # Skip rows without descriptions
        
    # Parse unique reference
    ref_num = f"TX-{int(datetime.now().timestamp() * 1000) % 1000000000}"
    if ref_idx != -1 and ref_idx < len(row) and row[ref_idx].strip():
        ref_num = row[ref_idx].strip()
        
    # Calculate amount: Credit/Inflows (positive), Debit/Outflows (negative)
    amount = 0.0
    
    # 1. Separate Debit & Credit columns
    if debit_idx != -1 and debit_idx < len(row) and row[debit_idx].strip():
        try:
            val = float(re.sub(r'[^\d.]', '', row[debit_idx].replace(',', '.')))
            if val > 0:
                amount = -val
        except ValueError:
            pass
            
    if credit_idx != -1 and credit_idx < len(row) and row[credit_idx].strip():
        try:
            val = float(re.sub(r'[^\d.]', '', row[credit_idx].replace(',', '.')))
            if val > 0:
                amount = val
        except ValueError:
            pass
            
    # 2. Single Amount column
    if amount == 0.0 and amt_idx != -1 and amt_idx < len(row) and row[amt_idx].strip():
        try:
            raw_amt = row[amt_idx].replace(',', '')
            # Handle parentheses or negative signs
            is_negative = '-' in raw_amt or '(' in raw_amt
            val = float(re.sub(r'[^\d.]', '', raw_amt))
            amount = -val if is_negative else val
        except ValueError:
            pass
            
    # Skip transactions with zero value
    if amount == 0.0:
        return None
        
    return {
        "id": ref_num,
        "transaction_date": tx_date,
        "reference_number": ref_num,
        "description": desc,
        "amount": amount,
        "bank_name": bank
    }


def find_matching_invoice(tx: BankTransaction) -> tuple[str | None, float]:
    """
    Match a BankTransaction to outstanding invoices using NLP / Phonetic logic.
    Returns: (matched_invoice_id, confidence_score)
    """
    cleaned_desc = clean_vietnamese_text(tx.description)
    
    # Fetch invoices that belong to the active taxpayer MST
    # If the transaction is incoming (amount > 0), match against sales (we collect cash)
    # If transaction is outgoing (amount < 0), match against purchases (we pay supplier)
    invoice_type = "sale" if tx.amount > 0 else "purchase"
    target_amount = abs(tx.amount)
    
    query = Invoice.query.filter(
        Invoice.taxpayer_mst == tx.taxpayer_mst,
        Invoice.invoice_type == invoice_type
    )
    
    open_invoices = query.all()
    if not open_invoices:
        return None, 0.0
        
    best_match_id = None
    best_score = 0.0
    best_reason = ""
    
    for inv in open_invoices:
        score = 0.0
        
        # --- Heuristic 1: Invoice Number Substring Match ---
        # Vietnamese invoice numbers are padded (e.g., '1002' or '0001002'). 
        # Check if invoice number is specified clearly in the remark.
        raw_num = str(inv.number).lstrip('0')
        if raw_num and len(raw_num) >= 2:
            num_patterns = [
                rf"\bHD\s*{raw_num}\b",
                rf"\bHD{raw_num}\b",
                rf"\b{raw_num}\b"
            ]
            for pat in num_patterns:
                if re.search(pat, cleaned_desc):
                    score += 0.60
                    break
                    
        # --- Heuristic 2: Corporate Name Token Match ---
        # Match buyer name for sales, or seller name for purchases
        partner_name = inv.buyer_name if invoice_type == "sale" else inv.seller_name
        if partner_name:
            partner_tokens = clean_company_name_tokens(partner_name)
            matched_tokens = [t for t in partner_tokens if t in cleaned_desc]
            if partner_tokens:
                ratio = len(matched_tokens) / len(partner_tokens)
                score += ratio * 0.30
                
        # --- Heuristic 3: Exact Amount Alignment ---
        # Highly weighted check to prevent false positives
        amount_diff_ratio = abs(inv.total_amount - target_amount) / inv.total_amount
        if amount_diff_ratio < 0.005:  # within 0.5%
            score += 0.40
        elif amount_diff_ratio < 0.02:  # within 2%
            score += 0.20
            
        # Normalize score cap at 1.0
        final_score = min(score, 1.0)
        
        if final_score > best_score:
            best_score = final_score
            best_match_id = inv.id
            
    # We require a threshold score of 0.65 to automatically pair a transaction
    if best_score >= 0.65:
        return best_match_id, best_score
        
    return None, 0.0


def execute_auto_reconciliation(taxpayer_mst: str) -> dict:
    """Run fuzzy matching matching engine on all unreconciled transactions."""
    unreconciled = BankTransaction.query.filter_by(
        taxpayer_mst=taxpayer_mst,
        status="unreconciled"
    ).all()
    
    matches_completed = 0
    results = []
    
    for tx in unreconciled:
        matched_id, score = find_matching_invoice(tx)
        if matched_id:
            tx.matched_invoice_id = matched_id
            tx.confidence_score = score
            tx.status = "matched"
            matches_completed += 1
            
            # Fetch invoice details for return metadata
            inv = Invoice.query.get(matched_id)
            results.append({
                "transaction_id": tx.id,
                "description": tx.description,
                "amount": tx.amount,
                "matched_invoice_id": matched_id,
                "invoice_number": inv.number if inv else "",
                "partner_name": (inv.buyer_name if tx.amount > 0 else inv.seller_name) if inv else "",
                "confidence": f"{int(score * 100)}%"
            })
            
    if matches_completed > 0:
        db.session.commit()
        
    return {
        "status": "success",
        "matches_found": matches_completed,
        "details": results
    }


def check_cash_payment_compliance(taxpayer_mst: str) -> list[dict]:
    """Verify if invoices with value >= 20M VND are paid via cash or lack bank transfer matching (US-203)."""
    # Fetch all invoices >= 20M VND for this taxpayer
    high_value_invoices = Invoice.query.filter(
        Invoice.taxpayer_mst == taxpayer_mst,
        Invoice.total_amount >= 20000000.0
    ).all()
    
    compliance_flags = []
    
    for inv in high_value_invoices:
        # Check if there is a matching BankTransaction in the DB
        matched_tx = BankTransaction.query.filter_by(
            matched_invoice_id=inv.id
        ).first()
        
        payment_method_lower = (inv.payment_method or "").lower()
        is_cash = any(kw in payment_method_lower for kw in ["tm", "tien mat", "cash"])
        
        if is_cash:
            compliance_flags.append({
                "invoice_id": inv.id,
                "invoice_number": inv.number,
                "partner_name": inv.seller_name if inv.invoice_type == "purchase" else inv.buyer_name,
                "total_amount": inv.total_amount,
                "payment_method": inv.payment_method,
                "compliance_status": "non_compliant",
                "message": f"Hoa don so {inv.number} tri gia {inv.total_amount:,.0f} VND ghi phuong thuc thanh toan Tien mat (TM), vi pham quy dinh thanh toan khong dung tien mat tu 20 trieu VND tro len."
            })
        elif not matched_tx:
            compliance_flags.append({
                "invoice_id": inv.id,
                "invoice_number": inv.number,
                "partner_name": inv.seller_name if inv.invoice_type == "purchase" else inv.buyer_name,
                "total_amount": inv.total_amount,
                "payment_method": inv.payment_method or "Chua ro",
                "compliance_status": "pending_verification",
                "message": f"Hoa don so {inv.number} tri gia {inv.total_amount:,.0f} VND chua duoc doi chieu voi giao dich chuyen khoan ngan hang."
            })
            
    return compliance_flags

