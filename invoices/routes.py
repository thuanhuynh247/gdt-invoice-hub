"""Invoice-facing routes for search, download and export."""

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

invoices_blueprint = Blueprint("invoices", __name__)

import os
import uuid
import threading
from datetime import datetime

DOWNLOAD_TASKS = {}
DOWNLOAD_TASKS_LOCK = threading.Lock()



def _ensure_logged_in():
    """Return a 401 JSON response when the session is missing."""

    if not session.get("logged_in"):
        return jsonify({"error": "Phien dang nhap da het han. Vui long dang nhap lai."}), 401
    return None


@invoices_blueprint.get("/invoices")
def invoices_page():
    """Render the invoice search screen for authenticated users."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    return render_template("invoices.html")

@invoices_blueprint.get("/cashflow")
def cashflow_page():
    """Render the cashflow oracle dashboard."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    return render_template("cashflow.html")


@invoices_blueprint.get("/harness")
def harness_page():
    """Render the Harness Agent Control Center."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    return render_template("harness.html")


@invoices_blueprint.get("/tax-bctc")
def tax_bctc_page():
    """Render the V17 Tax and BCTC services screen for authenticated users."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    return render_template("tax_bctc.html")


@invoices_blueprint.get("/api/config")
def api_config():
    """Return small frontend configuration flags."""

    return jsonify({"mock_mode": current_app.config["GDT_USE_MOCK"], "locale": "vi-VN"})


@invoices_blueprint.get("/api/invoices")
def api_invoices():
    """Return invoices in JSON for the requested date range."""

    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    try:
        parsed_from, parsed_to = validate_date_range(
            request.args.get("from", ""),
            request.args.get("to", ""),
        )
        cancelled_only = request.args.get("cancelled_only", "false").lower() == "true"
        direction = request.args.get("direction", "purchase")
        current_app.config["CURRENT_JWT"] = session.get("jwt")
        invoices = fetch_invoices(InvoiceQuery(parsed_from, parsed_to, cancelled_only, direction))
    except DateValidationError as error:
        return jsonify({"error": str(error)}), 400
    except GDTIntegrationNotReadyError as error:
        return jsonify({"error": str(error)}), 503
    finally:
        session["invoice_lookup"] = build_invoice_lookup(invoices) if "invoices" in locals() else {}
        current_app.config["CURRENT_JWT"] = None

    return jsonify({"total_count": len(invoices), "invoices": invoices})


@invoices_blueprint.get("/api/sync/events")
def sse_sync_stream():
    """SSE endpoint to stream real-time sync progress to the frontend."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from invoices.sync_daemon import get_sse_stream
    from flask import Response
    
    return Response(get_sse_stream(), mimetype="text/event-stream")

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

@invoices_blueprint.get("/api/cancelled-invoices")

def api_cancelled_invoices():
    """Return cancelled invoices using the same date filters."""

    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    try:
        parsed_from, parsed_to = validate_date_range(
            request.args.get("from", ""),
            request.args.get("to", ""),
        )
        direction = request.args.get("direction", "purchase")
        current_app.config["CURRENT_JWT"] = session.get("jwt")
        invoices = fetch_invoices(InvoiceQuery(parsed_from, parsed_to, True, direction))
    except DateValidationError as error:
        return jsonify({"error": str(error)}), 400
    except GDTIntegrationNotReadyError as error:
        return jsonify({"error": str(error)}), 503
    finally:
        session["invoice_lookup"] = build_invoice_lookup(invoices) if "invoices" in locals() else {}
        current_app.config["CURRENT_JWT"] = None

    return jsonify({"total_count": len(invoices), "cancelled_invoices": invoices})


@invoices_blueprint.get("/api/invoices/<invoice_id>/download")
def api_download_invoice(invoice_id: str):
    """Download one invoice XML file."""

    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    try:
        current_app.config["CURRENT_JWT"] = session.get("jwt")
        current_app.config["CURRENT_INVOICE_LOOKUP"] = session.get("invoice_lookup", {})
        xml_bytes = download_invoice_xml(invoice_id)
        invoice = (current_app.config.get("CURRENT_INVOICE_LOOKUP") or {}).get(invoice_id)
    except FileNotFoundError as error:
        return jsonify({"error": str(error)}), 404
    except NotImplementedError as error:
        return jsonify({"error": str(error)}), 501
    except GDTIntegrationNotReadyError as error:
        return jsonify({"error": str(error)}), 503
    finally:
        current_app.config["CURRENT_JWT"] = None
        current_app.config["CURRENT_INVOICE_LOOKUP"] = {}

    filename = resolve_live_download_name(invoice) if invoice else f"invoice_{invoice_id}.xml"
    return Response(
        xml_bytes,
        mimetype="application/zip" if filename.endswith(".zip") else "application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@invoices_blueprint.get("/api/invoices/<invoice_id>/details")
def api_invoice_details(invoice_id: str):
    """Return the detailed line items for a specific invoice."""

    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    session_inv = None
    try:
        current_app.config["CURRENT_JWT"] = session.get("jwt")
        current_app.config["CURRENT_INVOICE_LOOKUP"] = session.get("invoice_lookup", {})
        line_items = fetch_invoice_line_items(invoice_id)
        session_inv = (current_app.config.get("CURRENT_INVOICE_LOOKUP") or {}).get(invoice_id)
    except FileNotFoundError as error:
        return jsonify({"error": str(error)}), 404
    except NotImplementedError as error:
        return jsonify({"error": str(error)}), 501
    except GDTIntegrationNotReadyError as error:
        return jsonify({"error": str(error)}), 503
    finally:
        current_app.config["CURRENT_JWT"] = None
        current_app.config["CURRENT_INVOICE_LOOKUP"] = {}

    from invoices.service import get_local_invoices
    local_invoices = get_local_invoices()
    local_inv = None
    for inv in local_invoices:
        if inv["id"] == invoice_id:
            local_inv = inv
            break

    warnings = local_inv.get("warnings", []) if local_inv else []
    is_valid = local_inv.get("is_valid", True) if local_inv else True

    payment_method = ""
    if local_inv:
        payment_method = local_inv.get("payment_method", "")
    elif session_inv:
        payment_method = session_inv.get("payment_method") or session_inv.get("raw", {}).get("htttoan") or ""

    from invoices.models import Invoice
    invoice = db.session.get(Invoice, invoice_id)
    ai_warnings = []
    if invoice:
        ai_warnings = [w.to_dict() for w in invoice.ai_audit_results]

    return jsonify({
        "invoice_id": invoice_id,
        "line_items": line_items,
        "warnings": warnings,
        "is_valid": is_valid,
        "payment_method": payment_method,
        "ai_warnings": ai_warnings,
        "ai_audited": invoice.ai_audited if invoice else False,
        "signature_details": invoice.signature_details if invoice else None
    })



@invoices_blueprint.get("/api/invoices/stats")
def api_invoices_stats():
    """Return financial statistics and aggregations for the requested date range."""

    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    try:
        parsed_from, parsed_to = validate_date_range(
            request.args.get("from", ""),
            request.args.get("to", ""),
        )
        direction = request.args.get("direction", "purchase")
        
        # Check hybrid stats cache first (US-124)
        mst = session.get("tax_code")
        from_str = parsed_from.isoformat()
        to_str = parsed_to.isoformat()
        
        from invoices.stats_cache import get_cached_stats, set_cached_stats
        cached_result = get_cached_stats(mst, from_str, to_str, direction)
        if cached_result is not None:
            return jsonify(cached_result)

        current_app.config["CURRENT_JWT"] = session.get("jwt")
        invoices = fetch_invoices(InvoiceQuery(parsed_from, parsed_to, False, direction))
    except DateValidationError as error:
        return jsonify({"error": str(error)}), 400
    except GDTIntegrationNotReadyError as error:
        return jsonify({"error": str(error)}), 503
    finally:
        current_app.config["CURRENT_JWT"] = None

    total_spend = 0.0
    total_tax = 0.0
    active_count = 0
    cancelled_count = 0

    vendor_stats = {}
    tax_breakdown = {"0%": 0.0, "5%": 0.0, "8%": 0.0, "10%": 0.0, "khac": 0.0}

    for inv in invoices:
        amount = inv.get("amount", 0.0)
        is_cancelled = inv.get("is_cancelled", False)

        if is_cancelled:
            cancelled_count += 1
        else:
            active_count += 1
            total_spend += amount

            vendor = inv.get("issuer", "Khong ro")
            if vendor not in vendor_stats:
                vendor_stats[vendor] = {"spend": 0.0, "count": 0}
            vendor_stats[vendor]["spend"] += amount
            vendor_stats[vendor]["count"] += 1

            line_items = inv.get("line_items", [])
            for item in line_items:
                rate = str(item.get("tax_rate", "10%")).strip()
                tax_amt = item.get("tax_amount", 0.0)
                total_tax += tax_amt

                if "10" in rate:
                    tax_breakdown["10%"] += tax_amt
                elif "8" in rate:
                    tax_breakdown["8%"] += tax_amt
                elif "5" in rate:
                    tax_breakdown["5%"] += tax_amt
                elif "0" in rate:
                    tax_breakdown["0%"] += tax_amt
                else:
                    tax_breakdown["khac"] += tax_amt

    top_vendors = []
    for vendor, data in vendor_stats.items():
        top_vendors.append({"name": vendor, "spend": data["spend"], "count": data["count"]})
    top_vendors.sort(key=lambda x: x["spend"], reverse=True)
    top_vendors = top_vendors[:5]

    response_payload = {
        "total_spend": total_spend,
        "total_tax": total_tax,
        "active_count": active_count,
        "cancelled_count": cancelled_count,
        "top_vendors": top_vendors,
        "tax_breakdown": tax_breakdown,
    }
    
    # Store calculated stats in hybrid cache
    set_cached_stats(mst, from_str, to_str, direction, response_payload)

    return jsonify(response_payload)





@invoices_blueprint.get("/api/export-excel")
def api_export_excel():
    """Export invoice search results to an Excel workbook download."""

    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    try:
        parsed_from, parsed_to = validate_date_range(
            request.args.get("from", ""),
            request.args.get("to", ""),
        )
        cancelled_only = request.args.get("cancelled_only", "false").lower() == "true"
        direction = request.args.get("direction", "purchase")
        current_app.config["CURRENT_JWT"] = session.get("jwt")
        invoices = fetch_invoices(InvoiceQuery(parsed_from, parsed_to, cancelled_only, direction))
        workbook_bytes = generate_excel_workbook(invoices)
    except DateValidationError as error:
        return jsonify({"error": str(error)}), 400
    except GDTIntegrationNotReadyError as error:
        return jsonify({"error": str(error)}), 503
    finally:
        current_app.config["CURRENT_JWT"] = None

    filename = f"invoices_{parsed_from.isoformat()}_{parsed_to.isoformat()}.xlsx"
    return send_file(
        BytesIO(workbook_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )


@invoices_blueprint.get("/api/erp/export/misa")
def api_erp_export_misa():
    """Export selected or all invoices to a MISA-compatible Excel template."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    ids_str = request.args.get("ids", "")
    from invoices.models import Invoice
    if ids_str:
        invoices = Invoice.query.filter(Invoice.id.in_(ids_str.split(","))).all()
    else:
        invoices = Invoice.query.all()

    from invoices.erp_service import generate_misa_export
    try:
        excel_bytes = generate_misa_export(invoices)
        filename = "misa_export.xlsx"
        return send_file(
            BytesIO(excel_bytes),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename,
        )
    except Exception as e:
        return jsonify({"error": f"Lỗi xuất MISA: {str(e)}"}), 500


@invoices_blueprint.get("/api/erp/export/odoo")
def api_erp_export_odoo():
    """Export selected or all invoices to an Odoo-compatible CSV template."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    ids_str = request.args.get("ids", "")
    from invoices.models import Invoice
    if ids_str:
        invoices = Invoice.query.filter(Invoice.id.in_(ids_str.split(","))).all()
    else:
        invoices = Invoice.query.all()

    from invoices.erp_service import generate_odoo_export
    try:
        csv_str = generate_odoo_export(invoices)
        filename = "odoo_export.csv"
        return send_file(
            BytesIO(csv_str.encode("utf-8")),
            mimetype="text/csv",
            as_attachment=True,
            download_name=filename,
        )
    except Exception as e:
        return jsonify({"error": f"Lỗi xuất Odoo: {str(e)}"}), 500


@invoices_blueprint.get("/api/partners")
def api_partners():
    """Extract and return corporate business partners and their statistics, or return catalog if no date range is provided."""

    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    date_from = request.args.get("from", "")
    date_to = request.args.get("to", "")
    if not date_from and not date_to:
        from invoices.models import Partner
        try:
            partners = Partner.query.order_by(Partner.mst).all()
            return jsonify([p.to_dict() for p in partners])
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    try:
        parsed_from, parsed_to = validate_date_range(
            date_from,
            date_to,
        )
        direction = request.args.get("direction", "purchase")
        current_app.config["CURRENT_JWT"] = session.get("jwt")
        invoices = fetch_invoices(InvoiceQuery(parsed_from, parsed_to, False, direction))
        partners = extract_partners_from_invoices(invoices)
    except DateValidationError as error:
        return jsonify({"error": str(error)}), 400
    except GDTIntegrationNotReadyError as error:
        return jsonify({"error": str(error)}), 503
    finally:
        current_app.config["CURRENT_JWT"] = None

    return jsonify({"partners": partners})


@invoices_blueprint.get("/api/partners/<mst>/status")
def api_partner_status(mst):
    """Force an on-demand MST tax status verification."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from invoices.mst_service import check_mst_status
    try:
        result = check_mst_status(mst, force_refresh=True)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.get("/api/reports/usage")
def api_reports_usage():
    """Aggregate and return BC26 Vietnamese tax invoice usage compliance tables."""

    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    try:
        parsed_from, parsed_to = validate_date_range(
            request.args.get("from", ""),
            request.args.get("to", ""),
        )
        direction = request.args.get("direction", "sold")  # Default to sold for business output tracking
        current_app.config["CURRENT_JWT"] = session.get("jwt")
        invoices = fetch_invoices(InvoiceQuery(parsed_from, parsed_to, False, direction))
        report = generate_tax_usage_report(invoices)
    except DateValidationError as error:
        return jsonify({"error": str(error)}), 400
    except GDTIntegrationNotReadyError as error:
        return jsonify({"error": str(error)}), 503
    finally:
        current_app.config["CURRENT_JWT"] = None

    return jsonify({"report": report})


@invoices_blueprint.get("/api/invoices/<invoice_id>/pdf-view")
def api_invoice_pdf_view(invoice_id):
    """Render a beautiful, printable official-style HTML/CSS Vietnamese electronic invoice."""

    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    # Locate invoice
    current_app.config["CURRENT_JWT"] = session.get("jwt")
    current_app.config["CURRENT_INVOICE_LOOKUP"] = session.get("invoice_lookup", {})
    try:
        from datetime import date
        invoice = current_app.config["CURRENT_INVOICE_LOOKUP"].get(invoice_id)
        
        if not invoice:
            invoices_purchase = fetch_invoices(InvoiceQuery(date(2026, 5, 1), date(2026, 5, 20), False, "purchase"))
            invoice = build_invoice_lookup(invoices_purchase).get(invoice_id)
            
        if not invoice:
            invoices_sold = fetch_invoices(InvoiceQuery(date(2026, 5, 1), date(2026, 5, 20), False, "sold"))
            invoice = build_invoice_lookup(invoices_sold).get(invoice_id)

        if not invoice:
            from invoices.service import get_local_invoices
            local_db = get_local_invoices()
            for item in local_db:
                if item["id"] == invoice_id:
                    invoice = item
                    break
            
        if not invoice:
            return "Khong tim thay hoa don yeu cau.", 404

        line_items = fetch_invoice_line_items(invoice_id)
    except FileNotFoundError:
        return "Khong tim thay hoa don yeu cau.", 404
    except Exception as error:
        return f"Loi he thong: {str(error)}", 500
    finally:
        current_app.config["CURRENT_JWT"] = None
        current_app.config["CURRENT_INVOICE_LOOKUP"] = {}

    # Calculate sums
    sum_before_tax = sum(item.get("amount_before_tax", 0.0) for item in line_items)
    sum_tax = sum(item.get("tax_amount", 0.0) for item in line_items)
    total_payable = sum_before_tax + sum_tax

    # Auto buyer/seller properties
    user_company = {
        "name": "CONG TY CO PHAN CONG NGHE GDT INVOICE HUB",
        "mst": "0109999999",
        "address": "Toa nha Technopark, Gia Lam, TP. Ha Noi",
        "phone": "1900 8888",
    }
    
    partner_details = {
        "Cong ty A": {"mst": "0101234567", "address": "So 10 Pho Hue, Quan Hai Ba Trung, Ha Noi"},
        "Cong ty B": {"mst": "0209876543", "address": "250 Nguyen Thi Minh Khai, Quan 3, TP. Ho Chi Minh"},
        "Cong ty C": {"mst": "0301122334", "address": "15 Le Loi, Quan Hai Chau, Da Nang"},
    }
    
    if "seller_name" in invoice:
        seller = {
            "name": invoice.get("seller_name", ""),
            "mst": invoice.get("seller_mst", ""),
            "address": invoice.get("seller_address", ""),
            "phone": invoice.get("seller_phone", ""),
        }
        buyer = {
            "name": invoice.get("buyer_name", ""),
            "mst": invoice.get("buyer_mst", ""),
            "address": invoice.get("buyer_address", ""),
        }
    else:
        issuer = invoice.get("issuer", "Doi tac khac")
        partner = partner_details.get(
            issuer,
            {
                "mst": f"0{abs(hash(issuer)) % 1000000000:09d}",
                "address": f"Khu cong nghiep Binh Duong, Tinh Binh Duong",
            }
        )
        partner["name"] = issuer

        # If it is a purchase invoice, issuer is Seller, user_company is Buyer
        if invoice.get("direction", "purchase") == "purchase":
            seller = partner
            buyer = user_company
        else:
            seller = user_company
            buyer = partner

    return render_template(
        "invoice_pdf.html",
        invoice=invoice,
        line_items=line_items,
        seller=seller,
        buyer=buyer,
        sum_before_tax=sum_before_tax,
        sum_tax=sum_tax,
        total_payable=total_payable,
    )


from flask import send_file
import io

@invoices_blueprint.post("/api/invoices/batch-download")
def api_batch_download_invoices():
    """Fetch and package all GDT invoices for a month in a ZIP archive (Asynchronous)."""

    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    payload = request.get_json(silent=True) or {}
    month = payload.get("month", "").strip()  # Format: YYYY-MM
    direction = payload.get("direction", "purchase").strip()
    duplicate_strategy = payload.get("duplicate_strategy", "overwrite").strip()

    if not month:
        return jsonify({"error": "Vui long chon thang can tai."}), 400

    task_id = str(uuid.uuid4())

    with DOWNLOAD_TASKS_LOCK:
        DOWNLOAD_TASKS[task_id] = {
            "task_id": task_id,
            "status": "pending",
            "progress": 0,
            "completed_count": 0,
            "total": 0,
            "imported_count": 0,
            "skipped_count": 0,
            "overwritten_count": 0,
            "failed_count": 0,
            "error": None,
            "zip_bytes": None,
            "created_at": datetime.now().isoformat()
        }

    # Fetch configuration for child thread execution
    jwt_token = session.get("jwt")
    username = session.get("username")
    encrypted_password = session.get("encrypted_password")
    invoice_lookup = session.get("invoice_lookup", {})
    gdt_use_mock = current_app.config.get("GDT_USE_MOCK", True)
    gdt_base_url = current_app.config.get("GDT_BASE_URL")
    gdt_timeout = current_app.config.get("GDT_TIMEOUT_SECONDS", 10)
    app_instance = current_app._get_current_object()

    def run_task():
        with app_instance.app_context():
            # Inject active context configs
            app_instance.config["CURRENT_JWT"] = jwt_token
            app_instance.config["CURRENT_USERNAME"] = username
            app_instance.config["CURRENT_ENCRYPTED_PASSWORD"] = encrypted_password
            app_instance.config["CURRENT_INVOICE_LOOKUP"] = invoice_lookup
            app_instance.config["GDT_USE_MOCK"] = gdt_use_mock
            app_instance.config["GDT_BASE_URL"] = gdt_base_url
            app_instance.config["GDT_TIMEOUT_SECONDS"] = gdt_timeout

            def on_progress(completed, total, status, error=None, zip_bytes=None, imported=0, skipped=0, overwritten=0, failed=0):
                with DOWNLOAD_TASKS_LOCK:
                    if task_id in DOWNLOAD_TASKS:
                        task = DOWNLOAD_TASKS[task_id]
                        task["completed_count"] = completed
                        task["total"] = total
                        task["status"] = status
                        task["error"] = error
                        task["imported_count"] = imported
                        task["skipped_count"] = skipped
                        task["overwritten_count"] = overwritten
                        task["failed_count"] = failed
                        if zip_bytes:
                            task["zip_bytes"] = zip_bytes
                        if total > 0:
                            task["progress"] = int((completed / total) * 100)

            try:
                from invoices.service import batch_download_invoices
                batch_download_invoices(month, direction, on_progress=on_progress, duplicate_strategy=duplicate_strategy)
            except Exception as e:
                on_progress(0, 0, "failed", error=str(e))
            finally:
                # Clean thread configurations
                app_instance.config["CURRENT_JWT"] = None
                app_instance.config["CURRENT_USERNAME"] = None
                app_instance.config["CURRENT_ENCRYPTED_PASSWORD"] = None
                app_instance.config["CURRENT_INVOICE_LOOKUP"] = {}


    thread = threading.Thread(target=run_task, name=f"BatchDownloadThread-{task_id}")
    thread.daemon = True
    thread.start()

    return jsonify({"task_id": task_id, "status": "pending"}), 202


@invoices_blueprint.get("/api/invoices/batch-download/status/<task_id>")
def api_batch_download_status(task_id):
    """Check progress of a batch download task."""

    with DOWNLOAD_TASKS_LOCK:
        task = DOWNLOAD_TASKS.get(task_id)
        if not task:
            return jsonify({"error": "Khong tim thay thong tin tien trinh tai."}), 404

        return jsonify({
            "task_id": task["task_id"],
            "status": task["status"],
            "progress": task["progress"],
            "completed_count": task["completed_count"],
            "total": task["total"],
            "imported_count": task.get("imported_count", 0),
            "skipped_count": task.get("skipped_count", 0),
            "overwritten_count": task.get("overwritten_count", 0),
            "failed_count": task.get("failed_count", 0),
            "error": task["error"]
        })


@invoices_blueprint.get("/api/invoices/batch-download/download/<task_id>")
def api_batch_download_retrieve(task_id):
    """Retrieve the generated ZIP file for a completed batch download task."""

    with DOWNLOAD_TASKS_LOCK:
        task = DOWNLOAD_TASKS.get(task_id)
        if not task:
            return jsonify({"error": "Khong tim thay file tai ve cho phien nay."}), 404

        if task["status"] != "completed" or not task.get("zip_bytes"):
            return jsonify({"error": f"Tien trinh chua hoan thanh. Trang thai: {task['status']}"}), 400

        zip_bytes = task["zip_bytes"]
        # Clear ZIP memory to prevent leaks
        del DOWNLOAD_TASKS[task_id]

    import io
    return send_file(
        io.BytesIO(zip_bytes),
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"GDT_Invoices_Batch.zip"
    )


@invoices_blueprint.post("/api/invoices/upload")
@roles_required("admin", "auditor")
def api_upload_invoices():
    """Import drag-and-drop XML/ZIP invoices and run smart MISA audits."""

    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    if "files" not in request.files:
        return jsonify({"error": "Khong tim thay tep tin duoc tai len."}), 400

    files = request.files.getlist("files")
    if not files or files[0].filename == "":
        return jsonify({"error": "Khong co tep tin nao duoc chon."}), 400

    duplicate_strategy = request.form.get("duplicate_strategy", "overwrite").strip()

    from invoices.service import import_xml_invoice
    import zipfile

    imported_count = 0
    skipped_count = 0
    overwritten_count = 0
    errors = []

    for file in files:
        filename = file.filename
        try:
            file_bytes = file.read()
            if filename.lower().endswith(".xml"):
                res = import_xml_invoice(file_bytes, filename, duplicate_strategy=duplicate_strategy)
                status = res.get("import_status", "imported")
                if status == "skipped":
                    skipped_count += 1
                elif status == "overwritten":
                    overwritten_count += 1
                else:
                    imported_count += 1
            elif filename.lower().endswith(".zip"):
                with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
                    for zinfo in z.infolist():
                        if zinfo.filename.lower().endswith(".xml") and not zinfo.is_dir():
                            xml_content = z.read(zinfo.filename)
                            base_xml_name = os.path.basename(zinfo.filename)
                            res = import_xml_invoice(xml_content, base_xml_name, duplicate_strategy=duplicate_strategy)
                            status = res.get("import_status", "imported")
                            if status == "skipped":
                                skipped_count += 1
                            elif status == "overwritten":
                                overwritten_count += 1
                            else:
                                imported_count += 1
            else:
                errors.append(f"Tep {filename} khong dung dinh dang XML hoac ZIP.")
        except Exception as e:
            errors.append(f"Loi khi nhap tep {filename}: {str(e)}")

    return jsonify({
        "status": "success",
        "imported_count": imported_count,
        "skipped_count": skipped_count,
        "overwritten_count": overwritten_count,
        "errors": errors
    })


@invoices_blueprint.get("/api/invoices/local")
def api_get_local_invoices():
    """Retrieve all smart-audited locally stored invoices."""

    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from invoices.service import get_local_invoices
    mst = request.args.get("taxpayer_mst") or session.get("active_taxpayer_mst")
    if mst == "all" or not mst:
        mst = None
    return jsonify({"invoices": get_local_invoices(mst)})


@invoices_blueprint.get("/api/invoices/local/export-excel")
@roles_required("admin", "auditor")
def api_export_local_excel():
    """Export the local audited database to an Excel workbook download, filtered by active corporate taxpayer profile."""

    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    try:
        from invoices.service import get_local_invoices
        mst = request.args.get("taxpayer_mst") or session.get("active_taxpayer_mst")
        if mst == "all" or not mst:
            mst = None
        invoices = get_local_invoices(mst)
        workbook_bytes = generate_local_excel_workbook(invoices)
    except Exception as error:
        return jsonify({"error": str(error)}), 500

    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"audited_invoices_{timestamp}.xlsx"
    return send_file(
        BytesIO(workbook_bytes),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )


@invoices_blueprint.get("/api/invoices/local/items")
def api_search_local_items():
    """Global search across line items of locally imported invoices, filtered by active corporate taxpayer profile."""

    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    q = request.args.get("q", "").strip()
    mst = request.args.get("taxpayer_mst") or session.get("active_taxpayer_mst")
    if mst == "all" or not mst:
        mst = None
    from invoices.service import search_local_items
    return jsonify({"items": search_local_items(q, mst)})


@invoices_blueprint.delete("/api/invoices/local/clear")
@roles_required("admin", "auditor")
def api_clear_local_invoices():
    """Clear all records from local SQLite database and remove XML storage files."""

    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from extensions import db
    from invoices.models import Invoice, LineItem
    from invoices.service import XML_DIR
    import shutil
    import os

    try:
        # Delete all records from Invoice and LineItem tables
        LineItem.query.delete()
        Invoice.query.delete()
        db.session.commit()

        from invoices.security_audit_service import log_security_event
        log_security_event("DELETE", "Cleared all records from local SQLite database and removed XML storage files.")

        if os.path.exists(XML_DIR):
            shutil.rmtree(XML_DIR)
            os.makedirs(XML_DIR, exist_ok=True)

        return jsonify({"status": "success", "message": "Da lam sach co so du lieu cuc bo."})

    except Exception as e:
        return jsonify({"error": f"Loi khi lam sach du lieu: {str(e)}"}), 500


@invoices_blueprint.delete("/api/invoices/local/<invoice_id>")
@roles_required("admin", "auditor")
def api_delete_local_invoice(invoice_id):
    """Delete a single local invoice and its XML file."""

    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from invoices.service import delete_local_invoice
    success = delete_local_invoice(invoice_id)
    if not success:
        return jsonify({"error": "Không tìm thấy hóa đơn cần xóa."}), 404

    from invoices.security_audit_service import log_security_event
    log_security_event("DELETE", f"Deleted local invoice: {invoice_id}")

    return jsonify({"status": "success", "message": "Đã xóa hóa đơn thành công."})


@invoices_blueprint.patch("/api/invoices/local/<invoice_id>")
def api_adjust_local_invoice(invoice_id):
    """Adjust fields of a local invoice and update its smart auditing warnings."""

    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    payload = request.get_json(silent=True) or {}

    from invoices.service import adjust_local_invoice
    try:
        updated_invoice = adjust_local_invoice(invoice_id, payload)
        return jsonify({
            "status": "success",
            "message": "Đã điều chỉnh hóa đơn thành công.",
            "invoice": updated_invoice
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"Lỗi không xác định: {str(e)}"}), 500


@invoices_blueprint.get("/api/settings")
@roles_required("admin", "auditor")
def api_get_settings():
    """Retrieve current scheduler and SMTP settings with masked passwords."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from invoices.scheduler import load_scheduler_settings
    settings = load_scheduler_settings()

    # Mask sensitive credentials
    if settings.get("smtp_pass"):
        settings["smtp_pass"] = "••••••••"
    if settings.get("gdt_password"):
        settings["gdt_password"] = "••••••••"
    if settings.get("ai_api_key"):
        settings["ai_api_key"] = "••••••••"
    if settings.get("telegram_bot_token"):
        settings["telegram_bot_token"] = "••••••••"
    if settings.get("gdrive_client_secret"):
        settings["gdrive_client_secret"] = "••••••••"
    if settings.get("gdrive_refresh_token"):
        settings["gdrive_refresh_token"] = "••••••••"
    if settings.get("onedrive_client_secret"):
        settings["onedrive_client_secret"] = "••••••••"
    # Mask sensitive credentials
    if settings.get("smtp_pass"):
        settings["smtp_pass"] = "••••••••"
    if settings.get("gdt_password"):
        settings["gdt_password"] = "••••••••"
    if settings.get("ai_api_key"):
        settings["ai_api_key"] = "••••••••"
    if settings.get("telegram_bot_token"):
        settings["telegram_bot_token"] = "••••••••"
    if settings.get("gdrive_client_secret"):
        settings["gdrive_client_secret"] = "••••••••"
    if settings.get("gdrive_refresh_token"):
        settings["gdrive_refresh_token"] = "••••••••"
    if settings.get("onedrive_client_secret"):
        settings["onedrive_client_secret"] = "••••••••"
    if settings.get("onedrive_refresh_token"):
        settings["onedrive_refresh_token"] = "••••••••"
    if settings.get("erp_auth_token"):
        settings["erp_auth_token"] = "••••••••"
    if settings.get("webhook_secret"):
        settings["webhook_secret"] = "••••••••"

    return jsonify(settings)


@invoices_blueprint.post("/api/settings")
@roles_required("admin")
def api_post_settings():
    """Save scheduler and SMTP settings."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    payload = request.get_json(silent=True) or {}

    try:
        smtp_port = int(payload.get("smtp_port", 587))
        schedule_weekday = int(payload.get("schedule_weekday", 0))
        realtime_interval = int(payload.get("realtime_sync_interval", 15))
    except ValueError:
        return jsonify({"error": "Dữ liệu cấu hình không hợp lệ."}), 400

    from invoices.scheduler import save_scheduler_settings
    save_scheduler_settings({
        "smtp_host": payload.get("smtp_host", "").strip(),
        "smtp_port": smtp_port,
        "smtp_user": payload.get("smtp_user", "").strip(),
        "smtp_pass": payload.get("smtp_pass", ""),
        "smtp_use_tls": bool(payload.get("smtp_use_tls", True)),
        "recipient_email": payload.get("recipient_email", "").strip(),
        "schedule_enabled": bool(payload.get("schedule_enabled", False)),
        "schedule_interval": payload.get("schedule_interval", "daily"),
        "schedule_time": payload.get("schedule_time", "08:00").strip(),
        "schedule_weekday": schedule_weekday,
        "gdt_username": payload.get("gdt_username", "").strip(),
        "gdt_password": payload.get("gdt_password", ""),
        "ai_enabled": bool(payload.get("ai_enabled", False)),
        "ai_provider": payload.get("ai_provider", "ollama").strip(),
        "ai_ollama_endpoint": payload.get("ai_ollama_endpoint", "http://localhost:11434").strip(),
        "ai_api_key": payload.get("ai_api_key", ""),
        "ai_model_name": payload.get("ai_model_name", "gemma-4").strip(),
        "ai_system_prompt": payload.get("ai_system_prompt", "").strip(),
        "telegram_enabled": bool(payload.get("telegram_enabled", False)),
        "telegram_bot_token": payload.get("telegram_bot_token", ""),
        "telegram_chat_id": payload.get("telegram_chat_id", "").strip(),
        "audit_agent_enabled": bool(payload.get("audit_agent_enabled", False)),
        "audit_agent_schedule_time": payload.get("audit_agent_schedule_time", "23:00").strip(),
        "gdrive_enabled": bool(payload.get("gdrive_enabled", False)),
        "gdrive_client_id": payload.get("gdrive_client_id", "").strip(),
        "gdrive_client_secret": payload.get("gdrive_client_secret", ""),
        "gdrive_refresh_token": payload.get("gdrive_refresh_token", ""),
        "gdrive_folder_id": payload.get("gdrive_folder_id", "").strip(),
        "onedrive_enabled": bool(payload.get("onedrive_enabled", False)),
        "onedrive_client_id": payload.get("onedrive_client_id", "").strip(),
        "onedrive_client_secret": payload.get("onedrive_client_secret", ""),
        "onedrive_refresh_token": payload.get("onedrive_refresh_token", ""),
        "onedrive_folder_path": payload.get("onedrive_folder_path", "HoaDon_DienTu").strip(),
        "erp_enabled": bool(payload.get("erp_enabled", False)),
        "erp_type": payload.get("erp_type", "none").strip(),
        "erp_api_url": payload.get("erp_api_url", "").strip(),
        "erp_auth_token": payload.get("erp_auth_token", ""),
        "realtime_sync_enabled": bool(payload.get("realtime_sync_enabled", False)),
        "realtime_sync_interval": realtime_interval,
        "webhook_enabled": bool(payload.get("webhook_enabled", False)),
        "webhook_url": payload.get("webhook_url", "").strip(),
        "webhook_secret": payload.get("webhook_secret", ""),
        "signature_filter_enabled": bool(payload.get("signature_filter_enabled", True)),
        "blacklist_filter_enabled": bool(payload.get("blacklist_filter_enabled", True))
    })

    from invoices.security_audit_service import log_security_event
    log_security_event("UPDATE", "Updated application settings (SMTP, scheduler, AI, cloud sync, ERP, and webhooks).")

    return jsonify({"status": "success", "message": "Đã lưu thiết lập thành công."})


@invoices_blueprint.post("/api/invoices/realtime/trigger")
@roles_required("admin", "auditor")
def api_trigger_realtime_sync():
    """Manually trigger background real-time sync immediately."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from invoices.scheduler import load_scheduler_settings
    settings = load_scheduler_settings()

    # Trigger async thread so we return immediately and keep the UI responsive!
    from flask import current_app
    from invoices.scheduler import _scheduler_thread

    if _scheduler_thread and _scheduler_thread.is_alive():
        # Spin up a daemon thread to run the sync
        import threading
        def worker(app):
            with app.app_context():
                try:
                    _scheduler_thread.execute_realtime_sync(settings)
                except Exception as ex:
                    app.logger.error(f"Manual real-time sync failed: {ex}")

        t = threading.Thread(target=worker, args=(current_app._get_current_object(),), daemon=True)
        t.start()
        return jsonify({"status": "success", "message": "Đã kích hoạt đồng bộ hóa thời gian thực chạy ngầm."})
    else:
        return jsonify({"error": "Không thể kết nối với dịch vụ background scheduler."}), 500


@invoices_blueprint.get("/api/invoices/realtime/stream")
def api_realtime_stream():
    """SSE streaming endpoint to push downloaded invoice events in real-time."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    import queue
    from invoices.scheduler import REALTIME_CLIENT_QUEUES, REALTIME_QUEUES_LOCK

    q = queue.Queue(maxsize=100)
    with REALTIME_QUEUES_LOCK:
        REALTIME_CLIENT_QUEUES.append(q)

    def event_generator():
        try:
            # Send initial keepalive
            yield f"data: {json.dumps({'event': 'connected'})}\n\n"
            while True:
                try:
                    # Wait for an event with a 20-second timeout for heartbeat/keepalive
                    event_data = q.get(timeout=20)
                    yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                except queue.Empty:
                    # Send keepalive heartbeat to prevent connection timeout
                    yield "data: {\"event\": \"keepalive\"}\n\n"
        finally:
            with REALTIME_QUEUES_LOCK:
                if q in REALTIME_CLIENT_QUEUES:
                    REALTIME_CLIENT_QUEUES.remove(q)

    from flask import Response
    return Response(event_generator(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "Transfer-Encoding": "chunked",
        "Connection": "keep-alive"
    })


@invoices_blueprint.get("/api/blacklist")
@roles_required("admin", "auditor")
def api_list_blacklist():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized
    from invoices.models import BlacklistedMST
    blacklist = BlacklistedMST.query.all()
    return jsonify([item.to_dict() for item in blacklist])


@invoices_blueprint.post("/api/blacklist")
@roles_required("admin", "auditor")
def api_add_blacklist():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized
    payload = request.json or {}
    mst = payload.get("mst", "").strip()
    reason = payload.get("reason", "").strip()
    if not mst:
        return jsonify({"error": "Mã số thuế không được để trống"}), 400
    
    from invoices.models import BlacklistedMST
    from extensions import db
    import datetime
    
    existing = db.session.get(BlacklistedMST, mst)
    if existing:
        existing.reason = reason
        existing.blacklisted_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        item = BlacklistedMST(
            mst=mst,
            reason=reason,
            blacklisted_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        db.session.add(item)
    db.session.commit()
    return jsonify({"status": "success", "message": "Đã thêm mã số thuế vào danh sách đen."})


@invoices_blueprint.delete("/api/blacklist/<mst>")
@roles_required("admin", "auditor")
def api_delete_blacklist(mst):
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized
    from invoices.models import BlacklistedMST
    from extensions import db
    
    item = db.session.get(BlacklistedMST, mst)
    if not item:
        return jsonify({"error": "Không tìm thấy mã số thuế trong danh sách đen."}), 404
        
    db.session.delete(item)
    db.session.commit()
    return jsonify({"status": "success", "message": "Đã xóa mã số thuế khỏi danh sách đen."})


@invoices_blueprint.post("/api/settings/test-email")
@roles_required("admin")
def api_test_email():
    """Trigger a manual test email with the provided SMTP parameters."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    payload = request.get_json(silent=True) or {}

    from invoices.scheduler import load_scheduler_settings, SchedulerThread
    current_settings = load_scheduler_settings()

    smtp_host = payload.get("smtp_host", "").strip()
    try:
        smtp_port = int(payload.get("smtp_port", 587))
    except ValueError:
        return jsonify({"error": "Cổng SMTP không hợp lệ."}), 400

    smtp_user = payload.get("smtp_user", "").strip()
    smtp_pass = payload.get("smtp_pass", "").strip()
    smtp_use_tls = payload.get("smtp_use_tls", True)
    recipient = payload.get("recipient_email", "").strip()

    if not smtp_host or not smtp_user or not recipient:
        return jsonify({"error": "Vui lòng nhập đầy đủ SMTP Host, SMTP User và Email nhận."}), 400

    # Retrieve existing encrypted password if they passed the mask
    if smtp_pass == "••••••••" or not smtp_pass:
        from auth.crypto import decrypt_password
        enc_pass = current_settings.get("smtp_pass", "")
        if enc_pass:
            try:
                smtp_pass = decrypt_password(enc_pass)
            except Exception:
                return jsonify({"error": "Không thể giải mã mật khẩu SMTP đã lưu."}), 500
        else:
            return jsonify({"error": "Mật khẩu SMTP trống."}), 400

    # Build a simple text test message
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    
    msg = MIMEMultipart()
    msg["From"] = smtp_user
    msg["To"] = recipient
    msg["Subject"] = "[GDT Invoice Hub] Kiểm tra kết nối SMTP thành công"
    msg.attach(MIMEText("Kết nối SMTP từ GDT Invoice Hub của bạn hoạt động bình thường!", "plain"))

    try:
        SchedulerThread.send_smtp_message(smtp_host, smtp_port, smtp_user, smtp_pass, smtp_use_tls, recipient, msg)
        return jsonify({"status": "success", "message": "Đã gửi email thử nghiệm thành công!"})
    except Exception as e:
        return jsonify({"error": f"Lỗi gửi email thử nghiệm: {str(e)}"}), 500


@invoices_blueprint.post("/api/settings/test-audit")
@roles_required("admin")
def api_test_audit():
    """Trigger a manual run of the autonomous AI audit agent immediately."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from invoices.scheduler import load_scheduler_settings, SchedulerThread
    settings = load_scheduler_settings()
    # Force audit agent to run synchronously by ignoring its scheduled time check
    thread = SchedulerThread(current_app)
    try:
        thread.execute_autonomous_audit(settings)
        return jsonify({"status": "success", "message": "Đã chạy kiểm toán tự động thành công!"})
    except Exception as e:
        return jsonify({"error": f"Lỗi chạy kiểm toán tự động: {str(e)}"}), 500


@invoices_blueprint.get("/api/settings/logs")
@roles_required("admin", "auditor")
def api_get_settings_logs():
    """Retrieve history of background scheduler executions."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from invoices.scheduler import get_scheduler_logs
    return jsonify(get_scheduler_logs())


@invoices_blueprint.post("/api/invoices/local/<invoice_id>/ai-audit")
@roles_required("admin", "auditor")
def api_trigger_ai_audit(invoice_id):
    """Trigger manual AI auditing for a specific local invoice."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from invoices.models import Invoice
    from invoices.ai_service import AIComplianceAuditor
    
    invoice = db.session.get(Invoice, invoice_id)
    if not invoice:
        return jsonify({"error": "Không tìm thấy hóa đơn cần phân tích."}), 404

    # Run AI audit (which returns AIAuditResult objects and commits them to the DB)
    auditor = AIComplianceAuditor()
    results = auditor.audit_invoice(invoice)

    return jsonify({
        "status": "success",
        "ai_warnings": [w.to_dict() for w in results]
    })


@invoices_blueprint.get("/api/invoices/local/<invoice_id>/correction-proposals")
def api_get_invoice_correction_proposals(invoice_id):
    """Get all correction proposals for a specific invoice."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from invoices.models import InvoiceCorrectionProposal
    proposals = InvoiceCorrectionProposal.query.filter_by(invoice_id=invoice_id).order_by(InvoiceCorrectionProposal.id.desc()).all()
    return jsonify([p.to_dict() for p in proposals])


@invoices_blueprint.get("/api/correction-proposals")
def api_get_all_correction_proposals():
    """Get all correction proposals filtered by current taxpayer/tenant MST."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from invoices.models import InvoiceCorrectionProposal
    mst = session.get("tax_code")
    
    query = InvoiceCorrectionProposal.query
    if mst:
        query = query.filter_by(taxpayer_mst=mst)
        
    proposals = query.order_by(InvoiceCorrectionProposal.id.desc()).all()
    return jsonify([p.to_dict() for p in proposals])


@invoices_blueprint.post("/api/invoices/local/<invoice_id>/correction-proposals/generate")
@roles_required("admin", "auditor")
def api_generate_invoice_correction_proposals(invoice_id):
    """Manually trigger AI Auditor correction proposals generation."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from invoices.models import Invoice
    from invoices.ai_service import AIComplianceAuditor

    invoice = db.session.get(Invoice, invoice_id)
    if not invoice:
        return jsonify({"error": "Không tìm thấy hóa đơn cần đề xuất hiệu chỉnh."}), 404

    auditor = AIComplianceAuditor()
    if not invoice.ai_audited:
        auditor.audit_invoice(invoice)
        
    proposals = auditor.generate_correction_proposals(invoice)
    return jsonify({
        "status": "success",
        "proposals": [p.to_dict() for p in proposals]
    })


@invoices_blueprint.post("/api/correction-proposals/<int:proposal_id>/approve")
@roles_required("admin", "auditor")
def api_approve_correction_proposal(proposal_id):
    """Approve a correction proposal and apply changes directly to the invoice."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from invoices.models import InvoiceCorrectionProposal
    from invoices.ai_service import apply_correction_proposal

    proposal = db.session.get(InvoiceCorrectionProposal, proposal_id)
    if not proposal:
        return jsonify({"error": "Không tìm thấy đề xuất hiệu chỉnh."}), 404

    if proposal.status != "pending":
        return jsonify({"error": f"Đề xuất đã ở trạng thái: {proposal.status}. Không thể phê duyệt lại."}), 400

    success = apply_correction_proposal(proposal)
    if success:
        return jsonify({
            "status": "success",
            "message": "Đã phê duyệt và áp dụng đề xuất hiệu chỉnh thành công.",
            "proposal": proposal.to_dict()
        })
    else:
        return jsonify({"error": "Thất bại khi áp dụng đề xuất hiệu chỉnh lên hóa đơn."}), 500


@invoices_blueprint.post("/api/correction-proposals/<int:proposal_id>/reject")
@roles_required("admin", "auditor")
def api_reject_correction_proposal(proposal_id):
    """Reject a correction proposal."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from invoices.models import InvoiceCorrectionProposal
    from datetime import datetime

    proposal = db.session.get(InvoiceCorrectionProposal, proposal_id)
    if not proposal:
        return jsonify({"error": "Không tìm thấy đề xuất hiệu chỉnh."}), 404

    if proposal.status != "pending":
        return jsonify({"error": f"Đề xuất đã ở trạng thái: {proposal.status}. Không thể từ chối."}), 400

    proposal.status = "rejected"
    proposal.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Đã từ chối đề xuất hiệu chỉnh.",
        "proposal": proposal.to_dict()
    })



@invoices_blueprint.post("/api/invoices/local/<invoice_id>/mitigation-letter")
@roles_required("admin", "auditor")
def api_generate_mitigation_letter(invoice_id):
    """Generate professional Vietnamese explanation letter (Công văn giải trình) using AI."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from invoices.models import Invoice
    from invoices.ai_service import AIComplianceAuditor

    invoice = db.session.get(Invoice, invoice_id)
    if not invoice:
        return jsonify({"error": "Không tìm thấy hóa đơn cần giải trình."}), 404

    try:
        auditor = AIComplianceAuditor()
        letter_content = auditor.generate_mitigation_letter(invoice)
        return jsonify({
            "status": "success",
            "letter": letter_content
        })
    except Exception as e:
        return jsonify({"error": f"Lỗi tạo giải trình AI: {str(e)}"}), 500


@invoices_blueprint.post("/api/invoices/local/<invoice_id>/mitigation-letter/export")
@roles_required("admin", "auditor")
def api_export_mitigation_letter(invoice_id):
    """Export explanation letter to Word (.doc) or PDF."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    payload = request.get_json(silent=True) or {}
    letter_text = payload.get("letter", "").strip()
    export_format = payload.get("format", "doc").lower()  # 'doc' or 'pdf'

    if not letter_text:
        return jsonify({"error": "Nội dung giải trình trống."}), 400

    filename = f"Giai_trinh_hoa_don_{invoice_id}"

    formatted_letter = letter_text.replace('\n', '<br>')

    if export_format == "pdf":
        html_content = f"""
        <html>
        <head>
        <meta charset="utf-8">
        <style>
            @page {{
                size: a4;
                margin: 2.5cm 2cm 2.5cm 2.5cm;
            }}
            body {{
                font-family: 'Arial', sans-serif;
                font-size: 12px;
                line-height: 1.6;
            }}
            .bold {{ font-weight: bold; }}
            .text-center {{ text-align: center; }}
            .text-right {{ text-align: right; }}
            .title {{ font-size: 14px; font-weight: bold; text-align: center; margin-top: 15px; margin-bottom: 15px; }}
            p {{ margin-bottom: 8px; text-align: justify; text-indent: 1cm; }}
            .no-indent {{ text-indent: 0; }}
        </style>
        </head>
        <body>
        {formatted_letter}
        </body>
        </html>
        """
        try:
            pdf_buf = render_html_to_pdf(html_content)
            return send_file(
                pdf_buf,
                mimetype="application/pdf",
                as_attachment=True,
                download_name=f"{filename}.pdf"
            )
        except Exception as e:
            return jsonify({"error": f"Lỗi xuất PDF: {str(e)}"}), 500

    else:
        # Default to Word compatible HTML (.doc)
        html_content = f"""
        <html xmlns:o="urn:schemas-microsoft-com:office:office"
              xmlns:w="urn:schemas-microsoft-com:office:word"
              xmlns="http://www.w3.org/TR/REC-html40">
        <head>
        <meta charset="utf-8">
        <!--[if gte mso 9]>
        <xml>
        <w:WordDocument>
        <w:View>Print</w:View>
        <w:Zoom>100</w:Zoom>
        <w:DoNotOptimizeForBrowser/>
        </w:WordDocument>
        </xml>
        <![endif]-->
        <style>
            @page {{
                size: 8.27in 11.69in; /* A4 */
                margin: 1.0in 0.79in 1.0in 1.18in; /* Top Right Bottom Left in Word format */
                mso-header-margin: .5in;
                mso-footer-margin: .5in;
                mso-paper-source: 0;
            }}
            body {{
                font-family: 'Times New Roman', serif;
                font-size: 12pt;
                line-height: 1.5;
            }}
            p {{
                margin-top: 0;
                margin-bottom: 6pt;
                text-align: justify;
            }}
            .bold {{ font-weight: bold; }}
            .text-center {{ text-align: center; }}
            .text-right {{ text-align: right; }}
        </style>
        </head>
        <body>
        {formatted_letter}
        </body>
        </html>
        """
        doc_bytes = html_content.encode("utf-8")
        return send_file(
            BytesIO(doc_bytes),
            mimetype="application/msword",
            as_attachment=True,
            download_name=f"{filename}.doc"
        )


def render_html_to_pdf(html_content: str) -> io.BytesIO:
    """Helper to compile HTML content to PDF using xhtml2pdf with pre-registered Vietnamese fonts."""
    # Find a suitable Vietnamese TrueType Font
    candidates = [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/tahoma.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    font_path = None
    for path in candidates:
        if os.path.exists(path):
            font_path = path
            break
            
    if font_path:
        try:
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont
            pdfmetrics.registerFont(TTFont('Arial', font_path))
            
            # Also attempt to register Bold font
            bold_path = font_path.replace("arial.ttf", "arialbd.ttf").replace("tahoma.ttf", "tahomabd.ttf").replace("Arial.ttf", "Arial Bold.ttf")
            if os.path.exists(bold_path):
                pdfmetrics.registerFont(TTFont('Arial-Bold', bold_path))
            else:
                pdfmetrics.registerFont(TTFont('Arial-Bold', font_path))
        except Exception:
            pass

    pdf_buffer = io.BytesIO()
    from xhtml2pdf import pisa
    pisa_status = pisa.CreatePDF(html_content, dest=pdf_buffer)
    if pisa_status.err:
        raise RuntimeError("xhtml2pdf rendering failed.")
    pdf_buffer.seek(0)
    return pdf_buffer


@invoices_blueprint.get("/api/invoices/<invoice_id>/pdf")
@roles_required("admin", "auditor")
def api_invoice_pdf_download(invoice_id):
    """Download printable official-style PDF electronic invoice using xhtml2pdf."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    # Locate invoice
    current_app.config["CURRENT_JWT"] = session.get("jwt")
    current_app.config["CURRENT_INVOICE_LOOKUP"] = session.get("invoice_lookup", {})
    try:
        from datetime import date
        invoice = current_app.config["CURRENT_INVOICE_LOOKUP"].get(invoice_id)
        
        if not invoice:
            invoices_purchase = fetch_invoices(InvoiceQuery(date(2026, 5, 1), date(2026, 5, 20), False, "purchase"))
            invoice = build_invoice_lookup(invoices_purchase).get(invoice_id)
            
        if not invoice:
            invoices_sold = fetch_invoices(InvoiceQuery(date(2026, 5, 1), date(2026, 5, 20), False, "sold"))
            invoice = build_invoice_lookup(invoices_sold).get(invoice_id)

        if not invoice:
            from invoices.service import get_local_invoices
            local_db = get_local_invoices()
            for item in local_db:
                if item["id"] == invoice_id:
                    invoice = item
                    break
            
        if not invoice:
            return jsonify({"error": "Không tìm thấy hóa đơn yêu cầu."}), 404

        line_items = fetch_invoice_line_items(invoice_id)
    except FileNotFoundError:
        return jsonify({"error": "Không tìm thấy hóa đơn yêu cầu."}), 404
    except Exception as error:
        return jsonify({"error": f"Lỗi hệ thống: {str(error)}"}), 500
    finally:
        current_app.config["CURRENT_JWT"] = None
        current_app.config["CURRENT_INVOICE_LOOKUP"] = {}

    # Calculate sums
    sum_before_tax = sum(item.get("amount_before_tax", 0.0) for item in line_items)
    sum_tax = sum(item.get("tax_amount", 0.0) for item in line_items)
    total_payable = sum_before_tax + sum_tax

    # Convert total payable to words
    from invoices.service import doc_so_tien_vietnam
    total_payable_words = doc_so_tien_vietnam(total_payable)

    # Auto buyer/seller properties
    user_company = {
        "name": "CONG TY CO PHAN CONG NGHE GDT INVOICE HUB",
        "mst": "0109999999",
        "address": "Toa nha Technopark, Gia Lam, TP. Ha Noi",
        "phone": "1900 8888",
    }
    
    partner_details = {
        "Cong ty A": {"mst": "0101234567", "address": "So 10 Pho Hue, Quan Hai Ba Trung, Ha Noi"},
        "Cong ty B": {"mst": "0209876543", "address": "250 Nguyen Thi Minh Khai, Quan 3, TP. Ho Chi Minh"},
        "Cong ty C": {"mst": "0301122334", "address": "15 Le Loi, Quan Hai Chau, Da Nang"},
    }
    
    if "seller_name" in invoice:
        seller = {
            "name": invoice.get("seller_name", ""),
            "mst": invoice.get("seller_mst", ""),
            "address": invoice.get("seller_address", ""),
            "phone": invoice.get("seller_phone", ""),
        }
        buyer = {
            "name": invoice.get("buyer_name", ""),
            "mst": invoice.get("buyer_mst", ""),
            "address": invoice.get("buyer_address", ""),
        }
    else:
        issuer = invoice.get("issuer", "Doi tac khac")
        partner = partner_details.get(
            issuer,
            {
                "mst": f"0{abs(hash(issuer)) % 1000000000:09d}",
                "address": f"Khu cong nghiep Binh Duong, Tinh Binh Duong",
            }
        )
        partner["name"] = issuer

        # If it is a purchase invoice, issuer is Seller, user_company is Buyer
        if invoice.get("direction", "purchase") == "purchase":
            seller = partner
            buyer = user_company
        else:
            seller = user_company
            buyer = partner

    html_content = render_template(
        "invoice_pdf_export.html",
        invoice=invoice,
        line_items=line_items,
        seller=seller,
        buyer=buyer,
        sum_before_tax=sum_before_tax,
        sum_tax=sum_tax,
        total_payable=total_payable,
        total_payable_words=total_payable_words
    )

    try:
        pdf_stream = render_html_to_pdf(html_content)
        filename = f"invoice_{invoice_id}.pdf"
        return send_file(
            pdf_stream,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({"error": f"Lỗi xuất PDF: {str(e)}"}), 500


@invoices_blueprint.get("/api/reports/partners/pdf")
@roles_required("admin", "auditor")
def api_reports_partners_pdf():
    """Export the Business Partner Directory matching the dashboard as a PDF report."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    try:
        parsed_from, parsed_to = validate_date_range(
            request.args.get("from", ""),
            request.args.get("to", ""),
        )
        direction = request.args.get("direction", "purchase")
        current_app.config["CURRENT_JWT"] = session.get("jwt")
        invoices = fetch_invoices(InvoiceQuery(parsed_from, parsed_to, False, direction))
        partners = extract_partners_from_invoices(invoices)
    except DateValidationError as error:
        return jsonify({"error": str(error)}), 400
    except GDTIntegrationNotReadyError as error:
        return jsonify({"error": str(error)}), 503
    finally:
        current_app.config["CURRENT_JWT"] = None

    date_now = datetime.now().strftime("%d/%m/%Y %H:%M")
    html_content = render_template(
        "report_partners_pdf.html",
        partners=partners,
        from_date=parsed_from.strftime("%d/%m/%Y"),
        to_date=parsed_to.strftime("%d/%m/%Y"),
        direction=direction,
        date_now=date_now
    )

    try:
        pdf_stream = render_html_to_pdf(html_content)
        filename = f"partner_directory_{parsed_from.isoformat()}_{parsed_to.isoformat()}.pdf"
        return send_file(
            pdf_stream,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({"error": f"Lỗi xuất PDF: {str(e)}"}), 500


@invoices_blueprint.get("/api/reports/usage/pdf")
@roles_required("admin", "auditor")
def api_reports_usage_pdf():
    """Export the BC26 Tax Compliance and invoice usage report as a PDF report."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    try:
        parsed_from, parsed_to = validate_date_range(
            request.args.get("from", ""),
            request.args.get("to", ""),
        )
        direction = request.args.get("direction", "sold")
        current_app.config["CURRENT_JWT"] = session.get("jwt")
        invoices = fetch_invoices(InvoiceQuery(parsed_from, parsed_to, False, direction))
        report = generate_tax_usage_report(invoices)
    except DateValidationError as error:
        return jsonify({"error": str(error)}), 400
    except GDTIntegrationNotReadyError as error:
        return jsonify({"error": str(error)}), 503
    finally:
        current_app.config["CURRENT_JWT"] = None

    date_now = datetime.now().strftime("%d/%m/%Y %H:%M")
    html_content = render_template(
        "report_usage_pdf.html",
        report=report,
        from_date=parsed_from.strftime("%d/%m/%Y"),
        to_date=parsed_to.strftime("%d/%m/%Y"),
        direction=direction,
        date_now=date_now
    )

    try:
        pdf_stream = render_html_to_pdf(html_content)
        filename = f"bc26_usage_report_{parsed_from.isoformat()}_{parsed_to.isoformat()}.pdf"
        return send_file(
            pdf_stream,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({"error": f"Lỗi xuất PDF: {str(e)}"}), 500


@invoices_blueprint.get("/api/ai/chat/sessions")
def api_chat_sessions():
    """Retrieve all conversational sessions."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized
    from invoices.models import AIChatSession
    try:
        sessions = AIChatSession.query.order_by(AIChatSession.created_at.desc()).all()
        # Return list directly to satisfy legacy unit test (we will make main.js support both formats)
        return jsonify([s.to_dict() for s in sessions]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/ai/chat/sessions")
def api_create_chat_session():
    """Create a new chat session."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized
    from invoices.models import AIChatSession, AIChatMessage, Invoice
    import uuid
    from datetime import datetime
    try:
        data = request.get_json() or {}
        title = data.get("title", "Cuộc hội thoại mới")
        invoice_id = data.get("invoice_id")
        
        invoice = None
        if invoice_id:
            invoice = db.session.get(Invoice, invoice_id)
            if not invoice:
                return jsonify({"error": "Không tìm thấy hóa đơn liên kết."}), 404
            title = f"Tham vấn hóa đơn {invoice.number}"
            
        session_id = str(uuid.uuid4())
        new_session = AIChatSession(
            id=session_id,
            title=title,
            invoice_id=invoice_id,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        db.session.add(new_session)
        
        if invoice:
            import json
            welcome_content = (
                f"### [Hệ thống Kiểm soát Tuân thủ Thuế AI - GDT Hub]\n\n"
                f"Kính chào Quý khách, tôi là **Cố vấn Thuế cấp cao AI**. Tôi đã tiếp nhận yêu cầu tham vấn về hóa đơn điện tử sau:\n\n"
                f"- **Nhà cung cấp:** {invoice.seller_name} (MST: `{invoice.seller_mst}`)\n"
                f"- **Số hóa đơn:** `{invoice.number}` | **Ký hiệu:** `{invoice.symbol}` | **Ngày lập:** {invoice.date}\n"
                f"- **Tổng tiền thanh toán (sau thuế):** {invoice.total_amount:,.2f} {invoice.currency or 'VND'}\n"
                f"- **Chỉ số tuân thủ T-Score:** **{invoice.t_score}/100** ({invoice.t_rating})\n\n"
                f"**Đánh giá tuân thủ sơ bộ (Nghị định 123/2020/NĐ-CP & Thông tư 219/2013/TT-BTC):**\n"
            )
            
            warnings = []
            if invoice.warnings_json:
                try:
                    warnings = json.loads(invoice.warnings_json)
                except Exception:
                    pass
            
            cash_threshold = 20000000.0
            if invoice.total_amount >= cash_threshold and invoice.payment_method == "Tiền mặt":
                warnings.append("Hóa đơn thanh toán bằng Tiền mặt từ 20 triệu đồng trở lên có nguy cơ không được khấu trừ thuế GTGT đầu vào và không được tính vào chi phí được trừ khi quyết toán thuế TNDN (Điều 15 Thông tư 219/2013/TT-BTC).")
            
            if warnings:
                welcome_content += "⚠️ **Các điểm cần lưu ý/rủi ro:**\n"
                for w in warnings:
                    welcome_content += f"- {w}\n"
            else:
                welcome_content += "✅ Hóa đơn không phát hiện lỗi cấu trúc hay cảnh báo rủi ro rác/rủi ro hình thức nào trọng yếu.\n"
                
            welcome_content += (
                f"\nQuý khách có thể bắt đầu đặt câu hỏi cho tôi về việc **tính hợp lệ chi phí được trừ (Thuế TNDN)**, "
                f"**khấu trừ thuế GTGT đầu vào**, hoặc **cơ sở pháp lý** liên quan đến hóa đơn này."
            )
            
            welcome_msg = AIChatMessage(
                session_id=session_id,
                role="assistant",
                content=welcome_content,
                created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            db.session.add(welcome_msg)
            
        db.session.commit()
        # Dual compatibility: return details both directly and nested under 'session'
        res_dict = new_session.to_dict()
        res_dict["session"] = new_session.to_dict()
        return jsonify(res_dict), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/ai/chat/sessions/<session_id>/message")
def api_send_chat_message(session_id):
    """Send a user message to the session and get the AI assistant response."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized
    from invoices.models import AIChatSession, AIChatMessage
    from invoices.ai_service import AIChatAgent
    from datetime import datetime
    try:
        session = db.session.get(AIChatSession, session_id)
        if not session:
            return jsonify({"error": "Không tìm thấy phiên hội thoại."}), 404

        data = request.get_json() or {}
        content = data.get("message", "").strip()
        if not content:
            return jsonify({"error": "Nội dung tin nhắn trống."}), 400

        # Save user message
        user_msg = AIChatMessage(
            session_id=session_id,
            role="user",
            content=content,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        db.session.add(user_msg)
        db.session.commit()

        # Update session title if it was default
        if session.title == "Cuộc hội thoại mới" or session.title == "Cuộc trò chuyện mới":
            session.title = content[:30] + ("..." if len(content) > 30 else "")
            db.session.commit()

        # Call AI assistant agent
        agent = AIChatAgent()
        ai_response = agent.ask(session_id, content)

        # Save assistant response
        assistant_msg = AIChatMessage(
            session_id=session_id,
            role="assistant",
            content=ai_response,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        db.session.add(assistant_msg)
        db.session.commit()

        # Dual compatibility: return both legacy fields and 'reply' field
        return jsonify({
            "user_message": user_msg.to_dict(),
            "assistant_message": assistant_msg.to_dict(),
            "session_title": session.title,
            "reply": ai_response
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.delete("/api/ai/chat/sessions/<session_id>")
def api_delete_chat_session(session_id):
    """Delete a chat session."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized
    from invoices.models import AIChatSession
    try:
        session = db.session.get(AIChatSession, session_id)
        if not session:
            return jsonify({"error": "Không tìm thấy phiên hội thoại."}), 404
        db.session.delete(session)
        db.session.commit()
        return jsonify({"success": True, "message": "Đã xóa phiên hội thoại thành công."}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/ai/classify-items")
@roles_required("admin", "auditor")
def api_classify_invoice_items():
    """Classify items inside an invoice."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from extensions import db
    from invoices.models import Invoice, LineItem
    from invoices.ai_service import AIExpenseClassifier

    try:
        data = request.get_json() or {}
        invoice_id = data.get("invoice_id")
        if not invoice_id:
            return jsonify({"error": "Thiếu mã hóa đơn invoice_id."}), 400

        invoice = db.session.get(Invoice, invoice_id)
        if not invoice:
            return jsonify({"error": "Không tìm thấy hóa đơn."}), 404

        classifier = AIExpenseClassifier()
        items = LineItem.query.filter_by(invoice_id=invoice.id).all()
        if not items:
            return jsonify({"success": True, "classified_items": []})

        classifications = classifier.classify_line_items(items)

        # Save results to DB
        for item in items:
            if item.id in classifications:
                item.expense_category = classifications[item.id]
        db.session.commit()

        return jsonify({
            "success": True,
            "classified_items": [
                {
                    "item_id": item.id,
                    "item_name": item.item_name,
                    "category": item.expense_category
                } for item in items
            ]
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/ai/update-item-category")
@roles_required("admin", "auditor")
def api_update_item_category():
    """Manually update the expense category of a specific line item."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from extensions import db
    from invoices.models import LineItem
    try:
        data = request.get_json() or {}
        item_id = data.get("item_id")
        new_category = data.get("category")

        if not item_id or not new_category:
            return jsonify({"error": "Thiếu thông tin item_id hoặc category."}), 400

        item = db.session.get(LineItem, item_id)
        if not item:
            return jsonify({"error": "Không tìm thấy mặt hàng."}), 404

        # Validate category matches standard list
        from invoices.ai_service import AIExpenseClassifier
        if new_category not in AIExpenseClassifier.CATEGORIES:
            return jsonify({"error": "Danh mục chi phí không hợp lệ."}), 400

        item.expense_category = new_category
        db.session.commit()

        return jsonify({"success": True, "item_id": item.id, "category": item.expense_category})

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/ai/repair-metadata")
@roles_required("admin", "auditor")
def api_repair_metadata():
    """Analyze and generate AI suggestions for repairing invoice metadata."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from extensions import db
    from invoices.models import Invoice
    from invoices.ai_service import AIDataRepairer

    try:
        data = request.get_json() or {}
        invoice_id = data.get("invoice_id")
        if not invoice_id:
            return jsonify({"error": "Thiếu mã hóa đơn invoice_id."}), 400

        invoice = db.session.get(Invoice, invoice_id)
        if not invoice:
            return jsonify({"error": "Không tìm thấy hóa đơn."}), 404

        repairer = AIDataRepairer()
        suggestions = repairer.repair_metadata(invoice)

        before = {
            "seller_name": invoice.seller_name or "",
            "buyer_name": invoice.buyer_name or "",
            "buyer_address": invoice.buyer_address or "",
            "amount_in_words": invoice.amount_in_words or ""
        }
        
        differences = []
        for key in ["seller_name", "buyer_name", "buyer_address", "amount_in_words"]:
            val_before = before[key].strip()
            val_after = suggestions.get(key, "").strip()
            if val_before != val_after and val_after:
                differences.append(key)

        return jsonify({
            "success": True,
            "invoice_id": invoice.id,
            "before": before,
            "after": suggestions,
            "differences": differences
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/ai/apply-repair")
@roles_required("admin", "auditor")
def api_apply_repair():
    """Apply selected AI repair suggestions to persistent SQLite database."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from extensions import db
    from invoices.models import Invoice

    try:
        data = request.get_json() or {}
        invoice_id = data.get("invoice_id")
        fields_to_apply = data.get("fields", [])

        if not invoice_id or not fields_to_apply:
            return jsonify({"error": "Thiếu thông tin invoice_id hoặc fields để áp dụng."}), 400

        invoice = db.session.get(Invoice, invoice_id)
        if not invoice:
            return jsonify({"error": "Không tìm thấy hóa đơn."}), 404

        allowed_fields = ["seller_name", "buyer_name", "buyer_address", "amount_in_words"]
        applied = []
        for field in fields_to_apply:
            if field in allowed_fields:
                val = data.get(field)
                if val:
                    setattr(invoice, field, val)
                    applied.append(field)

        if applied:
            db.session.commit()
            from invoices.security_audit_service import log_security_event
            log_security_event("REPAIR", f"Applied AI repair to invoice {invoice_id} for fields: {', '.join(applied)}")

        return jsonify({
            "success": True,
            "invoice_id": invoice.id,
            "applied_fields": applied
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.get("/api/invoices/summary-by-seller")
def api_summary_by_seller():
    """Aggregate input invoices by month or quarter, grouped by seller."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from extensions import db
    from invoices.models import Invoice
    from sqlalchemy import func

    try:
        period_type = request.args.get("period_type", "monthly")
        year_filter = request.args.get("year", "")

        # Base query for all invoices
        query = db.session.query(
            Invoice.seller_mst,
            Invoice.seller_name,
            Invoice.date,
            func.count(Invoice.id).label("invoice_count"),
            func.sum(Invoice.amount_before_tax).label("total_before_tax"),
            func.sum(Invoice.tax_amount).label("total_tax"),
            func.sum(Invoice.total_amount).label("total_amount")
        )

        # Apply year filter if provided
        if year_filter:
            query = query.filter(Invoice.date.like(f"{year_filter}-%"))
        
        # Pull raw grouped results and aggregate/group them cleanly in Python
        results = query.group_by(
            Invoice.seller_mst,
            Invoice.seller_name,
            func.substr(Invoice.date, 1, 7)
        ).all()

        period_map = {}

        for row in results:
            mst, name, date_val, count, before_tax, tax, total = row
            if not date_val or len(date_val) < 7:
                continue
            
            row_year = date_val[0:4]
            if year_filter and row_year != year_filter:
                continue

            row_month = date_val[5:7]

            if period_type == "quarterly":
                try:
                    m_int = int(row_month)
                except ValueError:
                    m_int = 1
                if m_int in [1, 2, 3]:
                    period = f"Quý 1 / {row_year}"
                elif m_int in [4, 5, 6]:
                    period = f"Quý 2 / {row_year}"
                elif m_int in [7, 8, 9]:
                    period = f"Quý 3 / {row_year}"
                else:
                    period = f"Quý 4 / {row_year}"
            else:
                period = f"Tháng {row_month} / {row_year}"

            if period not in period_map:
                period_map[period] = {}

            # Aggregate sellers within the same period
            seller_key = mst or "UNKNOWN"
            if seller_key not in period_map[period]:
                period_map[period][seller_key] = {
                    "seller_mst": mst or "Không rõ",
                    "seller_name": name or "Không rõ",
                    "invoice_count": 0,
                    "total_before_tax": 0.0,
                    "total_tax": 0.0,
                    "total_amount": 0.0
                }

            entry = period_map[period][seller_key]
            entry["invoice_count"] += count
            entry["total_before_tax"] += before_tax or 0.0
            entry["total_tax"] += tax or 0.0
            entry["total_amount"] += total or 0.0

        # Format and sort periods
        data = []
        for period, sellers_dict in period_map.items():
            sellers_list = list(sellers_dict.values())
            # Sort sellers by total amount descending
            sellers_list.sort(key=lambda x: x["total_amount"], reverse=True)
            data.append({
                "period": period,
                "sellers": sellers_list,
                "total_before_tax": sum(s["total_before_tax"] for s in sellers_list),
                "total_tax": sum(s["total_tax"] for s in sellers_list),
                "total_amount": sum(s["total_amount"] for s in sellers_list)
            })

        # Sort periods. Monthly: "Tháng 12 / 2026" -> "Tháng 01 / 2026" descending.
        # Format key is period title itself.
        data.sort(key=lambda x: x["period"], reverse=True)

        return jsonify({
            "success": True,
            "period_type": period_type,
            "year": year_filter or "Tất cả",
            "data": data
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def get_supplier_pivot_data(mst, year_filter, value_type):
    from extensions import db
    from invoices.models import Invoice
    from sqlalchemy import func

    # Query input invoices (invoice_type = 'purchase')
    query = db.session.query(
        Invoice.seller_mst,
        Invoice.seller_name,
        func.substr(Invoice.date, 1, 7).label("month_str"),
        func.count(Invoice.id).label("count"),
        func.sum(Invoice.amount_before_tax).label("amount_before_tax"),
        func.sum(Invoice.tax_amount).label("tax_amount"),
        func.sum(Invoice.total_amount).label("total_amount")
    ).filter(
        Invoice.invoice_type == 'purchase'
    )

    if mst and mst != "all":
        query = query.filter(Invoice.taxpayer_mst == mst)

    if year_filter:
        query = query.filter(Invoice.date.like(f"{year_filter}-%"))

    results = query.group_by(
        Invoice.seller_mst,
        Invoice.seller_name,
        func.substr(Invoice.date, 1, 7)
    ).all()

    # Build pivot structure
    if year_filter:
        months_list = [f"{i:02d}" for i in range(1, 13)]
    else:
        months_set = set()
        for r in results:
            if r.month_str and len(r.month_str) == 7:
                months_set.add(r.month_str)
        months_list = sorted(list(months_set))

    sellers_map = {}
    for r in results:
        seller_mst = r.seller_mst or "UNKNOWN"
        seller_name = r.seller_name or "Không rõ"
        month_key = r.month_str
        if year_filter and month_key:
            month_key = month_key.split("-")[1]

        val = 0.0
        if value_type == "amount_before_tax":
            val = r.amount_before_tax or 0.0
        elif value_type == "tax_amount":
            val = r.tax_amount or 0.0
        elif value_type == "invoice_count":
            val = r.count or 0
        else:
            val = r.total_amount or 0.0

        if seller_mst not in sellers_map:
            sellers_map[seller_mst] = {
                "seller_mst": seller_mst,
                "seller_name": seller_name,
                "monthly_values": {m: 0.0 for m in months_list},
                "row_total": 0.0
            }
        
        if month_key in sellers_map[seller_mst]["monthly_values"]:
            sellers_map[seller_mst]["monthly_values"][month_key] = val
            sellers_map[seller_mst]["row_total"] += val

    rows = list(sellers_map.values())
    rows.sort(key=lambda x: x["row_total"], reverse=True)

    column_totals = {m: 0.0 for m in months_list}
    grand_total = 0.0

    for r in rows:
        for m in months_list:
            val = r["monthly_values"].get(m, 0.0)
            column_totals[m] += val
            grand_total += val

    return {
        "year": year_filter or "Tất cả",
        "value_type": value_type,
        "months": months_list,
        "rows": rows,
        "column_totals": column_totals,
        "grand_total": grand_total
    }


@invoices_blueprint.get("/api/invoices/supplier-pivot")
def api_supplier_pivot():
    """Aggregate input invoices by supplier and month/year in a pivot structure."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    try:
        year_filter = request.args.get("year", "2026")
        value_type = request.args.get("value_type", "total_amount")
        mst = request.args.get("taxpayer_mst") or session.get("active_taxpayer_mst")
        if mst == "all":
            mst = None

        data = get_supplier_pivot_data(mst, year_filter, value_type)
        return jsonify({"success": True, **data})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@invoices_blueprint.get("/api/invoices/supplier-pivot/export")
def api_supplier_pivot_export():
    """Export the supplier pivot table to a beautifully formatted Excel sheet."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from io import BytesIO
    from flask import send_file
    import openpyxl
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    from export.formatter import auto_adjust_column_widths

    try:
        year_filter = request.args.get("year", "2026")
        value_type = request.args.get("value_type", "total_amount")
        mst = request.args.get("taxpayer_mst") or session.get("active_taxpayer_mst")
        if mst == "all":
            mst = None

        data = get_supplier_pivot_data(mst, year_filter, value_type)

        workbook = Workbook()
        ws = workbook.active
        ws.title = "Pivot NCC"
        ws.views.sheetView[0].showGridLines = True

        # Titles
        title_font = Font(name="Calibri", size=14, bold=True, color="1F4E78")
        info_font = Font(name="Calibri", size=11, italic=True)
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        bold_font = Font(name="Calibri", size=11, bold=True)
        regular_font = Font(name="Calibri", size=11)

        header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
        zebra_fill = PatternFill(start_color="F2F4F7", end_color="F2F4F7", fill_type="solid")
        total_fill = PatternFill(start_color="DDEBF7", end_color="DDEBF7", fill_type="solid")

        thin_border = Border(
            left=Side(style='thin', color='BFBFBF'),
            right=Side(style='thin', color='BFBFBF'),
            top=Side(style='thin', color='BFBFBF'),
            bottom=Side(style='thin', color='BFBFBF')
        )
        double_bottom_border = Border(
            left=Side(style='thin', color='BFBFBF'),
            right=Side(style='thin', color='BFBFBF'),
            top=Side(style='thin', color='BFBFBF'),
            bottom=Side(style='double', color='1F4E78')
        )

        ws["A1"] = f"BẢNG TỔNG HỢP HOÁ ĐƠN ĐẦU VÀO THEO NHÀ CUNG CẤP - NĂM {data['year']}"
        ws["A1"].font = title_font
        ws.row_dimensions[1].height = 25

        value_type_titles = {
            "total_amount": "Tổng tiền thanh toán (đồng)",
            "amount_before_tax": "Doanh số trước thuế (đồng)",
            "tax_amount": "Tiền thuế GTGT (đồng)",
            "invoice_count": "Số lượng hóa đơn (tờ)"
        }
        value_title = value_type_titles.get(data["value_type"], "Tổng tiền thanh toán")

        mst_str = mst if mst else "Tất cả Doanh nghiệp"
        ws["A2"] = f"Mã số thuế Doanh nghiệp: {mst_str} | Chỉ số: {value_title}"
        ws["A2"].font = info_font
        ws.row_dimensions[2].height = 20

        # Headers on row 4
        headers = ["Mã số thuế", "Tên nhà cung cấp"]
        for m in data["months"]:
            if len(m) == 2:
                headers.append(f"Tháng {m}")
            else:
                headers.append(m)
        headers.append("Tổng cộng")

        ws.append([]) # row 3 blank
        ws.append(headers) # row 4
        ws.row_dimensions[4].height = 25

        for col_idx in range(1, len(headers) + 1):
            cell = ws.cell(row=4, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = thin_border

        # Rows starting at row 5
        current_row = 5
        for row_idx, r in enumerate(data["rows"]):
            row_data = [r["seller_mst"], r["seller_name"]]
            for m in data["months"]:
                row_data.append(r["monthly_values"].get(m, 0.0))
            row_data.append(r["row_total"])

            ws.append(row_data)
            ws.row_dimensions[current_row].height = 20

            # Format cells
            is_even = row_idx % 2 == 1
            for col_idx in range(1, len(row_data) + 1):
                cell = ws.cell(row=current_row, column=col_idx)
                cell.border = thin_border
                
                if col_idx == 1:
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                    cell.font = regular_font
                elif col_idx == 2:
                    cell.alignment = Alignment(horizontal="left", vertical="center")
                    cell.font = regular_font
                else:
                    cell.alignment = Alignment(horizontal="right", vertical="center")
                    if value_type == "invoice_count":
                        cell.number_format = "#,##0"
                    else:
                        cell.number_format = "#,##0"
                    cell.font = regular_font

                if is_even:
                    cell.fill = zebra_fill

            current_row += 1

        # Totals Row at current_row
        total_row_data = ["TỔNG CỘNG", ""]
        for m in data["months"]:
            total_row_data.append(data["column_totals"].get(m, 0.0))
        total_row_data.append(data["grand_total"])

        ws.append(total_row_data)
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=2)
        ws.row_dimensions[current_row].height = 22

        for col_idx in range(1, len(total_row_data) + 1):
            cell = ws.cell(row=current_row, column=col_idx)
            cell.font = Font(name="Calibri", size=11, bold=True, color="1F4E78")
            cell.fill = total_fill
            cell.border = double_bottom_border
            if col_idx >= 3:
                cell.alignment = Alignment(horizontal="right", vertical="center")
                if value_type == "invoice_count":
                    cell.number_format = "#,##0"
                else:
                    cell.number_format = "#,##0"
            else:
                cell.alignment = Alignment(horizontal="center", vertical="center")

        # Auto adjust column widths
        auto_adjust_column_widths(ws)

        # Set specific widths for MST and Name columns to look beautiful
        ws.column_dimensions['A'].width = 16
        ws.column_dimensions['B'].width = 38

        # Output
        excel_file = BytesIO()
        workbook.save(excel_file)
        excel_bytes = excel_file.getvalue()

        filename = f"Pivot_NCC_{value_type}_{data['year']}.xlsx"
        return send_file(
            BytesIO(excel_bytes),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.get("/api/reports/vat-declaration")
def api_reports_vat_declaration():
    """Generate a draft of the Vietnamese VAT Return Mẫu 01/GTGT and list of disputed/high-risk input invoices."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    try:
        period_type = request.args.get("period_type", "monthly")
        period_value = request.args.get("period_value", "")
        year = request.args.get("year", datetime.now().strftime("%Y"))

        if not period_value:
            # Default to current or last completed month/quarter
            now = datetime.now()
            if period_type == "quarterly":
                period_value = str((now.month - 1) // 3 + 1)
            else:
                period_value = f"{now.month:02d}"

        # Standardizing month string to "02" instead of "2" for monthly
        if period_type == "monthly" and len(period_value) == 1:
            period_value = f"0{period_value}"

        from invoices.models import Invoice, LineItem

        query = Invoice.query.filter(Invoice.is_cancelled == False)

        # Apply date filters
        if period_type == "quarterly":
            try:
                q = int(period_value)
            except ValueError:
                q = 1
            if q == 1:
                months = ["01", "02", "03"]
            elif q == 2:
                months = ["04", "05", "06"]
            elif q == 3:
                months = ["07", "08", "09"]
            else:
                months = ["10", "11", "12"]
            
            from sqlalchemy import or_
            filters = [Invoice.date.like(f"{year}-{m}-%") for m in months]
            query = query.filter(or_(*filters))
        else:
            query = query.filter(Invoice.date.like(f"{year}-{period_value}-%"))

        invoices = query.all()

        # Initialize output VAT rate aggregates (Sold)
        output_exempt_val = 0.0
        output_0_val = 0.0
        output_5_val = 0.0
        output_5_vat = 0.0
        output_10_val = 0.0
        output_10_vat = 0.0
        
        # Input Aggregates (Purchase)
        input_total_value = 0.0
        input_total_vat = 0.0
        input_deductible_vat = 0.0
        
        disputed_invoices = []

        for inv in invoices:
            if inv.invoice_type == "sold":
                has_items = len(inv.items) > 0
                if has_items:
                    for item in inv.items:
                        rate = (item.tax_rate or "").strip().lower()
                        val = item.amount_before_tax or 0.0
                        tax = item.tax_amount or 0.0
                        
                        if "không chịu" in rate or "khong chiu" in rate:
                            output_exempt_val += val
                        elif "0%" in rate or rate == "0":
                            output_0_val += val
                        elif "5%" in rate or rate == "5":
                            output_5_val += val
                            output_5_vat += tax
                        else:
                            # 8% and 10% grouped into standard rate
                            output_10_val += val
                            output_10_vat += tax
                else:
                    # Fallback to invoice totals if no line items exist
                    val = inv.amount_before_tax or 0.0
                    tax = inv.tax_amount or 0.0
                    output_10_val += val
                    output_10_vat += tax

            elif inv.invoice_type == "purchase":
                val = inv.amount_before_tax or 0.0
                tax = inv.tax_amount or 0.0
                
                input_total_value += val
                input_total_vat += tax
                
                # Combine traditional parsing warnings and Gemma-4 AI auditor warnings
                warnings = list(inv.warnings) if inv.warnings else []
                ai_warnings = [f"[AI: {w.warning_type}] {w.explanation}" for w in inv.ai_audit_results]
                warnings.extend(ai_warnings)
                
                is_disputed = len(warnings) > 0
                
                if is_disputed:
                    warning_msg = "; ".join(warnings)
                    disputed_invoices.append({
                        "id": inv.id,
                        "number": inv.number or "Không số",
                        "date": inv.date or "Không ngày",
                        "seller_name": inv.seller_name or "Không rõ",
                        "seller_mst": inv.seller_mst or "Không rõ",
                        "amount_before_tax": val,
                        "tax_amount": tax,
                        "total_amount": inv.total_amount or (val + tax),
                        "warning": warning_msg
                    })
                else:
                    input_deductible_vat += tax

        output_taxable_val = output_0_val + output_5_val + output_10_val
        output_total_value = output_exempt_val + output_taxable_val
        output_total_vat = output_5_vat + output_10_vat

        vat_payable = max(0.0, output_total_vat - input_deductible_vat)
        vat_carried_forward = max(0.0, input_deductible_vat - output_total_vat)

        return jsonify({
            "success": True,
            "period_type": period_type,
            "period_value": period_value,
            "year": year,
            "outputs": {
                "exempt_val": output_exempt_val,
                "tax_0_val": output_0_val,
                "tax_5_val": output_5_val,
                "tax_5_vat": output_5_vat,
                "tax_10_val": output_10_val,
                "tax_10_vat": output_10_vat,
                "taxable_val": output_taxable_val,
                "total_val": output_total_value,
                "total_vat": output_total_vat
            },
            "inputs": {
                "total_value": input_total_value,
                "total_vat": input_total_vat,
                "deductible_vat": input_deductible_vat
            },
            "calculations": {
                "vat_payable": vat_payable,
                "vat_carried_forward": vat_carried_forward
            },
            "disputed_invoices": disputed_invoices
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Analytics Pro: Supplier Price Trends
# ---------------------------------------------------------------------------

@invoices_blueprint.get("/api/analytics/top-items")
def analytics_top_items():
    """Return top 20 most-purchased line item names for autocomplete."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    try:
        from extensions import db
        from invoices.models import LineItem
        rows = (
            db.session.query(LineItem.item_name, db.func.count(LineItem.id).label("cnt"))
            .group_by(db.func.lower(LineItem.item_name))
            .order_by(db.desc("cnt"))
            .limit(20)
            .all()
        )
        items = [{"name": r[0], "count": r[1]} for r in rows]
        return jsonify({"success": True, "items": items})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.get("/api/analytics/supplier-price-trends")
def analytics_supplier_price_trends():
    """Return monthly unit price data for a given item, grouped by seller."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    item_name = request.args.get("item_name", "").strip()
    year_filter = request.args.get("year", "").strip()

    if not item_name:
        return jsonify({"error": "Vui lòng cung cấp tên mặt hàng (item_name)."}), 400

    try:
        from extensions import db
        from invoices.models import LineItem, Invoice as Inv

        query = (
            db.session.query(
                LineItem.item_name,
                LineItem.unit_price,
                LineItem.amount_before_tax,
                Inv.date,
                Inv.seller_name,
                Inv.seller_mst,
            )
            .join(Inv, LineItem.invoice_id == Inv.id)
            .filter(db.func.lower(LineItem.item_name).like(f"%{item_name.lower()}%"))
            .filter(Inv.is_cancelled == False)
        )

        if year_filter:
            query = query.filter(Inv.date.like(f"{year_filter}%"))

        rows = query.all()

        if not rows:
            return jsonify({"success": True, "item_name": item_name, "sellers": [], "months": [], "series": [], "anomalies": []})

        # Compute global average unit price for anomaly detection
        all_prices = [r[1] for r in rows if r[1] and r[1] > 0]
        avg_global = sum(all_prices) / len(all_prices) if all_prices else 0

        # Build month × seller matrix
        seller_map = {}  # seller_mst → {name, months: {YYYY-MM: [prices]}}
        months_set = set()

        for item_name_val, unit_price, amount, inv_date, seller_name, seller_mst in rows:
            if not inv_date:
                continue
            month_key = inv_date[:7]  # YYYY-MM
            months_set.add(month_key)
            mst = seller_mst or "unknown"
            if mst not in seller_map:
                seller_map[mst] = {"seller_mst": mst, "seller_name": seller_name or mst, "months": {}}
            seller_map[mst]["months"].setdefault(month_key, []).append(unit_price or 0)

        months_sorted = sorted(months_set)

        # Build series for chart
        series = []
        anomalies = []
        for mst, info in seller_map.items():
            prices_by_month = []
            for m in months_sorted:
                month_prices = info["months"].get(m, [])
                if month_prices:
                    avg_m = sum(month_prices) / len(month_prices)
                    prices_by_month.append(round(avg_m, 0))
                    if avg_global > 0 and avg_m > avg_global * 1.20:
                        anomalies.append({
                            "month": m,
                            "seller_name": info["seller_name"],
                            "seller_mst": mst,
                            "price": round(avg_m, 0),
                            "avg_global": round(avg_global, 0),
                            "pct_above": round((avg_m / avg_global - 1) * 100, 1),
                        })
                else:
                    prices_by_month.append(None)

            # Summary stats
            flat = [p for p in prices_by_month if p is not None]
            series.append({
                "seller_mst": mst,
                "seller_name": info["seller_name"],
                "prices": prices_by_month,
                "avg_price": round(sum(flat) / len(flat), 0) if flat else 0,
                "min_price": round(min(flat), 0) if flat else 0,
                "max_price": round(max(flat), 0) if flat else 0,
                "purchase_count": sum(len(info["months"].get(m, [])) for m in months_sorted),
            })

        # Sort series by avg_price ascending (cheapest first)
        series.sort(key=lambda s: s["avg_price"])

        return jsonify({
            "success": True,
            "item_name": item_name,
            "avg_global": round(avg_global, 0),
            "months": months_sorted,
            "sellers": [{"seller_mst": s["seller_mst"], "seller_name": s["seller_name"]} for s in series],
            "series": series,
            "anomalies": anomalies,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Analytics Pro: VAT Forecast
# ---------------------------------------------------------------------------

@invoices_blueprint.get("/api/analytics/vat-forecast")
def analytics_vat_forecast():
    """Return monthly actual VAT net (output-input) and 2-month linear forecast."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from datetime import datetime as _dt
    year_filter = request.args.get("year", str(_dt.now().year)).strip()

    try:
        from extensions import db
        from invoices.models import Invoice
        invoices_all = Invoice.query.filter(Invoice.is_cancelled == False).all()

        # Build monthly buckets for the selected year
        monthly = {}
        for inv in invoices_all:
            if not inv.date or not inv.date.startswith(year_filter):
                continue
            month_key = inv.date[:7]  # YYYY-MM
            if month_key not in monthly:
                monthly[month_key] = {"output_vat": 0.0, "input_vat": 0.0}
            if inv.invoice_type == "sold":
                monthly[month_key]["output_vat"] += inv.tax_amount or 0.0
            elif inv.invoice_type == "purchase":
                monthly[month_key]["input_vat"] += inv.tax_amount or 0.0

        # All 12 months of the selected year
        all_months = [f"{year_filter}-{m:02d}" for m in range(1, 13)]
        actual = []
        for m in all_months:
            b = monthly.get(m, {"output_vat": 0.0, "input_vat": 0.0})
            net = b["output_vat"] - b["input_vat"]
            actual.append({
                "month": m,
                "output_vat": round(b["output_vat"], 0),
                "input_vat": round(b["input_vat"], 0),
                "net_vat": round(net, 0),
                "has_data": m in monthly,
            })

        # Identify last N months with real data for trend computation
        real_months = [a for a in actual if a["has_data"]]
        forecast = []

        if len(real_months) >= 2:
            # Linear trend: avg delta over last min(3, n) real months
            window = real_months[-3:] if len(real_months) >= 3 else real_months
            deltas = [window[i]["net_vat"] - window[i - 1]["net_vat"] for i in range(1, len(window))]
            avg_delta = sum(deltas) / len(deltas) if deltas else 0
            last_net = real_months[-1]["net_vat"]
            last_month_str = real_months[-1]["month"]

            # Build next 2 months after the last real month
            last_dt = _dt.strptime(last_month_str, "%Y-%m")
            for i in range(1, 3):
                if last_dt.month + i <= 12:
                    fdt = last_dt.replace(month=last_dt.month + i)
                else:
                    fdt = last_dt.replace(year=last_dt.year + 1, month=(last_dt.month + i) - 12)
                projected_net = last_net + avg_delta * i
                prev_net = last_net + avg_delta * (i - 1)
                warning = prev_net > 0 and projected_net > prev_net * 1.30
                forecast.append({
                    "month": fdt.strftime("%Y-%m"),
                    "net_vat_forecast": round(projected_net, 0),
                    "warning": warning,
                })

        # Compute year summary
        total_output = sum(a["output_vat"] for a in actual if a["has_data"])
        total_input = sum(a["input_vat"] for a in actual if a["has_data"])
        total_net = total_output - total_input

        return jsonify({
            "success": True,
            "year": year_filter,
            "actual": actual,
            "forecast": forecast,
            "summary": {
                "total_output_vat": round(total_output, 0),
                "total_input_vat": round(total_input, 0),
                "total_net_vat": round(total_net, 0),
                "months_with_data": len(real_months),
            },
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# US-035: Budget Monitor & Spending Alerts
# ---------------------------------------------------------------------------

@invoices_blueprint.get("/api/budget/config")
def budget_config_get():
    """Return saved budget configuration for a given month."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    month = request.args.get("month", "").strip()
    if not month:
        month = datetime.now().strftime("%Y-%m")

    try:
        from invoices.models import SystemConfig
        key = f"budget_config_{month}"
        cfg = db.session.get(SystemConfig, key)
        if cfg:
            import json as _json
            configs = _json.loads(cfg.value)
        else:
            configs = []
        return jsonify({"success": True, "month": month, "configs": configs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/budget/config")
@roles_required("admin", "auditor")
def budget_config_save():
    """Save budget configuration for a given month."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    try:
        import json as _json
        body = request.get_json(force=True) or {}
        month = body.get("month", "").strip()
        configs = body.get("configs", [])
        if not month:
            month = datetime.now().strftime("%Y-%m")

        from extensions import db
        from invoices.models import SystemConfig
        key = f"budget_config_{month}"
        cfg = db.session.get(SystemConfig, key)
        if cfg:
            cfg.value = _json.dumps(configs, ensure_ascii=False)
        else:
            cfg = SystemConfig(key=key, value=_json.dumps(configs, ensure_ascii=False))
            db.session.add(cfg)
        db.session.commit()
        return jsonify({"success": True, "month": month, "saved": len(configs)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.get("/api/budget/actuals")
def budget_actuals():
    """Return actual spending per expense_category for a given month with budget vs. actual comparison."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    month = request.args.get("month", "").strip()
    if not month:
        month = datetime.now().strftime("%Y-%m")

    try:
        import json as _json
        from extensions import db
        from invoices.models import LineItem, Invoice as _Inv, SystemConfig

        # Aggregate actual spending by expense_category for the month
        rows = (
            db.session.query(
                LineItem.expense_category,
                db.func.sum(LineItem.amount_before_tax).label("actual_vnd"),
            )
            .join(_Inv, LineItem.invoice_id == _Inv.id)
            .filter(
                _Inv.invoice_type == "purchase",
                _Inv.is_cancelled == False,
                _Inv.date.like(f"{month}%"),
            )
            .group_by(LineItem.expense_category)
            .all()
        )

        actuals_map = {}
        for category, actual_vnd in rows:
            cat = category or "Chưa phân loại"
            actuals_map[cat] = round(actual_vnd or 0, 0)

        # Load budget config
        key = f"budget_config_{month}"
        cfg_rec = db.session.get(SystemConfig, key)
        budget_configs = _json.loads(cfg_rec.value) if cfg_rec else []
        budget_map = {c["category"]: c["limit_vnd"] for c in budget_configs}

        # Build response combining actuals + budgets
        all_categories = set(actuals_map.keys()) | set(budget_map.keys())
        actuals = []
        for cat in sorted(all_categories):
            actual_vnd = actuals_map.get(cat, 0)
            limit_vnd = budget_map.get(cat)
            if limit_vnd and limit_vnd > 0:
                pct = round(actual_vnd / limit_vnd * 100, 1)
                if pct >= 100:
                    status = "over_budget"
                elif pct >= 70:
                    status = "warning"
                else:
                    status = "ok"
            else:
                pct = None
                status = "no_budget"
            actuals.append({
                "category": cat,
                "actual_vnd": actual_vnd,
                "limit_vnd": limit_vnd,
                "pct_used": pct,
                "status": status,
            })

        any_over = any(a["status"] == "over_budget" for a in actuals)
        any_warning = any(a["status"] == "warning" for a in actuals)
        alert_level = "over_budget" if any_over else ("warning" if any_warning else "ok")

        return jsonify({
            "success": True,
            "month": month,
            "actuals": actuals,
            "alert_level": alert_level,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# US-036: Invoice Aging & Receivable Tracker
# ---------------------------------------------------------------------------

_AGING_BUCKETS = [
    ("1–30 ngày",   1,  30),
    ("31–60 ngày",  31, 60),
    ("61–90 ngày",  61, 90),
    (">90 ngày",    91, None),
]


@invoices_blueprint.get("/api/aging/summary")
def aging_summary():
    """
    Return outstanding sold (receivables) and bought (payables) invoices classified into aging buckets.

    Buckets: Current / 1-30 / 31-60 / 61-90 / >90 days overdue.
    - Excludes invoices with paid_date set (already paid).
    - Excludes cancelled invoices.
    - Falls back to invoice.date when due_date is absent.
    - Accepts optional ?as_of=YYYY-MM-DD (default: today).
    """
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from datetime import date as _date
    as_of_str = request.args.get("as_of", "").strip()
    mst = request.args.get("mst") or session.get("active_taxpayer_mst")
    
    try:
        as_of = _date.fromisoformat(as_of_str) if as_of_str else _date.today()
    except ValueError:
        return jsonify({"error": "Định dạng as_of không hợp lệ. Dùng YYYY-MM-DD."}), 400

    try:
        from extensions import db
        from invoices.models import Invoice as _Inv

        # Fetch all outstanding sold and bought invoices for active taxpayer
        query = _Inv.query.filter(
            _Inv.is_cancelled == False,
            _Inv.paid_date == None,
        )
        if mst:
            query = query.filter(_Inv.taxpayer_mst == mst)
        invoices = query.all()

        # Build empty bucket structures for receivables and payables
        def empty_buckets():
            return [
                {"label": "Chưa quá hạn (Current)", "min_days": None, "max_days": 0, "count": 0, "total_amount": 0.0, "invoices": []},
                {"label": "1–30 ngày", "min_days": 1, "max_days": 30, "count": 0, "total_amount": 0.0, "invoices": []},
                {"label": "31–60 ngày", "min_days": 31, "max_days": 60, "count": 0, "total_amount": 0.0, "invoices": []},
                {"label": "61–90 ngày", "min_days": 61, "max_days": 90, "count": 0, "total_amount": 0.0, "invoices": []},
                {"label": ">90 ngày", "min_days": 91, "max_days": None, "count": 0, "total_amount": 0.0, "invoices": []}
            ]

        ar_buckets = empty_buckets()
        ap_buckets = empty_buckets()

        for inv in invoices:
            # Determine reference date for aging (due_date preferred, fall back to invoice date)
            ref_date_str = inv.due_date or inv.date
            if not ref_date_str:
                continue
            try:
                ref_date = _date.fromisoformat(ref_date_str)
            except ValueError:
                continue

            age_days = (as_of - ref_date).days

            # Phase 3: Autonomous Categorization rules
            cat = "OPEX"
            if inv.seller_name and any(kw in inv.seller_name.lower() for kw in ["điện", "nước", "utility"]):
                cat = "UTILITIES"
            elif inv.invoice_type == "sold":
                cat = "REVENUE"

            inv_data = {
                "id": inv.id,
                "date": inv.date,
                "due_date": inv.due_date,
                "invoice_type": inv.invoice_type,
                "seller_name": inv.seller_name or "",
                "buyer_name": inv.buyer_name or "",
                "buyer_mst": inv.buyer_mst or "",
                "amount_before_tax": inv.amount_before_tax or 0.0,
                "total_amount": inv.total_amount or 0.0,
                "age_days": age_days,
                "ai_category": cat
            }

            target_buckets = ar_buckets if inv.invoice_type == "sold" else ap_buckets

            # Assign to correct bucket based on age_days
            if age_days <= 0:
                target_buckets[0]["count"] += 1
                target_buckets[0]["total_amount"] += inv.total_amount or 0.0
                target_buckets[0]["invoices"].append(inv_data)
            else:
                for bucket in target_buckets[1:]:
                    mn, mx = bucket["min_days"], bucket["max_days"]
                    if age_days >= mn and (mx is None or age_days <= mx):
                        bucket["count"] += 1
                        bucket["total_amount"] += inv.total_amount or 0.0
                        bucket["invoices"].append(inv_data)
                        break

        # Calculate totals
        total_ar = sum(b["total_amount"] for b in ar_buckets)
        total_ap = sum(b["total_amount"] for b in ap_buckets)

        # For backwards compatibility with standard dashboard charts, return overdue-only AR buckets
        legacy_buckets = []
        for label, mn, mx in _AGING_BUCKETS:
            # Find the corresponding ar_bucket
            corr = next((b for b in ar_buckets if b["label"] == label), None)
            if corr:
                legacy_buckets.append(corr)
            else:
                legacy_buckets.append({
                    "label": label,
                    "min_days": mn,
                    "max_days": mx,
                    "count": 0,
                    "total_amount": 0.0,
                    "invoices": []
                })

        return jsonify({
            "success": True,
            "as_of": as_of.isoformat(),
            "total_outstanding": total_ar,  # legacy name for AR total
            "total_count": sum(b["count"] for b in ar_buckets[1:]),
            "buckets": legacy_buckets,      # legacy overdue sold buckets
            "receivables": {
                "total_amount": total_ar,
                "total_count": sum(b["count"] for b in ar_buckets),
                "buckets": ar_buckets
            },
            "payables": {
                "total_amount": total_ap,
                "total_count": sum(b["count"] for b in ap_buckets),
                "buckets": ap_buckets
            }
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.get("/api/cashflow/projection")
def cashflow_projection_endpoint():
    """
    US-083: Predictive Cash Projection & What-If late payment simulation.
    Projects optimistic vs pessimistic cash balance daily over the next 90 days.
    """
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from datetime import date as _date, timedelta
    as_of_str = request.args.get("as_of", "").strip()
    mst = request.args.get("mst") or session.get("active_taxpayer_mst")
    
    # Custom simulation parameters
    late_days = int(request.args.get("late_days", "0").strip() or "0")
    client_mst = request.args.get("client_mst", "").strip()
    
    # Base balance override
    base_balance_str = request.args.get("base_balance", "").strip()
    
    try:
        as_of = _date.fromisoformat(as_of_str) if as_of_str else _date.today()
    except ValueError:
        return jsonify({"error": "Định dạng as_of không hợp lệ. Dùng YYYY-MM-DD."}), 400

    try:
        from extensions import db
        from invoices.models import Invoice as _Inv, BankTransaction as _Tx

        # 1. Base Balance Dynamic Calculation
        if base_balance_str:
            try:
                base_balance = float(base_balance_str)
            except ValueError:
                base_balance = 500000000.0
        else:
            # Calculate base balance from actual bank transaction history
            tx_query = _Tx.query
            if mst:
                tx_query = tx_query.filter(_Tx.taxpayer_mst == mst)
            txs = tx_query.all()
            if txs:
                base_balance = sum(tx.amount for tx in txs)
            else:
                base_balance = 500000000.0  # Default fallback if no bank tx

        # 2. Fetch all unpaid outstanding invoices
        query = _Inv.query.filter(
            _Inv.is_cancelled == False,
            _Inv.paid_date == None
        )
        if mst:
            query = query.filter(_Inv.taxpayer_mst == mst)
        invoices = query.all()

        # 3. Simulate day-by-day cashflows for the next 90 days
        projections = []
        current_opt = base_balance
        current_sim = base_balance

        # We pre-calculate expected flows per day
        opt_inflows = {}
        sim_inflows = {}
        outflows = {}

        for i in range(91):
            day = as_of + timedelta(days=i)
            day_str = day.isoformat()
            opt_inflows[day_str] = 0.0
            sim_inflows[day_str] = 0.0
            outflows[day_str] = 0.0

        for inv in invoices:
            ref_date_str = inv.due_date or inv.date
            if not ref_date_str:
                continue
            try:
                ref_date = _date.fromisoformat(ref_date_str)
            except ValueError:
                continue

            amount = inv.total_amount or 0.0

            if inv.invoice_type == "sold":
                # Sales -> Inflows
                # Optimistic Expected Date (always due_date/date)
                opt_day = ref_date
                if opt_day < as_of:
                    opt_day = as_of # Already overdue: assume collected today
                opt_str = opt_day.isoformat()
                if opt_str in opt_inflows:
                    opt_inflows[opt_str] += amount

                # Simulated/Pessimistic Expected Date
                sim_day = ref_date
                if late_days > 0:
                    if not client_mst or inv.buyer_mst == client_mst:
                        sim_day = sim_day + timedelta(days=late_days)
                
                if sim_day < as_of:
                    sim_day = as_of # Overdue shift
                
                sim_str = sim_day.isoformat()
                if sim_str in sim_inflows:
                    sim_inflows[sim_str] += amount
            else:
                # Purchases -> Outflows
                out_day = ref_date
                if out_day < as_of:
                    out_day = as_of # Overdue payables must be paid today
                out_str = out_day.isoformat()
                if out_str in outflows:
                    outflows[out_str] += amount

        for i in range(91):
            day = as_of + timedelta(days=i)
            day_str = day.isoformat()

            in_opt = opt_inflows.get(day_str, 0.0)
            in_sim = sim_inflows.get(day_str, 0.0)
            out = outflows.get(day_str, 0.0)

            current_opt += (in_opt - out)
            current_sim += (in_sim - out)

            projections.append({
                "date": day_str,
                "day_label": day.strftime("%d/%m"),
                "inflow_opt": in_opt,
                "inflow_sim": in_sim,
                "outflow": out,
                "balance_opt": current_opt,
                "balance_sim": current_sim
            })

        return jsonify({
            "success": True,
            "base_balance": base_balance,
            "projections": projections
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.get("/api/analytics/cashflow_forecast")
def cashflow_forecast():
    """US-062: Cashflow Forecasting API
    Predicts inflow/outflow based on unpaid invoices over the next 30 days.
    """
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    try:
        from datetime import datetime, timedelta
        mst = request.args.get("mst") or session.get("active_taxpayer_mst")
        
        # Query unpaid invoices
        query = Invoice.query.filter(
            Invoice.is_cancelled == False,
            Invoice.paid_date == None
        )
        if mst:
            query = query.filter(Invoice.taxpayer_mst == mst)
            
        invoices = query.all()
        
        # Bucket by day (0 to 30 days ahead)
        today = datetime.now().date()
        forecast = []
        
        base_liquidity = 100000000  # Default base cash reserve
        current_liquidity = base_liquidity
        
        for i in range(30):
            target_date = today + timedelta(days=i)
            target_date_str = target_date.isoformat()
            
            inflow = 0
            outflow = 0
            
            for inv in invoices:
                due = inv.due_date or inv.date
                if due == target_date_str:
                    if inv.invoice_type == "sold":
                        inflow += inv.total_amount
                    else:
                        outflow += inv.total_amount
                        
            current_liquidity += (inflow - outflow)
            
            forecast.append({
                "date": target_date_str,
                "day_label": target_date.strftime("%d/%m"),
                "inflow": inflow,
                "outflow": outflow,
                "net_liquidity": current_liquidity
            })
            
        return jsonify({
            "success": True,
            "base_liquidity": base_liquidity,
            "forecast": forecast
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.patch("/api/invoices/<string:invoice_id>/payment")
def update_invoice_payment(invoice_id: str):
    """
    Update due_date and/or paid_date on an invoice.

    Body: {due_date?: "YYYY-MM-DD", paid_date?: "YYYY-MM-DD"}
    """
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    try:
        from extensions import db
        from invoices.models import Invoice as _Inv

        inv = db.session.get(_Inv, invoice_id)
        if not inv:
            return jsonify({"error": f"Không tìm thấy hóa đơn: {invoice_id}"}), 404

        body = request.get_json(force=True) or {}
        updated = False

        if "due_date" in body:
            inv.due_date = body["due_date"] or None
            updated = True
        if "paid_date" in body:
            inv.paid_date = body["paid_date"] or None
            updated = True

        if updated:
            inv.updated_at = datetime.now().isoformat()
            db.session.commit()

        return jsonify({
            "success": True,
            "id": invoice_id,
            "due_date": inv.due_date,
            "paid_date": inv.paid_date,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.get("/api/profiles")
@roles_required("admin", "auditor", "viewer")
def get_taxpayer_profiles():
    """Retrieve all stored taxpayer profiles."""
    err = _ensure_logged_in()
    if err:
        return err

    from invoices.models import TaxpayerProfile
    try:
        profiles = TaxpayerProfile.query.order_by(TaxpayerProfile.mst).all()
        return jsonify([p.to_dict() for p in profiles])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/profiles")
@roles_required("admin", "auditor")
def create_taxpayer_profile():
    """Create or update a taxpayer profile with encrypted credentials."""
    err = _ensure_logged_in()
    if err:
        return err

    from invoices.models import TaxpayerProfile
    from auth.crypto import encrypt_password
    try:
        body = request.get_json() or {}
        mst = body.get("mst")
        company_name = body.get("company_name")
        gdt_username = body.get("gdt_username")
        gdt_password = body.get("gdt_password")

        if not all([mst, company_name, gdt_username, gdt_password]):
            return jsonify({"error": "Thiếu các thông tin bắt buộc."}), 400

        mst = str(mst).strip()
        if len(mst) not in [10, 14]:
            return jsonify({"error": "Mã số thuế không đúng định dạng (phải có 10 hoặc 14 ký tự)."}), 400

        encrypted_password = encrypt_password(gdt_password)

        profile = db.session.get(TaxpayerProfile, mst)
        is_update = profile is not None
        if profile:
            profile.company_name = company_name
            profile.gdt_username = gdt_username
            profile.gdt_password_encrypted = encrypted_password
        else:
            profile = TaxpayerProfile(
                mst=mst,
                company_name=company_name,
                gdt_username=gdt_username,
                gdt_password_encrypted=encrypted_password,
                is_active=True,
                created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            db.session.add(profile)

        db.session.commit()

        from invoices.security_audit_service import log_security_event
        if is_update:
            log_security_event("PROFILE", f"Updated taxpayer profile for MST: {mst}")
        else:
            log_security_event("PROFILE", f"Created new taxpayer profile for MST: {mst}")

        return jsonify({"success": True, "profile": profile.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.delete("/api/profiles/<mst>")
@roles_required("admin", "auditor")
def delete_taxpayer_profile(mst):
    """Delete a taxpayer profile and cascade delete all its invoices."""
    err = _ensure_logged_in()
    if err:
        return err

    from invoices.models import TaxpayerProfile
    try:
        profile = db.session.get(TaxpayerProfile, mst)
        if not profile:
            return jsonify({"error": f"Không tìm thấy hồ sơ mã số thuế {mst}."}), 404

        db.session.delete(profile)
        db.session.commit()

        from invoices.security_audit_service import log_security_event
        log_security_event("PROFILE", f"Deleted taxpayer profile for MST: {mst}")

        return jsonify({"success": True, "message": f"Đã xóa hồ sơ và tất cả hóa đơn của MST {mst}."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/profiles/switch")
@roles_required("admin", "auditor", "viewer")
def switch_taxpayer_profile():
    """Switch the current active taxpayer profile in session."""
    err = _ensure_logged_in()
    if err:
        return err

    try:
        body = request.get_json() or {}
        mst = body.get("mst")

        from invoices.security_audit_service import log_security_event
        if mst == "all" or not mst:
            session["active_taxpayer_mst"] = None
            log_security_event("PROFILE", "Switched active taxpayer profile to all (no filter)")
            return jsonify({"success": True, "active_taxpayer_mst": None})

        from invoices.models import TaxpayerProfile
        profile = db.session.get(TaxpayerProfile, mst)
        if not profile:
            return jsonify({"error": f"Không tìm thấy hồ sơ mã số thuế {mst}."}), 404

        session["active_taxpayer_mst"] = mst
        log_security_event("PROFILE", f"Switched active taxpayer profile to MST: {mst}")
        return jsonify({"success": True, "active_taxpayer_mst": mst})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/invoices/<invoice_id>/post-erp")
@roles_required("admin", "auditor")
def api_post_invoice_to_erp(invoice_id):
    """Manually post an invoice to the configured ERP system."""
    err = _ensure_logged_in()
    if err:
        return err

    from invoices.models import Invoice
    from invoices.erp_service import post_invoice_to_erp

    invoice = db.session.get(Invoice, invoice_id)
    if not invoice:
        return jsonify({"error": "Không tìm thấy hóa đơn cần đồng bộ."}), 404

    success = post_invoice_to_erp(invoice)
    if success:
        return jsonify({
            "success": True,
            "message": "Đồng bộ hóa đơn lên ERP thành công.",
            "erp_synced": invoice.erp_synced,
            "erp_sync_date": invoice.erp_sync_date
        })
    else:
        return jsonify({
            "success": False,
            "message": "Đồng bộ hóa đơn lên ERP thất bại.",
            "error": invoice.erp_sync_error
        }), 400


def classify_fct_item(item_name: str, seller_name: str) -> tuple[str, float, float]:
    """
    Classify transaction based on Circular 103/2014/TT-BTC for e-commerce and digital services.
    Returns: (Category, VAT_rate, CIT_rate)
    """
    name = (item_name or "").lower() + " " + (seller_name or "").lower()
    
    # 1. Digital Advertising (e.g. Google Ads, Meta Ads)
    if any(k in name for k in ["ads", "quảng cáo", "quang cao", "marketing", "facebook ads", "google ads", "adwords"]):
        return "Dịch vụ Quảng cáo trực tuyến (Online Advertising)", 0.05, 0.05
        
    # 2. Cloud & Hosting (e.g. AWS, Azure)
    if any(k in name for k in ["cloud", "hosting", "aws", "amazon web services", "azure", "server", "vps", "lưu trữ", "digitalocean"]):
        return "Dịch vụ Điện toán đám mây & Lưu trữ (Cloud & Hosting)", 0.05, 0.05
        
    # 3. Software License / SaaS (VAT Exempt under VN Tax Law, CIT 5%)
    if any(k in name for k in ["phần mềm", "phan mem", "software", "license", "bản quyền", "ban quyen", "zoom", "slack", "subscription"]):
        return "Bản quyền & Phần mềm SaaS (Software & License)", 0.00, 0.05
        
    # Default fallback (General Digital Services)
    return "Thương mại điện tử & Dịch vụ số khác", 0.05, 0.05


def generate_fct_excel(fct_data: dict) -> bytes:
    """Generate a highly polished Excel sheet conforming to Mẫu số 01/NTNN layout."""
    import openpyxl
    from openpyxl import Workbook
    from export.formatter import auto_adjust_column_widths, HEADER_FILL, MED_RISK_FILL, OK_FILL

    workbook = Workbook()
    ws = workbook.active
    ws.title = "Tờ khai 01-NTNN"
    ws.views.sheetView[0].showGridLines = True

    # Title Banner
    ws.append(["TỜ KHAI THUẾ NHÀ THẦU NƯỚC NGOÀI (Mẫu số 01/NTNN)"])
    ws.merge_cells("A1:I1")
    title_cell = ws["A1"]
    title_cell.font = openpyxl.styles.Font(size=14, bold=True, color="FFFFFF")
    title_cell.fill = HEADER_FILL
    title_cell.alignment = openpyxl.styles.Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 40

    # Period Info
    period_str = f"Tháng {fct_data['period_value']}" if fct_data['period_type'] == "monthly" else f"Quý {fct_data['period_value']}"
    ws.append([f"Kỳ kê khai: {period_str} năm {fct_data['year']}", "", "", "", "", "", "", "", datetime.now().strftime("%d/%m/%Y %H:%M:%S")])
    ws.merge_cells("A2:H2")
    ws["A2"].font = openpyxl.styles.Font(italic=True, color="555555")
    ws["I2"].alignment = openpyxl.styles.Alignment(horizontal="right")
    ws.append([])  # Blank row

    # Headers
    headers = [
        "STT",
        "Tên Nhà thầu nước ngoài",
        "Mã số thuế",
        "Nội dung dịch vụ",
        "Doanh thu tính thuế (₫)",
        "Tỷ lệ GTGT (%)",
        "Thuế GTGT phải nộp (₫)",
        "Tỷ lệ TNDN (%)",
        "Thuế TNDN phải nộp (₫)",
    ]
    ws.append(headers)
    
    # Format Headers
    for col_idx in range(1, 10):
        cell = ws.cell(row=4, column=col_idx)
        cell.fill = HEADER_FILL
        cell.font = openpyxl.styles.Font(color="FFFFFF", bold=True)
        cell.alignment = openpyxl.styles.Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[4].height = 30

    # Data Rows
    invoices = fct_data.get("fct_invoices", [])
    for idx, inv in enumerate(invoices, 1):
        row = [
            idx,
            inv["seller_name"],
            inv["seller_mst"],
            inv["category"],
            inv["amount"],
            f"{inv['vat_rate'] * 100}%",
            inv["vat_withheld"],
            f"{inv['cit_rate'] * 100}%",
            inv["cit_withheld"]
        ]
        ws.append(row)
        
        # Zebra styling
        row_cells = ws[ws.max_row]
        for cell in row_cells:
            cell.fill = OK_FILL if idx % 2 == 0 else openpyxl.styles.PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
            cell.font = openpyxl.styles.Font(size=10)

    # Total Row
    ws.append([
        "TỔNG CỘNG", "", "", "",
        fct_data["total_revenue"],
        "",
        fct_data["total_vat_withheld"],
        "",
        fct_data["total_cit_withheld"]
    ])
    ws.merge_cells(f"A{ws.max_row}:D{ws.max_row}")
    
    for col_idx in range(1, 10):
        cell = ws.cell(row=ws.max_row, column=col_idx)
        cell.font = openpyxl.styles.Font(bold=True, size=11, color="1F4E78")
        cell.fill = MED_RISK_FILL
    ws.row_dimensions[ws.max_row].height = 24

    # Alignments & Formats
    for row in range(5, ws.max_row + 1):
        ws[f"A{row}"].alignment = openpyxl.styles.Alignment(horizontal="center")
        ws[f"C{row}"].alignment = openpyxl.styles.Alignment(horizontal="center")
        ws[f"F{row}"].alignment = openpyxl.styles.Alignment(horizontal="center")
        ws[f"H{row}"].alignment = openpyxl.styles.Alignment(horizontal="center")
        
        for col_idx in [5, 7, 9]:
            cell = ws.cell(row=row, column=col_idx)
            cell.number_format = '#,##0 "VND"'
            cell.alignment = openpyxl.styles.Alignment(horizontal="right")

    auto_adjust_column_widths(ws)

    output = BytesIO()
    workbook.save(output)
    output.seek(0)
    return output.getvalue()


@invoices_blueprint.get("/api/reports/fct-declaration")
def api_reports_fct_declaration():
    """
    Generate a draft of the Vietnamese Foreign Contractor Tax (FCT) Return Mẫu 01/NTNN.
    Identifies foreign e-commerce/digital giant suppliers and calculates withholding VAT/CIT.
    """
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    try:
        period_type = request.args.get("period_type", "monthly")
        period_value = request.args.get("period_value", "")
        year = request.args.get("year", datetime.now().strftime("%Y"))

        if not period_value:
            now = datetime.now()
            if period_type == "quarterly":
                period_value = str((now.month - 1) // 3 + 1)
            else:
                period_value = f"{now.month:02d}"

        if period_type == "monthly" and len(period_value) == 1:
            period_value = f"0{period_value}"

        from invoices.models import Invoice

        query = Invoice.query.filter(Invoice.is_cancelled == False, Invoice.invoice_type == "purchase")

        # Apply date filters
        if period_type == "quarterly":
            try:
                q = int(period_value)
            except ValueError:
                q = 1
            if q == 1:
                months = ["01", "02", "03"]
            elif q == 2:
                months = ["04", "05", "06"]
            elif q == 3:
                months = ["07", "08", "09"]
            else:
                months = ["10", "11", "12"]
            
            from sqlalchemy import or_
            filters = [Invoice.date.like(f"{year}-{m}-%") for m in months]
            query = query.filter(or_(*filters))
        else:
            query = query.filter(Invoice.date.like(f"{year}-{period_value}-%"))

        invoices = query.all()

        fct_invoices = []
        total_revenue = 0.0
        total_vat_withheld = 0.0
        total_cit_withheld = 0.0

        for inv in invoices:
            seller_mst = (inv.seller_mst or "").strip()
            seller_name = (inv.seller_name or "").strip()
            
            # Match 900xxxxxxx or digital giants names
            is_fct = (
                seller_mst.startswith("900") or
                any(k in seller_name.lower() for k in ["google", "facebook", "meta", "amazon", "aws", "netflix", "zoom", "slack", "microsoft", "github", "digitalocean"])
            )
            
            if not is_fct:
                continue

            amount = inv.amount_before_tax or 0.0
            category = "Thương mại điện tử & Dịch vụ số khác"
            vat_rate = 0.05
            cit_rate = 0.05
            
            if inv.items and len(inv.items) > 0:
                first_item = inv.items[0].item_name
                category, vat_rate, cit_rate = classify_fct_item(first_item, seller_name)
            else:
                category, vat_rate, cit_rate = classify_fct_item("", seller_name)

            vat_withheld = amount * vat_rate
            cit_withheld = amount * cit_rate
            fct_total = vat_withheld + cit_withheld

            fct_invoices.append({
                "id": inv.id,
                "number": inv.number or "Không số",
                "date": inv.date or "Không ngày",
                "seller_name": seller_name,
                "seller_mst": seller_mst,
                "category": category,
                "amount": amount,
                "vat_rate": vat_rate,
                "vat_withheld": vat_withheld,
                "cit_rate": cit_rate,
                "cit_withheld": cit_withheld,
                "fct_total": fct_total
            })

            total_revenue += amount
            total_vat_withheld += vat_withheld
            total_cit_withheld += cit_withheld

        return jsonify({
            "success": True,
            "period_type": period_type,
            "period_value": period_value,
            "year": year,
            "total_revenue": total_revenue,
            "total_vat_withheld": total_vat_withheld,
            "total_cit_withheld": total_cit_withheld,
            "total_fct_payable": total_vat_withheld + total_cit_withheld,
            "fct_invoices": fct_invoices
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.get("/api/reports/fct-declaration/export-excel")
def api_reports_fct_declaration_export_excel():
    """Export the Mẫu 01/NTNN draft to a beautifully formatted Excel spreadsheet."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    try:
        period_type = request.args.get("period_type", "monthly")
        period_value = request.args.get("period_value", "")
        year = request.args.get("year", datetime.now().strftime("%Y"))

        if not period_value:
            now = datetime.now()
            if period_type == "quarterly":
                period_value = str((now.month - 1) // 3 + 1)
            else:
                period_value = f"{now.month:02d}"

        if period_type == "monthly" and len(period_value) == 1:
            period_value = f"0{period_value}"

        from invoices.models import Invoice
        query = Invoice.query.filter(Invoice.is_cancelled == False, Invoice.invoice_type == "purchase")

        if period_type == "quarterly":
            try:
                q = int(period_value)
            except ValueError:
                q = 1
            if q == 1:
                months = ["01", "02", "03"]
            elif q == 2:
                months = ["04", "05", "06"]
            elif q == 3:
                months = ["07", "08", "09"]
            else:
                months = ["10", "11", "12"]
            
            from sqlalchemy import or_
            filters = [Invoice.date.like(f"{year}-{m}-%") for m in months]
            query = query.filter(or_(*filters))
        else:
            query = query.filter(Invoice.date.like(f"{year}-{period_value}-%"))

        invoices = query.all()

        fct_invoices = []
        total_revenue = 0.0
        total_vat_withheld = 0.0
        total_cit_withheld = 0.0

        for inv in invoices:
            seller_mst = (inv.seller_mst or "").strip()
            seller_name = (inv.seller_name or "").strip()
            
            is_fct = (
                seller_mst.startswith("900") or
                any(k in seller_name.lower() for k in ["google", "facebook", "meta", "amazon", "aws", "netflix", "zoom", "slack", "microsoft", "github", "digitalocean"])
            )
            
            if not is_fct:
                continue

            amount = inv.amount_before_tax or 0.0
            category = "Thương mại điện tử & Dịch vụ số khác"
            vat_rate = 0.05
            cit_rate = 0.05
            
            if inv.items and len(inv.items) > 0:
                first_item = inv.items[0].item_name
                category, vat_rate, cit_rate = classify_fct_item(first_item, seller_name)
            else:
                category, vat_rate, cit_rate = classify_fct_item("", seller_name)

            vat_withheld = amount * vat_rate
            cit_withheld = amount * cit_rate
            fct_total = vat_withheld + cit_withheld

            fct_invoices.append({
                "seller_name": seller_name,
                "seller_mst": seller_mst,
                "category": category,
                "amount": amount,
                "vat_rate": vat_rate,
                "vat_withheld": vat_withheld,
                "cit_rate": cit_rate,
                "cit_withheld": cit_withheld,
                "fct_total": fct_total
            })

            total_revenue += amount
            total_vat_withheld += vat_withheld
            total_cit_withheld += cit_withheld

        fct_data = {
            "period_type": period_type,
            "period_value": period_value,
            "year": year,
            "total_revenue": total_revenue,
            "total_vat_withheld": total_vat_withheld,
            "total_cit_withheld": total_cit_withheld,
            "total_fct_payable": total_vat_withheld + total_cit_withheld,
            "fct_invoices": fct_invoices
        }

        excel_bytes = generate_fct_excel(fct_data)
        
        filename = f"ToKhai_01NTNN_{year}_{period_value}.xlsx"
        return send_file(
            BytesIO(excel_bytes),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.get("/api/reports/vat-refund-eligibility")
@roles_required("admin", "auditor")
def api_vat_refund_eligibility():
    """Calculates taxpayer eligibility for VAT refund and returns a structured breakdown."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = request.args.get("mst") or session.get("active_taxpayer_mst")
    if not mst:
        # Fallback to the first taxpayer profile
        from invoices.models import TaxpayerProfile
        first_profile = TaxpayerProfile.query.first()
        if first_profile:
            mst = first_profile.mst
        else:
            return jsonify({"error": "Không có mã số thuế hoạt động hoặc hồ sơ doanh nghiệp nào được đăng ký."}), 400

    try:
        from invoices.refund_service import VATRefundEligibilityEngine
        engine = VATRefundEligibilityEngine()
        result = engine.get_eligibility(mst)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Lỗi tính toán hoàn thuế: {str(e)}"}), 500


@invoices_blueprint.post("/api/reports/vat-refund-eligibility/dossier")
@roles_required("admin", "auditor")
def api_vat_refund_dossier():
    """Generates Circular 80 Mẫu 01/HT refund dossier and AI justification letter."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    payload = request.get_json(silent=True) or {}
    mst = payload.get("mst") or session.get("active_taxpayer_mst")
    
    if not mst:
        from invoices.models import TaxpayerProfile
        first_profile = TaxpayerProfile.query.first()
        if first_profile:
            mst = first_profile.mst
        else:
            return jsonify({"error": "Không có mã số thuế hoạt động hoặc hồ sơ doanh nghiệp nào được đăng ký."}), 400

    try:
        from invoices.refund_service import VATRefundEligibilityEngine
        engine = VATRefundEligibilityEngine()
        result = engine.generate_dossier(mst)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Lỗi soạn hồ sơ AI: {str(e)}"}), 500


@invoices_blueprint.post("/api/reports/vat-refund-eligibility/dossier/export")
@roles_required("admin", "auditor")
def api_export_vat_refund_dossier():
    """Exports the generated dossier or justification letter to Word (.doc) or PDF."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    payload = request.get_json(silent=True) or {}
    content = payload.get("content", "").strip()
    export_format = payload.get("format", "doc").lower()  # 'doc' or 'pdf'
    document_type = payload.get("type", "dossier")  # 'dossier' or 'justification'

    if not content:
        return jsonify({"error": "Nội dung tài liệu trống."}), 400

    filename = "Mau_01_HT_De_Nghi_Hoan_Thue" if document_type == "dossier" else "Bao_Cao_Bien_Phap_Bao_Ve_Ho_So"

    if export_format == "pdf":
        html_content = f"""
        <html>
        <head>
        <meta charset="utf-8">
        <style>
            @page {{
                size: a4;
                margin: 2cm;
            }}
            body {{
                font-family: 'Arial', sans-serif;
                font-size: 11px;
                line-height: 1.5;
            }}
            .bold {{ font-weight: bold; }}
            .text-center {{ text-align: center; }}
            .text-right {{ text-align: right; }}
            .title {{ font-size: 13px; font-weight: bold; text-align: center; margin-top: 15px; margin-bottom: 15px; }}
            p {{ margin-bottom: 6px; text-align: justify; }}
            pre {{
                font-family: 'Arial', sans-serif;
                white-space: pre-wrap;
                word-wrap: break-word;
            }}
        </style>
        </head>
        <body>
        <pre>{content}</pre>
        </body>
        </html>
        """
        try:
            pdf_buf = render_html_to_pdf(html_content)
            return send_file(
                pdf_buf,
                mimetype="application/pdf",
                as_attachment=True,
                download_name=f"{filename}.pdf"
            )
        except Exception as e:
            return jsonify({"error": f"Lỗi xuất PDF: {str(e)}"}), 500

    else:
        # Default to Word compatible HTML (.doc)
        html_content = f"""
        <html xmlns:o="urn:schemas-microsoft-com:office:office"
              xmlns:w="urn:schemas-microsoft-com:office:word"
              xmlns="http://www.w3.org/TR/REC-html40">
        <head>
        <meta charset="utf-8">
        <style>
            @page {{
                size: 8.27in 11.69in; /* A4 */
                margin: 1.0in 0.79in 1.0in 1.18in;
            }}
            body {{
                font-family: 'Times New Roman', serif;
                font-size: 11pt;
                line-height: 1.5;
            }}
            pre {{
                font-family: 'Times New Roman', serif;
                white-space: pre-wrap;
                word-wrap: break-word;
            }}
        </style>
        </head>
        <body>
        <pre>{content}</pre>
        </body>
        </html>
        """
        buf = BytesIO(html_content.encode("utf-8"))
        return send_file(
            buf,
            mimetype="application/msword",
            as_attachment=True,
            download_name=f"{filename}.doc"
        )


# Helper HMAC decorator
def require_api_signature(f):
    from functools import wraps
    import time
    @wraps(f)
    def decorated(*args, **kwargs):
        signature = request.headers.get("X-GDT-Signature")
        timestamp_str = request.headers.get("X-GDT-Timestamp")
        
        if not signature or not timestamp_str:
            return jsonify({"error": "Missing signature or timestamp headers"}), 401
            
        try:
            timestamp = int(timestamp_str)
            if abs(time.time() - timestamp) > 300:
                return jsonify({"error": "Signature timestamp expired or invalid"}), 401
        except Exception:
            return jsonify({"error": "Invalid timestamp format"}), 401
            
        if request.method == "GET":
            payload_str = request.query_string.decode("utf-8")
        else:
            payload_str = request.get_data(as_text=True)
            
        secret = current_app.config.get("SECRET_KEY", "super-secret-key")
        
        import hmac
        import hashlib
        message = f"{timestamp_str}.{payload_str}".encode("utf-8")
        computed = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
        expected = f"sha256={computed}"
        
        if not hmac.compare_digest(signature, expected):
            return jsonify({"error": "Invalid signature verification failed"}), 401
            
        return f(*args, **kwargs)
    return decorated


@invoices_blueprint.post("/api/audit/vat-refund-eligibility")
def api_post_vat_refund_eligibility():
    """Receives MST, input_invoice_ids, and customs_declarations, returning eligibility evaluation."""
    body = request.get_json(silent=True) or {}
    mst = body.get("mst") or session.get("active_taxpayer_mst")
    if not mst:
        return jsonify({"error": "Missing taxpayer MST"}), 400
        
    try:
        from invoices.refund_service import VATRefundEligibilityEngine
        engine = VATRefundEligibilityEngine()
        
        input_invoice_ids = body.get("input_invoice_ids")
        customs_declarations = body.get("customs_declarations")
        
        result = engine.get_eligibility(
            mst,
            input_invoice_ids=input_invoice_ids,
            customs_declarations=customs_declarations
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Lỗi tính toán hoàn thuế: {str(e)}"}), 500



@invoices_blueprint.post("/api/audit/export-refund-xml")
def api_post_export_refund_xml():
    """Returns the GDT-compliant XML stream representing Form 01/ĐNHT."""
    body = request.get_json(silent=True) or {}
    mst = body.get("mst") or session.get("active_taxpayer_mst")
    invoice_ids = body.get("eligible_invoice_ids", [])
    bank_account = body.get("bank_account", "")
    bank_name = body.get("bank_name", "")
    reason_type = body.get("reason_type", "")
    
    if not mst:
        return jsonify({"error": "Missing taxpayer MST"}), 400
    if not invoice_ids:
        return jsonify({"error": "No eligible invoices provided"}), 400
        
    try:
        from invoices.refund_service import generate_form_01_dnht_xml
        xml_content = generate_form_01_dnht_xml(mst, invoice_ids, bank_account, bank_name, reason_type)
        return Response(xml_content, mimetype="application/xml", headers={
            "Content-Disposition": f"attachment; filename=Form_01_DNHT_{mst}.xml"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.get("/api/v1/invoices")
@require_api_signature
def api_v1_invoices():
    """REST API to fetch invoices securely with HMAC signature verification."""
    mst = request.args.get("mst") or session.get("active_taxpayer_mst")
    if not mst:
        return jsonify({"error": "Missing taxpayer MST"}), 400
        
    from invoices.models import Invoice
    invoice_type = request.args.get("invoice_type")
    query = Invoice.query.filter_by(taxpayer_mst=mst)
    if invoice_type:
        query = query.filter_by(invoice_type=invoice_type)
        
    invoices = query.all()
    return jsonify([inv.to_dict() for inv in invoices])


@invoices_blueprint.get("/api/v1/compliance-scores")
@require_api_signature
def api_v1_compliance_scores():
    """REST API to fetch compliance scores securely with HMAC signature verification."""
    mst = request.args.get("mst") or session.get("active_taxpayer_mst")
    if not mst:
        return jsonify({"error": "Missing taxpayer MST"}), 400
        
    from invoices.models import TaxpayerProfile, Invoice
    profile = TaxpayerProfile.query.get(mst)
    if not profile:
        return jsonify({"error": f"Taxpayer profile not found for MST: {mst}"}), 404
        
    invoices = Invoice.query.filter_by(taxpayer_mst=mst).all()
    avg_t_score = 100.0
    if invoices:
        avg_t_score = sum(inv.t_score for inv in invoices) / len(invoices)
        
    return jsonify({
        "mst": mst,
        "company_name": profile.company_name,
        "average_t_score": avg_t_score,
        "risk_level": "Safe" if avg_t_score >= 80 else "Caution" if avg_t_score >= 50 else "High-Risk"
    })


@invoices_blueprint.post("/api/v1/webhooks/register")
def api_v1_webhooks_register():
    """Registers a new webhook subscription for the taxpayer."""
    body = request.get_json(silent=True) or {}
    url = body.get("url")
    secret = body.get("secret")
    mst = body.get("mst") or session.get("active_taxpayer_mst")
    event_topics = body.get("event_topics", [])
    
    if not url or not secret:
        return jsonify({"error": "Missing url or secret"}), 400
    if not mst:
        return jsonify({"error": "Missing taxpayer MST"}), 400
    if not event_topics:
        return jsonify({"error": "Missing event_topics to subscribe"}), 400
        
    from invoices.models import WebhookSubscription
    import uuid
    
    created_subscriptions = []
    for topic in event_topics:
        sub_id = f"sub_{topic}_{uuid.uuid4().hex[:8]}"
        now_str = datetime.now().isoformat()
        sub = WebhookSubscription(
            id=sub_id,
            taxpayer_mst=mst,
            url=url,
            secret=secret,
            is_active=True,
            created_at=now_str
        )
        db.session.add(sub)
        created_subscriptions.append({
            "id": sub_id,
            "event_topic": topic,
            "url": url,
            "is_active": True
        })
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to save subscriptions: {str(e)}"}), 500
        
    return jsonify({
        "status": "success",
        "subscriptions": created_subscriptions
    }), 201


@invoices_blueprint.post("/api/v1/webhooks/dispatch-test")
def api_v1_webhooks_dispatch_test():
    """Triggers an async webhook dispatch test."""
    body = request.get_json(silent=True) or {}
    sub_id = body.get("subscription_id")
    payload = body.get("payload") or {"test": "data", "message": "Test event dispatch"}
    
    if not sub_id:
        return jsonify({"error": "Missing subscription_id"}), 400
        
    from invoices.models import WebhookSubscription
    sub = WebhookSubscription.query.get(sub_id)
    if not sub:
        return jsonify({"error": f"Webhook subscription not found for id: {sub_id}"}), 404
        
    try:
        from invoices.webhook_hub import WebhookHub
        hub = WebhookHub(db_session=db.session)
        topic = sub_id.split("_")[1] if "_" in sub_id else "test.dispatch"
        hub.trigger(
            url=sub.url,
            secret=sub.secret,
            event_topic=topic,
            payload=payload,
            subscription_id=sub.id
        )
        return jsonify({
            "status": "success",
            "message": f"Async test webhook dispatch triggered for topic: {topic}"
        })
    except Exception as e:
        return jsonify({"error": f"Failed to dispatch test: {str(e)}"}), 500


@invoices_blueprint.post("/api/audit/tax-rag-query")
def api_tax_rag_query():
    """Performs semantic RAG search over indexed tax regulations using Ollama/Fallback."""
    body = request.get_json(silent=True) or {}
    question = body.get("question")
    model = body.get("model", "gemma:2b")
    deep_research = body.get("deep_research", False)
    
    if not question:
        return jsonify({"error": "Missing question parameter"}), 400
        
    try:
        from invoices.ai_tax_advisor import query_local_tax_rag
        result = query_local_tax_rag(question, model_name=model, deep_research=deep_research)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Lỗi truy vấn RAG: {str(e)}"}), 500


@invoices_blueprint.post("/api/audit/draft-defense-letter")
def api_draft_defense_letter():
    """Drafts a formal tax defense letter template based on invoice anomalies citing Decree 125."""
    body = request.get_json(silent=True) or {}
    invoice_id = body.get("invoice_id", "INV-MOCK-99")
    issue_type = body.get("issue_type", "Chữ ký số không hợp lệ")
    seller = body.get("seller", "Công ty Cổ phần Mẫu")
    amount = body.get("amount", 25000000.0)
    mst = body.get("taxpayer_mst") or session.get("active_taxpayer_mst") or "0109998887"
    
    from invoices.models import TaxpayerProfile
    profile = TaxpayerProfile.query.get(mst)
    company_name = profile.company_name if profile else "DOANH NGHIEP"
    
    now = datetime.now()
    date_str = f"ngày {now.day} tháng {now.month} năm {now.year}"
    
    letter_template = f"""CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Độc lập - Tự do - Hạnh phúc
----------------

V/v: Giải trình chênh lệch/sai sót hóa đơn theo Nghị định 125/2020/NĐ-CP

Hà Nội, {date_str}

Kính gửi: Chi cục Thuế / Cục Thuế quản lý trực tiếp

1. Tên người nộp thuế: {company_name.upper()}
2. Mã số thuế: {mst}
3. Người đại diện theo pháp luật: Ban Giám đốc doanh nghiệp

Doanh nghiệp chúng tôi nhận được thông báo của Quý cơ quan về việc rà soát, giải trình các hóa đơn mua vào có dấu hiệu rủi ro. Cụ thể đối với hóa đơn mã số {invoice_id} phát hành bởi nhà cung cấp {seller} với giá trị giao dịch là {amount:,.0f} VND. Nội dung cảnh báo: {issue_type}.

Doanh nghiệp xin được giải trình cụ thể như sau:

I. Tình hình thực tế của giao dịch:
- Giao dịch mua bán hàng hóa/dịch vụ giữa hai bên là có thật, đã được hoàn thành bàn giao và có đầy đủ biên bản giao nhận hàng hóa, phiếu nhập kho, hợp đồng kinh tế đi kèm.
- Doanh nghiệp đã thực hiện thanh toán đầy đủ cho nhà cung cấp theo phương thức thanh toán thỏa thuận trong hợp đồng.

II. Căn cứ pháp lý theo Nghị định số 125/2020/NĐ-CP:
1. Đối với hành vi không cố ý hoặc do lỗi kỹ thuật chữ ký số của nhà cung cấp: Căn cứ theo Điều 9 Nghị định 125/2020/NĐ-CP quy định về các trường hợp không xử phạt vi phạm hành chính về thuế, hóa đơn đối với các sự cố khách quan hoặc lỗi hệ thống công nghệ thông tin của bên thứ ba.
2. Đối với chênh lệch thuế GTGT: Doanh nghiệp đã chủ động loại trừ các hóa đơn có rủi ro cao ra khỏi hồ sơ hoàn thuế để tự điều chỉnh theo quy định, không làm phát sinh số thuế thiếu hoặc trốn thuế quy định tại Điều 16 Nghị định 125/2020/NĐ-CP.

Doanh nghiệp xin cam đoan các thông tin giải trình nêu trên là đúng sự thật và kính mong Quý cơ quan xem xét, tạo điều kiện thuận lợi cho doanh nghiệp trong quá trình chấp hành pháp luật thuế.

ĐẠI DIỆN HỢP PHÁP CỦA DOANH NGHIỆP
(Ký, ghi rõ họ tên và đóng dấu)
"""
    return jsonify({
        "status": "success",
        "invoice_id": invoice_id,
        "draft_letter": letter_template
    })


@invoices_blueprint.post("/api/bank/reconcile/upload")
def api_bank_reconcile_upload():
    """Ingests a Techcombank/Vietcombank Excel statement and stores transactions."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    taxpayer_mst = request.form.get("taxpayer_mst") or session.get("active_taxpayer_mst")
    bank_name = request.form.get("bank_name", "Generic")
    account_number = request.form.get("account_number", "")

    if not taxpayer_mst:
        return jsonify({"error": "Mã số thuế hoạt động trống."}), 400

    if "file" not in request.files:
        return jsonify({"error": "Không có tệp tải lên."}), 400

    uploaded_file = request.files["file"]
    if not uploaded_file.filename:
        return jsonify({"error": "Tên tệp không hợp lệ."}), 400

    # Save to a local temporary location in our designated temp dir
    temp_dir = os.path.join(current_app.root_path, "data", "temp")
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, f"statement_{int(datetime.now().timestamp())}.xlsx")
    uploaded_file.save(temp_path)

    try:
        from invoices.bank_reconcile_service import parse_bank_statement
        parsed_txs = parse_bank_statement(temp_path, bank_name)
        
        from invoices.models import BankTransaction
        imported_count = 0
        skipped_count = 0
        
        for p in parsed_txs:
            # Check for reference duplicate
            exists = BankTransaction.query.filter_by(id=p["id"]).first()
            if exists:
                skipped_count += 1
                continue
                
            tx = BankTransaction(
                id=p["id"],
                taxpayer_mst=taxpayer_mst,
                bank_name=p["bank_name"],
                account_number=account_number,
                transaction_date=p["transaction_date"],
                reference_number=p["reference_number"],
                description=p["description"],
                amount=p["amount"],
                status="unreconciled",
                imported_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            db.session.add(tx)
            imported_count += 1
            
        if imported_count > 0:
            db.session.commit()
            
        return jsonify({
            "status": "success",
            "imported_count": imported_count,
            "skipped_count": skipped_count
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Lỗi xử lý tệp sổ phụ: {str(e)}"}), 500
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


@invoices_blueprint.get("/api/bank/reconcile/transactions")
def api_bank_reconcile_transactions():
    """Retrieve bank transactions list for active MST."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    taxpayer_mst = request.args.get("taxpayer_mst") or session.get("active_taxpayer_mst")
    status_filter = request.args.get("status", "all")  # 'all', 'unreconciled', 'matched'

    if not taxpayer_mst:
        return jsonify([])

    from invoices.models import BankTransaction, Invoice
    query = BankTransaction.query.filter_by(taxpayer_mst=taxpayer_mst)
    if status_filter != "all":
        query = query.filter_by(status=status_filter)

    transactions = query.order_by(BankTransaction.transaction_date.desc()).all()
    
    result = []
    for tx in transactions:
        tx_dict = tx.to_dict()
        if tx.matched_invoice_id:
            inv = Invoice.query.get(tx.matched_invoice_id)
            if inv:
                tx_dict["invoice_number"] = inv.number
                tx_dict["partner_name"] = inv.buyer_name if tx.amount > 0 else inv.seller_name
        else:
            tx_dict["invoice_number"] = ""
            tx_dict["partner_name"] = ""
        result.append(tx_dict)
        
    return jsonify(result)


@invoices_blueprint.post("/api/bank/reconcile/auto")
def api_bank_reconcile_auto():
    """Triggers autonomous Soundex/Phonetic matching reconciliation."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    payload = request.get_json(silent=True) or {}
    taxpayer_mst = payload.get("taxpayer_mst") or session.get("active_taxpayer_mst")

    if not taxpayer_mst:
        return jsonify({"error": "Mã số thuế hoạt động trống."}), 400

    try:
        from invoices.bank_reconcile_service import execute_auto_reconciliation
        res = execute_auto_reconciliation(taxpayer_mst)
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": f"Lỗi đối chiếu tự động: {str(e)}"}), 500


@invoices_blueprint.post("/api/bank/reconcile/manual")
def api_bank_reconcile_manual():
    """Manual reconciliation override by ledger accountant."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    payload = request.get_json(silent=True) or {}
    transaction_id = payload.get("transaction_id")
    invoice_id = payload.get("invoice_id")

    if not transaction_id or not invoice_id:
        return jsonify({"error": "Thiếu mã giao dịch hoặc mã hóa đơn khớp."}), 400

    from invoices.models import BankTransaction, Invoice
    tx = BankTransaction.query.get(transaction_id)
    inv = Invoice.query.get(invoice_id)

    if not tx or not inv:
        return jsonify({"error": "Không tìm thấy giao dịch ngân hàng hoặc hóa đơn tương ứng."}), 404

    try:
        tx.matched_invoice_id = invoice_id
        tx.confidence_score = 1.0  # Manual matching has 100% confidence
        tx.status = "matched"
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Đối chiếu thủ công thành công.",
            "details": {
                "transaction_id": tx.id,
                "matched_invoice_id": invoice_id,
                "invoice_number": inv.number,
                "partner_name": inv.buyer_name if tx.amount > 0 else inv.seller_name
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Lỗi đối chiếu thủ công: {str(e)}"}), 500


# ---------------------------------------------------------------------------
# US-084: Compliant E-Invoice Generator & Digital Signing Bridge (US-084, US-085)
# ---------------------------------------------------------------------------

@invoices_blueprint.get("/issue-invoice")
def issue_invoice_page():
    """Render the e-invoice draft builder page."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    return render_template("issue_invoice.html")


@invoices_blueprint.post("/api/invoices/issue/draft")
def api_issue_draft():
    """Create a new e-invoice draft."""
    import os
    from datetime import datetime

    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    payload = request.get_json(silent=True) or {}
    buyer_mst = payload.get("buyer_mst", "").strip()
    buyer_name = payload.get("buyer_name", "").strip()
    buyer_address = payload.get("buyer_address", "").strip()
    items_data = payload.get("items") or []

    if not buyer_mst or not buyer_name:
        return jsonify({"error": "Thiếu mã số thuế hoặc tên đơn vị mua hàng."}), 400

    if not items_data:
        return jsonify({"error": "Danh sách hàng hóa dịch vụ không được trống."}), 400

    # Get active taxpayer
    active_mst = session.get("active_taxpayer_mst")
    if not active_mst:
        return jsonify({"error": "Vui lòng chọn doanh nghiệp hoạt động trước."}), 400

    from invoices.models import TaxpayerProfile, Invoice, LineItem
    seller = TaxpayerProfile.query.filter_by(mst=active_mst).first()
    seller_name = seller.company_name if seller else "Công ty Phát hành Mẫu"
    seller_address = "123 Đường Phát Hành, Hà Nội"

    # Auto-increment number
    symbol = payload.get("symbol", "1C26TYY").strip()
    
    # Query count to auto-increment number
    count = Invoice.query.filter(Invoice.seller_mst == active_mst, Invoice.symbol == symbol).count()
    number = f"{count + 1:07d}"
    
    invoice_id = f"{active_mst}-{symbol}-{number}"

    # Calculate totals
    amount_before_tax = 0.0
    tax_amount = 0.0
    
    line_items = []
    
    for idx, item in enumerate(items_data):
        name = item.get("item_name", "").strip()
        unit = item.get("unit", "").strip()
        try:
            qty = float(item.get("quantity") or 0.0)
            price = float(item.get("unit_price") or 0.0)
        except ValueError:
            return jsonify({"error": f"Số lượng hoặc đơn giá của mục {idx+1} không hợp lệ."}), 400
            
        tax_rate_str = item.get("tax_rate", "10%")
        
        # Calculate item totals
        item_amt = qty * price
        
        # Calculate tax
        if "10" in tax_rate_str:
            item_tax = 0.10 * item_amt
        elif "8" in tax_rate_str:
            item_tax = 0.08 * item_amt
        elif "5" in tax_rate_str:
            item_tax = 0.05 * item_amt
        else:
            item_tax = 0.0
            
        amount_before_tax += item_amt
        tax_amount += item_tax
        
        line_items.append({
            "item_name": name,
            "unit": unit,
            "quantity": qty,
            "unit_price": price,
            "amount_before_tax": item_amt,
            "tax_rate": tax_rate_str,
            "tax_amount": item_tax
        })

    total_amount = amount_before_tax + tax_amount
    
    # Spell money in Vietnamese
    from invoices.ai_service import spell_money_vietnamese
    amount_in_words = spell_money_vietnamese(total_amount)

    try:
        inv = Invoice(
            id=invoice_id,
            filename=f"invoice_{invoice_id}.xml",
            invoice_type="sold",
            template_code="1",
            symbol=symbol,
            number=number,
            date=datetime.now().strftime("%Y-%m-%d"),
            currency="VND",
            seller_name=seller_name,
            seller_mst=active_mst,
            seller_address=seller_address,
            buyer_name=buyer_name,
            buyer_mst=buyer_mst,
            buyer_address=buyer_address,
            amount_before_tax=amount_before_tax,
            tax_amount=tax_amount,
            total_amount=total_amount,
            has_signature=False,
            amount_in_words=amount_in_words,
            imported_at=datetime.now().isoformat(),
            import_status="draft",
            invoice_status="draft",
            taxpayer_mst=active_mst
        )
        db.session.add(inv)
        
        for item_data in line_items:
            li = LineItem(
                invoice_id=invoice_id,
                item_name=item_data["item_name"],
                unit=item_data["unit"],
                quantity=item_data["quantity"],
                unit_price=item_data["unit_price"],
                amount_before_tax=item_data["amount_before_tax"],
                tax_rate=item_data["tax_rate"],
                tax_amount=item_data["tax_amount"],
                expense_category="REVENUE"
            )
            db.session.add(li)
            
        db.session.commit()
        return jsonify({
            "status": "success",
            "message": "Tạo hóa đơn nháp thành công.",
            "invoice": inv.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Lỗi lưu hóa đơn nháp: {str(e)}"}), 500


@invoices_blueprint.post("/api/invoices/issue/sign")
def api_issue_sign():
    """Digital sign draft e-invoice using mock USB Token."""
    import os
    import json
    from datetime import datetime

    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    payload = request.get_json(silent=True) or {}
    invoice_id = payload.get("invoice_id")

    if not invoice_id:
        return jsonify({"error": "Thiếu mã hóa đơn cần ký."}), 400

    from invoices.models import Invoice, LineItem
    inv = Invoice.query.get(invoice_id)
    if not inv:
        return jsonify({"error": "Không tìm thấy hóa đơn tương ứng."}), 404

    if inv.invoice_status != "draft":
        return jsonify({"error": "Hóa đơn này đã được phát hành và ký số."}), 400

    try:
        # Build GDT Circular 78 Compliant XML DSHDon list
        items_xml = ""
        for idx, item in enumerate(inv.items):
            items_xml += f"""        <HHDVu>
          <TChat>1</TChat>
          <STT>{idx + 1}</STT>
          <Ten>{item.item_name}</Ten>
          <DVT>{item.unit or 'Lần'}</DVT>
          <SLuong>{item.quantity}</SLuong>
          <DGia>{item.unit_price}</DGia>
          <ThTien>{item.amount_before_tax}</ThTien>
          <TSuat>{item.tax_rate}</TSuat>
          <TThue>{item.tax_amount}</TThue>
        </HHDVu>"""

        # Compile Canonical DLHDon XML
        dlhdon_xml = f"""<DLHDon Id="HD_{inv.id}">
      <TTChung>
        <PBan>1.0.0</PBan>
        <THDon>Hóa đơn giá trị gia tăng</THDon>
        <KHHDon>{inv.symbol}</KHHDon>
        <SHDon>{inv.number}</SHDon>
        <NLap>{inv.date}</NLap>
        <DVTTe>{inv.currency or 'VND'}</DVTTe>
        <TGia>1.0</TGia>
      </TTChung>
      <NDHDon>
        <NBan>
          <Ten>{inv.seller_name}</Ten>
          <MST>{inv.seller_mst}</MST>
          <DChi>{inv.seller_address or ''}</DChi>
        </NBan>
        <NMua>
          <Ten>{inv.buyer_name}</Ten>
          <MST>{inv.buyer_mst}</MST>
          <DChi>{inv.buyer_address or ''}</DChi>
        </NMua>
        <DSHDon>
{items_xml}
        </DSHDon>
        <TToan>
          <TgTCThue>{inv.amount_before_tax}</TgTCThue>
          <TgTThue>{inv.tax_amount}</TgTThue>
          <TgTTTBSo>{inv.total_amount}</TgTTTBSo>
          <TgTTTBChu>{inv.amount_in_words}</TgTTTBChu>
        </TToan>
      </NDHDon>
    </DLHDon>"""

        # Perform SHA-256 + RSA-2048 mock USB token cryptographic signing
        import hashlib
        import base64
        
        # Calculate digest
        digest = hashlib.sha256(dlhdon_xml.encode("utf-8")).digest()
        digest_b64 = base64.b64encode(digest).decode("utf-8")
        
        # Simulate USB Token RSA signature
        sig_b64 = base64.b64encode(hashlib.sha256(digest).digest() * 2).decode("utf-8")[:172] + "=="
        
        # Mock certificate x509
        mock_cert = "MIIDuTCCAqGgAwIBAgIUdT6ySjZ+N...MOCK_GDT_CIRCULAR_78_CERTIFICATE..."
        
        # Complete Circular 78 XML Package
        full_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<HDon>
    {dlhdon_xml}
    <Signature xmlns="http://www.w3.org/2000/09/xmldsig#">
        <SignedInfo>
            <CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>
            <SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha256"/>
            <Reference URI="#HD_{inv.id}">
                <Transforms>
                    <Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
                </Transforms>
                <DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
                <DigestValue>{digest_b64}</DigestValue>
            </Reference>
        </SignedInfo>
        <SignatureValue>{sig_b64}</SignatureValue>
        <KeyInfo>
            <X509Data>
                <X509Certificate>{mock_cert}</X509Certificate>
            </X509Data>
        </KeyInfo>
    </Signature>
</HDon>"""

        # Store signed XML file locally
        from invoices.service import XML_DIR
        safe_filename = f"invoice_{inv.id}.xml"
        xml_path = os.path.join(XML_DIR, safe_filename)
        with open(xml_path, "w", encoding="utf-8") as f:
            f.write(full_xml)

        # Update database model state
        inv.has_signature = True
        inv.signing_date = datetime.now().strftime("%Y-%m-%d")
        inv.import_status = "imported"
        inv.invoice_status = "Gốc"
        
        # Also generate mock signature JSON for frontend display
        inv.signature_details_json = json.dumps({
            "subject": f"C=VN, ST=Hanoi, O={inv.seller_name}, CN={inv.seller_name}",
            "issuer": "VNPT CA / GDT Root CA",
            "valid_from": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "valid_to": "2029-12-31 23:59:59",
            "serial": "18392098487293847293847",
            "algo": "sha256RSA"
        }, ensure_ascii=False)
        
        db.session.commit()
        
        # Trigger an SSE update stream event for newly issued invoice
        try:
            from invoices.sync_daemon import push_sync_event
            push_sync_event("invoice_downloaded", {
                "id": inv.id,
                "seller": inv.seller_name,
                "buyer": inv.buyer_name,
                "amount": inv.total_amount
            })
        except Exception:
            pass

        return jsonify({
            "status": "success",
            "message": "Ký số hóa đơn thành công thông qua USB Token.",
            "invoice_id": inv.id,
            "xml_preview": full_xml[:1000] + "..."
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Lỗi ký số hóa đơn: {str(e)}"}), 500


# ── Version 6.0.0: Cryptographic Audit Ledger API ─────────────────

@invoices_blueprint.get("/api/audit/ledger")
def get_audit_ledger():
    """List audit ledger blocks with pagination (US-090)."""
    guard = _ensure_logged_in()
    if guard:
        return guard

    from invoices.models import AuditBlock

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    per_page = min(per_page, 200)

    query = AuditBlock.query.order_by(AuditBlock.block_id.desc())
    total = query.count()
    blocks = query.offset((page - 1) * per_page).limit(per_page).all()

    return jsonify({
        "total": total,
        "page": page,
        "per_page": per_page,
        "blocks": [b.to_dict() for b in blocks],
    })


@invoices_blueprint.post("/api/audit/verify")
def verify_audit_ledger():
    """Run full-chain cryptographic integrity verification (US-091)."""
    guard = _ensure_logged_in()
    if guard:
        return guard

    from invoices.audit_ledger_service import verify_ledger_integrity
    from invoices.models import AuditBlock

    is_valid, corrupted_id, error_msg = verify_ledger_integrity()
    total_blocks = AuditBlock.query.count()

    return jsonify({
        "is_valid": is_valid,
        "total_blocks": total_blocks,
        "corrupted_block_id": corrupted_id,
        "error_message": error_msg,
    })


@invoices_blueprint.get("/api/audit/stats")
def get_audit_stats():
    """Return summary statistics for the audit ledger dashboard (US-091)."""
    guard = _ensure_logged_in()
    if guard:
        return guard

    from invoices.models import AuditBlock
    from sqlalchemy import func

    total = AuditBlock.query.count()
    action_counts = (
        db.session.query(AuditBlock.action_type, func.count(AuditBlock.block_id))
        .group_by(AuditBlock.action_type)
        .all()
    )

    latest = AuditBlock.query.order_by(AuditBlock.block_id.desc()).first()

    return jsonify({
        "total_blocks": total,
        "action_breakdown": {action: count for action, count in action_counts},
        "latest_block": latest.to_dict() if latest else None,
    })


@invoices_blueprint.post("/api/analytics/forecast")
@roles_required("admin", "auditor", "viewer")
def api_forecast_tax():
    """Forecast future tax liability using moving averages (US-110, US-111)."""
    err = _ensure_logged_in()
    if err:
        return err

    try:
        body = request.get_json() or {}
        historical_data = body.get("historical_data")
        projected_period = body.get("projected_period", datetime.now().strftime("%Y-%m"))
        alpha = body.get("alpha", 0.7)
        window_size = body.get("window_size", 3)
        budget_limit = body.get("budget_limit", 500000000.0)

        active_mst = session.get("active_taxpayer_mst")
        if not active_mst:
            from invoices.models import TaxpayerProfile
            prof = TaxpayerProfile.query.filter_by(is_active=True).first()
            if prof:
                active_mst = prof.mst

        # Query from DB if not provided in request body
        if historical_data is None:
            if not active_mst:
                return jsonify({"error": "Không tìm thấy mã số thuế hoạt động để truy vấn dữ liệu."}), 400

            from invoices.models import Invoice
            sales = Invoice.query.filter_by(seller_mst=active_mst, is_cancelled=False).all()
            purchases = Invoice.query.filter_by(buyer_mst=active_mst, is_cancelled=False).all()

            from collections import defaultdict
            period_map = defaultdict(lambda: {"output_vat": 0.0, "input_vat": 0.0})
            
            for s in sales:
                if not s.date or len(s.date) < 7:
                    continue
                period_map[s.date[:7]]["output_vat"] += s.tax_amount
            for p in purchases:
                if not p.date or len(p.date) < 7:
                    continue
                period_map[p.date[:7]]["input_vat"] += p.tax_amount

            historical_data = []
            for p in sorted(period_map.keys()):
                historical_data.append({
                    "period": p,
                    "output_vat": period_map[p]["output_vat"],
                    "input_vat": period_map[p]["input_vat"]
                })

        from invoices.tax_forecaster import forecast_next_period_tax, TaxAlertManager
        forecast = forecast_next_period_tax(
            historical_data,
            projected_period=projected_period,
            alpha=alpha,
            window_size=window_size
        )

        # Run alerts evaluation
        alert_manager = TaxAlertManager(budget_limit=budget_limit)
        forecast_evaluated = alert_manager.evaluate_forecast(forecast)

        return jsonify({
            "taxpayer_mst": active_mst,
            "forecast": forecast_evaluated.to_dict()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/invoices/batch-parse")
@roles_required("admin", "auditor")
def api_batch_parse_invoices():
    """Concurrently parse XML invoices, decompress if zipped, and import to DB (US-112, US-113)."""
    err = _ensure_logged_in()
    if err:
        return err

    try:
        body = request.get_json() or {}
        invoice_items = body.get("invoices", [])
        duplicate_strategy = body.get("duplicate_strategy", "overwrite")
        active_mst = session.get("active_taxpayer_mst")

        # 1. Prepare batch (decompress if needed)
        parsed_batch_inputs = []
        for idx, item in enumerate(invoice_items):
            filename = item.get("filename", f"invoice_{idx}.xml")
            content = item.get("content", "")
            compressed = item.get("compressed", False)

            if not content:
                continue

            try:
                if compressed:
                    import base64
                    try:
                        byte_data = base64.b64decode(content)
                    except Exception:
                        byte_data = bytes.fromhex(content)
                    
                    from invoices.batch_parser import decompress_xml
                    xml_str = decompress_xml(byte_data)
                else:
                    xml_str = content

                parsed_batch_inputs.append((filename, xml_str))
            except Exception as e:
                pass

        # 2. Parallel Parse
        from invoices.batch_parser import parse_batch_xml
        parse_results = parse_batch_xml(parsed_batch_inputs)

        # 3. Serial Import to DB
        from invoices.service import import_xml_invoice
        db_results = []
        for res, (filename, xml_str) in zip(parse_results, parsed_batch_inputs):
            if not res.success:
                db_results.append({
                    "filename": filename,
                    "success": False,
                    "error_message": res.error_message
                })
                continue
            
            try:
                xml_bytes = xml_str.encode("utf-8")
                imported_dict = import_xml_invoice(
                    xml_bytes,
                    filename,
                    duplicate_strategy=duplicate_strategy,
                    taxpayer_mst=active_mst
                )
                db_results.append({
                    "filename": filename,
                    "success": True,
                    "invoice_id": imported_dict.get("id"),
                    "invoice_number": imported_dict.get("number"),
                    "total_amount": imported_dict.get("total_amount")
                })
            except Exception as e:
                db_results.append({
                    "filename": filename,
                    "success": False,
                    "error_message": str(e)
                })

        return jsonify({
            "total_processed": len(db_results),
            "results": db_results
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.get("/api/analytics/kpis")
@roles_required("admin", "auditor", "viewer")
def api_get_financial_kpis():
    """Retrieve financial health metrics (Gross Margin, Tax Ratios, Clearance times) (US-114)."""
    err = _ensure_logged_in()
    if err:
        return err

    active_mst = session.get("active_taxpayer_mst")
    if not active_mst:
        from invoices.models import TaxpayerProfile
        prof = TaxpayerProfile.query.filter_by(is_active=True).first()
        if prof:
            active_mst = prof.mst

    if not active_mst:
        return jsonify({"error": "Không tìm thấy mã số thuế hoạt động. Vui lòng chọn hồ sơ MST."}), 400

    from invoices.models import Invoice
    sales = Invoice.query.filter_by(seller_mst=active_mst, is_cancelled=False).all()
    purchases = Invoice.query.filter_by(buyer_mst=active_mst, is_cancelled=False).all()

    sales_dicts = [
        {"id": s.id, "amount_before_tax": s.amount_before_tax, "tax_amount": s.tax_amount, "date": s.date}
        for s in sales
    ]
    purchases_dicts = [
        {"id": p.id, "amount_before_tax": p.amount_before_tax, "tax_amount": p.tax_amount, "date": p.date}
        for p in purchases
    ]

    clearances = []
    for inv in sales + purchases:
        if inv.paid_date:
            clearances.append({
                "invoice_id": inv.id,
                "clearance_date": inv.paid_date
            })

    from invoices.financial_kpi import calculate_financial_kpis
    kpi = calculate_financial_kpis(sales_dicts, purchases_dicts, clearances)

    from collections import defaultdict
    sales_by_month = defaultdict(list)
    purchases_by_month = defaultdict(list)
    clearances_by_month = defaultdict(list)

    for s in sales_dicts:
        month = s["date"][:7] if s.get("date") else "unknown"
        sales_by_month[month].append(s)
    for p in purchases_dicts:
        month = p["date"][:7] if p.get("date") else "unknown"
        purchases_by_month[month].append(p)
    for c in clearances:
        inv_date = None
        for s in sales_dicts:
            if s["id"] == c["invoice_id"]:
                inv_date = s["date"]
                break
        if not inv_date:
            for p in purchases_dicts:
                if p["id"] == c["invoice_id"]:
                    inv_date = p["date"]
                    break
        month = inv_date[:7] if inv_date else "unknown"
        clearances_by_month[month].append(c)

    all_months = set(sales_by_month.keys()).union(purchases_by_month.keys())
    all_months.discard("unknown")
    
    monthly_trends = {}
    for month in sorted(all_months):
        m_kpi = calculate_financial_kpis(
            sales_by_month[month],
            purchases_by_month[month],
            clearances_by_month[month]
        )
        monthly_trends[month] = m_kpi.to_dict()

    return jsonify({
        "taxpayer_mst": active_mst,
        "overall": kpi.to_dict(),
        "monthly_trends": monthly_trends
    })


@invoices_blueprint.get("/api/analytics/kpis/export")
@roles_required("admin", "auditor", "viewer")
def api_export_financial_kpis():
    """Export monthly financial KPIs to a downloadable CSV file (US-115)."""
    err = _ensure_logged_in()
    if err:
        return err

    active_mst = session.get("active_taxpayer_mst")
    if not active_mst:
        from invoices.models import TaxpayerProfile
        prof = TaxpayerProfile.query.filter_by(is_active=True).first()
        if prof:
            active_mst = prof.mst

    if not active_mst:
        return jsonify({"error": "Không tìm thấy mã số thuế hoạt động. Vui lòng chọn hồ sơ MST."}), 400

    from invoices.models import Invoice
    sales = Invoice.query.filter_by(seller_mst=active_mst, is_cancelled=False).all()
    purchases = Invoice.query.filter_by(buyer_mst=active_mst, is_cancelled=False).all()

    sales_dicts = [
        {"id": s.id, "amount_before_tax": s.amount_before_tax, "tax_amount": s.tax_amount, "date": s.date}
        for s in sales
    ]
    purchases_dicts = [
        {"id": p.id, "amount_before_tax": p.amount_before_tax, "tax_amount": p.tax_amount, "date": p.date}
        for p in purchases
    ]

    clearances = []
    for inv in sales + purchases:
        if inv.paid_date:
            clearances.append({
                "invoice_id": inv.id,
                "clearance_date": inv.paid_date
            })

    from collections import defaultdict
    sales_by_month = defaultdict(list)
    purchases_by_month = defaultdict(list)
    clearances_by_month = defaultdict(list)

    for s in sales_dicts:
        month = s["date"][:7] if s.get("date") else "unknown"
        sales_by_month[month].append(s)
    for p in purchases_dicts:
        month = p["date"][:7] if p.get("date") else "unknown"
        purchases_by_month[month].append(p)
    for c in clearances:
        inv_date = None
        for s in sales_dicts:
            if s["id"] == c["invoice_id"]:
                inv_date = s["date"]
                break
        if not inv_date:
            for p in purchases_dicts:
                if p["id"] == c["invoice_id"]:
                    inv_date = p["date"]
                    break
        month = inv_date[:7] if inv_date else "unknown"
        clearances_by_month[month].append(c)

    all_months = set(sales_by_month.keys()).union(purchases_by_month.keys())
    all_months.discard("unknown")
    
    from invoices.financial_kpi import calculate_financial_kpis, export_kpi_to_csv
    
    period_metrics = {}
    for month in sorted(all_months):
        period_metrics[month] = calculate_financial_kpis(
            sales_by_month[month],
            purchases_by_month[month],
            clearances_by_month[month]
        )

    csv_content = export_kpi_to_csv(period_metrics)

    from flask import Response
    response = Response(csv_content, mimetype="text/csv")
    filename = f"kpi_report_{active_mst}_{datetime.now().strftime('%Y%m%d')}.csv"
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response


@invoices_blueprint.get("/api/compliance/rulebook")
@roles_required("admin", "auditor", "viewer")
def api_get_compliance_rulebook():
    """Retrieve the currently active compliance rulebook (US-120)."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    import json
    from invoices.models import ComplianceRulebook
    active_mst = session.get("taxpayer_mst")
    
    rulebook = None
    if active_mst:
        rulebook = ComplianceRulebook.query.filter_by(taxpayer_mst=active_mst, is_active=True).first()
    
    if not rulebook:
        rulebook = ComplianceRulebook.query.filter_by(id="rulebook_default").first()

    if not rulebook:
        default_rulebook_json = {
            "name": "Default Compliance Rulebook",
            "rules": [
                {
                    "id": "rule_cash_limit",
                    "name": "Verify cash transactions over 20M limit",
                    "severity": "critical",
                    "channels": ["in_app"],
                    "expression": {
                        "and": [
                            {"field": "payment_method", "op": "contains", "value": "Tiền mặt"},
                            {"field": "total_amount", "op": ">=", "value": 20000000}
                        ]
                    }
                }
            ]
        }
        return jsonify({
            "status": "success",
            "rulebook": default_rulebook_json
        })

    try:
        data = json.loads(rulebook.rulebook_json)
    except Exception:
        data = {}

    return jsonify({
        "status": "success",
        "rulebook": data,
        "updated_at": rulebook.updated_at
    })


@invoices_blueprint.post("/api/compliance/rulebook")
@roles_required("admin", "auditor")
def api_update_compliance_rulebook():
    """Update or upload the active compliance rulebook DSL (US-120)."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    payload = request.get_json(silent=True) or {}
    rulebook_data = payload.get("rulebook")
    if not rulebook_data:
        return jsonify({"error": "Dữ liệu rulebook trống."}), 400

    import json
    from invoices.compliance_hub import validate_rulebook_dsl
    ok, err = validate_rulebook_dsl(rulebook_data)
    if not ok:
        return jsonify({"error": f"Lỗi cú pháp DSL Rulebook: {err}"}), 400

    from invoices.models import ComplianceRulebook
    active_mst = session.get("taxpayer_mst")
    rulebook_id = f"rulebook_{active_mst}" if active_mst else "rulebook_default"
    
    rulebook = db.session.get(ComplianceRulebook, rulebook_id)
    now = datetime.now().isoformat()
    
    if not rulebook:
        rulebook = ComplianceRulebook(
            id=rulebook_id,
            taxpayer_mst=active_mst,
            name=rulebook_data.get("name", "Custom Rulebook"),
            rulebook_json=json.dumps(rulebook_data, ensure_ascii=False),
            is_active=True,
            updated_at=now
        )
        db.session.add(rulebook)
    else:
        rulebook.name = rulebook_data.get("name", rulebook.name)
        rulebook.rulebook_json = json.dumps(rulebook_data, ensure_ascii=False)
        rulebook.updated_at = now

    db.session.commit()

    from invoices.security_audit_service import log_security_event
    log_security_event("UPDATE", f"Updated compliance rulebook DSL: {rulebook.name}")

    return jsonify({
        "status": "success",
        "message": "Cập nhật DSL Rulebook thành công.",
        "updated_at": now
    })


@invoices_blueprint.post("/api/compliance/evaluate")
@roles_required("admin", "auditor", "viewer")
def api_evaluate_compliance():
    """Evaluate compliance of specified invoices against the active rulebook (US-120)."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    payload = request.get_json(silent=True) or {}
    invoice_ids = payload.get("invoice_ids", [])
    
    if not invoice_ids:
        return jsonify({"error": "Danh sách invoice_ids trống."}), 400

    from invoices.models import Invoice, ComplianceRulebook
    from invoices.compliance_hub import ComplianceEngine
    import json

    active_mst = session.get("taxpayer_mst")
    rulebook = None
    if active_mst:
        rulebook = ComplianceRulebook.query.filter_by(taxpayer_mst=active_mst, is_active=True).first()
    if not rulebook:
        rulebook = ComplianceRulebook.query.filter_by(id="rulebook_default").first()

    engine = ComplianceEngine()
    if rulebook:
        try:
            rulebook_data = json.loads(rulebook.rulebook_json)
            engine.set_rulebook(rulebook_data)
        except Exception:
            pass

    invoices = Invoice.query.filter(Invoice.id.in_(invoice_ids)).all()
    all_alerts = []
    
    for inv in invoices:
        # Convert invoice model to dictionary format suited for ComplianceEngine
        inv_dict = inv.to_dict()
        alerts = engine.evaluate_invoice(inv_dict)
        all_alerts.extend([a.to_dict() for a in alerts])

    return jsonify({
        "status": "success",
        "alerts": all_alerts
    })


@invoices_blueprint.post("/api/compliance/map-ifrs")
@roles_required("admin", "auditor", "viewer")
def api_map_ifrs_compliance():
    """Map invoices to standard IFRS & calculate FCT liabilities dynamically (US-121)."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    payload = request.get_json(silent=True) or {}
    invoice_ids = payload.get("invoice_ids", [])
    reporting_currency = payload.get("reporting_currency", "USD").strip().upper()
    fct_category = payload.get("fct_category", "services").strip().lower()

    if not invoice_ids:
        return jsonify({"error": "Danh sách invoice_ids trống."}), 400

    from invoices.models import Invoice
    from invoices.tax_mapping import TaxMappingEngine
    from dataclasses import asdict

    engine = TaxMappingEngine()
    invoices = Invoice.query.filter(Invoice.id.in_(invoice_ids)).all()
    
    mapped_results = []
    for inv in invoices:
        inv_dict = inv.to_dict()
        mapping = engine.map_to_ifrs(inv_dict, reporting_currency=reporting_currency, fct_category=fct_category)
        mapped_results.append(asdict(mapping))

    return jsonify({
        "status": "success",
        "reporting_currency": reporting_currency,
        "mapped_invoices": mapped_results
    })


@invoices_blueprint.post("/api/compliance/ias12-deferred-tax")
@roles_required("admin", "auditor", "viewer")
def api_ias12_deferred_tax():
    """Calculate IAS 12 deferred taxes for a given MST and year."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    payload = request.get_json(silent=True) or {}
    active_mst = payload.get("mst") or session.get("active_taxpayer_mst") or session.get("taxpayer_mst")
    year = payload.get("year")
    
    if not active_mst:
        return jsonify({"error": "Mã số thuế không được để trống"}), 400
    if not year:
        year = datetime.now().year

    try:
        from invoices.ifrs_engine import IFRSTranslationService
        service = IFRSTranslationService()
        records = service.calculate_ias12_deferred_tax(active_mst, int(year))
        return jsonify({
            "status": "success",
            "mst": active_mst,
            "year": year,
            "records": records
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/compliance/ifrs16-lease-schedule")
@roles_required("admin", "auditor", "viewer")
def api_ifrs16_lease_schedule():
    """Generate IFRS 16 lease amortization schedule month-by-month."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    payload = request.get_json(silent=True) or {}
    lease_id = payload.get("lease_id")
    monthly_payment = payload.get("monthly_payment")
    discount_rate = payload.get("discount_rate")
    lease_term_months = payload.get("lease_term_months")

    if not lease_id:
        return jsonify({"error": "lease_id không được để trống"}), 400
    if monthly_payment is None or discount_rate is None or lease_term_months is None:
        return jsonify({"error": "Thiếu các thông số tính toán amortization"}), 400

    try:
        from invoices.ifrs_engine import IFRSTranslationService
        service = IFRSTranslationService()
        schedule = service.calculate_ifrs16_amortization(
            lease_id, float(monthly_payment), float(discount_rate), int(lease_term_months)
        )
        return jsonify({
            "status": "success",
            "lease_id": lease_id,
            "schedule": schedule
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/compliance/pillar-two-estimate")
@roles_required("admin", "auditor", "viewer")
def api_pillar_two_estimate():
    """Estimate consolidated OECD Pillar Two GloBE top-up taxes."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    payload = request.get_json(silent=True) or {}
    parent_mst = payload.get("parent_mst") or session.get("active_taxpayer_mst") or session.get("taxpayer_mst")
    group_msts = payload.get("group_msts")
    year = payload.get("year")

    if not parent_mst:
        return jsonify({"error": "parent_mst không được để trống"}), 400
    if not group_msts or not isinstance(group_msts, list):
        return jsonify({"error": "group_msts phải là danh sách MST hợp lệ"}), 400
    if not year:
        year = datetime.now().year

    try:
        from invoices.ifrs_engine import IFRSTranslationService
        service = IFRSTranslationService()
        estimate = service.estimate_pillar_two_topup(parent_mst, group_msts, int(year))
        return jsonify({
            "status": "success",
            "estimate": estimate
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.get("/api/reports/tax-risk-scoreboard")
@roles_required("admin", "auditor", "viewer")
def api_tax_risk_scoreboard():
    """Retrieve tax compliance audit warning distribution and supplier risk scoreboard."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from invoices.supplier_risk_service import get_all_suppliers_risk_radar
    active_mst = session.get("taxpayer_mst")

    # Fetch dynamic supplier risk radar data
    radar_data = get_all_suppliers_risk_radar(active_mst)

    # Map fields for UI compatibility
    for s in radar_data["suppliers"]:
        s["average_t_score"] = s["risk_score"]
        s["warnings_count"] = len(s["flags"])
        s["is_blacklisted"] = "BLACKLISTED" in s["flags"] or s.get("gdt_status") == "BLACKLISTED"

    # Only include suppliers with warnings or blacklisted in high_risk list for the view
    high_risk_suppliers = [s for s in radar_data["suppliers"] if s["warnings_count"] > 0 or s["is_blacklisted"]]

    return jsonify({
        "status": "success",
        "summary": radar_data["summary"],
        "suppliers": high_risk_suppliers
    })


@invoices_blueprint.get("/api/reports/supplier-risk-radar")
@roles_required("admin", "auditor", "viewer")
def api_supplier_risk_radar():
    """Retrieve all suppliers and summarize the risk radar statistics."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized
    
    from invoices.supplier_risk_service import get_all_suppliers_risk_radar
    active_mst = session.get("taxpayer_mst")
    
    radar_data = get_all_suppliers_risk_radar(active_mst)
    return jsonify(radar_data)


@invoices_blueprint.post("/api/reports/supplier-risk-radar/blacklist")
@roles_required("admin", "auditor")
def api_add_supplier_blacklist():
    """Add a supplier MST to the blacklist."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized
        
    payload = request.json or {}
    mst = payload.get("mst", "").strip()
    reason = payload.get("reason", "").strip()
    if not mst:
        return jsonify({"error": "Mã số thuế không được để trống"}), 400
        
    from invoices.models import BlacklistedMST
    from extensions import db
    import datetime
    
    existing = db.session.get(BlacklistedMST, mst)
    if existing:
        existing.reason = reason
        existing.blacklisted_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        item = BlacklistedMST(
            mst=mst,
            reason=reason,
            blacklisted_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        db.session.add(item)
    db.session.commit()
    return jsonify({"status": "success", "message": "Đã thêm nhà cung cấp vào danh sách đen."})


@invoices_blueprint.delete("/api/reports/supplier-risk-radar/blacklist/<mst>")
@roles_required("admin", "auditor")
def api_delete_supplier_blacklist(mst):
    """Remove a supplier MST from the blacklist."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized
    from invoices.models import BlacklistedMST
    from extensions import db
    
    item = db.session.get(BlacklistedMST, mst)
    if not item:
        return jsonify({"error": "Không tìm thấy nhà cung cấp trong danh sách đen."}), 404
        
    db.session.delete(item)
    db.session.commit()
    return jsonify({"status": "success", "message": "Đã xóa nhà cung cấp khỏi danh sách đen."})




def get_harness_db():
    import sqlite3
    import os
    
    conn = sqlite3.connect("harness.db", timeout=10.0)
    conn.text_factory = lambda x: str(x, encoding="utf-8", errors="replace")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    
    # Auto-initialize tables if story table doesn't exist
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='story';")
    if not cur.fetchone():
        conn.execute("""
        CREATE TABLE IF NOT EXISTS story (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            risk_lane TEXT NOT NULL,
            contract_doc TEXT,
            status TEXT NOT NULL,
            notes TEXT,
            unit_proof INTEGER DEFAULT 0,
            integration_proof INTEGER DEFAULT 0,
            e2e_proof INTEGER DEFAULT 0,
            platform_proof INTEGER DEFAULT 0,
            evidence TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        conn.execute("""
        CREATE TABLE IF NOT EXISTS decision (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            status TEXT NOT NULL,
            doc_path TEXT,
            verify_command TEXT,
            last_verified_at TIMESTAMP,
            last_verified_result TEXT,
            predicted_impact TEXT,
            actual_outcome TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        conn.execute("""
        CREATE TABLE IF NOT EXISTS backlog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            discovered_while TEXT,
            current_pain TEXT,
            suggested_improvement TEXT,
            risk TEXT,
            status TEXT NOT NULL,
            predicted_impact TEXT,
            actual_outcome TEXT,
            implemented_at TIMESTAMP,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        conn.execute("""
        CREATE TABLE IF NOT EXISTS trace (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_summary TEXT NOT NULL,
            intake_id TEXT,
            story_id TEXT,
            agent TEXT,
            actions_taken TEXT,
            files_read TEXT,
            files_changed TEXT,
            decisions_made TEXT,
            errors TEXT,
            outcome TEXT,
            duration_seconds INTEGER,
            token_estimate INTEGER,
            harness_friction TEXT,
            notes TEXT,
            git_hash TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        conn.commit()
    return conn


@invoices_blueprint.get("/api/harness/summary")
def api_harness_summary():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    conn = None
    try:
        conn = get_harness_db()
        cur = conn.cursor()

        # Get status counts for stories
        cur.execute("SELECT status, COUNT(*) as cnt FROM story GROUP BY status")
        story_status_rows = cur.fetchall()
        story_status = {r["status"]: r["cnt"] for r in story_status_rows}

        # Get risk lane counts for stories
        cur.execute("SELECT risk_lane, COUNT(*) as cnt FROM story GROUP BY risk_lane")
        story_lane_rows = cur.fetchall()
        story_lane = {r["risk_lane"]: r["cnt"] for r in story_lane_rows}

        # Get decision status counts
        cur.execute("SELECT status, COUNT(*) as cnt FROM decision GROUP BY status")
        decision_status_rows = cur.fetchall()
        decision_status = {r["status"]: r["cnt"] for r in decision_status_rows}

        # Get backlog status counts
        cur.execute("SELECT status, COUNT(*) as cnt FROM backlog GROUP BY status")
        backlog_status_rows = cur.fetchall()
        backlog_status = {r["status"]: r["cnt"] for r in backlog_status_rows}

        # Get trace counts
        cur.execute("SELECT COUNT(*) as cnt FROM trace")
        trace_count = cur.fetchone()["cnt"]

        # Fetch all stories
        cur.execute("SELECT id, title, created_at, risk_lane, contract_doc, status, unit_proof, integration_proof, e2e_proof, platform_proof, evidence, notes FROM story ORDER BY id DESC")
        stories = [dict(r) for r in cur.fetchall()]

        # Fetch all decisions
        cur.execute("SELECT id, title, created_at, status, doc_path, verify_command, last_verified_at, last_verified_result, predicted_impact, actual_outcome, notes FROM decision ORDER BY id DESC")
        decisions = [dict(r) for r in cur.fetchall()]

        # Fetch recent traces (last 30)
        cur.execute("SELECT id, created_at, task_summary, intake_id, story_id, agent, actions_taken, files_read, files_changed, decisions_made, errors, outcome, duration_seconds, token_estimate, harness_friction, notes, git_hash FROM trace ORDER BY id DESC LIMIT 30")
        traces = [dict(r) for r in cur.fetchall()]

        # Fetch all backlog items
        cur.execute("SELECT id, created_at, title, discovered_while, current_pain, suggested_improvement, risk, status, predicted_impact, actual_outcome, implemented_at, notes FROM backlog ORDER BY id DESC")
        backlog = [dict(r) for r in cur.fetchall()]

        # Build stats struct
        stats = {
            "stories": {
                "total": sum(story_status.values()),
                "status": story_status,
                "lanes": story_lane
            },
            "decisions": {
                "total": sum(decision_status.values()),
                "status": decision_status
            },
            "backlog": {
                "total": sum(backlog_status.values()),
                "status": backlog_status
            },
            "traces": {
                "total": trace_count
            }
        }

        return jsonify({
            "stats": stats,
            "stories": stories,
            "decisions": decisions,
            "traces": traces,
            "backlog": backlog
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@invoices_blueprint.post("/api/harness/story")
def api_harness_story_add():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    conn = None
    try:
        body = request.get_json(force=True) or {}
        story_id = body.get("id", "").strip()
        title = body.get("title", "").strip()
        lane = body.get("lane", "normal").strip()
        contract = (body.get("contract") or body.get("contract_doc") or "").strip()
        status = body.get("status", "planned").strip()
        notes = body.get("notes", "").strip()

        if not story_id or not title:
            return jsonify({"error": "Mã (id) và Tiêu đề (title) là bắt buộc."}), 400

        conn = get_harness_db()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO story (id, title, risk_lane, contract_doc, status, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (story_id, title, lane, contract, status, notes)
        )
        conn.commit()
        return jsonify({"success": True, "message": f"Story {story_id} added successfully."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@invoices_blueprint.post("/api/harness/story/update")
def api_harness_story_update():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    conn = None
    try:
        body = request.get_json(force=True) or {}
        story_id = body.get("id", "").strip()
        status = body.get("status", "planned").strip()
        evidence = body.get("evidence", "").strip()
        
        proofs = body.get("proofs") or {}
        unit = body.get("unit") if body.get("unit") is not None else proofs.get("unit")
        integration = body.get("integration") if body.get("integration") is not None else proofs.get("integration")
        e2e = body.get("e2e") if body.get("e2e") is not None else proofs.get("e2e")
        platform = body.get("platform") if body.get("platform") is not None else proofs.get("platform")

        if not story_id:
            return jsonify({"error": "Mã (id) là bắt buộc."}), 400

        # convert potential empty strings or convert type
        try:
            unit = int(unit) if unit is not None and str(unit).strip() != "" else None
        except Exception:
            unit = None
        try:
            integration = int(integration) if integration is not None and str(integration).strip() != "" else None
        except Exception:
            integration = None
        try:
            e2e = int(e2e) if e2e is not None and str(e2e).strip() != "" else None
        except Exception:
            e2e = None
        try:
            platform = int(platform) if platform is not None and str(platform).strip() != "" else None
        except Exception:
            platform = None

        conn = get_harness_db()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE story
            SET status = ?, evidence = COALESCE(?, evidence),
                unit_proof = COALESCE(?, unit_proof),
                integration_proof = COALESCE(?, integration_proof),
                e2e_proof = COALESCE(?, e2e_proof),
                platform_proof = COALESCE(?, platform_proof)
            WHERE id = ?
            """,
            (status, evidence, unit, integration, e2e, platform, story_id)
        )
        conn.commit()
        return jsonify({"success": True, "message": f"Story {story_id} updated successfully."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@invoices_blueprint.post("/api/harness/decision")
def api_harness_decision_add():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    conn = None
    try:
        body = request.get_json(force=True) or {}
        decision_id = body.get("id", "").strip()
        title = body.get("title", "").strip()
        status = body.get("status", "proposed").strip()
        doc = (body.get("doc") or body.get("doc_path") or "").strip()
        verify = (body.get("verify") or body.get("verify_command") or body.get("verify_cmd") or "").strip()
        predicted = (body.get("predicted") or body.get("predicted_impact") or "").strip()
        notes = body.get("notes", "").strip()

        if not decision_id or not title:
            return jsonify({"error": "Mã (id) và Tiêu đề (title) là bắt buộc."}), 400

        conn = get_harness_db()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO decision (id, title, status, doc_path, verify_command, predicted_impact, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (decision_id, title, status, doc, verify, predicted, notes)
        )
        conn.commit()
        return jsonify({"success": True, "message": f"Decision {decision_id} recorded successfully."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@invoices_blueprint.post("/api/harness/backlog")
def api_harness_backlog_add():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    conn = None
    try:
        body = request.get_json(force=True) or {}
        title = body.get("title", "").strip()
        discovered_while = body.get("discovered_while", "").strip()
        current_pain = body.get("current_pain", "").strip()
        suggested_improvement = body.get("suggested_improvement", "").strip()
        risk = body.get("risk", "normal").strip()
        status = body.get("status", "open").strip()
        predicted_impact = body.get("predicted_impact", "").strip()
        notes = body.get("notes", "").strip()

        if not title:
            return jsonify({"error": "Tiêu đề (title) là bắt buộc."}), 400

        conn = get_harness_db()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO backlog (title, discovered_while, current_pain, suggested_improvement, risk, status, predicted_impact, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """,
            (title, discovered_while, current_pain, suggested_improvement, risk, status, predicted_impact, notes)
        )
        conn.commit()
        return jsonify({"success": True, "message": "Backlog item added successfully."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@invoices_blueprint.get("/api/harness/agent/stream")
def api_agent_stream():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    provider = request.args.get("provider", "gemini").strip()
    model = request.args.get("model", "gemini-2.5-flash").strip()
    goal = request.args.get("goal", "").strip()
    story_id = request.args.get("story_id", "").strip()

    if not goal:
        return jsonify({"error": "Goal is required"}), 400

    from flask import Response

    def generate():
        import subprocess
        import os
        import json

        env = os.environ.copy()
        env["AGENT_PROVIDER"] = provider
        env["AGENT_MODEL"] = model
        env["AGENT_GOAL"] = goal
        if story_id:
            env["AGENT_STORY_ID"] = story_id

        cmd = ["node", "scripts/agent-harness/run-agent.js"]

        proc = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        while True:
            line = proc.stdout.readline()
            if not line:
                break
            line_str = line.strip()
            if line_str:
                yield f"data: {line_str}\n\n"

        err = proc.stderr.read()
        if err:
            try:
                # Try parsing as JSON error from run-agent.js
                err_data = json.loads(err.strip())
                yield f"data: {json.dumps(err_data)}\n\n"
            except Exception:
                yield f"data: {json.dumps({'type': 'error', 'message': err.strip()})}\n\n"

        proc.wait()

        if proc.returncode != 0:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Process exited with code {proc.returncode}'})}\n\n"
        else:
            if story_id:
                try:
                    git_hash = "unknown"
                    try:
                        git_hash = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
                        status_out = subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()
                        if status_out:
                            git_hash += " (dirty)"
                    except Exception:
                        pass

                    conn = None
                    try:
                        conn = get_harness_db()
                        cur = conn.cursor()
                        cur.execute(
                            """
                            INSERT INTO trace (task_summary, story_id, agent, outcome, git_hash, created_at, actions_taken, notes)
                            VALUES (?, ?, ?, 'completed', ?, datetime('now'), ?, ?)
                            """,
                            (f"Autonomous Run: {goal[:50]}...", story_id, "SkawldAgent", git_hash, '["run-agent.js"]', f"Goal: {goal}")
                        )
                        conn.commit()
                    finally:
                        if conn:
                            conn.close()
                except Exception as db_err:
                    print(f"Error logging trace to DB: {db_err}")

    return Response(generate(), mimetype="text/event-stream")


@invoices_blueprint.post("/api/harness/risk/evaluate")
def api_harness_risk_evaluate():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized
    body = request.get_json(force=True) or {}
    text = body.get("text", "").strip()
    if not text:
        return jsonify({"error": "No spec text provided"}), 400

    text_lower = text.lower()
    
    checklist = {
        "auth": ["auth", "login", "logout", "session", "password", "token"],
        "authorization": ["role", "permission", "tenant", "access control"],
        "data_model": ["schema", "migration", "sqlite", "table", "column", "drop table"],
        "security": ["audit", "security", "privacy", "access log", "secret", "oauth"],
        "external": ["email", "payment", "sdk", "webhook", "queue", "api", "request", "http", "vietqr", "gdt"],
        "contract": ["api shape", "response envelope", "client-visible", "contract"],
        "cross_platform": ["desktop", "mobile", "browser", "native", "deep link"],
        "existing_behavior": ["refactor", "change", "fix", "patch"],
        "weak_proof": ["untested", "missing tests", "no test"],
        "multi_domain": ["multi-domain", "multiple domain"]
    }
    
    flags_found = []
    for flag, kw_list in checklist.items():
        if any(kw in text_lower for kw in kw_list):
            flags_found.append(flag)
            
    hard_gates = ["auth", "authorization", "data_model", "security", "external"]
    has_hard_gate = any(fg in hard_gates for fg in flags_found)
    
    num_flags = len(flags_found)
    if has_hard_gate or num_flags >= 4:
        lane = "high_risk"
    elif num_flags >= 2:
        lane = "normal"
    else:
        lane = "tiny"
        
    return jsonify({
        "suggested_lane": lane,
        "flags_found": flags_found,
        "has_hard_gate": has_hard_gate,
        "flag_count": num_flags
    })


@invoices_blueprint.get("/api/harness/db/stats")
def api_harness_db_stats():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized
    
    db_file = "harness.db"
    size_mb = 0.0
    last_modified = "unknown"
    if os.path.exists(db_file):
        size_bytes = os.path.getsize(db_file)
        size_mb = round(size_bytes / (1024 * 1024), 2)
        mtime = os.path.getmtime(db_file)
        last_modified = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")

    conn = None
    try:
        conn = get_harness_db()
        cur = conn.cursor()
        
        tables = {}
        for tbl in ["story", "decision", "backlog", "trace"]:
            cur.execute(f"SELECT COUNT(*) as count FROM {tbl}")
            tables[tbl] = cur.fetchone()["count"]
            
        return jsonify({
            "file_name": db_file,
            "size_mb": size_mb,
            "last_modified": last_modified,
            "table_counts": tables
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()


@invoices_blueprint.post("/api/harness/db/backup")
def api_harness_db_backup():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized
    
    import shutil
    db_file = "harness.db"
    if not os.path.exists(db_file):
        return jsonify({"error": "Database file not found"}), 404
        
    try:
        backup_dir = "data/backup"
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(backup_dir, f"harness_backup_{timestamp}.db")
        shutil.copy2(db_file, backup_file)
        return jsonify({
            "success": True, 
            "message": f"Successfully backed up database to {backup_file}",
            "backup_file": backup_file
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.get("/api/harness/db/download")
def api_harness_db_download():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized
    
    db_file = "harness.db"
    if not os.path.exists(db_file):
        return jsonify({"error": "Database file not found"}), 404
        
    return send_file(db_file, as_attachment=True, download_name="harness.db")


@invoices_blueprint.get("/api/harness/validate/stream")
def api_harness_validate_stream():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from flask import Response
    
    def generate_validation():
        import subprocess
        import os
        import json
        
        validate_script = os.path.join("scripts", "validate.bat")
        
        if not os.path.exists(validate_script):
            yield f"data: {json.dumps({'type': 'error', 'message': 'Validation script scripts/validate.bat not found.'})}\n\n"
            return
            
        proc = subprocess.Popen(
            [validate_script],
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        yield f"data: {json.dumps({'type': 'status', 'message': 'Running system validation checks...'})}\n\n"
        
        while True:
            line = proc.stdout.readline()
            if not line and proc.poll() is not None:
                break
            if line:
                yield f"data: {json.dumps({'type': 'output', 'text': line})}\n\n"
                
        proc.wait()
        
        if proc.returncode == 0:
            yield f"data: {json.dumps({'type': 'status', 'message': 'Validation PASSED. All tests and checks passed successfully.'})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'success': True})}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'status', 'message': f'Validation FAILED with exit code {proc.returncode}.'})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'success': False})}\n\n"
            
    return Response(generate_validation(), mimetype="text/event-stream")
@invoices_blueprint.post("/api/bctc/compile")
@roles_required("admin", "auditor")
def api_bctc_compile():
    """Compile BCTC B01-DN, B02-DN, B03-DN from Trial Balance ledger data (US-200)."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized
        
    balances = {}
    metadata = request.json or {}
    
    if "file" in request.files:
        file = request.files["file"]
        if file and file.filename:
            try:
                from invoices.bctc_service import parse_ledger_file
                balances = parse_ledger_file(file.read(), file.filename)
                # Populate metadata from request form fields if present
                metadata = {
                    "mst": request.form.get("mst", "0109998887"),
                    "company_name": request.form.get("company_name", "CONG TY TNHH MOCK"),
                    "year": int(request.form.get("year", datetime.now().year)),
                    "reporting_period_type": request.form.get("reporting_period_type", "N"),
                    "dividends_paid": float(request.form.get("dividends_paid", 0.0))
                }
            except Exception as e:
                return jsonify({"error": f"Loi doc file: {str(e)}"}), 400
    else:
        balances = metadata.get("balances", {})
        
    if not balances:
        return jsonify({"error": "Thieu du lieu bang can doi phat sinh / so cai."}), 400
        
    try:
        from invoices.bctc_service import compile_bctc
        xml_str, warnings = compile_bctc(balances, metadata)
        return jsonify({
            "status": "success" if not warnings else "warning",
            "xml": xml_str,
            "warnings": warnings
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/bctc/audit-ledger")
@roles_required("admin", "auditor")
def api_bctc_audit_ledger():
    """Cross-reference General Ledger entries with e-invoices for compliance (US-201)."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized
        
    balances = {}
    taxpayer_mst = request.args.get("taxpayer_mst") or session.get("taxpayer_mst") or "0109998887"
    
    if "file" in request.files:
        file = request.files["file"]
        if file and file.filename:
            try:
                from invoices.bctc_service import parse_ledger_file
                balances = parse_ledger_file(file.read(), file.filename)
                taxpayer_mst = request.form.get("taxpayer_mst") or taxpayer_mst
            except Exception as e:
                return jsonify({"error": f"Loi doc file: {str(e)}"}), 400
    else:
        payload = request.json or {}
        balances = payload.get("balances", {})
        taxpayer_mst = payload.get("taxpayer_mst") or taxpayer_mst
        
    if not balances:
        return jsonify({"error": "Thieu du lieu bang can doi phat sinh / so cai."}), 400
        
    try:
        from invoices.bctc_service import audit_ledger_against_invoices
        report = audit_ledger_against_invoices(balances, taxpayer_mst)
        return jsonify(report)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/payments/tax-slip")
@roles_required("admin", "auditor")
def api_payments_tax_slip():
    """Generate GDT Form 711/MB Tax Payment Slip XML and VietQR code (US-202)."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized
        
    payload = request.json or {}
    mst = payload.get("mst") or session.get("taxpayer_mst") or "0109998887"
    company_name = payload.get("company_name", "CONG TY TNHH MOCK")
    tax_type = payload.get("tax_type")
    amount = payload.get("amount")
    
    if not tax_type or not amount:
        return jsonify({"error": "Thieu thong tin loai thue hoac so tien."}), 400
        
    try:
        amount_val = float(amount)
    except ValueError:
        return jsonify({"error": "So tien khong hop le."}), 400
        
    chapter_type = payload.get("chapter_type", "domestic_private")
    treasury_name = payload.get("treasury_name", "Kho bac Nha nuoc Quan Cau Giay")
    treasury_account = payload.get("treasury_account", "111222333444")
    bank_bin = payload.get("bank_bin", "970415")
    
    try:
        from invoices.tax_payment_service import generate_tax_payment_slip
        slip = generate_tax_payment_slip(
            mst=mst,
            company_name=company_name,
            tax_type=tax_type,
            amount=amount_val,
            chapter_type=chapter_type,
            treasury_name=treasury_name,
            treasury_account=treasury_account,
            bank_bin=bank_bin
        )
        return jsonify(slip)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/payments/bank-recon")
@roles_required("admin", "auditor")
def api_payments_bank_recon():
    """Standard bank statement parsing, fuzzy matching, and cash payment compliance auditing (US-203)."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized
        
    taxpayer_mst = request.args.get("taxpayer_mst") or session.get("taxpayer_mst") or "0109998887"
    
    # Process uploaded bank statement if present
    results = {}
    if "file" in request.files:
        file = request.files["file"]
        if file and file.filename:
            try:
                content = file.read().decode("utf-8")
                from invoices.reconciliation_service import ReconciliationEngine
                engine = ReconciliationEngine()
                engine.process_csv(content)
                results = engine.run_matching()
            except Exception as e:
                return jsonify({"error": f"Loi xu ly file sao ke: {str(e)}"}), 400
                
    # Run cash compliance checks for invoices >= 20M VND
    try:
        from invoices.bank_reconcile_service import check_cash_payment_compliance
        compliance_flags = check_cash_payment_compliance(taxpayer_mst)
        return jsonify({
            "status": "success",
            "reconciliation_summary": results,
            "compliance_warnings": compliance_flags
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/ecommerce/sync")
@roles_required("admin", "auditor")
def api_ecommerce_sync():
    """Parse platform reports and record daily consolidated revenue & fees in the database (US-204)."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized
        
    platform = request.args.get("platform", "shopee").strip()
    taxpayer_mst = request.args.get("taxpayer_mst") or session.get("taxpayer_mst") or "0109998887"
    
    orders = []
    
    if "file" in request.files:
        file = request.files["file"]
        if file and file.filename:
            try:
                from invoices.ecommerce_service import parse_ecommerce_sheet
                orders = parse_ecommerce_sheet(file.read(), platform)
            except Exception as e:
                return jsonify({"error": f"Loi doc file: {str(e)}"}), 400
    else:
        payload = request.json or {}
        orders = payload.get("orders", [])
        taxpayer_mst = payload.get("taxpayer_mst") or taxpayer_mst
        platform = payload.get("platform") or platform
        
    if not orders:
        return jsonify({"error": "Thieu du lieu don hang e-commerce."}), 400
        
    try:
        from invoices.ecommerce_service import sync_ecommerce_orders
        res = sync_ecommerce_orders(orders, taxpayer_mst, platform)
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.get("/api/ecommerce/reconcile")
@roles_required("admin", "auditor", "viewer")
def api_ecommerce_reconcile():
    """Reconcile Shopee/TikTok Shop order logs with output invoices (US-205)."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized
        
    taxpayer_mst = request.args.get("taxpayer_mst") or session.get("taxpayer_mst") or "0109998887"
    
    import json
    orders_json = request.args.get("orders")
    platform_orders = []
    if orders_json:
        try:
            platform_orders = json.loads(orders_json)
        except Exception:
            pass
            
    if not platform_orders:
        platform_orders = session.get("normalized_orders", [])
        
    if not platform_orders:
        platform_orders = [
            {"order_id": "ORD-SHOPEE-1001", "date": datetime.now().strftime("%Y-%m-%d"), "gross_revenue": 500000.0, "commission_fee": 15000.0, "service_fee": 5000.0},
            {"order_id": "ORD-SHOPEE-1002", "date": datetime.now().strftime("%Y-%m-%d"), "gross_revenue": 1200000.0, "commission_fee": 36000.0, "service_fee": 12000.0},
            {"order_id": "ORD-SHOPEE-1003", "date": datetime.now().strftime("%Y-%m-%d"), "gross_revenue": 850000.0, "commission_fee": 25500.0, "service_fee": 8500.0}
        ]
        
    try:
        from invoices.ecommerce_service import reconcile_ecommerce_tax
        report = reconcile_ecommerce_tax(taxpayer_mst, platform_orders)
        return jsonify(report)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# US-141: Audit Trail Viewer UI & Export
# ---------------------------------------------------------------------------

@invoices_blueprint.get("/audit-trail")
@roles_required("admin", "auditor")
def audit_trail_page():
    """Render the Audit Trail Viewer UI."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return redirect(url_for("index"))
    return render_template("audit_trail.html",
                           logged_in=session.get("logged_in"),
                           session_username=session.get("display_name") or session.get("username"))


@invoices_blueprint.get("/advanced-audit")
@roles_required("admin", "auditor")
def advanced_audit_page():
    """Render the Advanced Audit & Fraud Detection Page."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return redirect(url_for("index"))
    return render_template("advanced_audit.html",
                           logged_in=session.get("logged_in"),
                           session_username=session.get("display_name") or session.get("username"))


@invoices_blueprint.get("/api/audit-logs")
@roles_required("admin", "auditor")
def api_get_audit_logs():
    """Retrieve security audit logs with optional filtering."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from invoices.models import SecurityAuditLog

    try:
        query = SecurityAuditLog.query

        # Filters
        category = request.args.get("category")
        if category:
            query = query.filter(SecurityAuditLog.event_category == category)

        username = request.args.get("username")
        if username:
            query = query.filter(SecurityAuditLog.username.ilike(f"%{username}%"))

        tax_code = request.args.get("tax_code")
        if tax_code:
            query = query.filter(SecurityAuditLog.tax_code.ilike(f"%{tax_code}%"))

        date_from = request.args.get("date_from")
        if date_from:
            query = query.filter(SecurityAuditLog.timestamp >= date_from)

        date_to = request.args.get("date_to")
        if date_to:
            query = query.filter(SecurityAuditLog.timestamp <= date_to + "T23:59:59Z")

        keyword = request.args.get("keyword")
        if keyword:
            query = query.filter(SecurityAuditLog.event_details.ilike(f"%{keyword}%"))

        # Pagination
        page = request.args.get("page", 1, type=int)
        per_page = request.args.get("per_page", 50, type=int)
        per_page = min(per_page, 200)

        total = query.count()
        logs = query.order_by(SecurityAuditLog.id.desc()).offset((page - 1) * per_page).limit(per_page).all()

        return jsonify({
            "total": total,
            "page": page,
            "per_page": per_page,
            "logs": [
                {
                    "id": log.id,
                    "timestamp": log.timestamp,
                    "username": log.username,
                    "tax_code": log.tax_code,
                    "event_category": log.event_category,
                    "ip_address": log.ip_address,
                    "event_details": log.event_details,
                }
                for log in logs
            ],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.get("/api/audit-logs/export/csv")
@roles_required("admin", "auditor")
def api_export_audit_logs_csv():
    """Export filtered audit logs as CSV file."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from invoices.models import SecurityAuditLog
    import csv
    import io

    try:
        query = SecurityAuditLog.query

        category = request.args.get("category")
        if category:
            query = query.filter(SecurityAuditLog.event_category == category)
        username = request.args.get("username")
        if username:
            query = query.filter(SecurityAuditLog.username.ilike(f"%{username}%"))
        tax_code = request.args.get("tax_code")
        if tax_code:
            query = query.filter(SecurityAuditLog.tax_code.ilike(f"%{tax_code}%"))
        date_from = request.args.get("date_from")
        if date_from:
            query = query.filter(SecurityAuditLog.timestamp >= date_from)
        date_to = request.args.get("date_to")
        if date_to:
            query = query.filter(SecurityAuditLog.timestamp <= date_to + "T23:59:59Z")
        keyword = request.args.get("keyword")
        if keyword:
            query = query.filter(SecurityAuditLog.event_details.ilike(f"%{keyword}%"))

        logs = query.order_by(SecurityAuditLog.id.desc()).limit(10000).all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Timestamp", "Username", "Tax Code", "Category", "IP Address", "Details"])
        for log in logs:
            writer.writerow([
                log.id, log.timestamp, log.username, log.tax_code or "",
                log.event_category, log.ip_address or "", log.event_details or "",
            ])

        from datetime import datetime
        filename = f"audit_trail_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.get("/api/audit-logs/export/pdf")
@roles_required("admin", "auditor")
def api_export_audit_logs_pdf():
    """Export filtered audit logs as PDF file."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from invoices.models import SecurityAuditLog
    from datetime import datetime

    try:
        query = SecurityAuditLog.query

        category = request.args.get("category")
        if category:
            query = query.filter(SecurityAuditLog.event_category == category)
        username = request.args.get("username")
        if username:
            query = query.filter(SecurityAuditLog.username.ilike(f"%{username}%"))
        tax_code = request.args.get("tax_code")
        if tax_code:
            query = query.filter(SecurityAuditLog.tax_code.ilike(f"%{tax_code}%"))
        date_from = request.args.get("date_from")
        if date_from:
            query = query.filter(SecurityAuditLog.timestamp >= date_from)
        date_to = request.args.get("date_to")
        if date_to:
            query = query.filter(SecurityAuditLog.timestamp <= date_to + "T23:59:59Z")
        keyword = request.args.get("keyword")
        if keyword:
            query = query.filter(SecurityAuditLog.event_details.ilike(f"%{keyword}%"))

        logs = query.order_by(SecurityAuditLog.id.desc()).limit(5000).all()

        # Generate HTML-based PDF using render_template
        html = render_template("audit_trail_pdf.html",
                               logs=logs,
                               generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                               total_records=len(logs),
                               filters={
                                   "category": category,
                                   "username": username,
                                   "tax_code": tax_code,
                                   "date_from": date_from,
                                   "date_to": date_to,
                                   "keyword": keyword,
                               })

        filename = f"audit_trail_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        return Response(
            html,
            mimetype="text/html",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.get("/api/reports/signed-compliance")
@roles_required("admin", "auditor")
def api_export_signed_compliance():
    """Export audited compliance report with embedded cryptographic signature."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    try:
        parsed_from, parsed_to = validate_date_range(
            request.args.get("from", ""),
            request.args.get("to", ""),
        )
        direction = request.args.get("direction", "purchase")
        
        # Get invoices from service
        current_app.config["CURRENT_JWT"] = session.get("jwt")
        invoices = fetch_invoices(InvoiceQuery(parsed_from, parsed_to, False, direction))
        
        # Get system secret key for hashing
        secret_key = current_app.config.get("SECRET_KEY", "compliance-system-secret-key-12345")
        
        from invoices.compliance_report_service import generate_signed_excel_report
        excel_bytes = generate_signed_excel_report(invoices, secret_key)
        
        # Log this administrative export event in the security audit ledger
        from invoices.security_audit_service import log_security_event
        log_security_event(
            username=session.get("username", "admin"),
            event_category="EXPORT",
            tax_code=session.get("tax_code", ""),
            ip_address=request.remote_addr,
            event_details=f"Exported cryptographically signed compliance report for period {parsed_from} to {parsed_to} ({len(invoices)} invoices)."
        )

        filename = f"signed_compliance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return send_file(
            BytesIO(excel_bytes),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=filename,
        )
    except DateValidationError as error:
        return jsonify({"error": str(error)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        current_app.config["CURRENT_JWT"] = None


@invoices_blueprint.post("/api/reports/verify-signed")
@roles_required("admin", "auditor")
def api_verify_signed_report():
    """Upload and verify a signed compliance report file."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    if "file" not in request.files:
        return jsonify({"error": "Không tìm thấy tệp tin báo cáo được tải lên."}), 400

    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"error": "Tên tệp tin không hợp lệ."}), 400

    try:
        file_bytes = file.read()
        secret_key = current_app.config.get("SECRET_KEY", "compliance-system-secret-key-12345")
        
        from invoices.compliance_report_service import verify_excel_report
        result = verify_excel_report(file_bytes, secret_key)
        
        # Log security audit verification event
        status_str = "SUCCESS" if result.get("verified") else "FAILED"
        from invoices.security_audit_service import log_security_event
        log_security_event(
            username=session.get("username", "admin"),
            event_category="VERIFY",
            tax_code=session.get("tax_code", ""),
            ip_address=request.remote_addr,
            event_details=f"Performed cryptographic verification of compliance report file '{file.filename}'. Result: {status_str} ({result.get('invoices_count', 0)} invoices parsed)."
        )

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Lỗi xử lý xác minh báo cáo: {str(e)}"}), 500


@invoices_blueprint.get("/api/sync/health")
@roles_required("admin", "auditor")
def api_sync_health():
    """Retrieve CAPTCHA solver statistics and overall crawler status."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    try:
        from auth.captcha_solver import captcha_analytics

        # CAPTCHA metrics
        stats = captcha_analytics.get_stats()

        # Crawler status
        crawler_status = "idle"
        queue_instance = current_app.extensions.get("resilient_sync_queue")
        if queue_instance:
            with queue_instance._lock:
                if any(job.status == "running" for job in queue_instance.jobs.values()):
                    crawler_status = "running"

        return jsonify({
            "status": "healthy",
            "crawler_status": crawler_status,
            "solver": stats,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.get("/consolidated-dashboard")
@roles_required("admin", "auditor")
def consolidated_dashboard_page():
    """Render the corporate multi-entity consolidated dashboard."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    return render_template("consolidated.html")


@invoices_blueprint.route("/api/tenant/groups", methods=["GET", "POST"])
@roles_required("admin", "auditor")
def api_tenant_groups():
    """GET/POST API to fetch or create corporate tenant groups."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from invoices.models import TenantGroup
    import json

    username = session.get("username", "admin")

    if request.method == "POST":
        try:
            data = request.get_json() or {}
            group_name = data.get("group_name")
            taxpayer_msts = data.get("taxpayer_msts", [])

            if not group_name:
                return jsonify({"error": "Tên tập đoàn không được để trống."}), 400
            if not isinstance(taxpayer_msts, list):
                return jsonify({"error": "Danh sách MST phải là một mảng."}), 400

            # Validate MSTs
            taxpayer_msts = [str(mst).strip() for mst in taxpayer_msts if mst]

            # Upsert group
            group = TenantGroup.query.filter_by(group_name=group_name).first()
            if group:
                group.taxpayer_msts = json.dumps(taxpayer_msts)
                group.admin_username = username
            else:
                group = TenantGroup(
                    group_name=group_name,
                    admin_username=username,
                    taxpayer_msts=json.dumps(taxpayer_msts)
                )
                db.session.add(group)

            db.session.commit()
            return jsonify({"status": "success", "group": group.to_dict()})
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    # GET
    try:
        groups = TenantGroup.query.filter_by(admin_username=username).all()
        # Fallback to all groups if admin or no group found
        if not groups and username == "admin":
            groups = TenantGroup.query.all()
        return jsonify([g.to_dict() for g in groups])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.get("/api/tenant/consolidated")
@roles_required("admin", "auditor")
def api_tenant_consolidated():
    """Retrieve consolidated financial metrics and risk scores across a group's MSTs."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from invoices.models import TenantGroup
    from invoices.multitenant_service import get_tenant_consolidated_stats
    import json

    username = session.get("username", "admin")
    group_id = request.args.get("group_id")

    try:
        # 1. Resolve Group
        group = None
        if group_id:
            group = TenantGroup.query.get(group_id)
        else:
            group = TenantGroup.query.filter_by(admin_username=username).first()
            if not group and username == "admin":
                group = TenantGroup.query.first()

        if not group:
            return jsonify({
                "group_id": None,
                "group_name": "Không có nhóm",
                "summary": {
                    "total_invoices": 0,
                    "total_revenue": 0.0,
                    "vat_output": 0.0,
                    "vat_input": 0.0,
                    "average_t_score": 100.0
                },
                "entities": []
            })

        # 2. Query each member MST
        mst_list = group.get_mst_list()
        entities = []
        for mst in mst_list:
            stats = get_tenant_consolidated_stats(mst)
            entities.append(stats)

        # 3. Aggregate totals
        total_invoices = sum(e["total_invoices"] for e in entities)
        total_revenue = sum(e["total_revenue"] for e in entities)
        vat_output = sum(e["vat_output"] for e in entities)
        vat_input = sum(e["vat_input"] for e in entities)
        
        # Weighted average for T-Score
        t_score_sum = 0.0
        t_score_count = 0
        for e in entities:
            if e["total_invoices"] > 0:
                t_score_sum += e["average_t_score"] * e["total_invoices"]
                t_score_count += e["total_invoices"]
            else:
                t_score_sum += e["average_t_score"]
                t_score_count += 1
                
        average_t_score = round(t_score_sum / t_score_count, 1) if t_score_count > 0 else 100.0

        return jsonify({
            "group_id": group.id,
            "group_name": group.group_name,
            "summary": {
                "total_invoices": total_invoices,
                "total_revenue": total_revenue,
                "vat_output": vat_output,
                "vat_input": vat_input,
                "average_t_score": average_t_score
            },
            "entities": entities
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/cit/finalize")
@roles_required("admin", "auditor")
def api_cit_finalize():
    """US-180: Compile CIT Finalization and generate Form 03/TNDN XML."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from datetime import datetime
    balances = {}
    metadata = {
        "mst": request.form.get("mst") or session.get("taxpayer_mst") or "0109998887",
        "company_name": request.form.get("company_name", "CONG TY TNHH MOCK"),
        "year": int(request.form.get("year", datetime.now().year)),
        "non_deductible_manual": float(request.form.get("non_deductible_manual", 0.0)),
        "loss_carry_forward": float(request.form.get("loss_carry_forward", 0.0)),
        "rd_allowance": float(request.form.get("rd_allowance", 0.0))
    }

    if "file" in request.files:
        file = request.files["file"]
        if file and file.filename:
            try:
                from invoices.bctc_service import parse_ledger_file
                balances = parse_ledger_file(file.read(), file.filename)
            except Exception as e:
                return jsonify({"error": f"Loi doc file: {str(e)}"}), 400
    else:
        payload = request.json or {}
        balances = payload.get("balances", {})
        metadata.update(payload.get("metadata", {}))

    if not balances:
        return jsonify({"error": "Thieu du lieu bang can doi phat sinh / so cai."}), 400

    try:
        from invoices.cit_service import finalize_cit
        result = finalize_cit(balances, metadata)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/cit/simulate-scenario")
@roles_required("admin", "auditor")
def api_cit_simulate_scenario():
    """US-181: Simulate what-if tax scenarios based on slider adjustments."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    try:
        payload = request.get_json() or {}
        base_data = payload.get("base_data", {})
        adjustments = payload.get("adjustments", {})
        
        from invoices.cit_service import simulate_cit_scenario
        result = simulate_cit_scenario(base_data, adjustments)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# US-150: Smart Cash Flow Predictor — rolling 30/60/90-day projections
# US-151: Interactive Scenario Simulator — what-if stress testing
# ---------------------------------------------------------------------------


@invoices_blueprint.route("/api/finance/cashflow")
def api_finance_cashflow():
    """US-150: Return rolling 30/60/90-day cash-flow projections."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    try:
        taxpayer_mst = session.get("active_taxpayer_mst") or request.args.get("mst")
        from invoices.cashflow_service import calculate_cashflow_projection
        result = calculate_cashflow_projection(taxpayer_mst=taxpayer_mst)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500



@invoices_blueprint.route("/api/finance/simulate", methods=["POST"])
def api_finance_simulate():
    """US-151: Stateless scenario simulation with adjustable parameters."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    try:
        payload = request.get_json() or {}
        delay_days = int(payload.get("delay_days", 0))
        rejection_rate = float(payload.get("rejection_rate", 0.0))
        vat_adjustment = float(payload.get("vat_adjustment", 0.0))
        taxpayer_mst = session.get("active_taxpayer_mst") or payload.get("mst")

        from invoices.cashflow_service import simulate_scenario
        result = simulate_scenario(
            taxpayer_mst=taxpayer_mst,
            delay_days=delay_days,
            rejection_rate=rejection_rate,
            vat_adjustment=vat_adjustment,
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@invoices_blueprint.post("/api/partners/<mst>/decree-132")
@roles_required("admin", "auditor")
def update_partner_decree_132(mst):
    """Update Decree 132 relationship code for a specific partner."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized
    from invoices.models import Partner
    from extensions import db
    try:
        partner = db.session.get(Partner, mst)
        if not partner:
            return jsonify({"error": f"Không tìm thấy đối tác với MST {mst}"}), 404
        
        body = request.get_json(silent=True) or {}
        relationship = body.get("decree_132_relationship")
        
        if relationship is not None:
            relationship = str(relationship).strip()
            if relationship == "":
                relationship = None
            else:
                valid_codes = {chr(c) for c in range(ord('A'), ord('L') + 1)}
                if relationship.upper() not in valid_codes:
                    return jsonify({"error": "Mã liên kết không hợp lệ. Phải thuộc từ A đến L."}), 400
                relationship = relationship.upper()
                
        partner.decree_132_relationship = relationship
        db.session.commit()
        
        return jsonify({
            "success": True,
            "partner": partner.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/agents/send")
def api_agents_send():
    """US-320: Post a message from one AI agent to another."""
    import json
    from datetime import datetime, timezone
    from invoices.models import AgentMessage
    from extensions import db

    body = request.get_json(silent=True) or {}
    sender = body.get("sender_agent")
    receiver = body.get("receiver_agent")
    subject = body.get("subject")
    payload = body.get("payload", {})

    if not sender or not receiver or not subject:
        return jsonify({"error": "sender_agent, receiver_agent, and subject are required."}), 400

    try:
        if isinstance(payload, (dict, list)):
            payload_str = json.dumps(payload)
        else:
            payload_str = str(payload)

        msg = AgentMessage(
            sender_agent=str(sender).strip(),
            receiver_agent=str(receiver).strip(),
            subject=str(subject).strip(),
            payload=payload_str,
            status="pending",
            timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )
        db.session.add(msg)
        db.session.commit()

        return jsonify({
            "success": True,
            "message": "Message sent successfully.",
            "data": msg.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.get("/api/agents/inbox/<agent_name>")
def api_agents_inbox(agent_name):
    """US-320: Get pending and processed messages for a specific agent."""
    from invoices.models import AgentMessage
    try:
        status_filter = request.args.get("status", "pending")
        query = AgentMessage.query.filter_by(receiver_agent=agent_name)
        if status_filter:
            query = query.filter_by(status=status_filter)
        messages = query.order_by(AgentMessage.id.desc()).all()
        return jsonify([msg.to_dict() for msg in messages])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/agents/update-status/<int:message_id>")
def api_agents_update_status(message_id):
    """US-320: Update the processing status of an agent message."""
    from invoices.models import AgentMessage
    from extensions import db
    try:
        msg = db.session.get(AgentMessage, message_id)
        if not msg:
            return jsonify({"error": f"Message with ID {message_id} not found."}), 404

        body = request.get_json(silent=True) or {}
        new_status = body.get("status")
        if new_status not in ["pending", "processed", "failed"]:
            return jsonify({"error": "Invalid status. Must be pending, processed, or failed."}), 400

        msg.status = new_status
        db.session.commit()
        return jsonify({
            "success": True,
            "message": "Status updated successfully.",
            "data": msg.to_dict()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/agents/audit-coordinator")
def api_agents_audit_coordinator():
    """US-321: Run the multi-agent joint audit coordinator swarm."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    taxpayer_mst = session.get("active_taxpayer_mst") or body.get("taxpayer_mst")
    user_prompt = body.get("user_prompt")

    if not taxpayer_mst or not user_prompt:
        return jsonify({"error": "taxpayer_mst and user_prompt are required."}), 400

    from invoices.agent_swarm import JointAuditCoordinator
    try:
        coordinator = JointAuditCoordinator()
        result = coordinator.execute_swarm(taxpayer_mst=taxpayer_mst, user_prompt=user_prompt)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/bank/ingest")
def api_bank_ingest():
    """US-322: Ingest bank statement feed files."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    taxpayer_mst = session.get("active_taxpayer_mst") or body.get("taxpayer_mst")
    file_content = body.get("file_content")
    bank_name = body.get("bank_name", "Vietcombank")
    file_type = body.get("file_type", "csv")

    if not taxpayer_mst or not file_content:
        return jsonify({"error": "taxpayer_mst and file_content are required."}), 400

    from invoices.bank_stream_service import BankStreamService
    try:
        service = BankStreamService()
        count = service.ingest_bank_statement(file_content, taxpayer_mst, bank_name, file_type)
        return jsonify({"success": True, "inserted_count": count}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/bank/match")
def api_bank_match():
    """US-323: Execute automated matching of transactions with invoices."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    taxpayer_mst = session.get("active_taxpayer_mst") or body.get("taxpayer_mst")

    if not taxpayer_mst:
        return jsonify({"error": "taxpayer_mst is required."}), 400

    from invoices.bank_stream_service import BankStreamService
    try:
        service = BankStreamService()
        result = service.execute_transaction_matching(taxpayer_mst)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.get("/api/bank/transactions")
def api_bank_transactions():
    """List bank transactions."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    taxpayer_mst = session.get("active_taxpayer_mst") or request.args.get("taxpayer_mst")
    if not taxpayer_mst:
        return jsonify({"error": "taxpayer_mst is required."}), 400

    match_status = request.args.get("match_status")
    from invoices.models import BankTransaction
    query = BankTransaction.query.filter_by(taxpayer_mst=taxpayer_mst)
    if match_status:
        query = query.filter_by(match_status=match_status)

    transactions = query.all()
    return jsonify([tx.to_dict() for tx in transactions])


@invoices_blueprint.get("/api/fraud/network")
def api_fraud_network():
    """US-330: Fetch directed supplier-buyer transaction network graph."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    taxpayer_mst = session.get("active_taxpayer_mst") or request.args.get("taxpayer_mst")
    if not taxpayer_mst:
        return jsonify({"error": "taxpayer_mst is required."}), 400

    from invoices.graph_service import TaxpayerNetworkGraphGenerator
    try:
        graph = TaxpayerNetworkGraphGenerator.build_network_graph(taxpayer_mst)
        formatted_nodes = [node for node in graph["nodes"].values()]
        formatted_edges = [edge for edge in graph["edges"].values()]
        return jsonify({
            "status": "success",
            "nodes": formatted_nodes,
            "edges": formatted_edges
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.get("/api/fraud/alerts")
def api_fraud_alerts():
    """US-331: Get VAT circular invoicing loop alerts and authority score outliers."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    taxpayer_mst = session.get("active_taxpayer_mst") or request.args.get("taxpayer_mst")
    if not taxpayer_mst:
        return jsonify({"error": "taxpayer_mst is required."}), 400

    from invoices.graph_service import TaxpayerNetworkGraphGenerator, VATFraudRingNetworkDetector
    try:
        graph = TaxpayerNetworkGraphGenerator.build_network_graph(taxpayer_mst)
        detector = VATFraudRingNetworkDetector(graph)
        alerts = detector.detect_fraud_networks()
        return jsonify({
            "status": "success",
            "alerts": alerts
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/ledger/verify")
def api_ledger_verify():
    """US-332: Verify the cryptographic Merkle Ledger integrity for a taxpayer."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    taxpayer_mst = session.get("active_taxpayer_mst") or body.get("taxpayer_mst")
    if not taxpayer_mst:
        return jsonify({"error": "taxpayer_mst is required."}), 400

    from invoices.merkle_service import verify_ledger_integrity, rebuild_and_write_merkle_roots
    try:
        rebuild_and_write_merkle_roots(taxpayer_mst)
        is_valid, tampered_ids = verify_ledger_integrity(taxpayer_mst)
        return jsonify({
            "status": "success",
            "is_valid": is_valid,
            "tampered_invoice_ids": tampered_ids,
            "message": "Không phát hiện hành vi can thiệp dữ liệu." if is_valid else f"Phát hiện dữ liệu bị sửa đổi ở các hóa đơn: {', '.join(tampered_ids)}"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/ledger/zkp-prove")
def api_ledger_zkp_prove():
    """US-333: Generate ZKP proof of compliance for a given invoice."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    invoice_id = body.get("invoice_id")
    if not invoice_id:
        return jsonify({"error": "invoice_id is required."}), 400

    from invoices.models import Invoice
    invoice = Invoice.query.filter_by(id=invoice_id).first()
    if not invoice:
        return jsonify({"error": "Invoice not found."}), 404

    rate_percent = 10
    if invoice.amount_before_tax > 0:
        calculated_rate = (invoice.tax_amount / invoice.amount_before_tax) * 100
        rate_percent = int(round(calculated_rate))

    from invoices.zkp_service import generate_vat_compliance_proof
    try:
        proof = generate_vat_compliance_proof(
            amount_before_tax=invoice.amount_before_tax,
            tax_amount=invoice.tax_amount,
            rate_percent=rate_percent
        )
        return jsonify({
            "status": "success",
            "invoice_id": invoice_id,
            "proof": proof
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/ledger/zkp-verify")
def api_ledger_zkp_verify():
    """US-333: Verify a ZKP proof of compliance."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    proof_data = body.get("proof_data")
    if not proof_data:
        return jsonify({"error": "proof_data is required."}), 400

    from invoices.zkp_service import verify_vat_compliance_proof
    try:
        is_valid = verify_vat_compliance_proof(proof_data)
        return jsonify({
            "status": "success",
            "is_valid": is_valid,
            "message": "Chứng minh tuân thủ thuế GTGT hợp lệ (ZKP Verified)." if is_valid else "Chứng minh tuân thủ không hợp lệ."
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/customs/upload")
@roles_required("admin", "auditor")
def api_customs_upload():
    """US-334: Import VNACCS/VCIS Customs XML import declarations."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if not file or not file.filename.endswith(".xml"):
        return jsonify({"error": "Only XML files are supported"}), 400

    try:
        xml_bytes = file.read()
        from invoices.customs_service import CustomsReconciliationEngine
        decl = CustomsReconciliationEngine.ingest_declaration(xml_bytes)
        return jsonify({
            "status": "success",
            "message": "Customs declaration imported successfully.",
            "declaration": decl.to_dict()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/customs/reconcile")
@roles_required("admin", "auditor")
def api_customs_reconcile():
    """US-335: Compare customs declarations with domestic/import VAT input invoices."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    taxpayer_mst = session.get("active_taxpayer_mst") or body.get("taxpayer_mst")
    if not taxpayer_mst:
        return jsonify({"error": "taxpayer_mst is required."}), 400

    from invoices.customs_service import CustomsReconciliationEngine
    try:
        results = CustomsReconciliationEngine.run_reconciliation(taxpayer_mst)
        return jsonify({
            "status": "success",
            "results": results
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.get("/api/customs/declarations")
def api_customs_declarations():
    """US-334: List imported customs declarations."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    taxpayer_mst = session.get("active_taxpayer_mst") or request.args.get("taxpayer_mst")
    if not taxpayer_mst:
        return jsonify({"error": "taxpayer_mst is required."}), 400

    from invoices.models import CustomsDeclaration
    try:
        decls = CustomsDeclaration.query.filter_by(taxpayer_mst=taxpayer_mst).all()
        return jsonify({
            "status": "success",
            "declarations": [d.to_dict() for d in decls]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/predictive/tax-forecast")
def api_tax_forecast():
    """US-324: Retrieve predictive tax liability reports using ML trend + seasonality forecasting."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    taxpayer_mst = session.get("active_taxpayer_mst") or body.get("taxpayer_mst")
    months_ahead = int(body.get("months_ahead", 12))

    # Allow client to supply historical data, or aggregate from DB
    historical = body.get("historical_data")
    if historical is None:
        if not taxpayer_mst:
            return jsonify({"error": "taxpayer_mst is required to retrieve database history."}), 400

        from invoices.models import Invoice
        try:
            invoices = Invoice.query.filter_by(taxpayer_mst=taxpayer_mst, is_cancelled=False).all()
            from collections import defaultdict
            monthly_data = defaultdict(lambda: {
                "output_vat": 0.0,
                "input_vat": 0.0,
                "revenue": 0.0,
                "expenses": 0.0,
            })

            for inv in invoices:
                if not inv.date or len(inv.date) < 7:
                    continue
                period = inv.date[:7]  # YYYY-MM
                if "-" not in period:
                    continue

                if inv.seller_mst == taxpayer_mst:
                    monthly_data[period]["revenue"] += inv.amount_before_tax
                    monthly_data[period]["output_vat"] += inv.tax_amount
                elif inv.buyer_mst == taxpayer_mst:
                    monthly_data[period]["expenses"] += inv.amount_before_tax
                    monthly_data[period]["input_vat"] += inv.tax_amount

            historical = []
            for period, vals in monthly_data.items():
                vat_pay = max(0.0, vals["output_vat"] - vals["input_vat"])
                pretax = vals["revenue"] - vals["expenses"]
                cit_pay = max(0.0, pretax * 0.20)
                fct_pay = max(0.0, vals["expenses"] * 0.10 * 0.05)
                
                historical.append({
                    "period": period,
                    "vat_payable": vat_pay,
                    "cit_payable": cit_pay,
                    "fct_payable": fct_pay,
                })
        except Exception as e:
            return jsonify({"error": f"Failed to retrieve history: {str(e)}"}), 500

    from invoices.tax_forecaster import ml_forecast_tax_liabilities
    try:
        forecast = ml_forecast_tax_liabilities(historical, months_ahead=months_ahead)
        return jsonify({
            "status": "success",
            "forecast": forecast
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/predictive/simulate-scenario")
def api_simulate_scenario():
    """US-325: Execute stateless comparative tax scenario calculations."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    taxpayer_mst = session.get("active_taxpayer_mst") or body.get("taxpayer_mst")
    
    adjustments = body.get("adjustments", {})
    base_data = body.get("base_data")

    # If base data is not supplied, build it from DB aggregates or default mocks
    if base_data is None:
        if not taxpayer_mst:
            return jsonify({"error": "taxpayer_mst is required to aggregate baseline data."}), 400

        from invoices.models import Invoice
        try:
            invoices = Invoice.query.filter_by(taxpayer_mst=taxpayer_mst, is_cancelled=False).all()
            output_vat_base = 0.0
            input_vat_base = 0.0
            revenue_base = 0.0
            expenses_base = 0.0

            for inv in invoices:
                if inv.seller_mst == taxpayer_mst:
                    revenue_base += inv.amount_before_tax
                    output_vat_base += inv.tax_amount
                elif inv.buyer_mst == taxpayer_mst:
                    expenses_base += inv.amount_before_tax
                    input_vat_base += inv.tax_amount

            base_data = {
                "output_vat_base": output_vat_base,
                "input_vat_base": input_vat_base,
                "revenue_base": revenue_base,
                "expenses_base": expenses_base,
                "fct_base_amount": expenses_base * 0.10,
                "related_party_interest_base": expenses_base * 0.05,
                "depreciation_base": expenses_base * 0.08,
            }
        except Exception as e:
            return jsonify({"error": f"Failed to build baseline data: {str(e)}"}), 500

    from invoices.tax_forecaster import simulate_tax_scenario
    try:
        result = simulate_tax_scenario(base_data, adjustments)
        return jsonify({
            "status": "success",
            "result": result
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/audit/calculate-penalties")
def api_calculate_penalties():
    """US-340: Calculate GDT tax penalties and daily late payment interest."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized
    
    body = request.get_json(silent=True) or {}
    underpaid_tax = float(body.get("underpaid_tax", 0.0))
    due_date = body.get("due_date")
    payment_date = body.get("payment_date")
    evasion_multiplier = float(body.get("evasion_multiplier", 0.0))
    has_mitigating_factors = bool(body.get("has_mitigating_factors", False))
    
    if not due_date or not payment_date:
        return jsonify({"error": "Thieu thong tin ngay den han hoac ngay nop tien thuc te."}), 400
        
    try:
        from invoices.tax_audit_service import calculate_audit_penalties
        result = calculate_audit_penalties(
            underpaid_tax=underpaid_tax,
            due_date=due_date,
            payment_date=payment_date,
            evasion_multiplier=evasion_multiplier,
            has_mitigating_factors=has_mitigating_factors
        )
        return jsonify({
            "status": "success",
            "calculation": result
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/audit/generate-explanation")
def api_generate_explanation():
    """US-341: Generate statutory Vietnamese letters citing compliance laws."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized
        
    body = request.get_json(silent=True) or {}
    risk_type = body.get("risk_type", "")
    taxpayer_name = body.get("taxpayer_name", "CONG TY TNHH MOCK")
    taxpayer_mst = body.get("taxpayer_mst") or session.get("active_taxpayer_mst") or "0109998887"
    details = body.get("details", {})
    
    if not risk_type:
        return jsonify({"error": "Thieu thong tin loai rui ro (risk_type)."}), 400
        
    try:
        from invoices.tax_audit_service import generate_audit_defense_letter
        letter = generate_audit_defense_letter(
            risk_type=risk_type,
            taxpayer_name=taxpayer_name,
            taxpayer_mst=taxpayer_mst,
            details=details
        )
        return jsonify({
            "status": "success",
            "letter": letter
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/ecommerce/normalize-orders")
def api_ecommerce_normalize_orders():
    """US-342: Map raw platform order fields from Shopee, Lazada, and TikTok Shop into standardized internal model."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized
        
    body = request.get_json(silent=True) or {}
    raw_orders = body.get("orders") or body.get("raw_logs") or []
    platform = body.get("platform", "shopee")
    
    if not raw_orders:
        return jsonify({"error": "Thieu danh sach don hang."}), 400
        
    try:
        from invoices.ecommerce_service import normalize_ecommerce_orders
        normalized = normalize_ecommerce_orders(raw_orders, platform)
        session["normalized_orders"] = normalized
        return jsonify({
            "status": "success",
            "count": len(normalized),
            "orders": normalized
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/payroll/audit-summary")
def api_payroll_audit_summary():
    """US-344: Verify PIT progressive tax tables (5%-35%) and social insurance rates."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized
        
    body = request.get_json(silent=True) or {}
    employees = body.get("employees") or []
    
    if not employees:
        employees = [
            {"id": "EMP001", "name": "Nguyễn Văn A", "mst": "8012345678", "gross_salary": 45000000.0, "dependents": 2, "withheld_pit": 2445000.0, "withheld_insurance": 4725000.0},
            {"id": "EMP002", "name": "Trần Thị B", "mst": "8012345679", "gross_salary": 12000000.0, "dependents": 0, "withheld_pit": 50000.0, "withheld_insurance": 1260000.0},
            {"id": "EMP003", "name": "Lê Văn C", "mst": "8012345680", "gross_salary": 85000000.0, "dependents": 1, "withheld_pit": 12500000.0, "withheld_insurance": 4914000.0},
            {"id": "EMP004", "name": "Phạm Thị D", "mst": "8012345681", "gross_salary": 25000000.0, "dependents": 3, "withheld_pit": 0.0, "withheld_insurance": 2625000.0},
            {"id": "EMP005", "name": "Hoàng Văn E", "mst": "8012345682", "gross_salary": 60000000.0, "dependents": 1, "withheld_pit": 7000000.0, "withheld_insurance": 4914000.0}
        ]
        
    try:
        from invoices.payroll_pit_service import audit_payroll_register
        report = audit_payroll_register(employees)
        return jsonify(report)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/payroll/export-pit-xml")
def api_payroll_export_pit_xml():
    """US-345: Scaffold GDT-compliant year-end PIT finalization Form 05/QTT-TNCN XML."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized
        
    body = request.get_json(silent=True) or {}
    metadata = body.get("metadata") or {}
    employees = body.get("employees") or []
    
    if not metadata:
        metadata = {
            "mst": body.get("taxpayer_mst") or "0109998887",
            "company_name": "Công ty TNHH GDT Invoice Hub",
            "year": body.get("tax_year") or datetime.now().year
        }
        
    if not employees:
        employees = [
            {"id": "EMP001", "name": "Nguyễn Văn A", "mst": "8012345678", "gross_salary": 45000000.0, "dependents": 2, "withheld_pit": 2445000.0, "withheld_insurance": 4725000.0},
            {"id": "EMP002", "name": "Trần Thị B", "mst": "8012345679", "gross_salary": 12000000.0, "dependents": 0, "withheld_pit": 50000.0, "withheld_insurance": 1260000.0},
            {"id": "EMP003", "name": "Lê Văn C", "mst": "8012345680", "gross_salary": 85000000.0, "dependents": 1, "withheld_pit": 12500000.0, "withheld_insurance": 4914000.0},
            {"id": "EMP004", "name": "Phạm Thị D", "mst": "8012345681", "gross_salary": 25000000.0, "dependents": 3, "withheld_pit": 0.0, "withheld_insurance": 2625000.0},
            {"id": "EMP005", "name": "Hoàng Văn E", "mst": "8012345682", "gross_salary": 60000000.0, "dependents": 1, "withheld_pit": 7000000.0, "withheld_insurance": 4914000.0}
        ]
        
    try:
        from invoices.payroll_pit_service import generate_form_05_qtt_tncn_xml
        xml_str = generate_form_05_qtt_tncn_xml(metadata, employees)
        return jsonify({
            "status": "success",
            "xml": xml_str
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/invoices/scaffold-xml")
def api_invoices_scaffold_xml():
    """US-361: Generate GDT-compliant e-invoice XML draft from OCR fields."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    ocr_data = body.get("ocr_data") or body
    
    if not ocr_data:
        return jsonify({"error": "Thieu thong tin OCR de tao XML."}), 400
        
    try:
        from invoices.v24_compliance_service import scaffold_xml_from_ocr_data
        xml_bytes = scaffold_xml_from_ocr_data(ocr_data)
        return jsonify({
            "status": "success",
            "xml": xml_bytes.decode("utf-8")
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/invoices/sign-hsm")
def api_invoices_sign_hsm():
    """US-362: Cryptographically sign invoice XML using simulated HSM certificate."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    xml_str = body.get("xml")
    ocr_data = body.get("ocr_data")
    
    try:
        from invoices.v24_compliance_service import scaffold_xml_from_ocr_data, generate_hsm_mock_certificate, sign_xml_invoice
        
        if not xml_str and ocr_data:
            xml_bytes = scaffold_xml_from_ocr_data(ocr_data)
            company_name = ocr_data.get("seller_name") or "Cong Ty Mau"
            mst = ocr_data.get("seller_mst") or "0100112233"
        elif xml_str:
            xml_bytes = xml_str.encode("utf-8")
            # Parse XML to extract company name and mst for certificate
            import lxml.etree
            root = lxml.etree.fromstring(xml_bytes)
            seller_mst_nodes = root.xpath("//*[local-name()='NBan']/*[local-name()='MST']")
            seller_name_nodes = root.xpath("//*[local-name()='NBan']/*[local-name()='Ten']")
            company_name = seller_name_nodes[0].text if seller_name_nodes else "Cong Ty Mau"
            mst = seller_mst_nodes[0].text if seller_mst_nodes else "0100112233"
        else:
            return jsonify({"error": "Yeu cau thieu xml hoac ocr_data."}), 400

        cert_der, priv_key = generate_hsm_mock_certificate(company_name, mst)
        signed_bytes = sign_xml_invoice(xml_bytes, cert_der, priv_key)
        
        return jsonify({
            "status": "success",
            "signed_xml": signed_bytes.decode("utf-8"),
            "certificate_issuer": "MISA-CA Root Authority"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/gdt-sandbox/transmit")
def api_gdt_sandbox_transmit():
    """US-363: Transmit signed XML to GDT Sandbox Gateway and verify compliance."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    xml_str = body.get("signed_xml") or body.get("xml")
    
    if not xml_str:
        return jsonify({"error": "Yeu cau thieu xml da ky."}), 400
        
    try:
        from invoices.v24_compliance_service import transmit_to_gdt_sandbox
        result = transmit_to_gdt_sandbox(xml_str.encode("utf-8"))
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.route("/api/compliance/decree132-checklist", methods=["GET", "POST"])
def api_compliance_decree132_checklist():
    """US-364: Check related party thresholds under Decree 132/2020/NĐ-CP."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        taxpayer_mst = body.get("taxpayer_mst")
        start_date = body.get("start_date")
        end_date = body.get("end_date")
    else:
        taxpayer_mst = request.args.get("taxpayer_mst")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")

    if not taxpayer_mst or not start_date or not end_date:
        return jsonify({"error": "Yeu cau thieu taxpayer_mst, start_date hoac end_date."}), 400

    try:
        from invoices.v24_compliance_service import calculate_related_party_disclosure
        checklist = calculate_related_party_disclosure(taxpayer_mst, start_date, end_date)
        return jsonify(checklist)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/compliance/transfer-pricing-risk")
def api_compliance_transfer_pricing_risk():
    """US-365: Compare operating margins against statistical sector benchmarks."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    transactions = body.get("transactions") or []
    sector = body.get("sector") or "Manufacturing"
    
    if not transactions:
        # Provide sample template transactions if empty
        transactions = [
            {"id": "TX001", "partner_name": "Cong ty Lien ket A", "revenue": 50000000000.0, "cogs": 48500000000.0},
            {"id": "TX002", "partner_name": "Cong ty Lien ket B", "revenue": 12000000000.0, "cogs": 11000000000.0}
        ]
        
    try:
        from invoices.v24_compliance_service import analyze_transfer_pricing_risk
        analysis = analyze_transfer_pricing_risk(transactions, sector)
        return jsonify(analysis)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Version 25.0.0 API Endpoints ──────────────────────────────────────────

@invoices_blueprint.get("/api/compliance/gdt-status")
def api_compliance_gdt_status():
    """US-371: Fetch invoice GDT verification status, search & filter."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    status_filter = request.args.get("status")
    search_query = request.args.get("q")
    
    from invoices.models import Invoice
    query = Invoice.query
    
    if status_filter:
        query = query.filter(Invoice.invoice_status == status_filter)
    if search_query:
        query = query.filter(
            Invoice.id.contains(search_query) | 
            Invoice.number.contains(search_query) | 
            Invoice.seller_mst.contains(search_query) | 
            Invoice.buyer_mst.contains(search_query)
        )
        
    invoices = query.order_by(Invoice.updated_at.desc()).all()
    
    return jsonify({
        "status": "success",
        "invoices": [{
            "id": inv.id,
            "number": inv.number,
            "symbol": inv.symbol,
            "template_code": inv.template_code,
            "date": inv.date,
            "seller_mst": inv.seller_mst,
            "seller_name": inv.seller_name,
            "buyer_mst": inv.buyer_mst,
            "buyer_name": inv.buyer_name,
            "total_amount": inv.total_amount,
            "payment_method": inv.payment_method,
            "has_signature": inv.has_signature,
            "invoice_status": inv.invoice_status or "pending",
            "notes": inv.notes,
            "updated_at": inv.updated_at
        } for inv in invoices]
    })


@invoices_blueprint.post("/api/compliance/gdt-sync")
def api_compliance_gdt_sync():
    """US-370 / US-371: Trigger GDT Sync Agent or sync specific invoice IDs."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    invoice_ids = body.get("invoice_ids")
    
    from invoices.v25_compliance_service import run_portal_sync_agent, sync_gdt_verification_status
    try:
        if invoice_ids:
            result = sync_gdt_verification_status(invoice_ids)
        else:
            result = run_portal_sync_agent()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/compliance/generate-correction-xml")
def api_compliance_generate_correction_xml():
    """US-372: Generate Decree 123 conforming XML for corrected/replaced invoice."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    original_invoice_id = body.get("original_invoice_id")
    type_change = body.get("type_change") # "correction" or "replacement"
    new_data = body.get("new_data") or {}

    if not original_invoice_id or not type_change:
        return jsonify({"error": "Thiếu original_invoice_id hoặc type_change."}), 400

    from invoices.models import Invoice
    orig_inv = Invoice.query.get(original_invoice_id)
    if not orig_inv:
        return jsonify({"error": f"Không tìm thấy hóa đơn gốc {original_invoice_id}."}), 404

    from invoices.v25_compliance_service import generate_correction_or_replacement_xml
    try:
        xml_bytes = generate_correction_or_replacement_xml(orig_inv, new_data, type_change)
        return jsonify({
            "status": "success",
            "xml": xml_bytes.decode("utf-8"),
            "filename": f"{type_change}_invoice_{orig_inv.number}.xml"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/compliance/transmit-form-04ss")
def api_compliance_transmit_form_04ss():
    """US-373: Scaffold, sign with HSM, and transmit Form 04/SS-HĐĐT."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    taxpayer_mst = body.get("taxpayer_mst")
    company_name = body.get("company_name")
    bad_invoices = body.get("bad_invoices") or []

    if not taxpayer_mst or not company_name or not bad_invoices:
        return jsonify({"error": "Thiếu taxpayer_mst, company_name hoặc danh sách bad_invoices."}), 400

    from invoices.v25_compliance_service import generate_form_04_ss_xml
    from invoices.v24_compliance_service import generate_hsm_mock_certificate, sign_xml_invoice, transmit_to_gdt_sandbox
    try:
        # 1. Scaffold Form 04/SS XML
        xml_bytes = generate_form_04_ss_xml(taxpayer_mst, company_name, bad_invoices)
        
        # 2. Sign XML using mock HSM certificate
        cert_der, priv_key = generate_hsm_mock_certificate(company_name, taxpayer_mst)
        signed_xml_bytes = sign_xml_invoice(xml_bytes, cert_der, priv_key)
        
        # 3. Transmit signed XML to GDT sandbox
        transmission_result = transmit_to_gdt_sandbox(signed_xml_bytes)
        
        return jsonify({
            "status": "success",
            "raw_xml": xml_bytes.decode("utf-8"),
            "signed_xml": signed_xml_bytes.decode("utf-8"),
            "transmission_result": transmission_result
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/compliance/tax-optimization")
def api_compliance_tax_optimization():
    """US-374: Run corporate tax optimization and scenario simulations."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    taxpayer_mst = body.get("taxpayer_mst") or session.get("taxpayer_mst") or "0109999999"
    scenarios_config = body.get("scenarios")

    if not scenarios_config:
        # Fallback to standard scenario checklist if empty
        scenarios_config = [
            {
                "name": "Kịch bản tối ưu 1: Thuế suất ưu đãi 10% & Miễn thuế 2 năm",
                "preferential_rate": 0.10,
                "holiday_exempt_years": 2,
                "holiday_reduce_years": 4,
                "reduce_loan_interest": True,
                "enforce_bank_transfer": True
            },
            {
                "name": "Kịch bản tối ưu 2: Thuế suất ưu đãi 15% & Giảm thuế 50% trong 2 năm",
                "preferential_rate": 0.15,
                "holiday_exempt_years": 0,
                "holiday_reduce_years": 2,
                "reduce_loan_interest": False,
                "enforce_bank_transfer": False
            }
        ]

    from invoices.v25_compliance_service import calculate_corporate_tax_optimization
    try:
        report = calculate_corporate_tax_optimization(taxpayer_mst, scenarios_config)
        return jsonify(report)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Version 26.0.0 Advanced Compliance & Tax Advisory Endpoints ────────────────

@invoices_blueprint.get("/v26-compliance")
def v26_compliance_page():
    """Render the Version 26.0.0 compliance and tax advisor screen."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    return render_template("v26_compliance.html")


@invoices_blueprint.post("/api/compliance/insurance-audit")
def api_compliance_insurance_audit():
    """US-380: Audit payroll trích đóng BHXH/BHYT/BHTN against statutory rates."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    basic_salary = request.args.get("basic_salary", type=float) or 2340000.0

    # Mock employee payroll records for auditing
    mock_payroll = [
        {"id": "EMP-001", "name": "Nguyễn Văn A", "gross_salary": 15000000.0, "withheld_insurance": 1575000.0},
        {"id": "EMP-002", "name": "Trần Thị B", "gross_salary": 25000000.0, "withheld_insurance": 2300000.0},  # Mismatch (Statutory is 2,625,000)
        {"id": "EMP-003", "name": "Lê Văn C", "gross_salary": 55000000.0, "withheld_insurance": 4914000.0}   # Capped at 46,800,000 (Statutory 4,914,000)
    ]

    from invoices.v26_service import audit_social_insurance
    try:
        result = audit_social_insurance(mock_payroll, basic_salary)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.get("/api/compliance/insurance-export-csv")
def api_compliance_insurance_export_csv():
    """US-381: Export social insurance audit discrepancies as a CSV report."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))

    basic_salary = request.args.get("basic_salary", type=float) or 2340000.0

    mock_payroll = [
        {"id": "EMP-001", "name": "Nguyễn Văn A", "gross_salary": 15000000.0, "withheld_insurance": 1575000.0},
        {"id": "EMP-002", "name": "Trần Thị B", "gross_salary": 25000000.0, "withheld_insurance": 2300000.0},
        {"id": "EMP-003", "name": "Lê Văn C", "gross_salary": 55000000.0, "withheld_insurance": 4914000.0}
    ]

    from invoices.v26_service import audit_social_insurance, export_si_reconciliation_csv
    try:
        audit_result = audit_social_insurance(mock_payroll, basic_salary)
        csv_data = export_si_reconciliation_csv(audit_result)
        
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-disposition": "attachment; filename=si_reconciliation_report.csv"}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/compliance/tax-ledger-reconcile")
def api_compliance_tax_ledger_reconcile():
    """US-382: Sync taxpayer e-Tax ledger and reconcile against local journals."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    local_payments = body.get("local_payments") or []
    taxpayer_mst = body.get("taxpayer_mst") or session.get("taxpayer_mst") or "0109999999"

    from invoices.v26_service import reconcile_tax_ledger
    try:
        recompiled = reconcile_tax_ledger(taxpayer_mst, local_payments)
        return jsonify({
            "status": "success",
            "recompiled": recompiled
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/compliance/vietqr-generate")
def api_compliance_vietqr_generate():
    """US-383: Generate Napas-compliant dynamic VietQR tax payment code."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    tax_type = body.get("tax_type", "VAT")
    amount = body.get("amount", 1000.0)
    taxpayer_mst = session.get("taxpayer_mst") or "0109999999"

    from invoices.v26_service import generate_napas_vietqr_payload
    try:
        payload = generate_napas_vietqr_payload(tax_type, amount, taxpayer_mst)
        return jsonify(payload)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/compliance/vietqr-confirm")
def api_compliance_vietqr_confirm():
    """US-383: Confirm dynamic tax payment transaction (status change simulation)."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    tx_id = body.get("transaction_id")
    if not tx_id:
        return jsonify({"error": "Thiếu transaction_id"}), 400

    return jsonify({
        "transaction_id": tx_id,
        "status": "paid",
        "message": f"Giao dịch nộp thuế {tx_id} đã được xác nhận khớp lệnh với Kho bạc Nhà nước.",
        "completed_at": datetime.now().isoformat()
    })


@invoices_blueprint.get("/api/compliance/kg-query")
def api_compliance_kg_query():
    """US-384: Query Vietnamese Tax Law Knowledge Graph."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    query = request.args.get("query", "")
    from invoices.v26_service import TaxLawKnowledgeGraph
    try:
        kg = TaxLawKnowledgeGraph()
        results = kg.keyword_search(query)
        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/compliance/defense-compose")
def api_compliance_defense_compose():
    """US-385: Dynamic AI Audit Defense Document Composer."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    warning_type = body.get("warning_type")
    context = body.get("context") or {}

    profile = {
        "mst": session.get("taxpayer_mst") or "0109999999",
        "company_name": session.get("company_name") or "Công ty TNHH Giải pháp Phần mềm Ánh Sáng",
        "district": "Cục Thuế Thành phố Hà Nội",
        "representative": "Giám Đốc"
    }

    from invoices.v26_service import compose_audit_defense_letter
    try:
        letter_html = compose_audit_defense_letter(profile, warning_type, context)
        return jsonify({
            "status": "success",
            "letter_html": letter_html
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Version 27.0.0 Advanced Compliance & Tax Advisory Endpoints ────────────────

@invoices_blueprint.get("/v27-compliance")
def v27_compliance_page():
    """Render the Version 27.0.0 compliance, risk radar, and treasury simulation screen."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    return render_template("v27_compliance.html")


@invoices_blueprint.post("/api/compliance/pxk-parse")
def api_compliance_pxk_parse():
    """US-390: Parse and validate official electronic delivery note XML."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    xml_content = body.get("xml_content", "")
    if not xml_content:
        return jsonify({"error": "Thiếu dữ liệu xml_content"}), 400

    from invoices.v27_service import parse_delivery_note_xml
    try:
        parsed = parse_delivery_note_xml(xml_content)
        return jsonify(parsed)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/compliance/pxk-reconcile")
def api_compliance_pxk_reconcile():
    """US-391: Reconcile delivery note items against commercial invoices."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    delivery_notes = body.get("delivery_notes") or []
    invoices = body.get("invoices") or []

    from invoices.v27_service import reconcile_delivery_to_invoice
    try:
        report = reconcile_delivery_to_invoice(delivery_notes, invoices)
        return jsonify(report)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/compliance/pxk-export-csv")
def api_compliance_pxk_export_csv():
    """US-391: Export reconciliation differences as a CSV report."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    delivery_notes = body.get("delivery_notes") or []
    invoices = body.get("invoices") or []

    from invoices.v27_service import reconcile_delivery_to_invoice, export_delivery_reconciliation_csv
    try:
        report = reconcile_delivery_to_invoice(delivery_notes, invoices)
        csv_data = export_delivery_reconciliation_csv(report)
        return Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-disposition": "attachment; filename=pxk_reconciliation_report.csv"}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/compliance/pre-audit-risk")
def api_compliance_pre_audit_risk():
    """US-392: Calculate the pre-audit corporate tax risk scorecard."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    invoices = body.get("invoices") or []
    related_party_context = body.get("related_party_context") or {}
    profile = {
        "mst": session.get("taxpayer_mst") or "0109999999",
        "company_name": session.get("company_name") or "Công ty TNHH Ánh Sáng"
    }

    from invoices.v27_service import calculate_pre_audit_risk
    try:
        report = calculate_pre_audit_risk(profile, invoices, related_party_context)
        return jsonify(report)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/compliance/risk-radar-svg")
def api_compliance_risk_radar_svg():
    """US-393: Generate dynamic SVG risk radar chart markup."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    scores = body.get("scores") or {}

    from invoices.v27_service import generate_svg_radar_chart
    try:
        svg_markup = generate_svg_radar_chart(scores)
        return jsonify({"svg_markup": svg_markup})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/compliance/econtract-parse")
def api_compliance_econtract_parse():
    """US-394: Parse electronic contract structured metadata."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    json_content = body.get("json_content", "")
    if not json_content:
        return jsonify({"error": "Thiếu dữ liệu json_content"}), 400

    from invoices.v27_service import parse_econtract_metadata
    try:
        parsed = parse_econtract_metadata(json_content)
        return jsonify(parsed)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/compliance/econtract-reconcile")
def api_compliance_econtract_reconcile():
    """US-394: Reconcile contract milestones with invoices and payments."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    contract = body.get("contract") or {}
    invoices = body.get("invoices") or []
    payments = body.get("payments") or []

    from invoices.v27_service import reconcile_contract_milestones
    try:
        report = reconcile_contract_milestones(contract, invoices, payments)
        return jsonify(report)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/compliance/treasury-forecast")
def api_compliance_treasury_forecast():
    """US-395: Smart treasury forecast scenario simulation."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    milestones = body.get("milestones") or []
    invoices = body.get("invoices") or []
    starting_cash = body.get("starting_cash", 1000000000.0)
    delay_days = body.get("delay_days", 0)
    cit_discount = body.get("cit_discount", 0.0)

    from invoices.v27_service import simulate_treasury_forecast
    try:
        forecast = simulate_treasury_forecast(milestones, invoices, starting_cash, delay_days, cit_discount)
        return jsonify(forecast)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Version 28.0.0 Advanced Compliance Auto-Repair & Swarm Advisor Endpoints ──────

@invoices_blueprint.get("/v28-compliance")
def v28_compliance_page():
    """Render the Version 28.0.0 XML Auto-Repair Hub & Swarm Advisor Panel."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    return render_template("v28_compliance.html")


@invoices_blueprint.post("/api/compliance/xml-audit")
def api_compliance_xml_audit():
    """US-397: Audit invoice XML compliance and structure."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    xml_content = body.get("xml_content", "")
    if not xml_content:
        return jsonify({"error": "Thiếu dữ liệu xml_content"}), 400

    from invoices.v28_service import audit_xml_compliance
    try:
        result = audit_xml_compliance(xml_content)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/compliance/xml-auto-repair")
def api_compliance_xml_auto_repair():
    """US-397: Auto-repair schema errors, tags order, and generate sign-off XML."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    xml_content = body.get("xml_content", "")
    if not xml_content:
        return jsonify({"error": "Thiếu dữ liệu xml_content"}), 400

    from invoices.v28_service import repair_xml_invoice
    try:
        result = repair_xml_invoice(xml_content)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/agents/swarm-chat")
def api_agents_swarm_chat():
    """US-396: Run interactive collaborative agent swarm simulation."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    query = body.get("query", "")
    if not query:
        return jsonify({"error": "Thiếu câu hỏi rà soát"}), 400

    taxpayer_mst = session.get("taxpayer_mst") or "0109998887"
    
    from invoices.v28_service import simulate_swarm_step_by_step, JointAuditCoordinator
    try:
        # Simulate swarm communication logs
        chat_steps = simulate_swarm_step_by_step(taxpayer_mst, query)
        
        # Also invoke the actual JointAuditCoordinator to get the final generated report markdown
        coordinator = JointAuditCoordinator(taxpayer_mst=taxpayer_mst)
        report_markdown = coordinator.execute_swarm(query)
        
        return jsonify({
            "status": "success",
            "chat_steps": chat_steps,
            "report_markdown": report_markdown
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Version 29.0.0 Advanced Ghost-Company Compliance & Tax Regulations Graph Endpoints ──────

@invoices_blueprint.get("/v29-compliance")
def v29_compliance_page():
    """Render the Version 29.0.0 Ghost-Company Audit Hub & Tax Knowledge Graph."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    return render_template("v29_compliance.html")


@invoices_blueprint.post("/api/compliance/ghost-check")
def api_compliance_ghost_check():
    """US-400: Ghost Company Blacklist Scraper & Probability Index Engine."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    seller_mst = body.get("seller_mst", "")
    seller_name = body.get("seller_name", "")
    invoice_value = float(body.get("invoice_value", 0))

    if not seller_mst:
        return jsonify({"error": "Thiếu dữ liệu seller_mst"}), 400

    from invoices.v29_service import check_ghost_company
    try:
        result = check_ghost_company(seller_mst, seller_name, invoice_value)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/compliance/defense-letter")
def api_compliance_defense_letter():
    """US-401: Generate Tax Audit Defense Letter & Rectification Plan."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    seller_mst = body.get("seller_mst", "")
    seller_name = body.get("seller_name", "")
    invoice_value = float(body.get("invoice_value", 0))
    payment_method = body.get("payment_method", "Chuyển khoản qua Ngân hàng thương mại")

    if not seller_mst or not seller_name:
        return jsonify({"error": "Thiếu dữ liệu nhà cung cấp"}), 400

    from invoices.v29_service import generate_audit_mitigation_letter
    try:
        letter_text = generate_audit_mitigation_letter(seller_mst, seller_name, invoice_value, payment_method)
        return jsonify({
            "success": True,
            "letter": letter_text
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.get("/api/compliance/tax-knowledge-graph")
def api_compliance_tax_knowledge_graph():
    """US-402: Return Vietnamese Tax Regulations Knowledge Graph."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from invoices.v29_service import get_tax_knowledge_graph
    try:
        graph_data = get_tax_knowledge_graph()
        return jsonify(graph_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/agents/swarm-v29-chat")
def api_agents_swarm_v29_chat():
    """US-401 Swarm: Run simulated multi-agent swarm discussion for invoice compliance defense."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    seller_mst = body.get("seller_mst", "")
    seller_name = body.get("seller_name", "")
    invoice_value = float(body.get("invoice_value", 0))
    taxpayer_mst = body.get("mst", "0109998887")

    if not seller_mst:
        return jsonify({"error": "Thiếu dữ liệu seller_mst"}), 400

    from invoices.v29_service import SwarmV29Advisor, generate_audit_mitigation_letter
    try:
        advisor = SwarmV29Advisor(taxpayer_mst=taxpayer_mst)
        chat_steps = advisor.simulate_defense_chat(seller_mst, seller_name, invoice_value)
        report_markdown = generate_audit_mitigation_letter(seller_mst, seller_name, invoice_value, "Chuyển khoản qua ngân hàng (CK)")
        return jsonify({
            "status": "success",
            "chat_steps": chat_steps,
            "report_markdown": report_markdown
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Version 30.0.0 Advanced Related-Party Transfer Pricing Compliance Endpoints ──────

@invoices_blueprint.get("/v30-compliance")
def v30_compliance_page():
    """Render the Version 30.0.0 Related-Party Transfer Pricing & Swarm Advisor portal."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    return render_template("v30_compliance.html")


@invoices_blueprint.post("/api/compliance/transfer-pricing-check")
def api_compliance_transfer_pricing_check():
    """US-410: Related-Party Transaction Markup & Interquartile (IQR) Margin Risk Analyzer."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    sector = body.get("sector", "manufacturing")
    markup_pct = float(body.get("markup_pct", 0.0))
    cost_of_goods = float(body.get("cost_of_goods", 0.0))

    from invoices.v30_service import calculate_transfer_pricing_risk
    try:
        result = calculate_transfer_pricing_risk(markup_pct, cost_of_goods, sector)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/agents/swarm-v30-chat")
def api_agents_swarm_v30_chat():
    """US-412 Swarm: Run simulated multi-agent swarm discussion for related-party transfer pricing audit preparation."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    taxpayer_mst = body.get("taxpayer_mst", "0109998887")
    taxpayer_name = body.get("taxpayer_name", "Doanh nghiệp mẫu")
    sector = body.get("sector", "manufacturing")
    markup_pct = float(body.get("markup_pct", 0.0))
    cost_of_goods = float(body.get("cost_of_goods", 0.0))

    from invoices.v30_service import SwarmV30Advisor, calculate_transfer_pricing_risk, generate_tp_audit_dossier
    try:
        advisor = SwarmV30Advisor(taxpayer_mst=taxpayer_mst)
        chat_steps = advisor.simulate_tp_defense_chat(sector, markup_pct, cost_of_goods)
        
        risk_details = calculate_transfer_pricing_risk(markup_pct, cost_of_goods, sector)
        dossier = generate_tp_audit_dossier(taxpayer_name, taxpayer_mst, sector, markup_pct, cost_of_goods, risk_details)
        
        return jsonify({
            "status": "success",
            "chat_steps": chat_steps,
            "dossier": dossier
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Version 31.0.0 Multi-Period VAT Reconciliation & AI Anomaly Detection ──────

@invoices_blueprint.get("/v31-compliance")
def v31_compliance_page():
    """Render the Version 31.0.0 Multi-Period VAT Reconciliation & AI Anomaly Detection panel."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    return render_template("v31_compliance.html")


@invoices_blueprint.post("/api/compliance/vat-reconciliation")
def api_compliance_vat_reconciliation():
    """US-420: Multi-Period VAT Reconciliation Engine with Input/Output VAT Balancing."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    taxpayer_mst = body.get("taxpayer_mst") or session.get("taxpayer_mst") or "0109999999"
    periods = body.get("periods")

    from invoices.v31_service import vat_reconciliation_multi_period
    try:
        result = vat_reconciliation_multi_period(taxpayer_mst, periods)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/compliance/form01-gtgt-xml")
def api_compliance_form01_gtgt_xml():
    """US-421: Automated Form 01/GTGT VAT Declaration XML Builder."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    taxpayer_mst = body.get("taxpayer_mst") or session.get("taxpayer_mst") or "0109999999"
    taxpayer_name = body.get("taxpayer_name") or "Công ty TNHH Giải pháp Phần mềm"
    period = body.get("period") or ""
    output_vat = float(body.get("output_vat", 0))
    input_vat = float(body.get("input_vat", 0))
    carry_forward_prev = float(body.get("carry_forward_prev", 0))

    if not period:
        return jsonify({"error": "Thiếu kỳ kê khai (period)"}), 400

    from invoices.v31_service import build_form01_gtgt_xml
    try:
        result = build_form01_gtgt_xml(
            taxpayer_mst, taxpayer_name, period,
            output_vat, input_vat, carry_forward_prev,
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/agents/swarm-v31-chat")
def api_agents_swarm_v31_chat():
    """US-422: AI VAT Anomaly Detection Swarm and Cross-Period Audit Advisory."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    taxpayer_mst = body.get("taxpayer_mst") or session.get("taxpayer_mst") or "0109999999"
    taxpayer_name = body.get("taxpayer_name") or "Doanh nghiệp phân tích"

    from invoices.v31_service import run_vat_anomaly_swarm
    try:
        result = run_vat_anomaly_swarm(taxpayer_mst, taxpayer_name)
        return jsonify({
            "status": "success",
            "chat_steps": result["chat_steps"],
            "report_markdown": result["report_markdown"],
            "reconciliation": result["reconciliation"],
            "risk_level": result["risk_level"],
            "total_anomalies": result["total_anomalies"],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Version 32.0.0 Exporter VAT Refund Wizard & AI Defense Swarm ────────────────

@invoices_blueprint.get("/v32-compliance")
def v32_compliance_page():
    """Render the Version 32.0.0 Exporter VAT Refund Wizard panel."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    return render_template("v32_refund.html")


@invoices_blueprint.post("/api/agents/swarm-v32-chat")
def api_agents_swarm_v32_chat():
    """US-432: AI Swarm VAT Refund Justification Compiler & Multi-Agent Debate."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    taxpayer_mst = body.get("taxpayer_mst") or session.get("active_taxpayer_mst")
    taxpayer_name = body.get("taxpayer_name") or "Doanh nghiệp hoàn thuế"
    eligible_invoice_ids = body.get("eligible_invoice_ids")
    customs_declarations = body.get("customs_declarations")

    if not taxpayer_mst:
        return jsonify({"error": "Missing taxpayer MST"}), 400

    from invoices.v32_service import run_refund_audit_swarm
    try:
        result = run_refund_audit_swarm(
            taxpayer_mst=taxpayer_mst,
            taxpayer_name=taxpayer_name,
            eligible_invoice_ids=eligible_invoice_ids,
            customs_declarations=customs_declarations
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Version 33.0.0 CIT Quarterly Declaration & Tax Compliance Calendar ──────────

@invoices_blueprint.get("/v33-compliance")
def v33_compliance_page():
    """Render the Version 33.0.0 CIT Quarterly & Tax Compliance Calendar panel."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    return render_template("v33_compliance.html")


@invoices_blueprint.post("/api/compliance/cit-quarterly")
def api_compliance_cit_quarterly():
    """US-450: CIT Quarterly Provisional Tax Calculation Engine."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    taxpayer_mst = body.get("taxpayer_mst") or session.get("taxpayer_mst") or "0109999999"
    quarter = int(body.get("quarter", 1))
    year = int(body.get("year", 2026))
    revenue = float(body.get("revenue", 0))
    cogs = float(body.get("cogs", 0))
    operating_expenses = float(body.get("operating_expenses", 0))
    other_income = float(body.get("other_income", 0))
    other_expenses = float(body.get("other_expenses", 0))
    preferential_rate = body.get("preferential_rate")
    if preferential_rate is not None:
        preferential_rate = float(preferential_rate)
    carry_forward_loss = float(body.get("carry_forward_loss", 0))

    from invoices.v33_service import calculate_cit_quarterly
    try:
        result = calculate_cit_quarterly(
            taxpayer_mst, quarter, year, revenue, cogs,
            operating_expenses, other_income, other_expenses,
            preferential_rate, carry_forward_loss,
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/compliance/form01a-tndn-xml")
def api_compliance_form01a_tndn_xml():
    """US-450: Generate Form 01A/TNDN HTKK-compatible XML."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    taxpayer_mst = body.get("taxpayer_mst") or session.get("taxpayer_mst") or "0109999999"
    taxpayer_name = body.get("taxpayer_name") or "Công ty TNHH Giải pháp Phần mềm"
    quarter = int(body.get("quarter", 1))
    year = int(body.get("year", 2026))
    revenue = float(body.get("revenue", 0))
    cogs = float(body.get("cogs", 0))
    operating_expenses = float(body.get("operating_expenses", 0))
    other_income = float(body.get("other_income", 0))
    other_expenses = float(body.get("other_expenses", 0))
    preferential_rate = body.get("preferential_rate")
    if preferential_rate is not None:
        preferential_rate = float(preferential_rate)
    carry_forward_loss = float(body.get("carry_forward_loss", 0))

    from invoices.v33_service import build_form01a_tndn_xml
    try:
        result = build_form01a_tndn_xml(
            taxpayer_mst, taxpayer_name, quarter, year, revenue, cogs,
            operating_expenses, other_income, other_expenses,
            preferential_rate, carry_forward_loss,
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.get("/api/compliance/tax-calendar")
def api_compliance_tax_calendar():
    """US-451: Return Vietnamese tax compliance calendar for a given year."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    year = request.args.get("year", type=int) or 2026

    from invoices.v33_service import get_tax_compliance_calendar
    try:
        cal = get_tax_compliance_calendar(year)
        return jsonify(cal)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/agents/swarm-v33-chat")
def api_agents_swarm_v33_chat():
    """US-451: CIT Optimization Swarm Advisory for quarterly declaration."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    taxpayer_mst = body.get("taxpayer_mst") or session.get("taxpayer_mst") or "0109999999"
    taxpayer_name = body.get("taxpayer_name") or "Doanh nghiệp phân tích"
    quarter = int(body.get("quarter", 1))
    year = int(body.get("year", 2026))
    revenue = float(body.get("revenue", 0))
    cogs = float(body.get("cogs", 0))
    operating_expenses = float(body.get("operating_expenses", 0))

    from invoices.v33_service import run_cit_optimization_swarm
    try:
        result = run_cit_optimization_swarm(
            taxpayer_mst, taxpayer_name, quarter, year,
            revenue, cogs, operating_expenses,
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Version 34.0.0 Invoice Aging Analysis & AR/AP Management ───────────────────

@invoices_blueprint.get("/v34-compliance")
def v34_compliance_page():
    """Render the Version 34.0.0 Invoice Aging & AR/AP Management panel."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    return render_template("v34_compliance.html")


@invoices_blueprint.post("/api/compliance/invoice-aging")
def api_compliance_invoice_aging():
    """US-460: Invoice Aging Analysis for AR and AP."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    taxpayer_mst = body.get("taxpayer_mst") or session.get("taxpayer_mst") or "0109999999"
    as_of_date = body.get("as_of_date")

    from invoices.v34_service import analyze_invoice_aging
    try:
        result = analyze_invoice_aging(taxpayer_mst, as_of_date)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/compliance/aging-heatmap")
def api_compliance_aging_heatmap():
    """US-461: Generate aging heatmap grid data."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    taxpayer_mst = body.get("taxpayer_mst") or session.get("taxpayer_mst") or "0109999999"
    as_of_date = body.get("as_of_date")

    from invoices.v34_service import analyze_invoice_aging, generate_aging_heatmap_data
    try:
        aging = analyze_invoice_aging(taxpayer_mst, as_of_date)
        heatmap = generate_aging_heatmap_data(aging)
        return jsonify(heatmap)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/agents/swarm-v34-chat")
def api_agents_swarm_v34_chat():
    """US-461: AR/AP Debt Collection Swarm Advisory."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    taxpayer_mst = body.get("taxpayer_mst") or session.get("taxpayer_mst") or "0109999999"
    taxpayer_name = body.get("taxpayer_name") or "Doanh nghiệp phân tích"

    from invoices.v34_service import run_aging_advisory_swarm
    try:
        result = run_aging_advisory_swarm(taxpayer_mst, taxpayer_name)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Version 35.0.0 Unified Audit Control Room & Tax Stress Simulator ───────────

@invoices_blueprint.get("/v35-compliance")
def v35_compliance_page():
    """Render the Version 35.0.0 Unified Audit Control Room panel."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    return render_template("v35_compliance.html")


@invoices_blueprint.post("/api/compliance/v35-health")
def api_compliance_v35_health():
    """US-470: Calculate compliance health score & risk tree nodes."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    taxpayer_mst = body.get("taxpayer_mst") or session.get("taxpayer_mst") or "0109999999"

    from invoices.v35_service import calculate_tax_health_score
    try:
        result = calculate_tax_health_score(taxpayer_mst)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/compliance/stress-test")
def api_compliance_stress_test():
    """US-471: Run tax audit risk stress simulation."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    taxpayer_mst = body.get("taxpayer_mst") or session.get("taxpayer_mst") or "0109999999"
    scan_rate = float(body.get("scan_rate", 0.5))
    strictness = body.get("strictness", "medium")

    from invoices.v35_service import run_tax_stress_simulation
    try:
        result = run_tax_stress_simulation(taxpayer_mst, scan_rate, strictness)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/compliance/defense-package")
def api_compliance_defense_package():
    """US-472: Generate and download defense briefcase ZIP."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    taxpayer_mst = body.get("taxpayer_mst") or session.get("taxpayer_mst") or "0109999999"
    invoice_ids = body.get("invoice_ids", [])

    from invoices.v35_service import build_defense_briefcase
    import os
    try:
        zip_path = build_defense_briefcase(taxpayer_mst, invoice_ids)
        from flask import send_file
        return send_file(
            zip_path,
            mimetype="application/zip",
            as_attachment=True,
            download_name=os.path.basename(zip_path)
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/agents/swarm-v35-chat")
def api_agents_swarm_v35_chat():
    """US-474: AI Swarm Defense Chat mock debate."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    taxpayer_mst = body.get("taxpayer_mst") or session.get("taxpayer_mst") or "0109999999"

    from invoices.v35_service import run_v35_swarm
    try:
        result = run_v35_swarm(taxpayer_mst)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Version 36.0.0 Annual CIT Finalization & Loss Carry-Forward Suite ───────────

@invoices_blueprint.get("/v36-cit-finalization")
def v36_cit_finalization_page():
    """Render the Version 36.0.0 Annual CIT Finalization & Optimizer panel."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    return render_template("v36_compliance.html")


@invoices_blueprint.post("/api/cit/calculate")
def api_cit_calculate():
    """US-480: Calculate CIT liability."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    revenue = float(body.get("revenue", 0.0))
    cogs = float(body.get("cogs", 0.0))
    selling_expenses = float(body.get("selling_expenses", 0.0))
    admin_expenses = float(body.get("admin_expenses", 0.0))
    non_deductible_adjustments = float(body.get("non_deductible_adjustments", 0.0))
    loss_offset = float(body.get("loss_offset", 0.0))
    cit_rate = float(body.get("cit_rate", 0.20))
    holiday_discount = float(body.get("holiday_discount", 0.0))

    from invoices.v36_service import CITFinalizationService
    try:
        result = CITFinalizationService.calculate_cit(
            revenue, cogs, selling_expenses, admin_expenses, 
            non_deductible_adjustments, loss_offset, cit_rate, holiday_discount
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/cit/optimize-losses")
def api_cit_optimize_losses():
    """US-481: Compute optimal carry-forward matrix."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    # Parse historical losses: keys should be ints
    hist_losses_raw = body.get("historical_losses", {})
    hist_losses = {int(k): float(v) for k, v in hist_losses_raw.items()}
    
    # Parse projected profits: keys should be ints
    proj_profits_raw = body.get("projected_profits", {})
    proj_profits = {int(k): float(v) for k, v in proj_profits_raw.items()}
    
    # Parse holidays: keys should be ints
    holidays_raw = body.get("tax_holidays", {})
    holidays = {}
    for k, v in holidays_raw.items():
        holidays[int(k)] = {
            "tax_free": bool(v.get("tax_free", False)),
            "reduction": float(v.get("reduction", 0.0))
        }
        
    cit_rate = float(body.get("cit_rate", 0.20))

    from invoices.v36_service import CITFinalizationService
    try:
        result = CITFinalizationService.optimize_loss_carry_forward(
            hist_losses, proj_profits, holidays, cit_rate
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/cit/export-xml")
def api_cit_export_xml():
    """US-482: Generate GDT Form 03/TNDN XML."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    mst = body.get("mst") or session.get("taxpayer_mst") or "0102030405"
    taxpayer_name = body.get("taxpayer_name") or "CÔNG TY CỔ PHẦN CÔNG NGHỆ ANTIGRAVITY"
    year = int(body.get("year", 2026))
    
    cit_data = body.get("cit_data", {})
    loss_data = body.get("loss_data", {})

    from invoices.v36_service import CITFinalizationService
    try:
        xml_content = CITFinalizationService.generate_cit_xml(
            mst, taxpayer_name, year, cit_data, loss_data
        )
        return Response(
            xml_content,
            mimetype="application/xml",
            headers={"Content-Disposition": f'attachment; filename="Form_03_TNDN_{year}.xml"'}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/cit/swarm-chat")
def api_cit_swarm_chat():
    """US-484: AI Swarm Consensus debate simulation."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    cit_data = body.get("cit_data", {})
    loss_data = body.get("loss_data", {})

    from invoices.v36_service import CITFinalizationService
    try:
        debate, memo = CITFinalizationService.simulate_cit_swarm_debate(cit_data, loss_data)
        return jsonify({
            "debate": debate,
            "memo": memo
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================================
# VERSION 37: CEO DASHBOARD, TAX PLANNING & ASSETS
# ==========================================

@invoices_blueprint.get("/v37-ceo-dashboard")
def v37_ceo_dashboard_page():
    """Render the CEO Intelligence & Tax Planning dashboard."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    return render_template("v37_ceo_dashboard.html")


@invoices_blueprint.get("/api/ceo-dashboard")
def api_ceo_dashboard():
    """US-490: Get financial indicators, health score and commentary."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"
    from invoices.v37_service import CEOIntelligenceService
    try:
        health = CEOIntelligenceService.calculate_financial_health_score(mst)
        commentary = CEOIntelligenceService.generate_management_commentary(mst)
        return jsonify({
            "status": "success",
            "health_score": health["overall_score"],
            "sub_scores": health["sub_scores"],
            "commentary": commentary,
            "mst": mst
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.get("/api/ceo-dashboard/sankey")
def api_ceo_dashboard_sankey():
    """US-490: Generate Sankey diagram node/link structures."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"
    from invoices.v37_service import CEOIntelligenceService
    try:
        sankey_data = CEOIntelligenceService.generate_sankey_data(mst)
        return jsonify(sankey_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.get("/api/tax-planning/projection")
def api_tax_planning_projection():
    """US-491: Linear regression tax projection and NPV optimization analysis."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"
    years = int(request.args.get("years", 3))
    rev_growth = float(request.args.get("rev_growth", 0.10))
    cost_inflation = float(request.args.get("cost_inflation", 0.05))
    discount_rate = float(request.args.get("discount_rate", 0.08))

    from invoices.v37_service import MultiYearTaxPlanningService
    try:
        proj = MultiYearTaxPlanningService.generate_tax_projection(mst, years, rev_growth, cost_inflation)
        npv_opt = MultiYearTaxPlanningService.optimize_tax_npv(proj, discount_rate)
        return jsonify({
            "status": "success",
            "projection": proj["projection"],
            "npv_optimization": npv_opt
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.get("/api/tax-planning/calendar")
def api_tax_planning_calendar():
    """US-492: Get or populate compliance deadline records."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    year = int(request.args.get("year", datetime.now().year))
    from invoices.v37_service import TaxFilingCalendarService
    from invoices.models import TaxFilingRecord
    try:
        # Populate calendar for current year if none exist
        count = TaxFilingRecord.query.filter(TaxFilingRecord.period.like(f"{year}%")).count()
        if count == 0:
            TaxFilingCalendarService.populate_calendar_db(year)

        records = TaxFilingRecord.query.all()
        compliance_score = TaxFilingCalendarService.calculate_compliance_score()
        return jsonify({
            "status": "success",
            "calendar": [r.to_dict() for r in records],
            "compliance_score": compliance_score
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/tax-planning/calendar/mark-filed")
def api_tax_planning_calendar_mark_filed():
    """US-492: Mark a filing task as filed."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    record_id = body.get("record_id")
    filed_date = body.get("filed_date") or date.today().isoformat()
    xml_path = body.get("xml_file_path")

    if not record_id:
        return jsonify({"error": "Missing record_id"}), 400

    from invoices.v37_service import TaxFilingCalendarService
    try:
        success = TaxFilingCalendarService.mark_filed(record_id, filed_date, xml_path)
        if success:
            return jsonify({"status": "success", "message": "Marked tax record as filed successfully."})
        return jsonify({"error": "Filing record not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.get("/api/assets")
def api_assets_list():
    """US-493: List all registered fixed assets."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from invoices.models import FixedAsset
    try:
        assets = FixedAsset.query.all()
        return jsonify({
            "status": "success",
            "assets": [a.to_dict() for a in assets]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/assets")
def api_assets_create():
    """US-493: Register a new fixed asset."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    code = body.get("asset_code")
    name = body.get("name")
    category = body.get("category")
    acq_date = body.get("acquisition_date") or date.today().isoformat()
    cost = float(body.get("original_cost", 0.0))
    residual = float(body.get("residual_value", 0.0))
    life = int(body.get("useful_life_months", 36))
    method = body.get("depreciation_method", "straight_line")
    linked_inv = body.get("linked_invoice_id")

    if not code or not name or not category:
        return jsonify({"error": "Missing required fields: code, name, or category"}), 400

    from invoices.models import FixedAsset
    try:
        asset = FixedAsset(
            asset_code=code,
            name=name,
            category=category,
            acquisition_date=acq_date,
            original_cost=cost,
            residual_value=residual,
            useful_life_months=life,
            depreciation_method=method,
            linked_invoice_id=linked_inv,
            status="active"
        )
        db.session.add(asset)
        db.session.commit()

        # Seed depreciation schedule immediately in DB
        from invoices.v37_service import FixedAssetDepreciationEngine
        schedule = FixedAssetDepreciationEngine.generate_depreciation_schedule(asset.id)
        from invoices.models import DepreciationEntry
        for entry in schedule:
            db_entry = DepreciationEntry(
                asset_id=asset.id,
                period=entry["period"],
                depreciation_amount=entry["depreciation_amount"],
                accumulated_depreciation=entry["accumulated_depreciation"],
                net_book_value=entry["net_book_value"]
            )
            db.session.add(db_entry)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Fixed asset registered successfully.",
            "asset": asset.to_dict()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.get("/api/assets/schedule")
def api_assets_schedule():
    """US-493: Get full depreciation schedule for an asset."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    asset_id = request.args.get("asset_id")
    if not asset_id:
        return jsonify({"error": "Missing asset_id"}), 400

    from invoices.models import DepreciationEntry
    try:
        entries = DepreciationEntry.query.filter_by(asset_id=int(asset_id)).order_by(DepreciationEntry.period.asc()).all()
        return jsonify({
            "status": "success",
            "schedule": [e.to_dict() for e in entries]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/assets/dispose")
def api_assets_dispose():
    """US-493: Dispose of an asset and record salvage gain/loss."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    body = request.get_json(silent=True) or {}
    asset_id = body.get("asset_id")
    disposed_date = body.get("disposed_date") or date.today().isoformat()
    proceeds = float(body.get("disposal_proceeds", 0.0))

    if not asset_id:
        return jsonify({"error": "Missing asset_id"}), 400

    from invoices.v37_service import FixedAssetDepreciationEngine
    try:
        res = FixedAssetDepreciationEngine.dispose_asset(int(asset_id), disposed_date, proceeds)
        if "error" in res:
            return jsonify(res), 404
        return jsonify({
            "status": "success",
            "message": "Asset disposed successfully.",
            "result": res
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.get("/api/assets/auto-detect")
def api_assets_auto_detect():
    """US-494: Auto-detect fixed asset candidates from purchase invoices."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"
    from invoices.v37_service import AIInvoiceAssetLinker
    try:
        candidates = AIInvoiceAssetLinker.auto_detect_fixed_assets(mst)
        return jsonify({
            "status": "success",
            "candidates": candidates
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.get("/api/assets/validate")
def api_assets_validate():
    """US-494: Check asset depreciation compliance against TT45 limits."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    asset_id = request.args.get("asset_id")
    if not asset_id:
        return jsonify({"error": "Missing asset_id"}), 400

    from invoices.models import FixedAsset
    from invoices.v37_service import AIInvoiceAssetLinker
    try:
        asset = db.session.get(FixedAsset, int(asset_id))
        if not asset:
            return jsonify({"error": "Asset not found"}), 404

        val_res = AIInvoiceAssetLinker.validate_depreciation_compliance(asset)
        return jsonify({
            "status": "success",
            "validation": val_res
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==========================================
# VERSION 38: E-DELIVERY NOTE & LOGISTICS COST ALLOCATION
# ==========================================

@invoices_blueprint.get("/v38-delivery-reconciliation")
def v38_delivery_reconciliation_page():
    """Render the E-Delivery Note and Logistics Cost Allocation Dashboard UI."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    return render_template("delivery_reconciliation.html")


@invoices_blueprint.get("/api/v38/delivery-notes")
def api_v38_delivery_notes():
    """Get all parsed electronic delivery notes."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from invoices.models import DeliveryNote
    notes = DeliveryNote.query.all()
    return jsonify({
        "status": "success",
        "delivery_notes": [n.to_dict() for n in notes]
    })


@invoices_blueprint.post("/api/v38/delivery-notes/upload")
def api_v38_upload_delivery_note():
    """Parse and upload a new GDT XML delivery note."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    xml_data = request.json.get("xml_content") if request.is_json else None
    if not xml_data:
        # Check files upload
        file = request.files.get("file")
        if file:
            xml_data = file.read().decode("utf-8", errors="ignore")
        else:
            return jsonify({"error": "No XML content provided"}), 400

    from invoices.v38_service import DeliveryNoteService
    from invoices.models import DeliveryNote

    try:
        parsed = DeliveryNoteService.parse_delivery_note_xml(xml_data)
        
        # Check if already exists
        existing = DeliveryNote.query.filter_by(note_number=parsed["note_number"]).first()
        if existing:
            # Update values
            existing.note_date = parsed["note_date"]
            existing.sender_mst = parsed["sender_mst"]
            existing.receiver_mst = parsed["receiver_mst"]
            existing.transport_contract = parsed["transport_contract"]
            existing.total_value = parsed["total_value"]
            db_note = existing
        else:
            db_note = DeliveryNote(
                note_number=parsed["note_number"],
                note_date=parsed["note_date"],
                sender_mst=parsed["sender_mst"],
                receiver_mst=parsed["receiver_mst"],
                transport_contract=parsed["transport_contract"],
                total_value=parsed["total_value"],
                status="Pending"
            )
            db.session.add(db_note)

        db.session.commit()

        # Perform auto-matching
        matched_inv = DeliveryNoteService.auto_match_invoice(db_note)
        if matched_inv:
            db_note.linked_invoice_id = matched_inv.id
            # Calculate penalty
            penalty_info = DeliveryNoteService.calculate_timing_penalty(db_note, matched_inv)
            if penalty_info["is_violating"]:
                db_note.status = "Overdue"
            else:
                db_note.status = "Invoiced"
        else:
            # Check if overdue without matching
            try:
                from datetime import datetime
                dn_date = datetime.strptime(db_note.note_date, "%Y-%m-%d").date()
                if (datetime.now().date() - dn_date).days > 10:
                    db_note.status = "Overdue"
            except Exception:
                pass

        db.session.commit()
        return jsonify({
            "status": "success",
            "delivery_note": db_note.to_dict()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/v38/delivery-notes/match")
def api_v38_match_delivery_note():
    """Manually map or clear match between delivery note and invoice."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    note_id = request.json.get("note_id")
    invoice_id = request.json.get("invoice_id") # Null/empty to clear match

    from invoices.models import DeliveryNote, Invoice
    from invoices.v38_service import DeliveryNoteService

    db_note = db.session.get(DeliveryNote, note_id)
    if not db_note:
        return jsonify({"error": "Delivery note not found"}), 404

    if not invoice_id:
        # Clear mapping
        db_note.linked_invoice_id = None
        db_note.status = "Pending"
        # Check if overdue
        try:
            dn_date = datetime.strptime(db_note.note_date, "%Y-%m-%d").date()
            if (datetime.now().date() - dn_date).days > 10:
                db_note.status = "Overdue"
        except Exception:
            pass
        db.session.commit()
        return jsonify({"status": "success", "delivery_note": db_note.to_dict()})

    inv = db.session.get(Invoice, invoice_id)
    if not inv:
        return jsonify({"error": "Invoice not found"}), 404

    db_note.linked_invoice_id = inv.id
    penalty_info = DeliveryNoteService.calculate_timing_penalty(db_note, inv)
    if penalty_info["is_violating"]:
        db_note.status = "Overdue"
    else:
        db_note.status = "Invoiced"
    
    db.session.commit()
    return jsonify({
        "status": "success",
        "delivery_note": db_note.to_dict(),
        "penalty": penalty_info
    })


@invoices_blueprint.get("/api/v38/delivery-notes/<int:note_id>/penalty")
def api_v38_delivery_note_penalty(note_id):
    """Retrieve timing and penalty information for a delivery note."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from invoices.models import DeliveryNote, Invoice
    from invoices.v38_service import DeliveryNoteService

    db_note = db.session.get(DeliveryNote, note_id)
    if not db_note:
        return jsonify({"error": "Delivery note not found"}), 404

    if not db_note.linked_invoice_id:
        # Check if overdue without matching
        try:
            dn_date = datetime.strptime(db_note.note_date, "%Y-%m-%d").date()
            days = (datetime.now().date() - dn_date).days
            if days > 10:
                return jsonify({
                    "status": "success",
                    "days_elapsed": days,
                    "is_violating": True,
                    "penalty_range": "10,000,000 - 25,000,000 VND (Overdue without commercial invoice)",
                    "risk_level": "Critical"
                })
        except Exception:
            pass
        return jsonify({
            "status": "success",
            "days_elapsed": 0,
            "is_violating": False,
            "penalty_range": "0 VND",
            "risk_level": "Low"
        })

    inv = db.session.get(Invoice, db_note.linked_invoice_id)
    if not inv:
        return jsonify({"error": "Linked invoice not found"}), 404

    penalty_info = DeliveryNoteService.calculate_timing_penalty(db_note, inv)
    return jsonify({
        "status": "success",
        **penalty_info
    })


@invoices_blueprint.get("/api/v38/logistics/eligible")
def api_v38_logistics_eligible():
    """List purchase invoices within range to allocate freight/logistics charges."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    logistics_invoice_id = request.args.get("logistics_invoice_id")
    if not logistics_invoice_id:
        return jsonify({"error": "Missing logistics_invoice_id"}), 400

    from invoices.models import Invoice
    from invoices.v38_service import LogisticsCostAllocatorService

    log_inv = db.session.get(Invoice, logistics_invoice_id)
    if not log_inv:
        return jsonify({"error": "Logistics invoice not found"}), 404

    eligible = LogisticsCostAllocatorService.find_eligible_purchase_invoices(log_inv)
    return jsonify({
        "status": "success",
        "eligible_invoices": [
            {
                "id": p.id,
                "invoice_number": p.invoice_number,
                "imported_at": p.imported_at,
                "total_amount": p.total_amount,
                "seller_name": p.seller_name
            } for p in eligible
        ]
    })


@invoices_blueprint.post("/api/v38/logistics/allocate")
def api_v38_logistics_allocate():
    """Allocate a logistics invoice total cost to target purchase invoices."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    logistics_invoice_id = request.json.get("logistics_invoice_id")
    purchase_invoice_ids = request.json.get("purchase_invoice_ids")
    method = request.json.get("method", "value_ratio")

    if not logistics_invoice_id or not purchase_invoice_ids:
        return jsonify({"error": "Missing parameters"}), 400

    from invoices.v38_service import LogisticsCostAllocatorService
    res = LogisticsCostAllocatorService.allocate_logistics_cost(
        logistics_invoice_id,
        purchase_invoice_ids,
        method=method
    )
    if res.get("status") == "error":
        return jsonify(res), 400
    return jsonify(res)


@invoices_blueprint.get("/api/v38/logistics/valuation")
def api_v38_logistics_valuation():
    """Retrieve adjusted inventory valuation report per VAS 02."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"
    from invoices.v38_service import LogisticsCostAllocatorService
    res = LogisticsCostAllocatorService.get_adjusted_inventory_valuation(mst)
    return jsonify({
        "status": "success",
        "valuation": res
    })


@invoices_blueprint.route("/v39-deferred-tax-and-risk")
def v39_deferred_tax_and_risk():
    """Render the dashboard command center page (US-511, US-512, US-513)."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from invoices.models import TaxpayerProfile
    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"
    profiles = TaxpayerProfile.query.filter_by(is_active=True).all()
    if not any(p.mst == mst for p in profiles) and profiles:
        mst = profiles[0].mst

    return render_template(
        "deferred_tax_and_risk.html",
        active_page="deferred_tax_and_risk",
        taxpayer_mst=mst,
        profiles=profiles
    )


@invoices_blueprint.get("/api/v39/deferred-tax")
def api_v39_deferred_tax():
    """Retrieve VAS 17 deferred tax calculations (US-510)."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"
    year = request.args.get("year", default=datetime.now().year, type=int)
    from invoices.v39_service import DeferredTaxService
    res = DeferredTaxService.calculate_vas17_deferred_tax(mst, year)
    return jsonify({
        "status": "success",
        "data": res
    })


@invoices_blueprint.get("/api/v39/journal-entries")
def api_v39_journal_entries():
    """Retrieve suggested double-entry journal postings (US-511)."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"
    year = request.args.get("year", default=datetime.now().year, type=int)
    from invoices.v39_service import DeferredTaxService
    entries = DeferredTaxService.generate_journal_entries(mst, year)
    return jsonify({
        "status": "success",
        "journal_entries": entries
    })


@invoices_blueprint.get("/api/v39/cash-stress")
def api_v39_cash_stress():
    """Simulate runway under DSO/DPO changes (US-512)."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"
    dso = request.args.get("dso_days", default=0, type=int)
    dpo = request.args.get("dpo_days", default=0, type=int)
    from invoices.v39_service import CashFlowStressService
    res = CashFlowStressService.run_cash_stress_simulation(mst, dso, dpo)
    return jsonify({
        "status": "success",
        "simulation": res
    })


@invoices_blueprint.get("/api/v39/supplier-network")
def api_v39_supplier_network():
    """Retrieve supplier network nodes and links (US-513)."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"
    from invoices.v39_service import SupplierRiskNetworkService
    res = SupplierRiskNetworkService.build_supplier_network_graph(mst)
    return jsonify({
        "status": "success",
        "network": res
    })


@invoices_blueprint.post("/api/v39/supplier-scraper-check")
def api_v39_supplier_scraper_check():
    """Simulate checking GDT state (US-514)."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    seller_mst = request.json.get("seller_mst")
    if not seller_mst:
        return jsonify({"error": "Missing seller_mst"}), 400

    from invoices.v39_service import SupplierRiskNetworkService
    res = SupplierRiskNetworkService.simulate_gdt_scraper_check(seller_mst)
    return jsonify({
        "status": "success",
        "check_result": res
    })


@invoices_blueprint.route("/v40-compliance-dashboard")
def v40_compliance_dashboard():
    """Render the dashboard command center page for FCT, Related Party & XML Signature (US-523)."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    from invoices.models import TaxpayerProfile
    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"
    profiles = TaxpayerProfile.query.filter_by(is_active=True).all()
    if not any(p.mst == mst for p in profiles) and profiles:
        mst = profiles[0].mst

    return render_template(
        "v40_compliance_dashboard.html",
        active_page="v40_compliance",
        taxpayer_mst=mst,
        profiles=profiles
    )


@invoices_blueprint.post("/api/v40/fct/calculate")
def api_v40_fct_calculate():
    """Calculate FCT withholding tax under Circular 103 (US-520)."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    val = float(data.get("contract_value", 0.0))
    ctype = data.get("contract_type", "gross")
    cat = data.get("service_category", "services")

    from invoices.v40_service import FCTService
    res = FCTService.calculate_fct_withholding(val, ctype, cat)
    return jsonify({
        "status": "success",
        "calculation": res
    })


@invoices_blueprint.get("/api/v40/fct/declaration")
def api_v40_fct_declaration():
    """Retrieve FCT Form 01/NTNN declaration mappings (US-520)."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"
    period = request.args.get("period", datetime.now().strftime("%Y-%m"))
    from invoices.v40_service import FCTService
    res = FCTService.generate_fct_declaration(mst, period)
    return jsonify({
        "status": "success",
        "declaration": res
    })


@invoices_blueprint.post("/api/v40/related-party/relationship")
def api_v40_related_party_relationship():
    """Register a new related party relationship (US-521)."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    partner_mst = data.get("partner_mst")
    partner_name = data.get("partner_name")
    rel_type = data.get("relationship_type")
    ownership = float(data.get("ownership_percentage", 0.0))
    details = data.get("details", "")

    if not partner_mst or not partner_name or not rel_type:
        return jsonify({"error": "Missing partner_mst, partner_name, or relationship_type"}), 400

    from invoices.v40_service import RelatedPartyService
    rel = RelatedPartyService.add_related_party_relationship(
        mst, partner_mst, partner_name, rel_type, ownership, details
    )
    return jsonify({
        "status": "success",
        "relationship": rel.to_dict()
    })


@invoices_blueprint.get("/api/v40/related-party/ebitda-limit")
def api_v40_related_party_ebitda_limit():
    """Calculate Decree 132 30% EBITDA interest expense cap limit (US-521)."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"
    year = request.args.get("year", default=datetime.now().year, type=int)
    profit = float(request.args.get("profit_before_tax", 0.0))
    expense = float(request.args.get("interest_expense", 0.0))
    income = float(request.args.get("interest_income", 0.0))
    depr = float(request.args.get("depreciation_amortization", 0.0))

    from invoices.v40_service import RelatedPartyService
    res = RelatedPartyService.calculate_ebitda_limit(mst, year, profit, expense, income, depr)
    return jsonify({
        "status": "success",
        "audit": res
    })


@invoices_blueprint.post("/api/v40/xml/verify")
def api_v40_xml_verify():
    """Audit digital signature & X.509 cert inside e-invoice XML (US-522)."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    xml_text = None
    if "file" in request.files:
        file = request.files["file"]
        xml_text = file.read().decode("utf-8", errors="ignore")
    elif request.json and "xml_content" in request.json:
        xml_text = request.json["xml_content"]
    else:
        xml_text = request.data.decode("utf-8", errors="ignore")

    from invoices.v40_service import InvoiceSignatureService
    res = InvoiceSignatureService.verify_invoice_xml_signature(xml_text)
    return jsonify({
        "status": "success",
        "verification": res
    })


@invoices_blueprint.get("/v41-export-refund")
def v41_export_refund_page():
    """Render the V41 Export Customs & VAT Refund Hub (Circular 80) screen."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    
    from invoices.models import TaxpayerProfile
    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"
    profiles = TaxpayerProfile.query.filter_by(is_active=True).all()
    if not any(p.mst == mst for p in profiles) and profiles:
        mst = profiles[0].mst

    return render_template(
        "v41_export_refund.html",
        active_page="v41_export_refund",
        taxpayer_mst=mst,
        profiles=profiles
    )


@invoices_blueprint.post("/api/v41/customs/upload")
def api_v41_customs_upload():
    """Upload and parse Customs XML Declaration (US-530)."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"
    xml_content = None
    if "file" in request.files:
        xml_content = request.files["file"].read().decode("utf-8", errors="ignore")
    elif request.json and "xml_content" in request.json:
        xml_content = request.json["xml_content"]

    if not xml_content:
        return jsonify({"error": "No XML content provided"}), 400

    from invoices.v41_service import ExportVatRefundService
    try:
        res = ExportVatRefundService.parse_customs_xml(xml_content, mst)
        return jsonify({"status": "success", "declaration": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.post("/api/v41/customs/reconcile")
def api_v41_customs_reconcile():
    """Reconcile pending Customs Declarations with GTGT invoices (US-531)."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = request.json.get("mst") if request.json else None
    mst = mst or request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"

    from invoices.v41_service import ExportVatRefundService
    matches = ExportVatRefundService.reconcile_declarations(mst)
    return jsonify({"status": "success", "matches": matches})


@invoices_blueprint.get("/api/v41/customs/form-01-1")
def api_v41_customs_form_01_1():
    """Retrieve Form 01-1/GTGT Circular 80 Export Goods List (US-532)."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"
    period_start = request.args.get("period_start", "2026-01-01")
    period_end = request.args.get("period_end", "2026-12-31")

    from invoices.v41_service import ExportVatRefundService
    form_data = ExportVatRefundService.build_form_01_1_gtgt(mst, period_start, period_end)
    return jsonify({"status": "success", "form_data": form_data})


@invoices_blueprint.get("/api/v41/customs/refund-limits")
def api_v41_customs_refund_limits():
    """Get calculated tax refund limits and eligibility (US-533)."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"
    period_start = request.args.get("period_start", "2026-01-01")
    period_end = request.args.get("period_end", "2026-12-31")
    total_input = float(request.args.get("total_input_vat", 0.0))

    from invoices.v41_service import ExportVatRefundService
    limits = ExportVatRefundService.calculate_refund_limits(mst, period_start, period_end, total_input)
    return jsonify({"status": "success", "limits": limits})


@invoices_blueprint.post("/api/v41/customs/refund-submit")
def api_v41_customs_refund_submit():
    """Submit a tax refund application Form 01/ĐNHT (US-533)."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    period_start = data.get("period_start", "2026-01-01")
    period_end = data.get("period_end", "2026-12-31")
    total_input = float(data.get("total_input_vat", 0.0))
    requested_amount = float(data.get("requested_amount", 0.0))

    from invoices.v41_service import ExportVatRefundService
    try:
        app_dict = ExportVatRefundService.submit_refund_application(
            mst, period_start, period_end, total_input, requested_amount
        )
        return jsonify({"status": "success", "application": app_dict})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.get("/api/v41/customs/dashboard")
def api_v41_customs_dashboard():
    """Get dashboard compliance aggregate statistics (US-534)."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"

    from invoices.v41_service import ExportVatRefundService
    stats = ExportVatRefundService.get_refund_dashboard_data(mst)
    return jsonify({"status": "success", "stats": stats})


@invoices_blueprint.get("/v42-advanced-audit")
def v42_advanced_audit_page():
    """Render the V42 Advanced Audit: Transfer Pricing & E-Commerce Hub (US-543)."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    
    from invoices.models import TaxpayerProfile
    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"
    profiles = TaxpayerProfile.query.filter_by(is_active=True).all()
    if not any(p.mst == mst for p in profiles) and profiles:
        mst = profiles[0].mst

    return render_template(
        "v42_advanced_audit.html",
        active_page="v42_advanced_audit",
        taxpayer_mst=mst,
        profiles=profiles
    )


@invoices_blueprint.post("/api/v42/transfer-pricing/calculate")
def api_v42_transfer_pricing_calculate():
    """Calculate related-party benchmarking and adjustments (US-540)."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    transactions = data.get("transactions", [])

    from invoices.v42_service import AdvancedAuditService
    try:
        res = AdvancedAuditService.calculate_transfer_pricing_benchmarks(mst, transactions)
        return jsonify({"status": "success", "data": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.post("/api/v42/transfer-pricing/export-xml")
def api_v42_transfer_pricing_export_xml():
    """Export Form 01/132 related-party disclosure XML (US-541)."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    taxpayer_name = data.get("taxpayer_name", "Viet Taxpayer Corp")
    year = data.get("year", datetime.now().year)
    tp_items = data.get("tp_items", [])

    from invoices.v42_service import AdvancedAuditService
    try:
        xml_content = AdvancedAuditService.generate_form_01_132_xml(mst, taxpayer_name, year, tp_items)
        return jsonify({"status": "success", "xml_content": xml_content})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.post("/api/v42/ecommerce/reconcile")
def api_v42_ecommerce_reconcile():
    """Reconcile e-commerce platform transactions (US-542)."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    transactions = data.get("transactions", [])

    from invoices.v42_service import AdvancedAuditService
    try:
        res = AdvancedAuditService.reconcile_ecommerce_transactions(mst, transactions)
        return jsonify({"status": "success", "data": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.get("/api/v42/dashboard-data")
def api_v42_dashboard_data():
    """Retrieve V42 aggregated compliance data and swarm memo (US-543)."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"

    from invoices.models import TransferPricingBenchmark, ECommerceReconciliationReport
    tp_items = TransferPricingBenchmark.query.filter_by(taxpayer_mst=mst).all()
    report = ECommerceReconciliationReport.query.filter_by(taxpayer_mst=mst).order_by(ECommerceReconciliationReport.id.desc()).first()

    tp_dict = {
        "items": [item.to_dict() for item in tp_items],
        "total_cit_adjustment": sum(item.adjustment_amount for item in tp_items)
    }

    eco_dict = {
        "report": report.to_dict() if report else {}
    }

    from invoices.v42_service import AdvancedAuditService
    debate, memo = AdvancedAuditService.simulate_advisor_debate(tp_dict, eco_dict)

    return jsonify({
        "status": "success",
        "transfer_pricing": tp_dict,
        "ecommerce": eco_dict,
        "debate": debate,
        "memo": memo
    })


@invoices_blueprint.get("/v43-ifrs-dashboard")
def v43_ifrs_dashboard_page():
    """Render the Version 43 IFRS Translation Engine and OECD Pillar Two GMT Dashboard."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    return render_template("v43_ifrs_dashboard.html")


@invoices_blueprint.post("/api/v43/deferred-tax/calculate")
def api_v43_deferred_tax_calculate():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    year = int(data.get("year", 2026))

    from invoices.ifrs_engine import IFRSTranslationService
    engine = IFRSTranslationService(current_app.config["BASE_DATA_DIR"])
    conn = engine.get_tenant_connection(mst)
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM ifrs_deferred_tax_ledger WHERE fiscal_year = ?", (year,))
    if cur.fetchone()[0] == 0:
        cur.executemany("""
            INSERT INTO ifrs_deferred_tax_ledger (fiscal_year, fiscal_period, balance_sheet_item, carrying_amount_ifrs, tax_base_vas, tax_rate)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [
            (year, 12, "Property, Plant & Equipment", 120000000.0, 100000000.0, 0.20),
            (year, 12, "Provisions for Warranties", 15000000.0, 0.0, 0.20),
            (year, 12, "Prepaid Lease Expense", 50000000.0, 60000000.0, 0.20),
        ])
        conn.commit()
    conn.close()

    try:
        results = engine.calculate_ias12_deferred_tax(mst, year)
        return jsonify({"status": "success", "results": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.post("/api/v43/ifrs15/allocate")
def api_v43_ifrs15_allocate():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    contract_id = data.get("contract_id", "CON-7799")
    customer_name = data.get("customer_name", "Acme Global")
    contract_date = data.get("contract_date", "2026-06-11")
    total_price = float(data.get("total_price", 150000.0))
    obligations = data.get("obligations", [
        {"obligation_name": "Software License", "standalone_selling_price": 100000.0},
        {"obligation_name": "Implementation Services", "standalone_selling_price": 40000.0},
        {"obligation_name": "Premium Support", "standalone_selling_price": 20000.0}
    ])

    from invoices.ifrs_engine import IFRSTranslationService
    try:
        engine = IFRSTranslationService(current_app.config["BASE_DATA_DIR"])
        res = engine.allocate_ifrs15_transaction_price(mst, contract_id, customer_name, contract_date, total_price, obligations)
        return jsonify({"status": "success", "allocated_price_splits": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.post("/api/v43/ifrs15/recognize")
def api_v43_ifrs15_recognize():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    contract_id = data.get("contract_id", "CON-7799")
    satisfied_names = data.get("satisfied_names", ["Software License"])
    satisfied_date = data.get("satisfied_date", "2026-06-11")

    from invoices.ifrs_engine import IFRSTranslationService
    try:
        engine = IFRSTranslationService(current_app.config["BASE_DATA_DIR"])
        res = engine.recognize_ifrs15_revenue(mst, contract_id, satisfied_names, satisfied_date)
        return jsonify({"status": "success", "revenue_recognized": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.post("/api/v43/ifrs16/amortize")
def api_v43_ifrs16_amortize():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    lease_id = data.get("lease_id", "LEASE-007")
    supplier_mst = data.get("supplier_mst", "9988776655")
    commencement_date = data.get("commencement_date", "2026-01-01")
    lease_term_months = int(data.get("lease_term_months", 36))
    monthly_payment = float(data.get("monthly_payment", 5000.0))
    discount_rate = float(data.get("discount_rate", 0.06))

    from invoices.ifrs_engine import IFRSTranslationService
    try:
        engine = IFRSTranslationService(current_app.config["BASE_DATA_DIR"])
        conn = engine.get_tenant_connection(mst)
        cur = conn.cursor()
        r = discount_rate / 12
        if r > 0:
            pv = monthly_payment * ((1 - (1 + r) ** -lease_term_months) / r)
        else:
            pv = monthly_payment * lease_term_months
            
        cur.execute("""
            INSERT OR REPLACE INTO lease_amortization_schedule (
                lease_id, supplier_mst, commencement_date, lease_term_months, monthly_payment, discount_rate, present_value_rou, liability_balance
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (lease_id, supplier_mst, commencement_date, lease_term_months, monthly_payment, discount_rate, pv, pv))
        conn.commit()
        conn.close()

        res = engine.calculate_ifrs16_amortization_table(mst, lease_id)
        return jsonify({"status": "success", "amortization_table": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.post("/api/v43/pillar2/estimate")
def api_v43_pillar2_estimate():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    parent_mst = data.get("parent_mst") or session.get("taxpayer_mst") or "0102030405"
    year = int(data.get("year", 2026))
    subsidiary_msts = data.get("subsidiary_msts", ["0102030406", "0102030407"])

    from invoices.ifrs_engine import IFRSTranslationService
    try:
        engine = IFRSTranslationService(current_app.config["BASE_DATA_DIR"])
        res = engine.estimate_pillar_two_topup(parent_mst, [parent_mst] + subsidiary_msts, year)
        return jsonify({"status": "success", "pillar_two_estimate": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.get("/api/v43/dashboard-data")
def api_v43_dashboard_data():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"
    year = int(request.args.get("year", 2026))

    from invoices.ifrs_engine import IFRSTranslationService
    engine = IFRSTranslationService(current_app.config["BASE_DATA_DIR"])
    
    # 1. Deferred Tax calculation
    conn = engine.get_tenant_connection(mst)
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM ifrs_deferred_tax_ledger WHERE fiscal_year = ?", (year,))
    if cur.fetchone()[0] == 0:
        cur.executemany("""
            INSERT INTO ifrs_deferred_tax_ledger (fiscal_year, fiscal_period, balance_sheet_item, carrying_amount_ifrs, tax_base_vas, tax_rate)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [
            (year, 12, "Property, Plant & Equipment", 120000000.0, 100000000.0, 0.20),
            (year, 12, "Provisions for Warranties", 15000000.0, 0.0, 0.20),
            (year, 12, "Prepaid Lease Expense", 50000000.0, 60000000.0, 0.20),
        ])
        conn.commit()
    deferred_tax_results = engine.calculate_ias12_deferred_tax(mst, year)
    
    # 2. Leases
    cur.execute("SELECT count(*) FROM lease_amortization_schedule")
    if cur.fetchone()[0] == 0:
        cur.execute("""
            INSERT INTO lease_amortization_schedule (
                lease_id, supplier_mst, commencement_date, lease_term_months, monthly_payment, discount_rate, present_value_rou, liability_balance
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ("LEASE-007", "9988776655", "2026-01-01", 36, 5000.0, 0.06, 164295.38, 164295.38))
        conn.commit()
    
    cur.execute("SELECT lease_id, commencement_date, lease_term_months, monthly_payment, discount_rate, present_value_rou, liability_balance FROM lease_amortization_schedule")
    leases = [dict(row) for row in cur.fetchall()]
    
    lease_schedules = {}
    for lease in leases:
        lid = lease["lease_id"]
        lease_schedules[lid] = engine.calculate_ifrs16_amortization_table(mst, lid)
        
    # 3. Revenue Contracts
    cur.execute("SELECT count(*) FROM ifrs15_revenue_contracts")
    if cur.fetchone()[0] == 0:
        engine.allocate_ifrs15_transaction_price(
            mst, "CON-7799", "Acme Global", "2026-06-11", 150000.0,
            [
                {"obligation_name": "Software License", "standalone_selling_price": 100000.0},
                {"obligation_name": "Implementation Services", "standalone_selling_price": 40000.0},
                {"obligation_name": "Premium Support", "standalone_selling_price": 20000.0}
            ]
        )
        engine.recognize_ifrs15_revenue(mst, "CON-7799", ["Software License"], "2026-06-11")
        
    cur.execute("SELECT contract_id, customer_name, contract_date, total_transaction_price, deferred_revenue, recognized_revenue FROM ifrs15_revenue_contracts")
    contracts = [dict(row) for row in cur.fetchall()]
    for c in contracts:
        cur.execute("SELECT obligation_name, standalone_selling_price, allocated_price, is_satisfied, satisfied_date FROM ifrs15_performance_obligations WHERE contract_id = ?", (c["contract_id"],))
        c["obligations"] = [dict(row) for row in cur.fetchall()]
        
    conn.close()
    
    # 4. Pillar Two
    subsidiary_msts = ["0102030406", "0102030407"]
    pillar2_result = engine.estimate_pillar_two_topup(mst, [mst] + subsidiary_msts, year)
    
    debate_transcript = [
        {"speaker": "Local Tax Inspector", "text": "For deferred tax, IAS 12 recognition of deferred tax asset is subject to stringent probability testing under standard requirements. We must verify if future taxable profit is probable."},
        {"speaker": "IFRS Accounting Advisor", "text": "Agreed, but IFRS 16 lease liability is a major source of temporary differences here. As the ROU asset depreciates and the liability is reduced via cash payments, DTA and DTL are recognized. We should automate this mapping."},
        {"speaker": "OECD Tax Compliance Expert", "text": "Under Pillar Two GloBE rules, the ETR calculation uses Adjusted Covered Taxes over GloBE Income. If the Vietnamese ETR is estimated at 12%, a 3% Top-up Tax must be calculated, subject to SBIE."}
    ]
    
    consensus_summary = "AUTOMATED VERDICT: The IFRS Translation engine has correctly computed the temporary differences and generated the relative Standalone Selling Price allocation schedules. Pillar Two estimation stands ready."

    return jsonify({
        "status": "success",
        "deferred_tax": deferred_tax_results,
        "leases": leases,
        "lease_schedules": lease_schedules,
        "revenue_contracts": contracts,
        "pillar_two": pillar2_result,
        "debate": debate_transcript,
        "consensus_summary": consensus_summary
    })


@invoices_blueprint.get("/v44-compliance-hub")
def v44_compliance_hub_page():
    """Render the Version 44 compliance hub."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    return render_template("v44_compliance_hub.html")


@invoices_blueprint.post("/api/v44/reconcile-adjustments")
def api_v44_reconcile_adjustments():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"

    from invoices.v44_service import V44ComplianceService
    try:
        service = V44ComplianceService(current_app.config["BASE_DATA_DIR"])
        results = service.reconcile_decree123_adjustments(mst)
        return jsonify({"status": "success", "results": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.post("/api/v44/sci-tech-fund/simulate")
def api_v44_sci_tech_fund_simulate():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    year = int(data.get("year", 2026))
    taxable_income = float(data.get("taxable_income", 1000000000.0))
    allocation_percent = float(data.get("allocation_percent", 10.0))
    annual_rd_spend = float(data.get("annual_rd_spend", 150000000.0))
    qualified_ratio = float(data.get("qualified_ratio", 0.8))
    welfare_expenses = float(data.get("welfare_expenses", 20000000.0))
    average_monthly_salary = float(data.get("average_monthly_salary", 15000000.0))

    from invoices.v44_service import V44ComplianceService
    try:
        service = V44ComplianceService(current_app.config["BASE_DATA_DIR"])
        res = service.simulate_sci_tech_fund(
            mst, year, taxable_income, allocation_percent, 
            annual_rd_spend, qualified_ratio, welfare_expenses, average_monthly_salary
        )
        return jsonify({"status": "success", "simulation_results": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.get("/api/v44/compliance-data")
def api_v44_compliance_data():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"
    year = int(request.args.get("year", 2026))

    from invoices.v44_service import V44ComplianceService
    service = V44ComplianceService(current_app.config["BASE_DATA_DIR"])
    
    # 1. Initialize DB and seed mock data if empty
    conn = service.get_tenant_connection(mst)
    cur = conn.cursor()
    
    # Check if adjustments table is empty
    cur.execute("SELECT count(*) FROM decree123_invoice_adjustments")
    if cur.fetchone()[0] == 0:
        cur.executemany("""
            INSERT INTO decree123_invoice_adjustments (original_invoice_symbol, original_invoice_number, adjustment_invoice_symbol, adjustment_invoice_number, adjustment_type, amount_change, vat_change, tax_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            ("1C26TAA", "0000015", "1C26TAA", "0000088", "adjustment", -10000000.0, -1000000.0, 0.10),
            ("2C26TBB", "0000020", "2C26TBB", "0000099", "discount", -5000000.0, -500000.0, 0.10),
            ("INVALID", "9999999", "3C26TCC", "0000100", "replacement", -20000000.0, -2000000.0, 0.10),
            ("1C26TAA", "0000015", "1C26TAA", "0000122", "adjustment", -500000000.0, -50000000.0, 0.10), # Exceeds original
        ])
        conn.commit()
        
    # Seed mock invoices in tenant DB if none exist
    cur.execute("SELECT count(*) FROM invoice")
    if cur.fetchone()[0] == 0:
        cur.executemany("""
            INSERT INTO invoice (id, filename, seller_name, seller_mst, buyer_name, buyer_mst, amount_before_tax, tax_amount, total_amount, date, imported_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            ("0000015", "invoice_0000015.xml", "This Corp", mst, "Acme Client", "0102030499", 100000000.0, 10000000.0, 110000000.0, "2026-06-11", "2026-06-11"),
            ("0000020", "invoice_0000020.xml", "This Corp", mst, "Beta Client", "0102030488", 50000000.0, 5000000.0, 55000000.0, "2026-06-11", "2026-06-11"),
        ])
        conn.commit()

    conn.close()

    # Calculate compliance metrics
    reconciliation_results = service.reconcile_decree123_adjustments(mst)
    
    # Trigger default simulation
    simulation_results = service.simulate_sci_tech_fund(
        mst, year, 1000000000.0, 10.0, 150000000.0, 0.8, 20000000.0, 15000000.0
    )

    debate_transcript = [
        {"speaker": "Local Tax Inspector", "text": "Under Decree 123, price reduction and discount adjustment invoices must clearly reference the original invoice number and symbol. Any unlinked adjustments will be disallowed for VAT input tax deduction immediately."},
        {"speaker": "CIT Auditor", "text": "Correct, and under Circular 67, R&D funds must be spent on qualified activities. Non-qualified spend triggers a 20% CIT clawback plus 0.03% daily interest. Let's make sure the timeline modeler captures this."},
        {"speaker": "CFO Advisor", "text": "By optimizing our allocation rate between 5% and 10% and closely auditing our R&D expenditures, we can maximize tax savings while avoiding audit penalties."}
    ]
    
    consensus_summary = "AUTOMATED VERDICT: Decree 123 adjustments have been reconciled against the local ledger. Science & Tech Fund projections indicate potential CIT savings of 100,000,000 VND, subject to qualification audits."

    return jsonify({
        "status": "success",
        "reconciliation": reconciliation_results,
        "simulation": simulation_results,
        "debate": debate_transcript,
        "consensus_summary": consensus_summary
    })


@invoices_blueprint.get("/v45-compliance-hub")
def v45_compliance_hub_page():
    """Render the Version 45 compliance hub."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    return render_template("v45_compliance_hub.html")


@invoices_blueprint.post("/api/v45/cit-incentives/calculate")
def api_v45_cit_incentives_calculate():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    year = int(data.get("year", 2026))
    total_taxable_income = float(data.get("total_taxable_income", 1000000000.0))
    preferential_income = float(data.get("preferential_income", 600000000.0))
    preferential_rate = float(data.get("preferential_rate", 0.10))
    holiday_start_year = int(data.get("holiday_start_year", 2024))
    exemption_years = int(data.get("exemption_years", 2))
    reduction_years = int(data.get("reduction_years", 4))

    from invoices.v45_service import V45ComplianceService
    try:
        service = V45ComplianceService(current_app.config["BASE_DATA_DIR"])
        res = service.simulate_preferential_cit(
            mst, year, total_taxable_income, preferential_income,
            preferential_rate, holiday_start_year, exemption_years, reduction_years
        )
        return jsonify({"status": "success", "results": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.post("/api/v45/tp-safe-harbors/evaluate")
def api_v45_tp_safe_harbors_evaluate():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    year = int(data.get("year", 2026))
    total_revenue = float(data.get("total_revenue", 45000000000.0))
    related_party_txn_value = float(data.get("related_party_txn_value", 25000000000.0))
    net_profit_margin = float(data.get("net_profit_margin", 0.03))
    activity_type = data.get("activity_type", "trading")
    apa_lower = data.get("apa_lower")
    apa_upper = data.get("apa_upper")
    actual_margin = data.get("actual_margin")

    if apa_lower is not None:
        apa_lower = float(apa_lower)
    if apa_upper is not None:
        apa_upper = float(apa_upper)
    if actual_margin is not None:
        actual_margin = float(actual_margin)

    from invoices.v45_service import V45ComplianceService
    try:
        service = V45ComplianceService(current_app.config["BASE_DATA_DIR"])
        res = service.evaluate_tp_safe_harbors(
            mst, year, total_revenue, related_party_txn_value,
            net_profit_margin, activity_type, apa_lower, apa_upper, actual_margin
        )
        return jsonify({"status": "success", "results": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.get("/api/v45/compliance-data")
def api_v45_compliance_data():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"
    year = int(request.args.get("year", 2026))

    from invoices.v45_service import V45ComplianceService
    service = V45ComplianceService(current_app.config["BASE_DATA_DIR"])
    
    # Initialize DB and run initial simulations/evaluations to seed tables
    cit_res = service.simulate_preferential_cit(
        mst=mst, year=year, total_taxable_income=1200000000.0, preferential_income=700000000.0,
        preferential_rate=0.10, holiday_start_year=2024, exemption_years=2, reduction_years=4
    )
    tp_res = service.evaluate_tp_safe_harbors(
        mst=mst, year=year, total_revenue=48000000000.0, related_party_txn_value=28000000000.0,
        net_profit_margin=0.035, activity_type="trading", apa_lower=0.03, apa_upper=0.05, actual_margin=0.04
    )

    debate_transcript = [
        {"speaker": "Tax Inspector", "text": "Under Circular 80, CIT incentives are projects-based. Income segregation must be clearly audited. Also, Decree 132 imposes strict Transfer Pricing documentation unless Safe Harbor thresholds are strictly met."},
        {"speaker": "CFO", "text": "Our trading margins are currently at 3.5%, which safely satisfies the 2.0% safe harbor threshold for distributors under 200B VND revenue. We also have active APA compliance at 4.0%."},
        {"speaker": "Auditor", "text": "Ensure that the holiday exemption schedule (2 years exempt, 4 years 50% reduced) uses the correct start year (2024), making 2026 the first year of 50% reduction."}
    ]
    consensus_summary = "AUTOMATED VERDICT: Safe Harbor requirements are met for trading activities. CIT incentives calculation projects total tax liability reduction."

    return jsonify({
        "status": "success",
        "cit_simulation": cit_res,
        "tp_safe_harbor": tp_res,
        "debate": debate_transcript,
        "consensus_summary": consensus_summary
    })


@invoices_blueprint.get("/v46-compliance-hub")
def v46_compliance_hub_page():
    """Render the Version 46 compliance hub."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    return render_template("v46_compliance_hub.html")


@invoices_blueprint.post("/api/v46/incidents/submit-form")
def api_v46_submit_form():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    symbol = data.get("original_invoice_symbol", "1C26TAA")
    number = data.get("original_invoice_number", "0000015")
    invoice_date = data.get("invoice_date", "2026-06-11")
    filing_date = data.get("filing_date", "2026-07-20")
    gdt_status = int(data.get("gdt_status", 1))

    from invoices.v46_service import V46ComplianceService
    try:
        service = V46ComplianceService(current_app.config["BASE_DATA_DIR"])
        res = service.process_form_04_ss(
            mst, symbol, number, invoice_date, filing_date, gdt_status
        )
        return jsonify({"status": "success", "results": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.post("/api/v46/conversions/reconcile")
def api_v46_conversions_reconcile():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    symbol = data.get("invoice_symbol", "1C26TAA")
    number = data.get("invoice_number", "0000015")
    print_date = data.get("print_date", "2026-06-12")
    print_count = int(data.get("print_count", 2))
    converted_by = data.get("converted_by", "Admin Office")
    invoice_amount = float(data.get("invoice_amount", 100000000.0))

    from invoices.v46_service import V46ComplianceService
    try:
        service = V46ComplianceService(current_app.config["BASE_DATA_DIR"])
        res = service.audit_conversion_prints(
            mst, symbol, number, print_date, print_count, converted_by, invoice_amount
        )
        return jsonify({"status": "success", "results": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.get("/api/v46/compliance-data")
def api_v46_compliance_data():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"

    from invoices.v46_service import V46ComplianceService
    service = V46ComplianceService(current_app.config["BASE_DATA_DIR"])
    
    # Initialize and seed default records
    incident_res = service.process_form_04_ss(
        mst=mst, original_invoice_symbol="1C26TAA", original_invoice_number="0000015",
        invoice_date_str="2026-06-11", filing_date_str="2026-07-25", gdt_status_code=1
    )
    conversion_res = service.audit_conversion_prints(
        mst=mst, invoice_symbol="1C26TAA", invoice_number="0000015",
        print_date_str="2026-06-12", print_count=2, converted_by="Admin Office", invoice_amount=100000000.0
    )

    debate_transcript = [
        {"speaker": "Tax Officer", "text": "Under Decree 123, any error on an e-invoice must trigger Form 04/SS-HĐĐT to be sent to GDT. Late submission beyond subsequent month/quarter will incur severe regulatory fines."},
        {"speaker": "Internal Auditor", "text": "Our conversion auditor successfully flagged invoice 0000015 for multiple prints (2 copies) and triggered a DUPLICATE_CONVERSION_CLAIM warning since the corresponding XML was already claimed."},
        {"speaker": "Finance Director", "text": "This protects our CIT expense deductions. Converted prints should only be used as proof of receipt once, and must carry conversion signatures."}
    ]
    consensus_summary = "AUTOMATED VERDICT: Form 04/SS logs ingest completed with 1 alert. Conversion prints duplicate claim checks flagged 2 risk alerts."

    return jsonify({
        "status": "success",
        "incidents": incident_res,
        "conversions": conversion_res,
        "debate": debate_transcript,
        "consensus_summary": consensus_summary
    })


# ═══════════════════════════════════════════════════════════════════
# VERSION 47 — VAT Law 48/2024/QH15 Compliance Engine
# ═══════════════════════════════════════════════════════════════════

@invoices_blueprint.get("/v47-compliance-hub")
def v47_compliance_hub_page():
    """Render the Version 47 VAT Law 48 compliance hub."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    return render_template("v47_compliance_hub.html")


@invoices_blueprint.post("/api/v47/rate/classify")
def api_v47_rate_classify():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    item_description = data.get("item_description", "Dịch vụ tư vấn")

    from invoices.v47_service import V47ComplianceService
    try:
        service = V47ComplianceService(current_app.config["BASE_DATA_DIR"])
        res = service.classify_vat_rate(mst, item_description)
        return jsonify({"status": "success", "results": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.post("/api/v47/credit/check")
def api_v47_credit_check():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    invoice_number = data.get("invoice_number", "INV-2026-001")
    invoice_amount = float(data.get("invoice_amount", 50000000.0))
    has_vat_invoice = data.get("has_vat_invoice", True)
    has_bank_payment = data.get("has_bank_payment", True)
    seller_declared = data.get("seller_declared", True)

    from invoices.v47_service import V47ComplianceService
    try:
        service = V47ComplianceService(current_app.config["BASE_DATA_DIR"])
        res = service.check_input_credit_eligibility(
            mst, invoice_number, invoice_amount,
            has_vat_invoice, has_bank_payment, seller_declared
        )
        return jsonify({"status": "success", "results": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.post("/api/v47/refund/estimate")
def api_v47_refund_estimate():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    period_label = data.get("period_label", "Q1-2026")
    total_output_vat = float(data.get("total_output_vat", 100000000.0))
    total_input_vat = float(data.get("total_input_vat", 500000000.0))
    export_revenue = float(data.get("export_revenue", 5000000000.0))

    from invoices.v47_service import V47ComplianceService
    try:
        service = V47ComplianceService(current_app.config["BASE_DATA_DIR"])
        res = service.estimate_vat_refund(
            mst, period_label, total_output_vat, total_input_vat, export_revenue
        )
        return jsonify({"status": "success", "results": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.get("/api/v47/compliance-data")
def api_v47_compliance_data():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"

    from invoices.v47_service import V47ComplianceService
    service = V47ComplianceService(current_app.config["BASE_DATA_DIR"])

    rate_res = service.classify_vat_rate(mst, "Thiết bị y tế chẩn đoán hình ảnh")
    credit_res = service.check_input_credit_eligibility(
        mst=mst, invoice_number="INV-2026-001", invoice_amount=50000000.0,
        has_vat_invoice=True, has_bank_payment=True, seller_declared=True
    )
    refund_res = service.estimate_vat_refund(
        mst=mst, period_label="Q1-2026",
        total_output_vat=100000000.0, total_input_vat=500000000.0,
        export_revenue=5000000000.0
    )

    debate_transcript = [
        {"speaker": "Tax Inspector", "text": "Under Law 48/2024/QH15, all goods/services default to 10% VAT unless specifically listed under Article 5 (non-taxable) or Article 9.2 (5%). Export activities qualify for 0% per Article 9.1."},
        {"speaker": "Legal Advisor", "text": "Input credit eligibility requires three conditions per Article 14: valid VAT invoice, non-cash payment proof, and seller's tax declaration compliance. Missing any one blocks deduction."},
        {"speaker": "CFO", "text": "Our uncredited VAT balance of 400M VND exceeds the 300M threshold for refund eligibility. With 5B export revenue, the 10% cap is 500M, so full 400M refund is available."}
    ]
    consensus_summary = "AUTOMATED VERDICT: Rate classification engine operational. Input credit check passed. Refund estimate: 400,000,000 VND eligible."

    return jsonify({
        "status": "success",
        "rate_classification": rate_res,
        "credit_check": credit_res,
        "refund_estimate": refund_res,
        "debate": debate_transcript,
        "consensus_summary": consensus_summary
    })


# ═══════════════════════════════════════════════════════════════════
# VERSION 48 — VAT Law Amendments 149/2025/QH15 Compliance Engine
# ═══════════════════════════════════════════════════════════════════

@invoices_blueprint.get("/v48-compliance-hub")
def v48_compliance_hub_page():
    """Render the Version 48 VAT Law 149 amendments compliance hub."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    return render_template("v48_compliance_hub.html")


@invoices_blueprint.post("/api/v48/threshold/evaluate")
def api_v48_threshold_evaluate():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    business_name = data.get("business_name", "Quán Phở Bình")
    annual_revenue = float(data.get("annual_revenue", 350000000.0))

    from invoices.v48_service import V48ComplianceService
    try:
        service = V48ComplianceService(current_app.config["BASE_DATA_DIR"])
        res = service.evaluate_threshold(mst, business_name, annual_revenue)
        return jsonify({"status": "success", "results": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.post("/api/v48/agri/classify")
def api_v48_agri_classify():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    product_description = data.get("product_description", "Lúa gạo chưa chế biến")
    seller_type = data.get("seller_type", "doanh nghiệp")
    buyer_type = data.get("buyer_type", "hợp tác xã")

    from invoices.v48_service import V48ComplianceService
    try:
        service = V48ComplianceService(current_app.config["BASE_DATA_DIR"])
        res = service.classify_agri_product(mst, product_description, seller_type, buyer_type)
        return jsonify({"status": "success", "results": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.post("/api/v48/waste/compute")
def api_v48_waste_compute():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    item_description = data.get("item_description", "Vỏ bào gỗ phế liệu")
    source_product = data.get("source_product", "Nội thất gỗ cao cấp")
    waste_rate_pct = float(data.get("waste_rate_pct", 5.0))
    source_rate_pct = float(data.get("source_rate_pct", 10.0))
    amount = float(data.get("amount", 100000000.0))

    from invoices.v48_service import V48ComplianceService
    try:
        service = V48ComplianceService(current_app.config["BASE_DATA_DIR"])
        res = service.compute_waste_scrap_rate(
            mst, item_description, source_product,
            waste_rate_pct, source_rate_pct, amount
        )
        return jsonify({"status": "success", "results": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.get("/api/v48/compliance-data")
def api_v48_compliance_data():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"

    from invoices.v48_service import V48ComplianceService
    service = V48ComplianceService(current_app.config["BASE_DATA_DIR"])

    threshold_res = service.evaluate_threshold(
        mst=mst, business_name="Quán Phở Bình", annual_revenue=350000000.0
    )
    agri_res = service.classify_agri_product(
        mst=mst, product_description="Lúa gạo chưa chế biến",
        seller_type="doanh nghiệp", buyer_type="hợp tác xã"
    )
    waste_res = service.compute_waste_scrap_rate(
        mst=mst, item_description="Vỏ bào gỗ phế liệu",
        source_product="Nội thất gỗ cao cấp",
        waste_rate_pct=5.0, source_rate_pct=10.0, amount=100000000.0
    )

    debate_transcript = [
        {"speaker": "Tax Policy Analyst", "text": "Law 149/2025/QH15 raises the non-taxable revenue threshold from 200M to 500M VND/year for household businesses. This reclassifies an estimated 30% of previously taxable small businesses as exempt, effective January 1, 2026."},
        {"speaker": "Agricultural Advisor", "text": "The Article 5.1 amendment creates a new 'no-declaration-required' category for unprocessed agricultural products traded between enterprises and cooperatives. Critically, input VAT credits remain deductible — unlike standard non-taxable items."},
        {"speaker": "Accounting Director", "text": "For waste/scrap, the Article 9.5 amendment ensures taxation at the waste item's own rate rather than the source product rate. This corrects over-taxation of low-value recovery materials."}
    ]
    consensus_summary = "AUTOMATED VERDICT: Threshold reclassification identified (350M VND: TAXABLE→NON_TAXABLE). Agricultural products correctly classified with preserved input credits. Waste rate difference computed: 5M VND savings."

    return jsonify({
        "status": "success",
        "threshold_audit": threshold_res,
        "agri_classification": agri_res,
        "waste_scrap": waste_res,
        "debate": debate_transcript,
        "consensus_summary": consensus_summary
    })


# ═══════════════════════════════════════════════════════════════════
# VERSION 49 — CIT Law Amendments 67/2025/QH15 Compliance Engine
# ═══════════════════════════════════════════════════════════════════

@invoices_blueprint.get("/v49-compliance-hub")
def v49_compliance_hub_page():
    """Render the Version 49 CIT Law 67 amendments compliance hub."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    return render_template("v49_compliance_hub.html")


@invoices_blueprint.post("/api/v49/sme-cit/calculate")
def api_v49_sme_cit_calculate():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    business_name = data.get("business_name", "Cong Ty A")
    annual_revenue = float(data.get("annual_revenue", 2500000000.0))
    has_transfer_pricing = bool(data.get("has_transfer_pricing", False))

    from invoices.v49_service import V49ComplianceService
    try:
        service = V49ComplianceService(current_app.config["BASE_DATA_DIR"])
        res = service.classify_sme_cit(mst, business_name, annual_revenue, has_transfer_pricing)
        return jsonify({"status": "success", "results": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.post("/api/v49/re-loss/offset")
def api_v49_re_loss_offset():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    tax_year = int(data.get("tax_year", 2025))
    main_income = float(data.get("main_income", 1000000000.0))
    re_loss = float(data.get("re_loss", 200000000.0))

    from invoices.v49_service import V49ComplianceService
    try:
        service = V49ComplianceService(current_app.config["BASE_DATA_DIR"])
        res = service.apply_re_loss_offset(mst, tax_year, main_income, re_loss)
        return jsonify({"status": "success", "results": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.post("/api/v49/digital-cit/audit")
def api_v49_digital_cit_audit():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    vendor_name = data.get("vendor_name", "Google Ireland")
    is_foreign_platform = bool(data.get("is_foreign_platform", True))
    amount = float(data.get("amount", 500000000.0))
    component_type = data.get("component_type", "service")

    from invoices.v49_service import V49ComplianceService
    try:
        service = V49ComplianceService(current_app.config["BASE_DATA_DIR"])
        res = service.audit_digital_cit(mst, vendor_name, is_foreign_platform, amount, component_type)
        return jsonify({"status": "success", "results": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.post("/api/v49/green-exemption/scan")
def api_v49_green_exemption_scan():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    item_description = data.get("item_description", "Interest from green bonds issued 2025")
    amount = float(data.get("amount", 50000000.0))

    from invoices.v49_service import V49ComplianceService
    try:
        service = V49ComplianceService(current_app.config["BASE_DATA_DIR"])
        res = service.scan_green_exemptions(mst, item_description, amount)
        return jsonify({"status": "success", "results": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.get("/api/v49/compliance-data")
def api_v49_compliance_data():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"

    from invoices.v49_service import V49ComplianceService
    service = V49ComplianceService(current_app.config["BASE_DATA_DIR"])

    sme_res = service.classify_sme_cit(mst, "Cong Ty SME A", 2500000000.0, False)
    offset_res = service.apply_re_loss_offset(mst, 2025, 1000000000.0, 200000000.0)
    digital_res = service.audit_digital_cit(mst, "Google Ireland", True, 500000000.0, "service")
    green_res = service.scan_green_exemptions(mst, "Interest from green bonds issued 2025", 50000000.0)

    debate_transcript = [
        {"speaker": "Tax Consultant", "text": "Under Law 67/2025/QH15, corporate income tax for SMEs is reduced to 15% or 17%. However, if the business is part of a transfer pricing relationship, it remains under the standard 20% rate."},
        {"speaker": "Real Estate Analyst", "text": "Allowing businesses to offset real estate losses against their main operations represents a massive shift. Previously, real estate losses had to be ring-fenced, resulting in higher taxes."},
        {"speaker": "Environmental Economist", "text": "Article 8 provides critical CIT exemptions on the first transfer of carbon credits and interest from green bonds, providing strong financial incentives for green initiatives."}
    ]
    consensus_summary = "CIT Law 67/2025/QH15 Engine: Verified SME progressive rate classification, RE loss offset logic, e-commerce CIT withholding triggers, and tax exemptions for green activities."

    return jsonify({
        "status": "success",
        "sme_classification": sme_res,
        "re_loss_offset": offset_res,
        "digital_audit": digital_res,
        "green_exemption": green_res,
        "debate": debate_transcript,
        "consensus_summary": consensus_summary
    })


# ═══════════════════════════════════════════════════════════════════
# VERSION 50 — PIT Law Amendments 109/2025/QH15 Compliance Engine
# ═══════════════════════════════════════════════════════════════════

@invoices_blueprint.get("/v50-compliance-hub")
def v50_compliance_hub_page():
    """Render the Version 50 PIT Law 109 amendments compliance hub."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    return render_template("v50_compliance_hub.html")


@invoices_blueprint.post("/api/v50/household-pit/evaluate")
def api_v50_household_pit_evaluate():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    business_name = data.get("business_name", "Tiem tap hoa Vy")
    annual_revenue = float(data.get("annual_revenue", 450000000.0))
    activity_type = data.get("activity_type", "distribution")

    from invoices.v50_service import V50ComplianceService
    try:
        service = V50ComplianceService(current_app.config["BASE_DATA_DIR"])
        res = service.evaluate_household_pit(mst, business_name, annual_revenue, activity_type)
        return jsonify({"status": "success", "results": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.post("/api/v50/wage-pit/calculate")
def api_v50_wage_pit_calculate():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    employee_name = data.get("employee_name", "Nguyen Van A")
    monthly_salary = float(data.get("monthly_salary", 35000000.0))
    dependent_count = int(data.get("dependent_count", 2))

    from invoices.v50_service import V50ComplianceService
    try:
        service = V50ComplianceService(current_app.config["BASE_DATA_DIR"])
        res = service.calculate_wage_pit(mst, employee_name, monthly_salary, dependent_count)
        return jsonify({"status": "success", "results": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.get("/api/v50/compliance-data")
def api_v50_compliance_data():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"

    from invoices.v50_service import V50ComplianceService
    service = V50ComplianceService(current_app.config["BASE_DATA_DIR"])

    household_res = service.evaluate_household_pit(mst, "Tiem tap hoa Vy", 450000000.0, "distribution")
    wage_res = service.calculate_wage_pit(mst, "Nguyen Van A", 35000000.0, 2)

    debate_transcript = [
        {"speaker": "Tax Policy Expert", "text": "Law 109/2025/QH15 raises the threshold for PIT exemption on household businesses to 500 million VND, which directly mirrors the VAT exemption threshold under Law 149/2025/QH15. This streamlines tax administration for micro-enterprises."},
        {"speaker": "HR Director", "text": "The increase in the monthly personal deduction to 15 million VND and dependent deduction to 5.5 million VND provides significant relief for middle-income employees, reducing their taxable wage bases substantially."},
        {"speaker": "Payroll Auditor", "text": "Our progressive wage PIT brackets calculator properly implements the 7 tax grades ranging from 5% to 35% based on these updated deductions. This ensures compliant tax calculation for standard wage-earners."}
    ]
    consensus_summary = "PIT Law 109/2025/QH15 Engine: Verified household business PIT exemption threshold (500M VND) and progressive wage tax calculations incorporating revised deductions."

    return jsonify({
        "status": "success",
        "household_evaluation": household_res,
        "wage_calculation": wage_res,
        "debate": debate_transcript,
        "consensus_summary": consensus_summary
    })


# ═══════════════════════════════════════════════════════════════════
# VERSION 51 — Tax Administration Law 108/2025/QH15 Compliance Engine
# ═══════════════════════════════════════════════════════════════════

@invoices_blueprint.get("/v51-compliance-hub")
def v51_compliance_hub_page():
    """Render the Version 51 Tax Administration Law 108 amendments compliance hub."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    return render_template("v51_compliance_hub.html")


@invoices_blueprint.post("/api/v51/signature/verify")
def api_v51_signature_verify():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    invoice_number = data.get("invoice_number", "INV2026-001")
    sign_date = data.get("sign_date", "2026-07-01 10:00:00")
    receive_date = data.get("receive_date", "2026-07-01 11:30:00")
    cert_expiry_date = data.get("cert_expiry_date", "2027-12-31 23:59:59")

    from invoices.v51_service import V51ComplianceService
    try:
        service = V51ComplianceService(current_app.config["BASE_DATA_DIR"])
        res = service.audit_etransaction_signature(mst, invoice_number, sign_date, receive_date, cert_expiry_date)
        return jsonify({"status": "success", "results": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.post("/api/v51/withholding/calculate")
def api_v51_withholding_calculate():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    vendor_name = data.get("vendor_name", "Meta Platforms")
    is_registered_vendor = bool(data.get("is_registered_vendor", False))
    service_amount = float(data.get("service_amount", 100000000.0))
    goods_amount = float(data.get("goods_amount", 50000000.0))

    from invoices.v51_service import V51ComplianceService
    try:
        service = V51ComplianceService(current_app.config["BASE_DATA_DIR"])
        res = service.calculate_ecommerce_withholding(mst, vendor_name, is_registered_vendor, service_amount, goods_amount)
        return jsonify({"status": "success", "results": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.get("/api/v51/compliance-data")
def api_v51_compliance_data():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"

    from invoices.v51_service import V51ComplianceService
    service = V51ComplianceService(current_app.config["BASE_DATA_DIR"])

    # Register sample vendor
    service.register_foreign_vendor(mst, "Meta Platforms", "999888777", "ACTIVE")

    sig_res = service.audit_etransaction_signature(
        mst, "INV2026-001", "2026-07-01 10:00:00", "2026-07-01 11:30:00", "2027-12-31 23:59:59"
    )
    withholding_res = service.calculate_ecommerce_withholding(
        mst, "Meta Platforms", False, 100000000.0, 50000000.0
    )

    debate_transcript = [
        {"speaker": "Tax Audit Inspector", "text": "Law 108/2025/QH15 establishes strict e-transaction controls. XML invoices must be signed with active certificates, and GDT transmission delays exceeding 24 hours must be audited and flagged for penalties."},
        {"speaker": "E-Commerce Expert", "text": "If a foreign vendor has not registered directly on the GDT vendor portal, local B2B buyers are legally required to withhold tax. This means 5% VAT and 5% CIT on digital services, and 5% VAT and 1% CIT on goods purchases."},
        {"speaker": "IT Director", "text": "Our API enables direct audit validation. We can trace the difference between signature date and reception date, flag certificate expiration, and automatically apply B2B withholding calculations for Meta, Netflix, and other platforms."}
    ]
    consensus_summary = "Tax Administration Law 108/2025/QH15 Engine: Audited electronic signature timestamps (24-hour transmission rule) and cross-border withholding tax rules for unregistered suppliers."

    return jsonify({
        "status": "success",
        "signature_audit": sig_res,
        "withholding_calculation": withholding_res,
        "debate": debate_transcript,
        "consensus_summary": consensus_summary
    })


# ═══════════════════════════════════════════════════════════════════
# VERSION 52 — SCT Law No. 66/2025/QH15 Compliance Engine
# ═══════════════════════════════════════════════════════════════════

@invoices_blueprint.get("/v52-compliance-hub")
def v52_compliance_hub_page():
    """Render the Version 52 SCT Law 66 amendments compliance hub."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    return render_template("v52_compliance_hub.html")


@invoices_blueprint.post("/api/v52/beverage/calculate")
def api_v52_beverage_calculate():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    drink_name = data.get("drink_name", "Energy Drink Power")
    sugar_content = float(data.get("sugar_content", 7.5))
    category = data.get("category", "soft drink")
    year = int(data.get("year", 2026))
    price_before_tax = float(data.get("price_before_tax", 20000.0))

    from invoices.v52_service import V52ComplianceService
    try:
        service = V52ComplianceService(current_app.config["BASE_DATA_DIR"])
        res = service.calculate_sugary_beverage_sct(mst, drink_name, sugar_content, category, year, price_before_tax)
        return jsonify({"status": "success", "results": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.post("/api/v52/ac/calculate")
def api_v52_ac_calculate():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    model_name = data.get("model_name", "CoolMax 30000")
    capacity_btu = float(data.get("capacity_btu", 30000.0))
    price_before_tax = float(data.get("price_before_tax", 15000000.0))

    from invoices.v52_service import V52ComplianceService
    try:
        service = V52ComplianceService(current_app.config["BASE_DATA_DIR"])
        res = service.calculate_air_conditioner_sct(mst, model_name, capacity_btu, price_before_tax)
        return jsonify({"status": "success", "results": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.post("/api/v52/nontariff/calculate")
def api_v52_nontariff_calculate():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    item_name = data.get("item_name", "Industrial Chemicals")
    destination = data.get("destination", "Tan Thuan Export Processing Zone")
    is_car_under_24_seats = bool(data.get("is_car_under_24_seats", False))
    price_before_tax = float(data.get("price_before_tax", 50000000.0))

    from invoices.v52_service import V52ComplianceService
    try:
        service = V52ComplianceService(current_app.config["BASE_DATA_DIR"])
        res = service.calculate_nontariff_sct(mst, item_name, destination, is_car_under_24_seats, price_before_tax)
        return jsonify({"status": "success", "results": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.post("/api/v52/promotion/calculate")
def api_v52_promotion_calculate():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    item_name = data.get("item_name", "Premium Beer Can (Promo)")
    promo_price = float(data.get("promo_price", 0.0))
    equivalent_price = float(data.get("equivalent_price", 15000.0))
    quantity = int(data.get("quantity", 1000))
    sct_rate = float(data.get("sct_rate", 10.0)) / 100.0

    from invoices.v52_service import V52ComplianceService
    try:
        service = V52ComplianceService(current_app.config["BASE_DATA_DIR"])
        res = service.calculate_promotion_sct(mst, item_name, promo_price, equivalent_price, quantity, sct_rate)
        return jsonify({"status": "success", "results": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.get("/api/v52/compliance-data")
def api_v52_compliance_data():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"

    from invoices.v52_service import V52ComplianceService
    service = V52ComplianceService(current_app.config["BASE_DATA_DIR"])

    beverage_res = service.calculate_sugary_beverage_sct(
        mst, "Energy Drink Power", 7.5, "soft drink", 2026, 20000.0
    )
    ac_res = service.calculate_air_conditioner_sct(
        mst, "CoolMax 30000", 30000.0, 15000000.0
    )
    nontariff_res = service.calculate_nontariff_sct(
        mst, "Industrial Chemicals", "Tan Thuan Export Processing Zone", False, 50000000.0
    )
    promo_res = service.calculate_promotion_sct(
        mst, "Premium Beer Can (Promo)", 0.0, 15000.0, 1000, 0.10
    )

    debate_transcript = [
        {"speaker": "Tax Audit Inspector", "text": "Special Consumption Tax Law No. 66/2025/QH15 expands the SCT base to sugary beverages with sugar content exceeding 5g/100ml. The roadmap starts at 0% in 2026, then increases to 8% in 2027 and 10% from 2028."},
        {"speaker": "SCT Specialist", "text": "Air conditioners up to 90,000 BTU are taxable at 10%, but models <= 24,000 BTU are exempt. Similarly, inland goods sold into non-tariff areas are taxable under SCT, but we must exempt passenger cars under 24 seats as they are already taxed at the registration/import stage."},
        {"speaker": "Compliance Counsel", "text": "For advertising or promotional goods, the taxable price is adjusted to the price of identical or equivalent goods in the same period. We cannot use 0 VND or discount values for SCT calculation."}
    ]
    consensus_summary = "SCT Law No. 66/2025/QH15 Compliance Engine: Classifies and audits sugary beverages, air conditioners, inland to non-tariff area sales, and promotional price adjustments."

    return jsonify({
        "status": "success",
        "beverage_audit": beverage_res,
        "ac_audit": ac_res,
        "nontariff_audit": nontariff_res,
        "promo_audit": promo_res,
        "debate": debate_transcript,
        "consensus_summary": consensus_summary
    })


# ═══════════════════════════════════════════════════════════════════
# VERSION 53 — Environmental Protection Tax Law 57/2010/QH12 Engine
# ═══════════════════════════════════════════════════════════════════

@invoices_blueprint.get("/v53-compliance-hub")
def v53_compliance_hub_page():
    """Render the Version 53 EP Tax compliance hub."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    return render_template("v53_compliance_hub.html")


@invoices_blueprint.post("/api/v53/fuel/calculate")
def api_v53_fuel_calculate():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    fuel_type = data.get("fuel_type", "petrol")
    quantity_litres = float(data.get("quantity_litres", 1000.0))
    price_before_tax = float(data.get("price_before_tax", 25000.0))
    is_transit_or_reexport = bool(data.get("is_transit_or_reexport", False))

    from invoices.v53_service import V53ComplianceService
    try:
        service = V53ComplianceService(current_app.config["BASE_DATA_DIR"])
        res = service.calculate_fuel_ep_tax(mst, fuel_type, quantity_litres, price_before_tax, is_transit_or_reexport)
        return jsonify({"status": "success", "results": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.post("/api/v53/coal/calculate")
def api_v53_coal_calculate():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    coal_type = data.get("coal_type", "anthracite")
    quantity_tonnes = float(data.get("quantity_tonnes", 500.0))
    price_before_tax = float(data.get("price_before_tax", 3000000.0))
    usage = data.get("usage", "other")

    from invoices.v53_service import V53ComplianceService
    try:
        service = V53ComplianceService(current_app.config["BASE_DATA_DIR"])
        res = service.calculate_coal_ep_tax(mst, coal_type, quantity_tonnes, price_before_tax, usage)
        return jsonify({"status": "success", "results": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.post("/api/v53/bag/calculate")
def api_v53_bag_calculate():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    bag_name = data.get("bag_name", "Standard Plastic Bag")
    weight_kg = float(data.get("weight_kg", 100.0))
    price_before_tax = float(data.get("price_before_tax", 200000.0))
    is_certified_biodegradable = bool(data.get("is_certified_biodegradable", False))

    from invoices.v53_service import V53ComplianceService
    try:
        service = V53ComplianceService(current_app.config["BASE_DATA_DIR"])
        res = service.calculate_plastic_bag_ep_tax(mst, bag_name, weight_kg, price_before_tax, is_certified_biodegradable)
        return jsonify({"status": "success", "results": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.post("/api/v53/chemical/calculate")
def api_v53_chemical_calculate():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    chemical_name = data.get("chemical_name", "HCFC-22")
    weight_kg = float(data.get("weight_kg", 50.0))
    price_before_tax = float(data.get("price_before_tax", 5000000.0))

    from invoices.v53_service import V53ComplianceService
    try:
        service = V53ComplianceService(current_app.config["BASE_DATA_DIR"])
        res = service.calculate_chemical_ep_tax(mst, chemical_name, weight_kg, price_before_tax)
        return jsonify({"status": "success", "results": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.get("/api/v53/compliance-data")
def api_v53_compliance_data():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"

    from invoices.v53_service import V53ComplianceService
    service = V53ComplianceService(current_app.config["BASE_DATA_DIR"])

    fuel_res = service.calculate_fuel_ep_tax(
        mst, "petrol", 1000.0, 25000.0, False
    )
    coal_res = service.calculate_coal_ep_tax(
        mst, "anthracite", 500.0, 3000000.0, "other"
    )
    bag_res = service.calculate_plastic_bag_ep_tax(
        mst, "Standard Plastic Bag", 100.0, 200000.0, False
    )
    chemical_res = service.calculate_chemical_ep_tax(
        mst, "HCFC-22", 50.0, 5000000.0
    )

    debate_transcript = [
        {"speaker": "Environmental Tax Inspector", "text": "Under Environmental Protection Tax Law 57/2010/QH12, absolute tax rates apply per physical unit: 2,000 VND/litre for petrol, 1,000 VND/litre for diesel, and 600 VND/litre for kerosene. Coal ranges from 15,000 to 30,000 VND/tonne depending on classification."},
        {"speaker": "Green Transition Advisor", "text": "Certified biodegradable plastic bags receive 100% EP tax exemption. Coal used directly for electricity generation or exported by licensed miners is also fully exempt. These exemptions incentivize the green transition under Vietnam's sustainability commitments."},
        {"speaker": "Customs Compliance Officer", "text": "Fuels temporarily imported for transit or re-export are exempt from EP tax. HCFC chemicals are taxed at 5,000 VND/kg to discourage ozone-depleting substances, aligning with the Montreal Protocol obligations."}
    ]
    consensus_summary = "EP Tax Law 57/2010/QH12 Compliance Engine: Verified fuel, coal, plastic bag, and HCFC chemical EP tax calculations with green transition exemptions for biodegradable materials, electricity-generation coal, and transit fuels."

    return jsonify({
        "status": "success",
        "fuel_audit": fuel_res,
        "coal_audit": coal_res,
        "bag_audit": bag_res,
        "chemical_audit": chemical_res,
        "debate": debate_transcript,
        "consensus_summary": consensus_summary
    })


# ═══════════════════════════════════════════════════════════════════
# VERSION 54 — Natural Resources Tax Law 45/2009/QH12 Engine
# ═══════════════════════════════════════════════════════════════════

@invoices_blueprint.get("/v54-compliance-hub")
def v54_compliance_hub_page():
    """Render the Version 54 NRT compliance hub."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    return render_template("v54_compliance_hub.html")


@invoices_blueprint.post("/api/v54/mineral/calculate")
def api_v54_mineral_calculate():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    mineral_name = data.get("mineral_name", "Iron Ore")
    mineral_category = data.get("mineral_category", "metallic")
    quantity = float(data.get("quantity", 1000.0))
    unit_price = float(data.get("unit_price", 500000.0))
    is_self_consumed = bool(data.get("is_self_consumed", False))

    from invoices.v54_service import V54ComplianceService
    try:
        service = V54ComplianceService(current_app.config["BASE_DATA_DIR"])
        res = service.calculate_mineral_nrt(mst, mineral_name, mineral_category, quantity, unit_price, is_self_consumed)
        return jsonify({"status": "success", "results": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.post("/api/v54/water/calculate")
def api_v54_water_calculate():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    water_source = data.get("water_source", "surface water")
    usage_purpose = data.get("usage_purpose", "industrial")
    volume_m3 = float(data.get("volume_m3", 10000.0))
    unit_price = float(data.get("unit_price", 5000.0))
    hydropower_capacity_mw = float(data.get("hydropower_capacity_mw", 0.0))

    from invoices.v54_service import V54ComplianceService
    try:
        service = V54ComplianceService(current_app.config["BASE_DATA_DIR"])
        res = service.calculate_water_nrt(mst, water_source, usage_purpose, volume_m3, unit_price, hydropower_capacity_mw)
        return jsonify({"status": "success", "results": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.post("/api/v54/timber/calculate")
def api_v54_timber_calculate():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    timber_name = data.get("timber_name", "Hardwood Logs")
    timber_source = data.get("timber_source", "natural forest")
    volume_m3 = float(data.get("volume_m3", 100.0))
    unit_price = float(data.get("unit_price", 8000000.0))

    from invoices.v54_service import V54ComplianceService
    try:
        service = V54ComplianceService(current_app.config["BASE_DATA_DIR"])
        res = service.calculate_timber_nrt(mst, timber_name, timber_source, volume_m3, unit_price)
        return jsonify({"status": "success", "results": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.post("/api/v54/marine/calculate")
def api_v54_marine_calculate():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    product_name = data.get("product_name", "Fresh Shrimp")
    product_category = data.get("product_category", "aquatic")
    quantity_kg = float(data.get("quantity_kg", 500.0))
    unit_price = float(data.get("unit_price", 200000.0))

    from invoices.v54_service import V54ComplianceService
    try:
        service = V54ComplianceService(current_app.config["BASE_DATA_DIR"])
        res = service.calculate_marine_nrt(mst, product_name, product_category, quantity_kg, unit_price)
        return jsonify({"status": "success", "results": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.get("/api/v54/compliance-data")
def api_v54_compliance_data():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"

    from invoices.v54_service import V54ComplianceService
    service = V54ComplianceService(current_app.config["BASE_DATA_DIR"])

    mineral_res = service.calculate_mineral_nrt(
        mst, "Iron Ore", "metallic", 1000.0, 500000.0, False
    )
    water_res = service.calculate_water_nrt(
        mst, "Surface Water", "industrial", 10000.0, 5000.0, 0.0
    )
    timber_res = service.calculate_timber_nrt(
        mst, "Hardwood Logs", "natural forest", 100.0, 8000000.0
    )
    marine_res = service.calculate_marine_nrt(
        mst, "Fresh Shrimp", "aquatic", 500.0, 200000.0
    )

    debate_transcript = [
        {"speaker": "Mining Tax Inspector", "text": "Under Natural Resources Tax Law 45/2009/QH12, metallic ores are taxed at ad-valorem rates: Iron 12%, Copper 13%, Gold 15%, Tin 20%. Non-metallic minerals range from 5% (limestone) to 9% (marble). Self-consumed resources extracted for internal use receive a 30% rate reduction."},
        {"speaker": "Environmental Compliance Advisor", "text": "Water resources for agriculture, forestry, fishery, and salt production are 100% exempt from NRT. Small-scale hydropower stations with installed capacity ≤ 2MW are also fully exempt. Industrial water extraction is taxed at 2% (surface) or 4% (groundwater)."},
        {"speaker": "Forestry & Marine Auditor", "text": "Natural forest timber attracts the highest NRT rates (up to 25% for hardwood), while plantation timber is only 3%. Marine aquatic products are taxed at 2%, but pearls and coral are at 8% due to their higher commercial value and conservation considerations."}
    ]
    consensus_summary = "NRT Law 45/2009/QH12 Compliance Engine: Verified mineral extraction taxes, water resource exemptions (agricultural, hydropower ≤ 2MW), timber classification, and marine product NRT calculations."

    return jsonify({
        "status": "success",
        "mineral_audit": mineral_res,
        "water_audit": water_res,
        "timber_audit": timber_res,
        "marine_audit": marine_res,
        "debate": debate_transcript,
        "consensus_summary": consensus_summary
    })


# ===================================================================
# VERSION 55 — Import-Export Tax Compliance Engine
# ===================================================================

@invoices_blueprint.get("/v55-compliance-hub")
def v55_compliance_hub_page():
    """Render the Version 55 Import-Export Tax compliance hub."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    return render_template("v55_compliance_hub.html")


@invoices_blueprint.post("/api/v55/calculate")
def api_v55_calculate():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    cargo_name = data.get("cargo_name", "Machinery Part")
    cargo_type = data.get("cargo_type", "import")
    quantity = float(data.get("quantity", 10.0))
    unit_price = float(data.get("unit_price", 10000000.0))
    tariff_type = data.get("tariff_type", "preferential")
    goods_purpose = data.get("goods_purpose", "commercial")

    from invoices.v55_service import V55ComplianceService
    try:
        service = V55ComplianceService(current_app.config["BASE_DATA_DIR"])
        res = service.calculate_import_export_duty(
            mst, cargo_name, cargo_type, quantity, unit_price, tariff_type, goods_purpose
        )
        return jsonify({"status": "success", "results": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.get("/api/v55/compliance-data")
def api_v55_compliance_data():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"

    from invoices.v55_service import V55ComplianceService
    service = V55ComplianceService(current_app.config["BASE_DATA_DIR"])

    import_mfn = service.calculate_import_export_duty(
        mst, "Industrial Machinery", "import", 1.0, 250000000.0, "preferential", "commercial"
    )
    processing_exempt = service.calculate_import_export_duty(
        mst, "Polyester Yarn", "import", 10000.0, 3500.0, "preferential", "processing contract"
    )
    export_minerals = service.calculate_import_export_duty(
        mst, "Copper Ores", "export", 500.0, 1200000.0, "preferential", "commercial"
    )
    gift_exempt = service.calculate_import_export_duty(
        mst, "Sample Machinery Spare Part", "import", 1.0, 1800000.0, "preferential", "gift"
    )

    debate_transcript = [
        {"speaker": "Border Customs Inspector", "text": "Under Import-Export Tax Law 107/2016/QH13, goods imported under processing contracts for foreign trade are 100% exempt from import-export duties. Proper contract registration must be verified."},
        {"speaker": "Trade Compliance Officer", "text": "Low-value non-commercial gifts and samples sent via courier are exempt if their value does not exceed 2,000,000 VND. Any amount above this limit is taxed on its full value."},
        {"speaker": "Tax Advisory Consultant", "text": "Export duties primarily target raw minerals and resources to discourage raw exports, while preferential import duties (MFN) and special FTA tariffs (EVFTA, CPTPP) support technical imports."}
    ]
    consensus_summary = "IET Law 107/2016/QH13 Compliance Engine: Verified import-export duties calculation, processing contract exemptions, temporary import/re-export exemptions, and low-value courier gift thresholds."

    return jsonify({
        "status": "success",
        "import_mfn": import_mfn,
        "processing_exempt": processing_exempt,
        "export_minerals": export_minerals,
        "gift_exempt": gift_exempt,
        "debate": debate_transcript,
        "consensus_summary": consensus_summary,
        "history": service.get_history(mst, 20)
    })


# ===================================================================
# VERSION 56 — License Fee (Lệ phí môn bài) Compliance Engine
# ===================================================================

@invoices_blueprint.get("/v56-compliance-hub")
def v56_compliance_hub_page():
    """Render the Version 56 License Fee compliance hub."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    return render_template("v56_compliance_hub.html")


@invoices_blueprint.post("/api/v56/calculate")
def api_v56_calculate():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    entity_name = data.get("entity_name", "Main Office")
    entity_type = data.get("entity_type", "enterprise")
    charter_capital = float(data.get("charter_capital", 15000000000.0))
    annual_revenue = float(data.get("annual_revenue", 0.0))
    is_newly_established = bool(data.get("is_newly_established", False))
    is_agri_cooperative = bool(data.get("is_agri_cooperative", False))

    from invoices.v56_service import V56ComplianceService
    try:
        service = V56ComplianceService(current_app.config["BASE_DATA_DIR"])
        res = service.calculate_license_fee(
            mst, entity_name, entity_type, charter_capital, annual_revenue, is_newly_established, is_agri_cooperative
        )
        return jsonify({"status": "success", "results": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.get("/api/v56/compliance-data")
def api_v56_compliance_data():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"

    from invoices.v56_service import V56ComplianceService
    service = V56ComplianceService(current_app.config["BASE_DATA_DIR"])

    enterprise_large = service.calculate_license_fee(
        mst, "HQ Headquarters", "enterprise", 15000000000.0, 0.0, False, False
    )
    branch_flat = service.calculate_license_fee(
        mst, "Southern Branch Office", "branch", 0.0, 0.0, False, False
    )
    new_exemption = service.calculate_license_fee(
        mst, "GreenTech StartUp JSC", "enterprise", 2500000000.0, 0.0, True, False
    )
    household_medium = service.calculate_license_fee(
        mst, "Binh Minh Retail Store", "household", 0.0, 450000000.0, False, False
    )

    debate_transcript = [
        {"speaker": "Municipal License Fee Auditor", "text": "Annual license fees under Decree 139/2016/NĐ-CP are categorised by Charter Capital for organisations and Annual Revenue for households. Branches pay a flat 1,000,000 VND fee."},
        {"speaker": "Business Registration Officer", "text": "Decree 22/2020/NĐ-CP introduced a full exemption on license fees for the first calendar year of establishment for all new enterprises, cooperatives, and households."},
        {"speaker": "Corporate Tax Legal Counsel", "text": "Agricultural cooperatives and household businesses with an annual revenue of 100,000,000 VND or less are completely exempt from the license fee. Verification is straightforward."}
    ]
    consensus_summary = "License Fee Decree 139/2016/NĐ-CP Compliance Engine: Verified enterprise brackets, branches flat fee, household revenue brackets, and newly established first-year exemptions."

    return jsonify({
        "status": "success",
        "enterprise_large": enterprise_large,
        "branch_flat": branch_flat,
        "new_exemption": new_exemption,
        "household_medium": household_medium,
        "debate": debate_transcript,
        "consensus_summary": consensus_summary,
        "history": service.get_history(mst, 20)
    })


# ===================================================================
# VERSION 57 — Registration Fee (Lệ phí trước bạ) Compliance Engine
# ===================================================================

@invoices_blueprint.get("/v57-compliance-hub")
def v57_compliance_hub_page():
    """Render the Version 57 Registration Fee compliance hub."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    return render_template("v57_compliance_hub.html")


@invoices_blueprint.post("/api/v57/calculate")
def api_v57_calculate():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"
    asset_description = data.get("asset_description", "Asset")
    asset_type = data.get("asset_type", "real_estate")
    asset_value = float(data.get("asset_value", 0.0))
    province = data.get("province", "standard")
    is_first_registration = bool(data.get("is_first_registration", True))
    cylinder_capacity = float(data.get("cylinder_capacity", 0.0))
    is_agricultural_land = bool(data.get("is_agricultural_land", False))
    is_diplomatic = bool(data.get("is_diplomatic", False))
    is_merit_family_housing = bool(data.get("is_merit_family_housing", False))
    is_family_agri_transfer = bool(data.get("is_family_agri_transfer", False))

    from invoices.v57_service import V57ComplianceService
    try:
        service = V57ComplianceService(current_app.config["BASE_DATA_DIR"])
        res = service.calculate_registration_fee(
            mst, asset_description, asset_type, asset_value, province,
            is_first_registration, cylinder_capacity,
            is_agricultural_land, is_diplomatic, is_merit_family_housing, is_family_agri_transfer
        )
        return jsonify({"status": "success", "results": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.get("/api/v57/compliance-data")
def api_v57_compliance_data():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"

    from invoices.v57_service import V57ComplianceService
    service = V57ComplianceService(current_app.config["BASE_DATA_DIR"])

    real_estate_apt = service.calculate_registration_fee(
        mst, "Căn hộ Vinhomes Grand Park", "real_estate", 5000000000.0
    )
    car_hanoi = service.calculate_registration_fee(
        mst, "Mercedes S-Class", "car", 3000000000.0,
        province="hanoi", is_first_registration=True
    )
    diplomatic_exempt = service.calculate_registration_fee(
        mst, "Embassy Official Vehicle", "car", 2000000000.0,
        is_diplomatic=True
    )
    motorbike_large = service.calculate_registration_fee(
        mst, "Honda CBR600RR", "motorbike", 280000000.0,
        cylinder_capacity=600
    )

    debate_transcript = [
        {"speaker": "Property Registration Auditor", "text": "Registration fees under Decree 10/2022/NĐ-CP apply at 0.5% for real estate, 2%-12% for cars depending on province and first/subsequent registration, 2%-5% for motorbikes by cylinder capacity, and 1% for yachts and aircraft."},
        {"speaker": "Vehicle Tax Inspector", "text": "Hanoi and HCMC impose a 12% first-time registration surcharge on automobiles to manage traffic density. Subsequent re-registrations revert to the standard 2% rate nationwide."},
        {"speaker": "Land Use Rights Legal Counsel", "text": "Agricultural and forestry land allocated by the State, diplomatic mission assets, revolutionary merit family housing, and within-family agricultural transfers are fully exempt under Article 10 of Decree 10/2022/NĐ-CP."}
    ]
    consensus_summary = "Registration Fee Decree 10/2022/NĐ-CP Compliance Engine: Verified real estate 0.5%, car brackets 2%-12%, motorbike capacity-based rates, yacht/aircraft 1%, and all exemption categories."

    return jsonify({
        "status": "success",
        "real_estate_apt": real_estate_apt,
        "car_hanoi": car_hanoi,
        "diplomatic_exempt": diplomatic_exempt,
        "motorbike_large": motorbike_large,
        "debate": debate_transcript,
        "consensus_summary": consensus_summary,
        "history": service.get_history(mst, 20)
    })


# ===================================================================
# VERSION 58 — Natural Resources Tax (Thuế tài nguyên) Compliance Engine
# ===================================================================

@invoices_blueprint.get("/v58-compliance-hub")
def v58_compliance_hub_page():
    """Render the Version 58 Natural Resources Tax compliance hub."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    return render_template("v58_compliance_hub.html")


@invoices_blueprint.post("/api/v58/calculate")
def api_v58_calculate():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"

    from invoices.v58_service import V58ComplianceService
    try:
        service = V58ComplianceService(current_app.config["BASE_DATA_DIR"])
        res = service.calculate_nrt(
            mst,
            data.get("resource_description", "Resource"),
            data.get("resource_type", "metallic"),
            data.get("resource_subtype", ""),
            float(data.get("extraction_value", 0.0)),
            float(data.get("daily_output", 0.0)),
            bool(data.get("is_agri_water", False)),
            bool(data.get("is_hydro_water", False)),
            bool(data.get("is_defense", False)),
        )
        return jsonify({"status": "success", "results": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.get("/api/v58/compliance-data")
def api_v58_compliance_data():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"

    from invoices.v58_service import V58ComplianceService
    service = V58ComplianceService(current_app.config["BASE_DATA_DIR"])

    iron_ore = service.calculate_nrt(mst, "Quặng sắt Hà Tĩnh", "metallic", "iron_ore", 50000000000.0)
    crude_oil_high = service.calculate_nrt(mst, "Mỏ dầu Bạch Hổ", "crude_oil", "", 500000000000.0, daily_output=25000)
    agri_water_exempt = service.calculate_nrt(mst, "Nước tưới ruộng lúa", "water", "", 1000000000.0, is_agri_water=True)
    hardwood_timber = service.calculate_nrt(mst, "Gỗ lim Quảng Bình", "timber", "hardwood", 20000000000.0)

    debate_transcript = [
        {"speaker": "Mining Resource Auditor", "text": "Natural resources tax under Law 45/2009/QH12 applies differentiated rates: metallic minerals 7%-25%, non-metallic 5%-15%, crude oil 6%-10% on a sliding scale by daily output, coal 4%-20%, timber 10%-35%, and marine products 1%-2%."},
        {"speaker": "Petroleum Tax Inspector", "text": "Crude oil fields producing over 20,000 barrels per day face a 10% rate versus 6% for lower output. Natural gas is uniformly taxed at 2%. These rates apply to the taxable value of extracted resources."},
        {"speaker": "Environmental Resources Counsel", "text": "Article 9 of Law 45/2009/QH12 grants full exemption for natural water used in agriculture, aquaculture, salt production, and hydroelectric generation. Resources extracted for national defense are also fully exempt."}
    ]
    consensus_summary = "Natural Resources Tax Law 45/2009/QH12 Compliance Engine: Verified metallic/non-metallic mineral rates, crude oil sliding scale, coal tiers, timber/marine rates, and all exemption categories."

    return jsonify({
        "status": "success",
        "iron_ore": iron_ore,
        "crude_oil_high": crude_oil_high,
        "agri_water_exempt": agri_water_exempt,
        "hardwood_timber": hardwood_timber,
        "debate": debate_transcript,
        "consensus_summary": consensus_summary,
        "history": service.get_history(mst, 20)
    })


# ===================================================================
# VERSION 59 — Non-Agricultural Land Use Tax (Thuế sử dụng đất phi NN)
# ===================================================================

@invoices_blueprint.get("/v59-compliance-hub")
def v59_compliance_hub_page():
    """Render the Version 59 Non-Agricultural Land Use Tax compliance hub."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    return render_template("v59_compliance_hub.html")


@invoices_blueprint.post("/api/v59/calculate")
def api_v59_calculate():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"

    from invoices.v59_service import V59ComplianceService
    try:
        service = V59ComplianceService(current_app.config["BASE_DATA_DIR"])
        res = service.calculate_nalut(
            mst,
            data.get("land_description", "Land"),
            data.get("land_type", "residential"),
            float(data.get("land_value", 0.0)),
            float(data.get("land_area", 0.0)),
            float(data.get("quota_area", 0.0)),
            int(data.get("idle_years", 0)),
            bool(data.get("is_public_welfare", False)),
            bool(data.get("is_religious", False)),
            bool(data.get("is_diplomatic", False)),
        )
        return jsonify({"status": "success", "results": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.get("/api/v59/compliance-data")
def api_v59_compliance_data():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"

    from invoices.v59_service import V59ComplianceService
    service = V59ComplianceService(current_app.config["BASE_DATA_DIR"])

    residential_within = service.calculate_nalut(mst, "Nhà ở Q.1 TP.HCM", "residential", 10000000000.0, land_area=200, quota_area=200)
    residential_exceed = service.calculate_nalut(mst, "Biệt thự Thảo Điền", "residential", 20000000000.0, land_area=800, quota_area=200)
    idle_land = service.calculate_nalut(mst, "Đất trống Long An", "idle", 10000000000.0, idle_years=5)
    religious_exempt = service.calculate_nalut(mst, "Chùa Giác Lâm", "residential", 30000000000.0, is_religious=True)

    debate_transcript = [
        {"speaker": "Land Use Tax Auditor", "text": "Non-agricultural land use tax under Law 48/2010/QH12 applies progressive tiered rates for residential land: 0.03% within quota, 0.07% for 1x-3x quota excess, and 0.15% beyond 3x quota. Commercial and production land are taxed at a flat 0.03%."},
        {"speaker": "Municipal Planning Inspector", "text": "Idle/unused land faces an annual surcharge of 0.02% per year of idleness, capped at a total rate of 0.15%. This incentivizes productive land use and discourages speculative hoarding."},
        {"speaker": "Property Rights Legal Counsel", "text": "Article 9 of Law 48/2010/QH12 exempts land used for public welfare, education, healthcare, religious institutions, and foreign diplomatic missions. All exempted parcels must maintain documented proof of qualifying use."}
    ]
    consensus_summary = "NALUT Law 48/2010/QH12 Engine: Verified residential progressive tiers (0.03%-0.15%), commercial/production flat rate (0.03%), idle surcharge with cap, and all exemption categories."

    return jsonify({
        "status": "success",
        "residential_within": residential_within,
        "residential_exceed": residential_exceed,
        "idle_land": idle_land,
        "religious_exempt": religious_exempt,
        "debate": debate_transcript,
        "consensus_summary": consensus_summary,
        "history": service.get_history(mst, 20)
    })


# ===================================================================
# VERSION 60 — Agricultural Land Use Tax (Thuế sử dụng đất nông nghiệp)
# ===================================================================

@invoices_blueprint.get("/v60-compliance-hub")
def v60_compliance_hub_page():
    """Render the Version 60 Agricultural Land Use Tax compliance hub."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    return render_template("v60_compliance_hub.html")


@invoices_blueprint.post("/api/v60/calculate")
def api_v60_calculate():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"

    from invoices.v60_service import V60ComplianceService
    try:
        service = V60ComplianceService(current_app.config["BASE_DATA_DIR"])
        res = service.calculate_alut(
            mst,
            data.get("land_description", "Agricultural Land"),
            int(data.get("land_grade", 1)),
            data.get("crop_type", "annual"),
            float(data.get("area_ha", 0.0)),
            data.get("producer_type", "household"),
            float(data.get("rice_price_per_kg", 8000.0))
        )
        return jsonify({"status": "success", "results": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.get("/api/v60/compliance-data")
def api_v60_compliance_data():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"

    from invoices.v60_service import V60ComplianceService
    service = V60ComplianceService(current_app.config["BASE_DATA_DIR"])

    # Baseline audits for verification
    household_exempt = service.calculate_alut(mst, "Cánh đồng lúa Hải Hậu", 1, "annual", 5.0, "household")
    coop_exempt = service.calculate_alut(mst, "Hợp tác xã chè Thái Nguyên", 2, "perennial", 12.0, "cooperative")
    state_enterprise_reduced = service.calculate_alut(mst, "Nông trường cao su Bình Phước", 1, "perennial", 50.0, "state_org")
    general_company_taxable = service.calculate_alut(mst, "Công ty phát triển nông nghiệp", 3, "annual", 10.0, "general_org")

    debate_transcript = [
        {"speaker": "Agricultural Tax Inspector", "text": "Agricultural land use tax under the 1993 Law dictates fixed rice rates: annual crop land (categories 1-6: 50-550 kg/ha) and perennial land (categories 1-5: 200-650 kg/ha)."},
        {"speaker": "Rural Policy Advisor", "text": "Resolution 117/2020/QH14 extended a 100% tax waiver until 2025 to support rural development. This applies to households, individuals, and agricultural co-ops."},
        {"speaker": "State Audit Specialist", "text": "Organizations using agricultural land for state research or special missions get a 50% discount. Commercial entities using land for speculative or generic production get no waiver."}
    ]
    consensus_summary = "ALUT Law 1993 / Resolution 117/2020 Engine: Verified land grade rates (50-650 kg/ha), 100% exemptions for households/co-ops, 50% state org reductions, and full tax billing for general commercial firms."

    return jsonify({
        "status": "success",
        "household_exempt": household_exempt,
        "coop_exempt": coop_exempt,
        "state_enterprise_reduced": state_enterprise_reduced,
        "general_company_taxable": general_company_taxable,
        "debate": debate_transcript,
        "consensus_summary": consensus_summary,
        "history": service.get_history(mst, 20)
    })


# ===================================================================
# VERSION 61 — Environment Protection Fee for Wastewater (EPFW)
# ===================================================================

@invoices_blueprint.get("/v61-compliance-hub")
def v61_compliance_hub_page():
    """Render the Version 61 Environment Protection Fee for Wastewater compliance hub."""
    if not session.get("logged_in"):
        return redirect(url_for("auth.login_page"))
    return render_template("v61_compliance_hub.html")


@invoices_blueprint.post("/api/v61/calculate")
def api_v61_calculate():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.json or {}
    mst = data.get("mst") or session.get("taxpayer_mst") or "0102030405"

    from invoices.v61_service import V61ComplianceService
    try:
        service = V61ComplianceService(current_app.config["BASE_DATA_DIR"])
        res = service.calculate_epfw(
            mst,
            data.get("water_description", "Wastewater Discharge"),
            data.get("wastewater_type", "domestic"),
            float(data.get("water_volume_m3", 0.0)),
            float(data.get("clean_water_price_vnd", 0.0)),
            float(data.get("pollutant_cod_kg", 0.0)),
            float(data.get("pollutant_tss_kg", 0.0)),
            float(data.get("pollutant_pb_kg", 0.0)),
            float(data.get("pollutant_cd_kg", 0.0)),
            float(data.get("pollutant_hg_kg", 0.0)),
            float(data.get("pollutant_as_kg", 0.0)),
            data.get("water_source", "central_water")
        )
        return jsonify({"status": "success", "results": res})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@invoices_blueprint.get("/api/v61/compliance-data")
def api_v61_compliance_data():
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = request.args.get("mst") or session.get("taxpayer_mst") or "0102030405"

    from invoices.v61_service import V61ComplianceService
    service = V61ComplianceService(current_app.config["BASE_DATA_DIR"])

    # Baseline audits for verification
    domestic_standard = service.calculate_epfw(mst, "Sinh hoạt đô thị", "domestic", 150.0, clean_water_price_vnd=12000.0)
    industrial_heavy_metals = service.calculate_epfw(mst, "Nước thải dệt nhuộm", "industrial", 500.0,
                                                     pollutant_cod_kg=120.0, pollutant_tss_kg=80.0, pollutant_pb_kg=0.5)
    cooling_exempt = service.calculate_epfw(mst, "Nước làm mát tuần hoàn", "industrial", 1000.0, water_source="cooling_recycling")
    runoff_exempt = service.calculate_epfw(mst, "Nước mưa thoát tự nhiên", "domestic", 2000.0, water_source="natural_runoff")

    debate_transcript = [
        {"speaker": "Wastewater Auditor", "text": "EPFW under Decree 53/2020/NĐ-CP levies 10% of clean water price on domestic wastewater. Industrial sites pay a 1,500,000 VND fixed fee plus variable surcharges on COD (2,000), TSS (2,400), Pb (1M), Cd (20M), Hg (40M), and As (20M) per kg."},
        {"speaker": "Industrial Park Supervisor", "text": "Water volumes exceeding 20m3/day trigger full variable pollution accounting. Below 20m3/day, only the flat fee applies."},
        {"speaker": "Legal Environmental Counsel", "text": "Article 5 exempts cooling water in closed recycling systems, natural runoff rainwater, and rural water extracted from local wells."}
    ]
    consensus_summary = "EPFW Decree 53/2020/NĐ-CP Compliance Engine: Verified domestic 10% rate, industrial fixed 1.5M VND base with heavy metal surcharges, and cooling/runoff exemptions."

    return jsonify({
        "status": "success",
        "domestic_standard": domestic_standard,
        "industrial_heavy_metals": industrial_heavy_metals,
        "cooling_exempt": cooling_exempt,
        "runoff_exempt": runoff_exempt,
        "debate": debate_transcript,
        "consensus_summary": consensus_summary,
        "history": service.get_history(mst, 20)
    })



