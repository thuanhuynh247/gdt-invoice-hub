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

    return jsonify(
        {
            "total_spend": total_spend,
            "total_tax": total_tax,
            "active_count": active_count,
            "cancelled_count": cancelled_count,
            "top_vendors": top_vendors,
            "tax_breakdown": tax_breakdown,
        }
    )




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
    """Extract and return corporate business partners and their statistics."""

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
        "webhook_secret": payload.get("webhook_secret", "")
    })

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
        {letter_text.replace('\n', '<br>')}
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
        {letter_text.replace('\n', '<br>')}
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
        return jsonify([s.to_dict() for s in sessions])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@invoices_blueprint.post("/api/ai/chat/sessions")
def api_create_chat_session():
    """Create a new chat session."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized
    from invoices.models import AIChatSession
    import uuid
    from datetime import datetime
    try:
        data = request.get_json() or {}
        title = data.get("title", "Cuộc hội thoại mới")
        session_id = str(uuid.uuid4())
        new_session = AIChatSession(
            id=session_id,
            title=title,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        db.session.add(new_session)
        db.session.commit()
        return jsonify(new_session.to_dict()), 201
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
        if session.title == "Cuộc hội thoại mới":
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

        return jsonify({
            "user_message": user_msg.to_dict(),
            "assistant_message": assistant_msg.to_dict(),
            "session_title": session.title
        })

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
        return jsonify({"success": True})
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
    Return outstanding sold invoices classified into aging buckets.

    Buckets: 1-30 / 31-60 / 61-90 / >90 days overdue.
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
    try:
        as_of = _date.fromisoformat(as_of_str) if as_of_str else _date.today()
    except ValueError:
        return jsonify({"error": "Định dạng as_of không hợp lệ. Dùng YYYY-MM-DD."}), 400

    try:
        from extensions import db
        from invoices.models import Invoice as _Inv

        # Fetch all outstanding sold invoices
        invoices = (
            _Inv.query
            .filter(
                _Inv.invoice_type == "sold",
                _Inv.is_cancelled == False,
                _Inv.paid_date == None,
            )
            .all()
        )

        # Build empty bucket structure
        buckets = [
            {
                "label": label,
                "min_days": mn,
                "max_days": mx,
                "count": 0,
                "total_amount": 0.0,
                "invoices": [],
            }
            for label, mn, mx in _AGING_BUCKETS
        ]

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
            if age_days <= 0:
                # Not yet overdue — skip (not-yet-due bucket is a future enhancement)
                continue

            # Assign to first matching bucket
            for bucket, (label, mn, mx) in zip(buckets, _AGING_BUCKETS):
                if age_days >= mn and (mx is None or age_days <= mx):
                    bucket["count"] += 1
                    bucket["total_amount"] += inv.amount_before_tax or 0
                    bucket["invoices"].append({
                        "id": inv.id,
                        "date": inv.date,
                        "due_date": inv.due_date,
                        "buyer_name": inv.buyer_name or "",
                        "buyer_mst": inv.buyer_mst or "",
                        "amount_before_tax": inv.amount_before_tax,
                        "age_days": age_days,
                    })
                    break

        total_outstanding = sum(b["total_amount"] for b in buckets)
        total_count = sum(b["count"] for b in buckets)

        return jsonify({
            "success": True,
            "as_of": as_of.isoformat(),
            "total_outstanding": total_outstanding,
            "total_count": total_count,
            "buckets": buckets,
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

        if mst == "all" or not mst:
            session["active_taxpayer_mst"] = None
            return jsonify({"success": True, "active_taxpayer_mst": None})

        from invoices.models import TaxpayerProfile
        profile = db.session.get(TaxpayerProfile, mst)
        if not profile:
            return jsonify({"error": f"Không tìm thấy hồ sơ mã số thuế {mst}."}), 404

        session["active_taxpayer_mst"] = mst
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



