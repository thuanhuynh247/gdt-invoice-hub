"""Flask entrypoint for the Invoice Download Webapp."""

from __future__ import annotations

import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"

from dotenv import load_dotenv
load_dotenv()

# Force tempfile to use a local temp folder inside the D: drive workspace due to full C: drive
local_temp = os.path.abspath(os.path.join(os.path.dirname(__file__), "data", "temp"))
os.makedirs(local_temp, exist_ok=True)
import tempfile
tempfile.tempdir = local_temp


from flask import Flask, jsonify, redirect, render_template, session, url_for
from auth import auth_blueprint
from invoices import invoices_blueprint
from invoices.smart_invoice_api import smart_invoice_blueprint
from config import Config


def create_app() -> Flask:
    """Create and configure the Flask application instance."""

    app = Flask(__name__)
    app.config.from_object(Config)

    from extensions import db
    db.init_app(app)

    from invoices.sync_queue import ResilientSyncQueue
    ResilientSyncQueue(app)

    with app.app_context():
        import os
        os.makedirs(os.path.join(app.root_path, "data"), exist_ok=True)
        import invoices.models
        db.create_all()
        from invoices.event_streamer import setup_webhook_delivery_bridge
        setup_webhook_delivery_bridge()
        try:
            # Live migration check to add missing columns dynamically
            res = db.session.execute(db.text("PRAGMA table_info(invoice);")).fetchall()
            columns = [r[1] for r in res]
            if "ai_audited" not in columns:
                db.session.execute(db.text("ALTER TABLE invoice ADD COLUMN ai_audited BOOLEAN DEFAULT 0;"))
                db.session.commit()
            if "t_score" not in columns:
                db.session.execute(db.text("ALTER TABLE invoice ADD COLUMN t_score INTEGER DEFAULT 100;"))
                db.session.commit()
            if "t_rating" not in columns:
                db.session.execute(db.text("ALTER TABLE invoice ADD COLUMN t_rating VARCHAR(10) DEFAULT 'A++';"))
                db.session.commit()
            if "taxpayer_mst" not in columns:
                db.session.execute(db.text("ALTER TABLE invoice ADD COLUMN taxpayer_mst VARCHAR(20) NULL;"))
                db.session.commit()
            if "amount_in_words" not in columns:
                db.session.execute(db.text("ALTER TABLE invoice ADD COLUMN amount_in_words TEXT NULL;"))
                db.session.commit()
            if "due_date" not in columns:
                db.session.execute(db.text("ALTER TABLE invoice ADD COLUMN due_date VARCHAR(20) NULL;"))
                db.session.commit()
            if "paid_date" not in columns:
                db.session.execute(db.text("ALTER TABLE invoice ADD COLUMN paid_date VARCHAR(20) NULL;"))
                db.session.commit()
            if "signature_details_json" not in columns:
                db.session.execute(db.text("ALTER TABLE invoice ADD COLUMN signature_details_json TEXT NULL;"))
                db.session.commit()
            if "erp_synced" not in columns:
                db.session.execute(db.text("ALTER TABLE invoice ADD COLUMN erp_synced BOOLEAN DEFAULT 0;"))
                db.session.commit()
            if "erp_sync_date" not in columns:
                db.session.execute(db.text("ALTER TABLE invoice ADD COLUMN erp_sync_date VARCHAR(50) NULL;"))
                db.session.commit()
            if "erp_sync_error" not in columns:
                db.session.execute(db.text("ALTER TABLE invoice ADD COLUMN erp_sync_error TEXT NULL;"))
                db.session.commit()
            if "merkle_hash" not in columns:
                db.session.execute(db.text("ALTER TABLE invoice ADD COLUMN merkle_hash VARCHAR(64) NULL;"))
                db.session.commit()
            if "merkle_root" not in columns:
                db.session.execute(db.text("ALTER TABLE invoice ADD COLUMN merkle_root VARCHAR(64) NULL;"))
                db.session.commit()
            if "merkle_index" not in columns:
                db.session.execute(db.text("ALTER TABLE invoice ADD COLUMN merkle_index INTEGER NULL;"))
                db.session.commit()


            res_item = db.session.execute(db.text("PRAGMA table_info(line_item);")).fetchall()
            columns_item = [r[1] for r in res_item]
            if "expense_category" not in columns_item:
                db.session.execute(db.text("ALTER TABLE line_item ADD COLUMN expense_category VARCHAR(100) NULL;"))
                db.session.commit()

            # Live migration check for bank_transaction table
            res_bank = db.session.execute(db.text("PRAGMA table_info(bank_transaction);")).fetchall()
            if res_bank:
                columns_bank = [r[1] for r in res_bank]
                if "taxpayer_mst" not in columns_bank:
                    db.session.execute(db.text("ALTER TABLE bank_transaction ADD COLUMN taxpayer_mst VARCHAR(20) NULL;"))
                    db.session.commit()
                if "bank_name" not in columns_bank:
                    db.session.execute(db.text("ALTER TABLE bank_transaction ADD COLUMN bank_name VARCHAR(50) NULL;"))
                    db.session.commit()
                if "account_number" not in columns_bank:
                    db.session.execute(db.text("ALTER TABLE bank_transaction ADD COLUMN account_number VARCHAR(50) NULL;"))
                    db.session.commit()
                if "reference_number" not in columns_bank:
                    db.session.execute(db.text("ALTER TABLE bank_transaction ADD COLUMN reference_number VARCHAR(100) NULL;"))
                    db.session.commit()
                if "status" not in columns_bank:
                    db.session.execute(db.text("ALTER TABLE bank_transaction ADD COLUMN status VARCHAR(20) DEFAULT 'unreconciled';"))
                    db.session.commit()
                if "imported_at" not in columns_bank:
                    db.session.execute(db.text("ALTER TABLE bank_transaction ADD COLUMN imported_at VARCHAR(30) NULL;"))
                    db.session.commit()

            # Live migration check for ai_chat_session table
            res_chat = db.session.execute(db.text("PRAGMA table_info(ai_chat_session);")).fetchall()
            if res_chat:
                columns_chat = [r[1] for r in res_chat]
                if "invoice_id" not in columns_chat:
                    db.session.execute(db.text("ALTER TABLE ai_chat_session ADD COLUMN invoice_id VARCHAR(100) NULL;"))
                    db.session.commit()

            # Live migration check for partner table
            res_partner = db.session.execute(db.text("PRAGMA table_info(partner);")).fetchall()
            if res_partner:
                columns_partner = [r[1] for r in res_partner]
                if "decree_132_relationship" not in columns_partner:
                    db.session.execute(db.text("ALTER TABLE partner ADD COLUMN decree_132_relationship VARCHAR(10) NULL;"))
                    db.session.commit()
        except Exception as e:
            app.logger.warning(f"Database migration check failed: {e}")
            db.session.rollback()

        try:
            # Enable WAL mode for SQLite to support concurrent reading and writing
            db.session.execute(db.text("PRAGMA journal_mode=WAL;"))
            db.session.execute(db.text("PRAGMA synchronous=NORMAL;"))
        except Exception:
            pass
        from invoices.service import migrate_legacy_json_to_sqlite, calculate_invoice_t_score
        migrate_legacy_json_to_sqlite()
        try:
            from invoices.models import Invoice
            for inv in Invoice.query.all():
                calculate_invoice_t_score(inv)
            db.session.commit()
        except Exception as e:
            app.logger.warning(f"Failed to recalculate initial T-Scores: {e}")

        try:
            from invoices.models import TenantGroup
            import json
            default_group = TenantGroup.query.filter_by(group_name="Tập đoàn GDT Hub").first()
            if not default_group:
                from invoices.multitenant_service import list_tenant_databases
                tenant_msts = [t["mst"] for t in list_tenant_databases()]
                if not tenant_msts:
                    tenant_msts = ["0101234567", "0102030405", "0208887776", "777888999"]
                
                group = TenantGroup(
                    group_name="Tập đoàn GDT Hub",
                    admin_username="admin",
                    taxpayer_msts=json.dumps(tenant_msts)
                )
                db.session.add(group)
                db.session.commit()
                app.logger.info("Successfully seeded default TenantGroup for admin.")
        except Exception as e:
            app.logger.warning(f"Failed to seed default TenantGroup: {e}")

    app.register_blueprint(auth_blueprint)
    app.register_blueprint(invoices_blueprint)
    app.register_blueprint(smart_invoice_blueprint)

    # Apply cybersecurity hardening headers (CSP, Clickjacking prevention, MIME protection)
    from auth.security import apply_security_headers
    apply_security_headers(app)


    # Initialize background worker threads & sync daemons
    from invoices.workers import init_background_workers
    init_background_workers(app)

    @app.get("/")
    def index():
        """Redirect users to the appropriate landing page."""

        if session.get("logged_in"):
            return redirect(url_for("invoices.invoices_page"))
        return redirect(url_for("auth.login_page"))

    @app.get("/health")
    def health_check():
        """Return a minimal health response for local verification."""

        return jsonify({"status": "ok", "mode": "mock" if app.config["GDT_USE_MOCK"] else "live"})

    @app.errorhandler(404)
    def not_found(_error):
        """Return friendly JSON for unknown API routes or a template for pages."""

        return jsonify({"error": "Khong tim thay tai nguyen."}), 404

    @app.errorhandler(500)
    def server_error(error):
        """Return a safe error message without exposing stack traces."""
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Co loi may chu. Vui long thu lai."}), 500



    @app.context_processor
    def inject_template_state():
        """Expose a small set of state values to all templates."""

        return {
            "logged_in": session.get("logged_in", False),
            "session_username": session.get("display_name") or session.get("username", ""),
        }

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=app.config["DEBUG"])
