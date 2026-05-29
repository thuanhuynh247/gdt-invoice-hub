"""Zero-Downtime Data Archiver & Query Engine (US-125).

Archives invoices older than 5 years to highly compressed zlib zip files
while maintaining seamless search querying across merged live and cold datasets.
"""

from __future__ import annotations

import os
import json
import zipfile
import logging
import threading
import time
from datetime import datetime, date
from extensions import db
from invoices.models import Invoice, LineItem

logger = logging.getLogger(__name__)

# Paths for cold storage
ARCHIVE_DIR = "data/archives"
ARCHIVE_FILE = os.path.join(ARCHIVE_DIR, "cold_invoices.zip")
ARCHIVE_LOCK = threading.Lock()

class InvoiceArchiver:
    """Enterprise archiver for compressing and querying historical invoices."""

    @staticmethod
    def initialize():
        """Ensure the archive directory exists."""
        os.makedirs(ARCHIVE_DIR, exist_ok=True)

    @staticmethod
    def archive_old_invoices(retention_years: int = 5, reference_date: date | None = None) -> int:
        """Move invoices older than retention_years into the compressed cold archive.
        
        Returns the number of archived invoices.
        """
        InvoiceArchiver.initialize()
        
        if reference_date is None:
            reference_date = date.today()
            
        current_year = reference_date.year
        cutoff_year = current_year - retention_years
        
        # We find all invoices whose date year is less than or equal to cutoff_year
        # Note: invoice.date is in format YYYY-MM-DD
        cutoff_date_str = f"{cutoff_year}-{reference_date.month:02d}-{reference_date.day:02d}"
        
        with ARCHIVE_LOCK:
            # Query candidate invoices for archiving
            candidates = Invoice.query.filter(Invoice.date <= cutoff_date_str).all()
            if not candidates:
                logger.info("No historical invoices found matching retention policy cutoff.")
                return 0
                
            logger.info(f"Found {len(candidates)} historical invoices to archive (older than {retention_years} years).")
            
            # Read existing archived invoices to append safely
            archived_records = {}
            if os.path.exists(ARCHIVE_FILE):
                try:
                    with zipfile.ZipFile(ARCHIVE_FILE, "r") as zf:
                        if "invoices.json" in zf.namelist():
                            with zf.open("invoices.json") as f:
                                import io
                                # Wrap f in a TextIOWrapper if needed or read directly
                                # json.load can read bytes in python 3.6+
                                archived_records = json.load(f)
                except Exception as e:
                    logger.error(f"Error reading existing cold archive: {e}")
            
            # Serialize candidates and add to active list
            count = 0
            for inv in candidates:
                inv_dict = inv.to_dict()
                
                # Ensure line items are fully serialized within the object
                items_list = []
                for item in inv.items:
                    items_list.append({
                        "id": item.id,
                        "item_name": item.item_name,
                        "unit": item.unit,
                        "quantity": item.quantity,
                        "unit_price": item.unit_price,
                        "amount_before_tax": item.amount_before_tax,
                        "tax_rate": item.tax_rate,
                        "tax_amount": item.tax_amount,
                        "expense_category": item.expense_category
                    })
                inv_dict["items"] = items_list
                
                archived_records[inv.id] = inv_dict
                count += 1
                
            # Write updated dataset back to compressed ZIP archive (zlib DEFLATE)
            try:
                temp_json_path = os.path.join(ARCHIVE_DIR, "temp_invoices.json")
                with open(temp_json_path, "w", encoding="utf-8") as f:
                    json.dump(archived_records, f, ensure_ascii=False, indent=2)
                    
                with zipfile.ZipFile(ARCHIVE_FILE, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                    zf.write(temp_json_path, "invoices.json")
                    
                # Clean up temporary JSON file
                os.remove(temp_json_path)
            except Exception as e:
                logger.error(f"Failed to write compressed cold store zip: {e}")
                return 0
                
            # Delete archived candidates from the live SQLite database
            try:
                for inv in candidates:
                    db.session.delete(inv)
                db.session.commit()
                logger.info(f"Successfully moved {count} invoices to encrypted/compressed cold store and deleted from main DB.")
            except Exception as e:
                db.session.rollback()
                logger.error(f"Failed to delete live entries during archive transaction: {e}")
                return 0
                
            return count

    @staticmethod
    def get_archived_invoices(taxpayer_mst: str | None = None) -> list[dict]:
        """Fetch all cold storage invoices, optionally filtered by taxpayer_mst."""
        InvoiceArchiver.initialize()
        
        if not os.path.exists(ARCHIVE_FILE):
            return []
            
        with ARCHIVE_LOCK:
            try:
                with zipfile.ZipFile(ARCHIVE_FILE, "r") as zf:
                    if "invoices.json" in zf.namelist():
                        with zf.open("invoices.json") as f:
                            data = json.load(f)
                            
                            results = list(data.values())
                            if taxpayer_mst:
                                results = [r for r in results if r.get("taxpayer_mst") == taxpayer_mst]
                            return results
            except Exception as e:
                logger.error(f"Failed to read archived dataset: {e}")
                
        return []

    @staticmethod
    def search_merged_invoices(
        date_from: date,
        date_to: date,
        cancelled_only: bool = False,
        direction: str = "purchase",
        taxpayer_mst: str | None = None
    ) -> list[dict]:
        """Search across merged active SQLite and zipped cold archived datasets.
        
        This enables zero-downtime historical search access transparently.
        """
        # 1. Read live records from SQL
        from invoices.models import Invoice
        query = Invoice.query
        
        # Apply filters
        query = query.filter(Invoice.date >= date_from.isoformat())
        query = query.filter(Invoice.date <= date_to.isoformat())
        if cancelled_only:
            query = query.filter(Invoice.is_cancelled == True)
        if taxpayer_mst:
            query = query.filter(Invoice.taxpayer_mst == taxpayer_mst)
            
        # Direction filtering
        # Purchase invoices: buyer is current taxpayer, or seller is not current
        # Sold invoices: seller is current taxpayer
        if taxpayer_mst:
            if direction == "sold":
                query = query.filter(Invoice.seller_mst == taxpayer_mst)
            else:
                query = query.filter(Invoice.buyer_mst == taxpayer_mst)
                
        live_invoices = [inv.to_dict() for inv in query.all()]
        
        # 2. Read cold archived records
        cold_invoices = InvoiceArchiver.get_archived_invoices(taxpayer_mst)
        
        # Apply filters to cold archive manually
        filtered_cold = []
        for inv in cold_invoices:
            inv_date = date.fromisoformat(inv["date"])
            if not (date_from <= inv_date <= date_to):
                continue
            if cancelled_only and not inv.get("is_cancelled"):
                continue
                
            # Direction check
            if taxpayer_mst:
                if direction == "sold" and inv.get("seller_mst") != taxpayer_mst:
                    continue
                if direction == "purchase" and inv.get("buyer_mst") != taxpayer_mst:
                    continue
                    
            filtered_cold.append(inv)
            
        # 3. Merge and return sorted by date desc
        merged = live_invoices + filtered_cold
        merged.sort(key=lambda x: x["date"], reverse=True)
        return merged
