import os
import json
import pytest
from extensions import db
from invoices.models import Invoice, LineItem, Partner, SystemConfig, SchedulerLog
from invoices.service import migrate_legacy_json_to_sqlite

def test_database_initialization(app):
    """Verify that the database initialization successfully creates all tables and columns."""
    with app.app_context():
        # Check that we can query all models without error
        assert Invoice.query.count() >= 0
        assert LineItem.query.count() >= 0
        assert Partner.query.count() >= 0
        assert SystemConfig.query.count() >= 0
        assert SchedulerLog.query.count() >= 0

def test_wal_mode(app):
    """Verify that SQLite is running in WAL mode."""
    with app.app_context():
        res = db.session.execute(db.text("PRAGMA journal_mode;")).fetchone()
        assert res[0].upper() == "WAL"

def test_auto_migration(app):
    """Verify that legacy invoices_db.json data is auto-migrated to SQLite."""
    legacy_db_file = os.path.join(app.root_path, "data", "invoices_db.json")
    
    # Let's ensure any existing backup is cleaned up first
    if os.path.exists(legacy_db_file + ".bak"):
        try:
            os.remove(legacy_db_file + ".bak")
        except Exception:
            pass

    # Create dummy legacy data
    legacy_data = {
        "invoices": [
            {
                "id": "LEGACY-INV-001",
                "filename": "legacy_invoice.xml",
                "amount_before_tax": 1000.0,
                "tax_amount": 100.0,
                "total_amount": 1100.0,
                "seller_name": "Legacy Seller",
                "seller_mst": "1234567890",
                "items": [
                    {
                        "item_name": "Legacy Item",
                        "quantity": 1.0,
                        "unit_price": 1000.0,
                        "amount_before_tax": 1000.0,
                        "tax_rate": "10%",
                        "tax_amount": 100.0
                    }
                ]
            }
        ],
        "partners": [
            {
                "mst": "1234567890",
                "name": "Legacy Seller",
                "address": "Legacy Address",
                "mst_status": "Đang hoạt động"
            }
        ],
        "settings": {
            "test_config_key": "test_config_value"
        },
        "scheduler_logs": [
            {
                "timestamp": "2026-05-23T00:00:00",
                "status": "SUCCESS",
                "details": "Legacy Log"
            }
        ]
    }
    
    with open(legacy_db_file, "w", encoding="utf-8") as f:
        json.dump(legacy_data, f)
        
    with app.app_context():
        # First clean up the database of any conflicting records
        Invoice.query.filter_by(id="LEGACY-INV-001").delete()
        Partner.query.filter_by(mst="1234567890").delete()
        SystemConfig.query.filter_by(key="test_config_key").delete()
        SchedulerLog.query.filter_by(details="Legacy Log").delete()
        db.session.commit()
        
        # Run migration
        migrate_legacy_json_to_sqlite()
        
        # Verify migrated invoices
        inv = db.session.get(Invoice, "LEGACY-INV-001")
        assert inv is not None
        assert inv.seller_name == "Legacy Seller"
        assert inv.total_amount == 1100.0
        
        # Verify items
        items = LineItem.query.filter_by(invoice_id="LEGACY-INV-001").all()
        assert len(items) == 1
        assert items[0].item_name == "Legacy Item"
        
        # Verify partners
        partner = db.session.get(Partner, "1234567890")
        assert partner is not None
        assert partner.name == "Legacy Seller"
        
        # Verify config
        cfg = db.session.get(SystemConfig, "test_config_key")
        assert cfg is not None
        assert cfg.value == "test_config_value"
        
        # Verify logs
        log = SchedulerLog.query.filter_by(details="Legacy Log").first()
        assert log is not None
        
        # Clean up database records
        db.session.delete(inv)
        db.session.delete(partner)
        db.session.delete(cfg)
        db.session.delete(log)
        db.session.commit()

    # Clean up file
    if os.path.exists(legacy_db_file):
        try:
            os.remove(legacy_db_file)
        except Exception:
            pass
    if os.path.exists(legacy_db_file + ".bak"):
        try:
            os.remove(legacy_db_file + ".bak")
        except Exception:
            pass
