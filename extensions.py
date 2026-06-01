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

