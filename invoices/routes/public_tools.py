"""Public (ungated) free tools routes — no login required.

Provides high-value standalone calculators for SEO traffic and lead generation.
These endpoints intentionally bypass session authentication so search engines
and anonymous visitors can use them.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, render_template, request

public_tools_bp = Blueprint("public_tools", __name__, url_prefix="/tools")


# ────────────────────────────────────────────────────────────────
# Pages
# ────────────────────────────────────────────────────────────────

@public_tools_bp.get("/")
def tools_index():
    """Landing page listing all free tools."""
    return render_template("tools/index.html")


@public_tools_bp.get("/tax-penalty-calculator")
def tax_penalty_calculator_page():
    """Render the standalone Tax Penalty & Interest Calculator."""
    return render_template("tools/tax_penalty_calculator.html")


# ────────────────────────────────────────────────────────────────
# API (public, rate-limit–friendly)
# ────────────────────────────────────────────────────────────────

@public_tools_bp.post("/api/penalty-calculate")
def api_penalty_calculate():
    """Calculate tax penalty & late-payment interest (Decree 125/2020).

    Accepts JSON:
      - underpaid_tax:  float (VND)
      - due_date:       str   (YYYY-MM-DD)
      - payment_date:   str   (YYYY-MM-DD)
      - evasion_multiplier: float (0.0 = underdeclaration, 1.0-3.0 = evasion)
      - has_mitigating_factors: bool
    """
    data = request.get_json(silent=True) or {}

    underpaid_tax = float(data.get("underpaid_tax", 0))
    due_date = data.get("due_date", "")
    payment_date = data.get("payment_date", "")
    evasion_multiplier = float(data.get("evasion_multiplier", 0.0))
    has_mitigating = bool(data.get("has_mitigating_factors", False))

    if underpaid_tax <= 0:
        return jsonify({"error": "Số thuế thiếu phải lớn hơn 0."}), 400
    if not due_date or not payment_date:
        return jsonify({"error": "Vui lòng nhập đầy đủ ngày hạn nộp và ngày thực nộp."}), 400

    from invoices.tax_audit_service import calculate_audit_penalties

    try:
        result = calculate_audit_penalties(
            underpaid_tax=underpaid_tax,
            due_date=due_date,
            payment_date=payment_date,
            evasion_multiplier=evasion_multiplier,
            has_mitigating_factors=has_mitigating,
        )
        return jsonify({"status": "success", "calculation": result})
    except ValueError as exc:
        return jsonify({"error": f"Dữ liệu không hợp lệ: {exc}"}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@public_tools_bp.get("/fct-calculator")
def fct_calculator_page():
    """Render the Foreign Contractor Tax (FCT) Calculator page."""
    return render_template("tools/fct_calculator.html")


@public_tools_bp.post("/api/fct-calculate")
def api_fct_calculate():
    """Calculate Foreign Contractor Tax (Circular 103/2014/TT-BTC).
    
    Accepts JSON:
      - contract_value: float (VND)
      - contract_type:  str   ("net" or "gross")
      - industry_type:  str   ("services", "goods_with_services", "construction_with_materials", etc.)
    """
    data = request.get_json(silent=True) or {}
    
    try:
        contract_value = float(data.get("contract_value", 0))
    except (ValueError, TypeError):
        return jsonify({"error": "Giá trị hợp đồng không hợp lệ."}), 400
        
    contract_type = data.get("contract_type", "gross")
    industry_type = data.get("industry_type", "services")
    
    if contract_value <= 0:
        return jsonify({"error": "Giá trị hợp đồng phải lớn hơn 0."}), 400
        
    if contract_type not in ("net", "gross"):
        return jsonify({"error": "Loại hợp đồng không hợp lệ (phải là Net hoặc Gross)."}), 400
        
    from invoices.tax_audit_service import calculate_fct_tax
    
    try:
        result = calculate_fct_tax(
            contract_value=contract_value,
            contract_type=contract_type,
            industry_type=industry_type
        )
        return jsonify({"status": "success", "calculation": result})
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

