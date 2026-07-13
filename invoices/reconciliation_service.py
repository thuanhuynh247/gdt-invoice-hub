import csv
import io
import uuid
import difflib
from datetime import datetime
from typing import List, Dict

from extensions import db
from invoices.models import Invoice, BankTransaction, AIAuditResult

def remove_accents(s: str) -> str:
    if not s:
        return ""
    accents_map = {
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
    char_map = {}
    for k, v in accents_map.items():
        for char in v:
            char_map[char] = k
    return "".join(char_map.get(c, c) for c in s)

def clean_text(text: str) -> str:
    if not text:
        return ""
    text = remove_accents(text.lower())
    suffixes = [
        "công ty", "cong ty", "tnhh", "cổ phần", "co phan", "cp", 
        "một thành viên", "1 thành viên", "1 tv", "mtv", "group", "jsc",
        "trách nhiệm hữu hạn", "trach nhiem huu han"
    ]
    for s in suffixes:
        text = text.replace(s, "")
    # Remove non-alphanumeric chars but keep spaces
    text = "".join(c if c.isalnum() or c.isspace() else " " for c in text)
    return " ".join(text.split())


def calculate_fuzzy_score(name1: str, name2: str) -> float:
    c1 = clean_text(name1)
    c2 = clean_text(name2)
    if not c1 or not c2:
        return 0.0
    tokens1 = set(c1.split())
    tokens2 = set(c2.split())
    if not tokens1 or not tokens2:
        return 0.0
    intersection = tokens1.intersection(tokens2)
    intersection_ratio = len(intersection) / max(len(tokens1), len(tokens2))
    seq_ratio = difflib.SequenceMatcher(None, c1, c2).ratio()
    return 0.4 * intersection_ratio + 0.6 * seq_ratio

class ReconciliationEngine:
    """Engine to process bank statements and match them to invoices."""

    def process_csv(self, file_content: str, taxpayer_mst: str) -> List[Dict]:
        """Parses CSV content and stores initial transactions for a taxpayer."""
        reader = csv.reader(io.StringIO(file_content))
        
        transactions = []
        for i, row in enumerate(reader):
            if i == 0 and any(h in row[0].lower() for h in ("date", "ngày", "time")):
                continue # Skip header
                
            if len(row) < 3:
                continue
                
            try:
                date_str = row[0].strip()
                desc = row[1].strip()
                amt = float(row[2].replace(",", "").strip())
                
                txn = BankTransaction(
                    id=str(uuid.uuid4()),
                    taxpayer_mst=taxpayer_mst,
                    transaction_date=date_str,
                    description=desc,
                    amount=amt,
                    bank_name="Imported",
                    status="unreconciled",
                    imported_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
                db.session.add(txn)
                transactions.append(txn)
            except Exception:
                pass
                
        db.session.commit()
        return [t.to_dict() for t in transactions]

    def run_matching(self, taxpayer_mst: str) -> Dict:
        """Matches un-matched transactions against outstanding invoices for a specific taxpayer."""
        
        unmatched_txns = BankTransaction.query.filter_by(
            taxpayer_mst=taxpayer_mst,
            matched_invoice_id=None
        ).all()
        
        # Find all purchase invoices
        purchase_invoices = Invoice.query.filter(
            Invoice.taxpayer_mst == taxpayer_mst,
            Invoice.invoice_type == "purchase"
        ).all()
        
        # Helper to parse date
        def parse_date(d_str):
            if not d_str:
                return None
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y", "%Y-%m-%dT%H:%M:%S"):
                try:
                    return datetime.strptime(d_str.strip()[:10], fmt)
                except ValueError:
                    continue
            return None

        # Build list of currently matched invoice IDs
        matched_invoice_ids = {
            t.matched_invoice_id for t in BankTransaction.query.filter(
                BankTransaction.taxpayer_mst == taxpayer_mst,
                BankTransaction.matched_invoice_id != None
            ).all()
        }
        
        unmatched_invoices = [
            inv for inv in purchase_invoices if inv.id not in matched_invoice_ids
        ]
        
        matched_count = 0

        # --- PASS 1: Exact / Best 1-to-1 Matching ---
        # For each unmatched invoice, find the best matching unmatched transaction
        for inv in list(unmatched_invoices):
            inv_date = parse_date(inv.date)
            best_match = None
            best_score = 0.0
            
            for txn in unmatched_txns:
                if txn.matched_invoice_id:
                    continue
                    
                score = 0.0
                
                # Rule 1: Amount match (within 1 VND)
                diff_amount = abs(txn.amount - inv.total_amount)
                if diff_amount < 1.0:
                    score += 0.5
                elif diff_amount < 100.0:
                    score += 0.4
                    
                # Rule 2: Date proximity check
                txn_date = parse_date(txn.transaction_date)
                if inv_date and txn_date:
                    days_diff = abs((txn_date - inv_date).days)
                    if days_diff <= 3:
                        score += 0.2
                    elif days_diff <= 15:
                        score += 0.1
                
                # Rule 3: Seller MST / Seller Name fuzzy matching
                desc_lower = txn.description.lower()
                if inv.seller_mst and inv.seller_mst in desc_lower:
                    score += 0.3
                    
                if inv.number and inv.number.lower() in desc_lower:
                    score += 0.2
                    
                if inv.seller_name:
                    fuzzy_score = calculate_fuzzy_score(inv.seller_name, txn.description)
                    if fuzzy_score > 0.6:
                        score += 0.2
                    elif fuzzy_score > 0.3:
                        score += 0.1
                        
                # Match threshold
                if score > best_score and score >= 0.5:
                    best_score = score
                    best_match = txn
                    
            if best_match:
                best_match.matched_invoice_id = inv.id
                best_match.confidence_score = best_score
                best_match.status = "matched"
                db.session.add(best_match)
                matched_count += 1
                unmatched_invoices.remove(inv)

        # --- PASS 2: Many-to-1 Matching (Multiple Transactions -> One Invoice) ---
        # Find a combination of 2 or 3 unmatched transactions that sum exactly to the invoice amount
        for inv in list(unmatched_invoices):
            inv_date = parse_date(inv.date)
            candidates = []
            for t in unmatched_txns:
                if t.matched_invoice_id:
                    continue
                t_date = parse_date(t.transaction_date)
                if inv_date and t_date:
                    days_diff = (t_date - inv_date).days
                    if -5 <= days_diff <= 45:
                        candidates.append(t)
            
            found_combination = None
            n_cand = len(candidates)
            for i in range(n_cand):
                if found_combination:
                    break
                for j in range(i + 1, n_cand):
                    t1, t2 = candidates[i], candidates[j]
                    if abs((t1.amount + t2.amount) - inv.total_amount) < 2.0:
                        desc_text = (t1.description + " " + t2.description).lower()
                        has_ref = (
                            (inv.number and inv.number.lower() in desc_text) or
                            (inv.seller_mst and inv.seller_mst in desc_text) or
                            (inv.seller_name and calculate_fuzzy_score(inv.seller_name, desc_text) > 0.4)
                        )
                        if has_ref:
                            found_combination = [t1, t2]
                            break
            
            if not found_combination:
                for i in range(n_cand):
                    if found_combination:
                        break
                    for j in range(i + 1, n_cand):
                        if found_combination:
                            break
                        for k in range(j + 1, n_cand):
                            t1, t2, t3 = candidates[i], candidates[j], candidates[k]
                            if abs((t1.amount + t2.amount + t3.amount) - inv.total_amount) < 2.0:
                                desc_text = (t1.description + " " + t2.description + " " + t3.description).lower()
                                has_ref = (
                                    (inv.number and inv.number.lower() in desc_text) or
                                    (inv.seller_mst and inv.seller_mst in desc_text) or
                                    (inv.seller_name and calculate_fuzzy_score(inv.seller_name, desc_text) > 0.4)
                                )
                                if has_ref:
                                    found_combination = [t1, t2, t3]
                                    break
            
            if found_combination:
                for t in found_combination:
                    t.matched_invoice_id = inv.id
                    t.confidence_score = 0.75
                    t.status = "matched"
                    db.session.add(t)
                    matched_count += 1
                unmatched_invoices.remove(inv)

        # --- PASS 3: 1-to-Many Matching (One Transaction -> Multiple Invoices) ---
        # Find a combination of unmatched invoices that sum exactly to a single unmatched transaction
        invoices_by_seller = {}
        for inv in unmatched_invoices:
            seller = inv.seller_mst or inv.seller_name
            if seller:
                invoices_by_seller.setdefault(seller, []).append(inv)

        for txn in unmatched_txns:
            if txn.matched_invoice_id:
                continue
            
            found_split = None
            for seller, invs in invoices_by_seller.items():
                if found_split:
                    break
                if len(invs) < 2:
                    continue
                
                n_invs = len(invs)
                for i in range(n_invs):
                    if found_split:
                        break
                    for j in range(i + 1, n_invs):
                        i1, i2 = invs[i], invs[j]
                        if abs((i1.total_amount + i2.total_amount) - txn.amount) < 2.0:
                            txn_d = parse_date(txn.transaction_date)
                            i1_d = parse_date(i1.date)
                            i2_d = parse_date(i2.date)
                            if txn_d and i1_d and i2_d:
                                diff1 = (txn_d - i1_d).days
                                diff2 = (txn_d - i2_d).days
                                if -15 <= diff1 <= 60 and -15 <= diff2 <= 60:
                                    found_split = [i1, i2]
                                    break
                
                if not found_split:
                    for i in range(n_invs):
                        if found_split:
                            break
                        for j in range(i + 1, n_invs):
                            if found_split:
                                break
                            for k in range(j + 1, n_invs):
                                i1, i2, i3 = invs[i], invs[j], invs[k]
                                if abs((i1.total_amount + i2.total_amount + i3.total_amount) - txn.amount) < 2.0:
                                    txn_d = parse_date(txn.transaction_date)
                                    i1_d = parse_date(i1.date)
                                    i2_d = parse_date(i2.date)
                                    i3_d = parse_date(i3.date)
                                    if txn_d and i1_d and i2_d and i3_d:
                                        diff1 = (txn_d - i1_d).days
                                        diff2 = (txn_d - i2_d).days
                                        diff3 = (txn_d - i3_d).days
                                        if -15 <= diff1 <= 60 and -15 <= diff2 <= 60 and -15 <= diff3 <= 60:
                                            found_split = [i1, i2, i3]
                                            break


            if found_split:
                # Split the transaction
                first_inv = found_split[0]
                txn.amount = first_inv.total_amount
                txn.matched_invoice_id = first_inv.id
                txn.confidence_score = 0.8
                txn.status = "matched"
                db.session.add(txn)
                matched_count += 1
                
                for other_inv in found_split[1:]:
                    new_txn = BankTransaction(
                        id=str(uuid.uuid4()),
                        taxpayer_mst=txn.taxpayer_mst,
                        bank_name=txn.bank_name,
                        account_number=txn.account_number,
                        transaction_date=txn.transaction_date,
                        reference_number=txn.reference_number,
                        description=f"{txn.description} (Tách đối chiếu)",
                        amount=other_inv.total_amount,
                        status="matched",
                        matched_invoice_id=other_inv.id,
                        confidence_score=0.8,
                        imported_at=txn.imported_at
                    )
                    db.session.add(new_txn)
                    matched_count += 1
                
                for inv in found_split:
                    if inv in unmatched_invoices:
                        unmatched_invoices.remove(inv)
                    seller = inv.seller_mst or inv.seller_name
                    if seller in invoices_by_seller and inv in invoices_by_seller[seller]:
                        invoices_by_seller[seller].remove(inv)

        db.session.commit()
        
        # Identify purchase invoices over 20M without bank transfer matches
        flagged_count = 0
        high_value_invoices = [inv for inv in purchase_invoices if inv.total_amount >= 20000000]
        
        for inv in high_value_invoices:
            match = BankTransaction.query.filter_by(matched_invoice_id=inv.id).first()
            if not match:
                warning = AIAuditResult.query.filter_by(
                    invoice_id=inv.id, 
                    warning_type="cash_payment_risk"
                ).first()
                
                if not warning:
                    w = AIAuditResult(
                        invoice_id=inv.id,
                        warning_type="cash_payment_risk",
                        explanation="Hóa đơn mua vào trên 20 triệu đồng không phát hiện giao dịch chuyển khoản đối chiếu phù hợp (Rủi ro không được khấu trừ VAT & chi phí hợp lý).",
                        created_at=datetime.now().isoformat()
                    )
                    db.session.add(w)
                    flagged_count += 1
                    
        db.session.commit()
        
        return {
            "transactions_processed": len(unmatched_txns),
            "matches_found": matched_count,
            "invoices_flagged_risk": flagged_count
        }

