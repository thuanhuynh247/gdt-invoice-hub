"""VBA & Excel Integration API Gateway Route.

Provides local API endpoints for Excel VBA macros to:
1. Query active taxpayers.
2. Solve vector SVG captchas offline.
3. Synchronize invoices from Excel sheets to the webapp DB with real-time audit logs.
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from flask import request, jsonify, current_app
from extensions import db
from invoices.routes.shared import invoices_blueprint
from invoices.models import Invoice, LineItem, TaxpayerProfile, SystemConfig
from auth.captcha_solver import solve_captcha_from_svg, captcha_analytics
from invoices.invoice_validator import validate_invoice

def check_vba_auth() -> bool:
    """Helper to authenticate VBA requests using a configured token or default fallback."""
    # Localhost requests are implicitly trusted or token-authenticated
    token = request.headers.get("X-VBA-Token") or request.args.get("vba_token")
    
    # Load token from SystemConfig
    cfg = db.session.get(SystemConfig, "vba_gateway_token")
    if not cfg:
        # Auto-initialize with a default secure token if missing
        cfg = SystemConfig(key="vba_gateway_token", value="vba-secret-token-123")
        db.session.add(cfg)
        db.session.commit()
        
    expected_token = cfg.value
    return token == expected_token


@invoices_blueprint.get("/api/v1/vba/status")
def api_vba_status():
    """VBA Gateway status & health statistics."""
    if not check_vba_auth():
        return jsonify({"error": "Unauthorized VBA Token"}), 401
        
    total_taxpayers = TaxpayerProfile.query.count()
    total_invoices = Invoice.query.count()
    c_stats = captcha_analytics.get_stats()
    
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "total_taxpayers": total_taxpayers,
        "total_invoices": total_invoices,
        "captcha_stats": c_stats
    })


@invoices_blueprint.get("/api/v1/vba/taxpayers")
def api_vba_taxpayers():
    """Retrieve all registered taxpayer profiles (MST + Name)."""
    if not check_vba_auth():
        return jsonify({"error": "Unauthorized VBA Token"}), 401
        
    taxpayers = TaxpayerProfile.query.all()
    return jsonify([
        {
            "mst": tp.mst,
            "company_name": tp.company_name,
            "is_active": tp.is_active
        }
        for tp in taxpayers
    ])


@invoices_blueprint.post("/api/v1/vba/solve-captcha")
def api_vba_solve_captcha():
    """Solve SVG captcha sent by Excel VBA and return the solution."""
    if not check_vba_auth():
        return jsonify({"error": "Unauthorized VBA Token"}), 401
        
    data = request.json or {}
    svg_content = data.get("svg_content") or data.get("content")
    captcha_key = data.get("captcha_key") or data.get("ckey") or data.get("key")
    
    if not svg_content:
        return jsonify({"error": "Missing svg_content in payload"}), 400
        
    start_time = time.time()
    try:
        solution = solve_captcha_from_svg(svg_content, captcha_key)
        latency = int((time.time() - start_time) * 1000)
        
        return jsonify({
            "success": True,
            "solution": solution,
            "solved_text": solution,
            "latency_ms": latency
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@invoices_blueprint.post("/api/v1/vba/sync-invoices")
def api_vba_sync_invoices():
    """Synchronize a batch of invoices (with line items) from Excel VBA into the DB.
    
    Runs automated integrity audits immediately upon import.
    """
    if not check_vba_auth():
        return jsonify({"error": "Unauthorized VBA Token"}), 401
        
    data = request.json or {}
    invoices_list = data.get("invoices")
    taxpayer_mst = data.get("taxpayer_mst")
    
    if not invoices_list:
        return jsonify({"error": "Missing invoices list in payload"}), 400
    if not taxpayer_mst:
        return jsonify({"error": "Missing taxpayer_mst in payload"}), 400
        
    # Verify taxpayer profile exists or create a placeholder
    taxpayer = db.session.get(TaxpayerProfile, taxpayer_mst)
    if not taxpayer:
        taxpayer = TaxpayerProfile(
            mst=taxpayer_mst,
            company_name=f"Placeholder Company ({taxpayer_mst})",
            gdt_username="",
            gdt_password_encrypted="",
            is_active=True,
            created_at=datetime.now().isoformat()
        )
        db.session.add(taxpayer)
        db.session.commit()

    created_count = 0
    updated_count = 0
    failed_count = 0
    errors = []

    for item in invoices_list:
        try:
            seller_mst = item.get("seller_mst", "").strip()
            symbol = item.get("symbol", "").strip()
            number = str(item.get("number", "")).strip()
            
            if not (seller_mst and symbol and number):
                failed_count += 1
                errors.append(f"Missing primary identifiers (seller_mst, symbol, number) for invoice: {item}")
                continue
                
            # Compute unique primary key: seller_mst-symbol-number
            invoice_id = f"{seller_mst}-{symbol}-{number}".lower()
            
            # Check if invoice exists
            inv = db.session.get(Invoice, invoice_id)
            is_new = False
            if not inv:
                inv = Invoice(id=invoice_id)
                is_new = True
                db.session.add(inv)
                
            # Bind fields
            inv.seller_mst = seller_mst
            inv.symbol = symbol
            inv.number = number
            inv.taxpayer_mst = taxpayer_mst
            
            inv.filename = item.get("filename", inv.filename)
            inv.invoice_type = item.get("invoice_type", inv.invoice_type or "GTGT")
            inv.template_code = item.get("template_code", inv.template_code)
            inv.date = item.get("date", inv.date)
            inv.currency = item.get("currency", inv.currency or "VND")
            inv.seller_name = item.get("seller_name", inv.seller_name)
            inv.seller_address = item.get("seller_address", inv.seller_address)
            inv.seller_phone = item.get("seller_phone", inv.seller_phone)
            inv.buyer_name = item.get("buyer_name", inv.buyer_name)
            inv.buyer_mst = item.get("buyer_mst", inv.buyer_mst)
            inv.buyer_address = item.get("buyer_address", inv.buyer_address)
            
            inv.amount_before_tax = float(item.get("amount_before_tax", 0.0))
            inv.tax_amount = float(item.get("tax_amount", 0.0))
            inv.total_amount = float(item.get("total_amount", 0.0))
            
            inv.has_signature = bool(item.get("has_signature", False))
            inv.signing_date = item.get("signing_date", inv.signing_date)
            inv.payment_method = item.get("payment_method", inv.payment_method)
            
            inv.is_cancelled = bool(item.get("is_cancelled", False))
            inv.cancellation_date = item.get("cancellation_date", inv.cancellation_date)
            inv.cancellation_reason = item.get("cancellation_reason", inv.cancellation_reason)
            inv.invoice_status = item.get("invoice_status", inv.invoice_status)
            inv.imported_at = item.get("imported_at", datetime.now().isoformat())
            inv.updated_at = datetime.now().isoformat()
            
            # VBA parity / deep parser fields
            inv.mccqt = item.get("mccqt", inv.mccqt)
            inv.msttcgp = item.get("msttcgp", inv.msttcgp)
            inv.lookup_code = item.get("lookup_code", inv.lookup_code)
            inv.lookup_url = item.get("lookup_url", inv.lookup_url)
            inv.exchange_rate = float(item.get("exchange_rate", 1.0))
            inv.tax_breakdown_json = item.get("tax_breakdown_json", inv.tax_breakdown_json)
            inv.fees_breakdown_json = item.get("fees_breakdown_json", inv.fees_breakdown_json)
            
            # Sync line items if provided
            if "items" in item:
                # Remove existing line items
                LineItem.query.filter_by(invoice_id=inv.id).delete()
                
                for line in item["items"]:
                    li = LineItem(
                        invoice_id=inv.id,
                        item_name=line.get("item_name", "").strip(),
                        unit=line.get("unit"),
                        quantity=float(line.get("quantity", 0.0)),
                        unit_price=float(line.get("unit_price", 0.0)),
                        amount_before_tax=float(line.get("amount_before_tax", 0.0)),
                        tax_rate=line.get("tax_rate", "0%"),
                        tax_amount=float(line.get("tax_amount", 0.0)),
                        discount_rate=float(line.get("discount_rate", 0.0)),
                        discount_amount=float(line.get("discount_amount", 0.0)),
                        amount_after_tax=float(line.get("amount_after_tax", 0.0))
                    )
                    db.session.add(li)
            
            # Run compliance validator audits immediately
            alerts = validate_invoice(inv)
            inv.warnings_json = json.dumps([a["detail"] for a in alerts], ensure_ascii=False)
            
            db.session.flush()
            
            if is_new:
                created_count += 1
            else:
                updated_count += 1
                
        except Exception as ex:
            failed_count += 1
            errors.append(f"Failed to sync invoice ({item.get('seller_mst')}-{item.get('symbol')}-{item.get('number')}): {str(ex)}")

    db.session.commit()
    
    return jsonify({
        "success": True,
        "summary": {
            "created": created_count,
            "updated": updated_count,
            "failed": failed_count
        },
        "errors": errors
    })
