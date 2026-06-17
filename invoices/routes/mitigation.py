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
