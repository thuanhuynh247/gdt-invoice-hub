import csv
import io
import uuid
import difflib
from datetime import datetime
from typing import List, Dict

from extensions import db
from invoices.models import Invoice, BankTransaction, AIAuditResult

class ReconciliationEngine:
    """Engine to process bank statements and match them to invoices."""

    def process_csv(self, file_content: str) -> List[Dict]:
        """Parses CSV content and stores initial transactions."""
        # Simple CSV format assumed: date, description, amount
        reader = csv.reader(io.StringIO(file_content))
        
        transactions = []
        for i, row in enumerate(reader):
            if i == 0 and ("date" in row[0].lower() or "ngày" in row[0].lower()):
                continue # Skip header
                
            if len(row) < 3:
                continue
                
            try:
                date_str = row[0].strip()
                desc = row[1].strip()
                amt = float(row[2].replace(",", "").strip())
                
                txn = BankTransaction(
                    id=str(uuid.uuid4()),
                    transaction_date=date_str,
                    description=desc,
                    amount=amt,
                    bank_name="Generic",
                    imported_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
                db.session.add(txn)
                transactions.append(txn)
            except Exception:
                pass
                
        db.session.commit()
        return [t.to_dict() for t in transactions]

    def run_matching(self) -> Dict:
        """Matches un-matched transactions against outstanding invoices over 20M."""
        
        unmatched_txns = BankTransaction.query.filter_by(matched_invoice_id=None).all()
        # Find all purchase invoices > 20M that are not yet matched
        high_value_invoices = Invoice.query.filter(
            Invoice.invoice_type == "purchase",
            Invoice.total_amount >= 20000000
        ).all()
        
        matched_count = 0
        
        for inv in high_value_invoices:
            # Check if this invoice is already matched
            existing_match = BankTransaction.query.filter_by(matched_invoice_id=inv.id).first()
            if existing_match:
                continue
                
            best_match = None
            best_score = 0.0
            
            for txn in unmatched_txns:
                if txn.matched_invoice_id:
                    continue
                    
                # Rule 1: Exact amount match
                if abs(txn.amount - inv.total_amount) < 1.0:
                    score = 0.5
                    
                    # Rule 2: Description fuzzy matching with Invoice Number or Seller Name
                    desc_lower = txn.description.lower()
                    if inv.number and inv.number.lower() in desc_lower:
                        score += 0.3
                        
                    if inv.seller_name:
                        # Simple Levenshtein distance check or keyword match
                        seller_words = set(inv.seller_name.lower().split())
                        desc_words = set(desc_lower.split())
                        overlap = len(seller_words.intersection(desc_words))
                        if overlap > 0:
                            score += min(0.2, overlap * 0.05)
                            
                    if score > best_score and score >= 0.5:
                        best_score = score
                        best_match = txn
                        
            if best_match:
                best_match.matched_invoice_id = inv.id
                best_match.confidence_score = best_score
                db.session.add(best_match)
                matched_count += 1
                
        db.session.commit()
        
        # Identify invoices over 20M without matches
        flagged_count = 0
        for inv in high_value_invoices:
            match = BankTransaction.query.filter_by(matched_invoice_id=inv.id).first()
            if not match:
                # Flag as cash payment risk
                warning = AIAuditResult.query.filter_by(
                    invoice_id=inv.id, 
                    warning_type="cash_payment_risk"
                ).first()
                
                if not warning:
                    w = AIAuditResult(
                        invoice_id=inv.id,
                        warning_type="cash_payment_risk",
                        explanation="Hóa đơn trên 20 triệu chưa thấy giao dịch chuyển khoản đối chiếu.",
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
