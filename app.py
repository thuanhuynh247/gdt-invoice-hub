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
from config import Config


def create_app() -> Flask:
    """Create and configure the Flask application instance."""

    app = Flask(__name__)
    app.config.from_object(Config)

    from extensions import db
    db.init_app(app)

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

    app.register_blueprint(auth_blueprint)
    app.register_blueprint(invoices_blueprint)

    # Apply cybersecurity hardening headers (CSP, Clickjacking prevention, MIME protection)
    from auth.security import apply_security_headers
    apply_security_headers(app)


    if not app.config.get("TESTING") and os.getenv("TESTING") != "True":
        from auth.captcha import start_captcha_prefetch_worker
        start_captcha_prefetch_worker(app)

        from invoices.scheduler import start_scheduler_worker
        start_scheduler_worker(app)

        from invoices.ai_service import start_dynamic_pdf_ingestion_thread
        start_dynamic_pdf_ingestion_thread(app)

        from invoices.sync_daemon import GDTSyncDaemon
        # Start the sync daemon with a fast 1-minute interval for demo purposes
        daemon = GDTSyncDaemon(app, interval_minutes=1)
        daemon.start()
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
    def server_error(_error):
        """Return a safe error message without exposing stack traces."""
    
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
