from __future__ import annotations
from flask import Blueprint, jsonify, request, session
from extensions import db
from auth.decorators import roles_required
from invoices.routes.shared import invoices_blueprint
from invoices.routes.helpers import _ensure_logged_in

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

    mst = session.get("active_taxpayer_mst") or session.get("taxpayer_mst") or session.get("tax_code") or "0102030405"

    try:
        content = file.read().decode("utf-8")
        from invoices.reconciliation_service import ReconciliationEngine
        engine = ReconciliationEngine()
        
        # 1. Parse and save
        transactions = engine.process_csv(content, mst)
        
        # 2. Run matching engine
        results = engine.run_matching(mst)
        
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
        
    mst = session.get("active_taxpayer_mst") or session.get("taxpayer_mst") or session.get("tax_code") or "0102030405"
    from invoices.models import BankTransaction
    txns = BankTransaction.query.filter_by(taxpayer_mst=mst).order_by(BankTransaction.transaction_date.desc()).all()
    
    return jsonify({
        "status": "success",
        "transactions": [t.to_dict() for t in txns]
    })

@invoices_blueprint.get("/api/invoices/unmatched")
@roles_required("admin", "auditor", "viewer")
def api_invoices_unmatched():
    """Get unmatched purchase invoices for manual matching select dropdown."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = session.get("active_taxpayer_mst") or session.get("taxpayer_mst") or session.get("tax_code") or "0102030405"
    from invoices.models import Invoice, BankTransaction
    
    # Get all purchase invoices for this taxpayer
    purchase_invoices = Invoice.query.filter_by(
        taxpayer_mst=mst,
        invoice_type="purchase"
    ).all()
    
    # Filter out those already matched in bank transactions
    matched_invoice_ids = [
        r[0] for r in db.session.query(BankTransaction.matched_invoice_id)
        .filter(BankTransaction.taxpayer_mst == mst, BankTransaction.matched_invoice_id != None)
        .all()
    ]
    
    unmatched_invoices = [
        {
            "id": inv.id,
            "number": inv.number,
            "date": inv.date,
            "seller_name": inv.seller_name,
            "total_amount": inv.total_amount
        }
        for inv in purchase_invoices if inv.id not in matched_invoice_ids
    ]
    
    return jsonify({
        "status": "success",
        "invoices": unmatched_invoices
    })

@invoices_blueprint.post("/api/invoices/reconcile/auto")
@roles_required("admin", "auditor")
def api_reconcile_auto():
    """Trigger automated matching run for existing transactions and invoices."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    mst = session.get("active_taxpayer_mst") or session.get("taxpayer_mst") or session.get("tax_code") or "0102030405"
    try:
        from invoices.reconciliation_service import ReconciliationEngine
        engine = ReconciliationEngine()
        results = engine.run_matching(mst)
        return jsonify({
            "status": "success",
            "message": "Automated matching engine executed successfully.",
            "results": results
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@invoices_blueprint.post("/api/invoices/reconcile/manual")
@roles_required("admin", "auditor")
def api_reconcile_manual():
    """Manually match a bank transaction to a purchase invoice."""
    unauthorized = _ensure_logged_in()
    if unauthorized:
        return unauthorized

    data = request.get_json() or {}
    transaction_id = data.get("transaction_id")
    invoice_id = data.get("invoice_id")

    if not transaction_id or not invoice_id:
        return jsonify({"status": "error", "message": "Missing transaction_id or invoice_id"}), 400

    from invoices.models import BankTransaction, Invoice
    from extensions import db

    try:
        txn = BankTransaction.query.get(transaction_id)
        inv = Invoice.query.get(invoice_id)

        if not txn:
            return jsonify({"status": "error", "message": "Transaction not found"}), 404
        if not inv:
            return jsonify({"status": "error", "message": "Invoice not found"}), 404

        mst = session.get("active_taxpayer_mst") or session.get("taxpayer_mst") or session.get("tax_code") or "0102030405"
        if txn.taxpayer_mst != mst or inv.taxpayer_mst != mst:
            return jsonify({"status": "error", "message": "Unauthorized access to these records"}), 403

        # Update matching status
        txn.matched_invoice_id = inv.id
        txn.status = "matched"
        txn.confidence_score = 1.0
        db.session.add(txn)
        
        # Remove warnings of cash_payment_risk type if present
        from invoices.models import AIAuditResult
        warning = AIAuditResult.query.filter_by(invoice_id=inv.id, warning_type="cash_payment_risk").first()
        if warning:
            db.session.delete(warning)

        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Invoice and transaction matched successfully."
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
