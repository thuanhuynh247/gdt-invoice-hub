"""Central extension repository for SQLAlchemy to prevent circular imports."""

from __future__ import annotations

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine
import sqlite3

from flask_sqlalchemy.session import Session as FlaskSQLAlchemySession

class TenantRoutingSession(FlaskSQLAlchemySession):
    def get_bind(self, mapper=None, clause=None, bind=None, **kwargs):
        if bind is not None:
            return bind

        try:
            from flask import has_request_context, session, current_app
            mst = None
            if has_request_context() and session.get("tax_code"):
                mst = session["tax_code"]
            else:
                from invoices.thread_local import get_current_thread_mst
                mst = get_current_thread_mst()

            if mst:
                sanitized_mst = mst.strip().replace("-", "").replace(" ", "")
                
                # Check cache of engines on the active app context
                if not hasattr(current_app, "_tenant_engines"):
                    current_app._tenant_engines = {}
                
                if sanitized_mst not in current_app._tenant_engines:
                    import os
                    from sqlalchemy import create_engine
                    from invoices.multitenant_service import get_tenant_db_path
                    
                    db_path = get_tenant_db_path(sanitized_mst).replace('\\', '/')
                    engine = create_engine(f"sqlite:///{db_path}")
                    
                    # Always ensure all tables in db.metadata exist in the tenant database
                    self._db.metadata.create_all(bind=engine)
                    
                    db_existed = os.path.exists(db_path) and os.path.getsize(db_path) > 0
                    if not db_existed:
                        from sqlalchemy import text
                        with engine.begin() as conn:
                            conn.execute(text("CREATE TABLE IF NOT EXISTS tenant_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);"))
                            conn.execute(text("INSERT OR REPLACE INTO tenant_meta (key, value) VALUES ('mst', :mst);"), {"mst": sanitized_mst})
                            conn.execute(text("INSERT OR REPLACE INTO tenant_meta (key, value) VALUES ('created_at', :now);"), {"now": "2026-05-29T00:00:00Z"})
                    
                    # Live migration checks for tenant databases
                    from sqlalchemy import text
                    try:
                        with engine.begin() as conn:
                            # 1. Partner table checks
                            res_partner = conn.execute(text("PRAGMA table_info(partner);")).fetchall()
                            if res_partner:
                                cols = [r[1] for r in res_partner]
                                if "decree_132_relationship" not in cols:
                                    conn.execute(text("ALTER TABLE partner ADD COLUMN decree_132_relationship VARCHAR(10) NULL;"))
                            
                            # 2. AI Chat Session table checks
                            res_chat = conn.execute(text("PRAGMA table_info(ai_chat_session);")).fetchall()
                            if res_chat:
                                cols = [r[1] for r in res_chat]
                                if "invoice_id" not in cols:
                                    conn.execute(text("ALTER TABLE ai_chat_session ADD COLUMN invoice_id VARCHAR(100) NULL;"))
                                    
                            # 3. Invoice table checks
                            res_inv = conn.execute(text("PRAGMA table_info(invoice);")).fetchall()
                            if res_inv:
                                cols = [r[1] for r in res_inv]
                                if "ai_audited" not in cols:
                                    conn.execute(text("ALTER TABLE invoice ADD COLUMN ai_audited BOOLEAN DEFAULT 0;"))
                                if "t_score" not in cols:
                                    conn.execute(text("ALTER TABLE invoice ADD COLUMN t_score INTEGER DEFAULT 100;"))
                                if "t_rating" not in cols:
                                    conn.execute(text("ALTER TABLE invoice ADD COLUMN t_rating VARCHAR(10) DEFAULT 'A++';"))
                                if "taxpayer_mst" not in cols:
                                    conn.execute(text("ALTER TABLE invoice ADD COLUMN taxpayer_mst VARCHAR(20) NULL;"))
                                if "amount_in_words" not in cols:
                                    conn.execute(text("ALTER TABLE invoice ADD COLUMN amount_in_words TEXT NULL;"))
                                if "due_date" not in cols:
                                    conn.execute(text("ALTER TABLE invoice ADD COLUMN due_date VARCHAR(20) NULL;"))
                                if "paid_date" not in cols:
                                    conn.execute(text("ALTER TABLE invoice ADD COLUMN paid_date VARCHAR(20) NULL;"))
                                if "signature_details_json" not in cols:
                                    conn.execute(text("ALTER TABLE invoice ADD COLUMN signature_details_json TEXT NULL;"))
                                if "erp_synced" not in cols:
                                    conn.execute(text("ALTER TABLE invoice ADD COLUMN erp_synced BOOLEAN DEFAULT 0;"))
                                if "erp_sync_date" not in cols:
                                    conn.execute(text("ALTER TABLE invoice ADD COLUMN erp_sync_date VARCHAR(50) NULL;"))
                                if "erp_sync_error" not in cols:
                                    conn.execute(text("ALTER TABLE invoice ADD COLUMN erp_sync_error TEXT NULL;"))
                                if "merkle_hash" not in cols:
                                    conn.execute(text("ALTER TABLE invoice ADD COLUMN merkle_hash VARCHAR(64) NULL;"))
                                if "merkle_root" not in cols:
                                    conn.execute(text("ALTER TABLE invoice ADD COLUMN merkle_root VARCHAR(64) NULL;"))
                                if "merkle_index" not in cols:
                                    conn.execute(text("ALTER TABLE invoice ADD COLUMN merkle_index INTEGER NULL;"))
                                    
                            # 4. Line Item table checks
                            res_item = conn.execute(text("PRAGMA table_info(line_item);")).fetchall()
                            if res_item:
                                cols = [r[1] for r in res_item]
                                if "expense_category" not in cols:
                                    conn.execute(text("ALTER TABLE line_item ADD COLUMN expense_category VARCHAR(100) NULL;"))
                                    
                            # 5. Bank Transaction table checks
                            res_bank = conn.execute(text("PRAGMA table_info(bank_transaction);")).fetchall()
                            if res_bank:
                                cols = [r[1] for r in res_bank]
                                if "taxpayer_mst" not in cols:
                                    conn.execute(text("ALTER TABLE bank_transaction ADD COLUMN taxpayer_mst VARCHAR(20) NULL;"))
                                if "bank_name" not in cols:
                                    conn.execute(text("ALTER TABLE bank_transaction ADD COLUMN bank_name VARCHAR(50) NULL;"))
                                if "account_number" not in cols:
                                    conn.execute(text("ALTER TABLE bank_transaction ADD COLUMN account_number VARCHAR(50) NULL;"))
                                if "reference_number" not in cols:
                                    conn.execute(text("ALTER TABLE bank_transaction ADD COLUMN reference_number VARCHAR(100) NULL;"))
                                if "status" not in cols:
                                    conn.execute(text("ALTER TABLE bank_transaction ADD COLUMN status VARCHAR(20) DEFAULT 'unreconciled';"))
                                if "imported_at" not in cols:
                                    conn.execute(text("ALTER TABLE bank_transaction ADD COLUMN imported_at VARCHAR(30) NULL;"))
                    except Exception as ex:
                        try:
                            current_app.logger.warning(f"Tenant database migration failed for {sanitized_mst}: {ex}")
                        except Exception:
                            pass
                    
                    current_app._tenant_engines[sanitized_mst] = engine
                
                return current_app._tenant_engines[sanitized_mst]
        except Exception as e:
            try:
                current_app.logger.warning(f"Tenant database routing failed: {e}")
            except Exception:
                pass

        return super().get_bind(mapper=mapper, clause=clause, bind=bind, **kwargs)


db = SQLAlchemy(session_options={"class_": TenantRoutingSession})


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()

