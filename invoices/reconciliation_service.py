import csv
import io
import uuid
from datetime import datetime
from typing import List, Dict

from extensions import db
from invoices.models import Invoice, BankTransaction, AIAuditResult

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
        
        # Find all purchase invoices that are not yet matched
        purchase_invoices = Invoice.query.filter(
            Invoice.taxpayer_mst == taxpayer_mst,
            Invoice.invoice_type == "purchase"
        ).all()
        
        matched_count = 0
        
        # Helper to parse date
        def parse_date(d_str):
            if not d_str:
                return None
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"):
                try:
                    return datetime.strptime(d_str.strip()[:10], fmt)
                except ValueError:
                    continue
            return None

        for inv in purchase_invoices:
            # Check if this invoice is already matched
            existing_match = BankTransaction.query.filter_by(matched_invoice_id=inv.id).first()
            if existing_match:
                continue
                
            best_match = None
            best_score = 0.0
            
            inv_date = parse_date(inv.date)
            
            for txn in unmatched_txns:
                if txn.matched_invoice_id:
                    continue
                    
                score = 0.0
                
                # Rule 1: Amount match
                diff_amount = abs(txn.amount - inv.total_amount)
                if diff_amount < 1.0:
                    score += 0.5
                elif diff_amount < 100.0:
                    score += 0.4
                    
                # Rule 2: Date proximity check (Vietnamese invoice date vs transfer date)
                txn_date = parse_date(txn.transaction_date)
                if inv_date and txn_date:
                    days_diff = abs((txn_date - inv_date).days)
                    if days_diff <= 3:
                        score += 0.2
                    elif days_diff <= 15:
                        score += 0.1
                
                # Rule 3: Seller MST / Seller Name fuzzy matching
                desc_lower = txn.description.lower()
                if inv.seller_mst and inv.seller_mst in txn.description:
                    score += 0.3
                    
                if inv.number and inv.number.lower() in desc_lower:
                    score += 0.2
                    
                if inv.seller_name:
                    seller_name_clean = inv.seller_name.lower().replace("công ty", "").replace("tnhh", "").strip()
                    if seller_name_clean and seller_name_clean in desc_lower:
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
                
        db.session.commit()
        
        # Identify purchase invoices over 20M without bank transfer matches
        flagged_count = 0
        high_value_invoices = [inv for inv in purchase_invoices if inv.total_amount >= 20000000]
        
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
