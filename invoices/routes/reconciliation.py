from __future__ import annotations
from io import BytesIO
from flask import Blueprint, Response, current_app, jsonify, redirect, render_template, request, send_file, session, url_for
from export.excel import generate_excel_workbook, generate_local_excel_workbook
from invoices.parser import DateValidationError, validate_date_range
from invoices.service import (
    GDTIntegrationNotReadyError,
    InvoiceQuery,
    build_invoice_lookup,
    download_invoice_xml,
    fetch_invoices,
    resolve_live_download_name,
    fetch_invoice_line_items,
    extract_partners_from_invoices,
    generate_tax_usage_report,
)
from extensions import db
from auth.decorators import roles_required
import os
import uuid
import threading
from datetime import datetime
from flask import send_file
import io
from invoices.routes.shared import invoices_blueprint, DOWNLOAD_TASKS, DOWNLOAD_TASKS_LOCK
from invoices.routes.helpers import (
    _ensure_logged_in,
    get_supplier_pivot_data,
    _AGING_BUCKETS,
    classify_fct_item,
    generate_fct_excel,
    require_api_signature,
    get_harness_db,
    render_html_to_pdf
)

@invoices_blueprint.post("/api/reconciliation/upload")
@roles_required("admin", "auditor")
def api_reconciliation_upload():
    """Upload bank statement CSV and perform automated reconciliation."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if not file or not file.filename.endswith(".csv"):
        return jsonify({"error": "Only CSV files are supported"}), 400

    try:
        content = file.read().decode("utf-8")
        from invoices.reconciliation_service import ReconciliationEngine
        engine = ReconciliationEngine()
        
        # 1. Parse and save
        transactions = engine.process_csv(content)
        
        # 2. Run matching engine
        results = engine.run_matching()
        
        return jsonify({
            "status": "success",
            "message": "Bank reconciliation completed successfully.",
            "results": results
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@invoices_blueprint.get("/api/reconciliation/results")
@roles_required("admin", "auditor", "viewer")
def api_reconciliation_results():
    """Get all parsed bank transactions and their matched status."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized
        
    from invoices.models import BankTransaction
    txns = BankTransaction.query.order_by(BankTransaction.transaction_date.desc()).all()
    
    return jsonify({
        "status": "success",
        "transactions": [t.to_dict() for t in txns]
    })
