"""Bank Stream Ingestion & Transaction Matching Service using existing schema (US-322, US-323)."""

from __future__ import annotations

import csv
import io
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from extensions import db
from invoices.models import BankTransaction, Invoice, Partner


class BankStreamService:
    """Service to ingest bank feed files and match transactions to invoices using the native BankTransaction schema."""

    @staticmethod
    def parse_iso20022_xml(xml_content: str, taxpayer_mst: str, bank_name: str = "ISO20022") -> list[dict]:
        """Parse ISO 20022 camt.053 standard XML statements."""
        transactions = []
        try:
            root = ET.fromstring(xml_content)
            # Remove namespace prefixes to simplify XPath querying
            for elem in root.iter():
                if '}' in elem.tag:
                    elem.tag = elem.tag.split('}', 1)[1]

            entries = root.findall(".//Ntry")
            for entry in entries:
                amount_node = entry.find("Amt")
                amount = float(amount_node.text) if amount_node is not None else 0.0
                
                cdt_dbt_node = entry.find("CdtDbtInd")
                credit_debit = cdt_dbt_node.text if cdt_dbt_node is not None else "CRDT"
                
                # Debit represents an outflow (negative amount)
                if credit_debit == "DBIT" and amount > 0:
                    amount = -amount

                book_date_node = entry.find("BookgDt/Dt")
                if book_date_node is None:
                    book_date_node = entry.find("BookgDt/DtTm")
                booking_date = book_date_node.text[:10] if book_date_node is not None else datetime.now(timezone.utc).strftime("%Y-%m-%d")

                tx_id_node = entry.find("AcctSvcrRef")
                tx_id = tx_id_node.text if tx_id_node is not None else f"TX-{int(datetime.now().timestamp() * 1000) % 1000000000}"

                # Extract partner details
                partner_name = ""
                partner_account = ""
                ref_code = ""

                entry_details = entry.find("NtryDtls/TxDtls")
                if entry_details is not None:
                    if credit_debit == "CRDT":
                        dbtr_name = entry_details.find("RltdPties/Dbtr/Nm")
                        partner_name = dbtr_name.text if dbtr_name is not None else ""
                        dbtr_acct = entry_details.find("RltdPties/DbtrAcct/Id/Othr/Id")
                        partner_account = dbtr_acct.text if dbtr_acct is not None else ""
                    else:
                        cdtr_name = entry_details.find("RltdPties/Cdtr/Nm")
                        partner_name = cdtr_name.text if cdtr_name is not None else ""
                        cdtr_acct = entry_details.find("RltdPties/CdtrAcct/Id/Othr/Id")
                        partner_account = cdtr_acct.text if cdtr_acct is not None else ""

                    rem_info = entry_details.find("RmtInf/Ustrd")
                    ref_code = rem_info.text if rem_info is not None else ""

                # Build combined description incorporating ref_code and partner name for fuzzy/NLP matching
                combined_desc = f"{ref_code} | Đối tác: {partner_name}".strip(" | ")

                transactions.append({
                    "id": tx_id,
                    "taxpayer_mst": taxpayer_mst,
                    "bank_name": bank_name,
                    "account_number": partner_account,
                    "transaction_date": booking_date,
                    "reference_number": tx_id,
                    "description": combined_desc if combined_desc else "No description",
                    "amount": amount,
                })
        except Exception as e:
            raise ValueError(f"Failed to parse ISO 20022 XML statement: {str(e)}")

        return transactions

    @staticmethod
    def parse_vietnamese_bank_csv(csv_content: str, taxpayer_mst: str, bank_name: str) -> list[dict]:
        """Parse custom CSV structures for Vietcombank and Techcombank statement reports."""
        transactions = []
        f = io.StringIO(csv_content.strip())
        reader = csv.reader(f)

        for row in reader:
            if not row or len(row) < 5:
                continue
            if "ngày" in row[0].lower() or "amount" in "".join(row).lower() or "số tiền" in "".join(row).lower():
                continue

            try:
                if bank_name.upper() == "VIETCOMBANK":
                    # Expected: Date, TxID, Amount, CreditDebit, PartnerAccount, PartnerName, RefCode
                    booking_date = row[0].strip()
                    tx_id = row[1].strip()
                    amount = float(re.sub(r"[^\d.]", "", row[2].strip()))
                    credit_debit = "CRDT" if row[3].strip().upper() in ("C", "CRDT", "RECEIVE", "IN") else "DBIT"
                    if credit_debit == "DBIT":
                        amount = -amount
                    partner_account = row[4].strip() if len(row) > 4 else ""
                    partner_name = row[5].strip() if len(row) > 5 else ""
                    ref_code = row[6].strip() if len(row) > 6 else ""
                else:  # TECHCOMBANK
                    booking_date = row[0].strip()
                    ref_code = row[1].strip()
                    amount = float(re.sub(r"[^\d.]", "", row[2].strip()))
                    credit_debit = "CRDT" if row[3].strip().upper() in ("C", "CRDT", "IN") else "DBIT"
                    if credit_debit == "DBIT":
                        amount = -amount
                    partner_name = row[4].strip() if len(row) > 4 else ""
                    partner_account = ""
                    tx_id = ref_code

                combined_desc = f"{ref_code} | Đối tác: {partner_name}".strip(" | ")

                transactions.append({
                    "id": tx_id if tx_id else f"TX-{int(datetime.now().timestamp() * 1000) % 1000000000}",
                    "taxpayer_mst": taxpayer_mst,
                    "bank_name": bank_name,
                    "account_number": partner_account,
                    "transaction_date": booking_date,
                    "reference_number": tx_id,
                    "description": combined_desc if combined_desc else "No description",
                    "amount": amount,
                })
            except Exception:
                continue

        return transactions

    def ingest_bank_statement(self, file_content: str, taxpayer_mst: str, bank_name: str, file_type: str) -> int:
        """Ingest transactions from file content and save to SQLite db."""
        if file_type.lower() == "xml":
            raw_txs = self.parse_iso20022_xml(file_content, taxpayer_mst, bank_name)
        else:
            raw_txs = self.parse_vietnamese_bank_csv(file_content, taxpayer_mst, bank_name)

        inserted_count = 0
        for tx in raw_txs:
            exists = BankTransaction.query.filter_by(
                id=tx["id"]
            ).first() is not None

            if not exists:
                bt = BankTransaction(
                    id=tx["id"],
                    taxpayer_mst=tx["taxpayer_mst"],
                    bank_name=tx["bank_name"],
                    account_number=tx["account_number"],
                    transaction_date=tx["transaction_date"],
                    reference_number=tx["reference_number"],
                    description=tx["description"],
                    amount=tx["amount"],
                    status="unreconciled",
                    confidence_score=0.0,
                    imported_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                )
                db.session.add(bt)
                inserted_count += 1

        db.session.commit()
        return inserted_count

    def execute_transaction_matching(self, taxpayer_mst: str) -> dict:
        """Execute the automated matching algorithm on all unmatched bank transactions (US-323)."""
        unmatched_txs = BankTransaction.query.filter_by(
            taxpayer_mst=taxpayer_mst,
            status="unreconciled"
        ).all()

        matched_count = 0
        warnings_raised = 0
        details = []

        # Fetch active partners
        partners = Partner.query.all()
        partner_map = {p.name.lower(): p.mst for p in partners if p.name}

        for tx in unmatched_txs:
            # 1. Resolve partner MST from description or metadata
            resolved_mst = None
            desc_lower = tx.description.lower()
            for name_key, mst_val in partner_map.items():
                if name_key in desc_lower:
                    resolved_mst = mst_val
                    break

            # 2. Extract digits (invoice number candidate) from description
            invoice_num_candidate = None
            numbers = re.findall(r"\d+", tx.description)
            invoices = []
            if numbers:
                for num in numbers:
                    invs = Invoice.query.filter(
                        (Invoice.taxpayer_mst == taxpayer_mst) &
                        ((Invoice.id == num) | (Invoice.number == num))
                    ).all()
                    invoices.extend(invs)

            if not invoices and resolved_mst:
                invoices = Invoice.query.filter(
                    (Invoice.taxpayer_mst == taxpayer_mst) &
                    ((Invoice.seller_mst == resolved_mst) | (Invoice.buyer_mst == resolved_mst))
                ).all()

            # 3. Match logic
            best_match = None
            best_status = "unreconciled"
            best_notes = ""
            best_score = 0.0

            for inv in invoices:
                # Direction matches: CRDT (>0) matches sales (buyer is taxpayer), DBIT (<0) matches purchases (seller is taxpayer)
                # Note: target amount comparison is absolute values
                target_amount = abs(tx.amount)
                amount_diff_ratio = abs(target_amount - inv.total_amount) / (inv.total_amount or 1.0)
                amount_match = amount_diff_ratio <= 0.001

                # Reference match
                ref_match = False
                if str(inv.number) in tx.description or str(inv.id) in tx.description:
                    ref_match = True

                mst_match = (inv.seller_mst == resolved_mst or inv.buyer_mst == resolved_mst)

                if (ref_match or mst_match) and amount_match:
                    best_match = inv
                    best_status = "matched"
                    best_score = 1.0
                    best_notes = "Khớp chính xác"
                    break
                elif (ref_match or mst_match) and not amount_match:
                    best_match = inv
                    best_status = "matched"  # Reconciled but with partial status flag
                    best_score = 0.7
                    best_notes = "Khớp bán phần (Lệch số tiền)"
                    warnings_raised += 1

            if best_match:
                tx.matched_invoice_id = best_match.id
                tx.status = "matched"
                tx.confidence_score = best_score
                matched_count += 1
                details.append({
                    "transaction_id": tx.id,
                    "description": tx.description,
                    "amount": tx.amount,
                    "matched_invoice_id": best_match.id,
                    "notes": best_notes,
                    "confidence": f"{int(best_score * 100)}%"
                })
            else:
                # Raise warning for high-value transactions >= 20M without match
                if abs(tx.amount) >= 20000000.0:
                    warnings_raised += 1
                    details.append({
                        "transaction_id": tx.id,
                        "description": tx.description,
                        "amount": tx.amount,
                        "matched_invoice_id": None,
                        "notes": "CẢNH BÁO: Giao dịch trên 20 triệu VND không khớp với hóa đơn.",
                        "confidence": "0%"
                    })

        db.session.commit()

        return {
            "success": True,
            "unmatched_processed": len(unmatched_txs),
            "matched_count": matched_count,
            "warnings_raised": warnings_raised,
            "details": details
        }
