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

@invoices_blueprint.post("/api/invoices/vision-upload")
@roles_required("admin", "auditor", "viewer")
def api_vision_upload():
    """Process an uploaded image/pdf using Vision OCR and return structured invoice data."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"error": "Empty file"}), 400

    allowed_exts = [".jpg", ".jpeg", ".png", ".pdf"]
    if not any(file.filename.lower().endswith(ext) for ext in allowed_exts):
        return jsonify({"error": "Only JPG, PNG, and PDF files are supported"}), 400

    try:
        file_bytes = file.read()
        mime_type = file.mimetype or "image/jpeg"
        
        from invoices.vision_service import VisionOCRService
        vision_service = VisionOCRService()
        
        # Call OCR service
        extracted_data = vision_service.extract_invoice_data(file_bytes, file.filename, mime_type)
        
        # In a real scenario we would save this to the database here as a Draft/Pending Invoice.
        # For now, we return it to the frontend to review and save.
        return jsonify({
            "status": "success",
            "message": "OCR Extraction successful (Needs human verification)",
            "data": extracted_data
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
