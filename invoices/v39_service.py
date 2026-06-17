"""
Version 39.0.0 Services: VAS 17 Deferred Tax Engine, Cash-Flow Stress Sandbox & Supplier Risk Network.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, date
from sqlalchemy import and_
from extensions import db
from invoices.models import Invoice, Partner, FixedAsset, DepreciationEntry, SystemConfig, BlacklistedMST, TaxpayerProfile
from invoices.supplier_risk_service import calculate_supplier_risk
from invoices.mst_service import check_mst_status, STATUS_ACTIVE, STATUS_SUSPENDED, STATUS_CLOSED, STATUS_NOT_FOUND

class DeferredTaxService:
    @staticmethod
    def calculate_vas17_deferred_tax(taxpayer_mst: str, year: int) -> dict:
        """
        US-510: Computes temporary and permanent differences under VAS 17.
        - Depreciation differences: Accounting useful life vs TT45 limits.
        - Provisions: Bad debt provisions or inventory write-downs.
        - Accrued Expenses: Accrued operating costs without invoice.
        """
        db.session.expire_all()
        
        # 1. Depreciation temporary differences
        assets = FixedAsset.query.all()
        depr_differences = []
        total_accounting_depr = 0.0
        total_tax_depr = 0.0
        
        for asset in assets:
            # Check compliance to see if accounting useful life is less than TT45 allowed minimum
            cat = asset.category.lower()
            life = asset.useful_life_months
            
            # Default allowed ranges under TT45
            min_m, max_m = 36, 600
            if "máy tính" in cat or "thiết bị" in cat or "computers" in cat or "quản lý" in cat:
                min_m, max_m = 36, 60
            elif "xe" in cat or "phương tiện" in cat or "vehicles" in cat:
                min_m, max_m = 72, 120
            elif "nhà" in cat or "xưởng" in cat or "buildings" in cat:
                min_m, max_m = 300, 600
                
            # If accounting life is less than minimum allowed, tax depreciation is restricted/deferred
            acc_monthly = asset.original_cost / asset.useful_life_months
            # Tax depreciation uses the minimum useful life to determine allowed monthly expense
            tax_monthly = asset.original_cost / max(min_m, asset.useful_life_months)
            
            diff_monthly = acc_monthly - tax_monthly
            
            # Annual values
            acc_annual = acc_monthly * 12
            tax_annual = tax_monthly * 12
            diff_annual = diff_monthly * 12
            
            total_accounting_depr += acc_annual
            total_tax_depr += tax_annual
            
            if diff_annual > 0:
                depr_differences.append({
                    "asset_code": asset.asset_code,
                    "asset_name": asset.name,
                    "accounting_annual": round(acc_annual, 2),
                    "tax_annual": round(tax_annual, 2),
                    "temporary_difference": round(diff_annual, 2),
                    "explanation": f"Khấu hao kế toán nhanh hơn thời gian tối thiểu của TT45 ({min_m} tháng)."
                })

        # 2. Provisions & Accruals temporary differences (simulated from custom inputs or database)
        # Fetch or mock provisions (e.g. provision for bad debt not yet realized)
        bad_debt_provision = 150000000.0  # 150M VND
        inventory_write_down = 80000000.0  # 80M VND
        accrued_opex = 50000000.0          # 50M VND
        
        # Deductible temporary differences: provision is added back to tax profit now, deductible when realized
        deductible_differences = [
            {
                "type": "Provision for Bad Debts",
                "amount": bad_debt_provision,
                "explanation": "Dự phòng nợ phải thu khó đòi trích lập chưa đủ hồ sơ chứng minh theo Thông tư 48."
            },
            {
                "type": "Inventory Obsolescence",
                "amount": inventory_write_down,
                "explanation": "Trích lập dự phòng giảm giá hàng tồn kho chưa hoàn tất thủ tục tiêu hủy."
            },
            {
                "type": "Accrued Expenses",
                "amount": accrued_opex,
                "explanation": "Chi phí trích trước lương tháng 13 hoặc chi phí dịch vụ chưa có hóa đơn."
            }
        ]
        
        # 3. Permanent differences (e.g., late payment penalties, excessive interest under Decree 132, fines)
        # Scan invoices for tax penalty keywords or disallowed cash payments
        invoices = Invoice.query.filter_by(taxpayer_mst=taxpayer_mst).all()
        disallowed_expenses = 0.0
        for inv in invoices:
            if inv.buyer_mst == taxpayer_mst and not inv.is_cancelled:
                pay_method = (inv.payment_method or "").upper()
                is_cash = any(x in pay_method for x in ["TM", "TIỀN MẶT", "CASH"])
                if is_cash and inv.total_amount >= 20000000.0:
                    disallowed_expenses += inv.total_amount
                    
        # Add a mock permanent difference (fines, non-deductible expenses)
        late_fees = 15000000.0 # 15M VND tax fine
        permanent_differences = [
            {
                "type": "Late Payment Fines & Administrative Penalties",
                "amount": late_fees,
                "explanation": "Tiền phạt vi phạm hành chính, phạt chậm nộp thuế không được trừ khi tính thuế TNDN."
            },
            {
                "type": "Disallowed Cash Payments >= 20M VND",
                "amount": disallowed_expenses,
                "explanation": "Hóa đơn mua vào trên 20 triệu thanh toán bằng tiền mặt vi phạm quy định khấu trừ thuế."
            }
        ]
        
        # Calculations
        tax_depr_diff = sum(d["temporary_difference"] for d in depr_differences)
        total_deductible_diff = sum(d["amount"] for d in deductible_differences)
        total_permanent_diff = sum(d["amount"] for d in permanent_differences)
        
        # Accounting Profit baseline estimation
        accounting_profit = 2000000000.0 # 2B VND baseline
        
        # Taxable income = Accounting profit + Permanent differences + Temporary differences
        taxable_income = accounting_profit + total_permanent_diff + tax_depr_diff + total_deductible_diff
        
        # Deferred Tax computations (20% corporate tax rate)
        # Tax depreciation differences and deductible provisions create Deferred Tax Assets (Tài sản thuế hoãn lại)
        # because we pay more tax now, but will deduct it in the future
        deferred_tax_assets = (tax_depr_diff + total_deductible_diff) * 0.20
        deferred_tax_liabilities = 0.0  # None in this model
        
        net_deferred_tax = deferred_tax_assets - deferred_tax_liabilities
        
        # Save or fetch previous year deferred tax asset to find movement
        # Let's say previous DTA was 80,000,000 VND
        prev_dta = 80000000.0
        dta_movement = deferred_tax_assets - prev_dta
        
        return {
            "taxpayer_mst": taxpayer_mst,
            "year": year,
            "accounting_profit": accounting_profit,
            "taxable_income": taxable_income,
            "depreciation_differences": depr_differences,
            "deductible_differences": deductible_differences,
            "permanent_differences": permanent_differences,
            "deferred_tax_assets": round(deferred_tax_assets, 2),
            "deferred_tax_liabilities": round(deferred_tax_liabilities, 2),
            "net_deferred_tax": round(net_deferred_tax, 2),
            "dta_movement": round(dta_movement, 2),
            "tax_rate": 0.20
        }

    @staticmethod
    def generate_journal_entries(taxpayer_mst: str, year: int) -> list[dict]:
        """
        US-511: Generates suggested double-entry journal entries for VAS 17 adjustments.
        """
        data = DeferredTaxService.calculate_vas17_deferred_tax(taxpayer_mst, year)
        movement = data["dta_movement"]
        
        entries = []
        if movement > 0:
            entries.append({
                "account_debit": "243",
                "account_credit": "8212",
                "amount": abs(movement),
                "debit_description": "Tài sản thuế thu nhập doanh nghiệp hoãn lại",
                "credit_description": "Chi phí thuế thu nhập doanh nghiệp hoãn lại",
                "explanation": f"Ghi nhận tăng tài sản thuế thu nhập hoãn lại năm {year} do phát sinh chênh lệch tạm thời được khấu trừ."
            })
        elif movement < 0:
            entries.append({
                "account_debit": "8212",
                "account_credit": "243",
                "amount": abs(movement),
                "debit_description": "Chi phí thuế thu nhập doanh nghiệp hoãn lại",
                "credit_description": "Tài sản thuế thu nhập doanh nghiệp hoãn lại",
                "explanation": f"Hoàn nhập tài sản thuế thu nhập hoãn lại năm {year} khi chênh lệch tạm thời được khấu trừ hoàn nhập."
            })
            
        return entries


class CashFlowStressService:
    @staticmethod
    def run_cash_stress_simulation(taxpayer_mst: str, dso_days: int = 0, dpo_days: int = 0) -> dict:
        """
        US-512: Simulates cash runway and burn rates under DSO and DPO stress adjustments.
        """
        # Seed parameters
        current_cash = 2500000000.0  # 2.5B VND base cash balance
        monthly_opex = 450000000.0   # 450M VND base monthly fixed expenses (payroll, rent, utilities)
        
        # Fetch invoices
        invoices = Invoice.query.filter(
            and_(
                Invoice.taxpayer_mst == taxpayer_mst,
                Invoice.is_cancelled == False
            )
        ).all()
        
        # Calculate receivables and payables
        receivables = []
        payables = []
        
        for inv in invoices:
            # Parse invoice date
            try:
                inv_date = datetime.strptime(inv.date[:10], "%Y-%m-%d")
            except Exception:
                inv_date = datetime.now()
                
            due_date = inv_date + timedelta(days=30)
            
            # Receivables: we are the seller
            if inv.seller_mst == taxpayer_mst:
                receivables.append({
                    "amount": inv.total_amount,
                    "original_due": due_date,
                    "adjusted_due": due_date + timedelta(days=dso_days)
                })
            # Payables: we are the buyer
            elif inv.buyer_mst == taxpayer_mst:
                payables.append({
                    "amount": inv.total_amount,
                    "original_due": due_date,
                    "adjusted_due": due_date + timedelta(days=dpo_days)
                })
                
        # Projections in a 90-day horizon
        horizon_end = datetime.now() + timedelta(days=90)
        projected_inflows = sum(r["amount"] for r in receivables if r["adjusted_due"] <= horizon_end)
        projected_outflows = sum(p["amount"] for p in payables if p["adjusted_due"] <= horizon_end)
        
        # Net monthly cash balance flow calculations
        net_monthly_inflow = (projected_inflows / 3.0) - (projected_outflows / 3.0) - monthly_opex
        
        # Runway calculations
        if net_monthly_inflow >= 0:
            runway_months = 12.0  # Stable positive cash runway, capped at 12 for dashboard gauge
            risk_level = "Emerald"
            warning_msg = "Dòng tiền ổn định. Doanh nghiệp có thặng dư tài chính tích cực."
        else:
            burn_rate = abs(net_monthly_inflow)
            runway_months = round(current_cash / burn_rate, 1)
            
            if runway_months < 3.0:
                risk_level = "Red"
                warning_msg = f"CẢNH BÁO BÁO ĐỘNG: Thời gian duy trì dòng tiền dưới {runway_months} tháng. Cần cải thiện thu hồi nợ (DSO) lập tức."
            elif runway_months <= 6.0:
                risk_level = "Amber"
                warning_msg = f"RỦI RO TRUNG BÌNH: Thời gian duy trì dòng tiền đạt {runway_months} tháng. Đề xuất kéo dài thời gian trả nợ nhà cung cấp (DPO)."
            else:
                risk_level = "Emerald"
                warning_msg = "Thời gian duy trì dòng tiền an toàn (> 6 tháng)."
                
        # Generate SVG Gauge paths
        # SVG Circular Gauge calculations: radius = 40, circumference = 2 * pi * r = 251.2
        # Stroke-dashoffset represents percent filled. Max runway is 12 months.
        percent = min(1.0, runway_months / 12.0)
        stroke_dasharray = 251.2
        stroke_dashoffset = stroke_dasharray * (1 - percent)
        
        gauge_svg = (
            f'<svg class="w-40 h-40" viewBox="0 0 100 100">\n'
            f'  <circle cx="50" cy="50" r="40" stroke="rgba(255,255,255,0.05)" stroke-width="8" fill="none" />\n'
            f'  <circle cx="50" cy="50" r="40" stroke="{ "var(--emerald)" if risk_level == "Emerald" else ("var(--amber)" if risk_level == "Amber" else "var(--red)") }" stroke-width="8" fill="none"\n'
            f'          stroke-dasharray="{stroke_dasharray}" stroke-dashoffset="{stroke_dashoffset}" stroke-linecap="round" transform="rotate(-90 50 50)" />\n'
            f'  <text x="50%" y="45%" dominant-baseline="middle" text-anchor="middle" class="fill-white font-bold text-lg">{runway_months}M</text>\n'
            f'  <text x="50%" y="65%" dominant-baseline="middle" text-anchor="middle" class="fill-gray text-xs">Runway</text>\n'
            f'</svg>'
        )
        
        return {
            "current_cash": current_cash,
            "monthly_opex": monthly_opex,
            "projected_inflows": round(projected_inflows, 2),
            "projected_outflows": round(projected_outflows, 2),
            "net_monthly_inflow": round(net_monthly_inflow, 2),
            "runway_months": runway_months,
            "risk_level": risk_level,
            "warning_message": warning_msg,
            "gauge_svg": gauge_svg,
            "dso_days": dso_days,
            "dpo_days": dpo_days
        }


class SupplierRiskNetworkService:
    @staticmethod
    def build_supplier_network_graph(taxpayer_mst: str) -> dict:
        """
        US-513: Compiles supplier scores and returns network graph nodes and links.
        """
        db.session.expire_all()
        
        # Get taxpayer details
        taxpayer = TaxpayerProfile.query.filter_by(mst=taxpayer_mst).first()
        company_name = taxpayer.company_name if taxpayer else "Doanh nghiệp của bạn"
        
        # Initialize nodes with taxpayer profile at center
        nodes = [
            {
                "id": taxpayer_mst,
                "name": company_name,
                "type": "center",
                "value": 0.0,
                "risk_score": 100,
                "trust_rating": "Center",
                "gdt_status": STATUS_ACTIVE
            }
        ]
        links = []
        
        # Fetch unique suppliers
        invoices = Invoice.query.filter(
            and_(
                Invoice.taxpayer_mst == taxpayer_mst,
                Invoice.is_cancelled == False
            )
        ).all()
        
        supplier_msts = set(inv.seller_mst for inv in invoices if inv.seller_mst)
        
        for idx, mst in enumerate(supplier_msts):
            # Calculate supplier risk details
            risk_data = calculate_supplier_risk(mst, taxpayer_mst)
            
            nodes.append({
                "id": mst,
                "name": risk_data["supplier_name"],
                "type": "supplier",
                "value": risk_data["total_value"],
                "risk_score": risk_data["risk_score"],
                "trust_rating": risk_data["trust_rating"],
                "gdt_status": risk_data["gdt_status"]
            })
            
            links.append({
                "source": taxpayer_mst,
                "target": mst,
                "value": risk_data["total_value"],
                "count": risk_data["invoice_count"]
            })
            
        # Draw SVG network graph coords (zero-dependency visual layout mapping)
        # Coordinates map outwards in circular fashion
        import math
        center_x, center_y = 300, 200
        radius = 150
        
        svg_elements = []
        
        # Add links first (so lines render behind nodes)
        for link in links:
            svg_elements.append(f'<!-- Link {link["source"]} to {link["target"]} -->')
            
        # Add center node
        svg_elements.append(
            f'<circle cx="{center_x}" cy="{center_y}" r="22" class="fill-blue stroke-white stroke-2 cursor-pointer transition-all hover:scale-110" />\n'
            f'<text x="{center_x}" y="{center_y + 35}" text-anchor="middle" class="fill-white font-bold text-xs">{company_name[:12]}...</text>'
        )
        
        # Add peripheral supplier nodes
        num_suppliers = len(supplier_msts)
        for i, node in enumerate(nodes[1:]):
            angle = (2 * math.pi / num_suppliers) * i if num_suppliers > 0 else 0
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            
            # Determine risk color representation
            rating = node["trust_rating"]
            color = "var(--emerald)" if rating in ("A++", "A", "B") else ("var(--amber)" if rating == "C" else "var(--red)")
            
            svg_elements.append(
                f'<line x1="{center_x}" y1="{center_y}" x2="{x}" y2="{y}" stroke="rgba(255,255,255,0.15)" stroke-width="2" />\n'
                f'<circle cx="{x}" cy="{y}" r="15" fill="{color}" class="stroke-white stroke-2 cursor-pointer transition-all hover:scale-125 hover:stroke-blue" onclick="openSupplierAudit(\'{node["id"]}\')" />\n'
                f'<text x="{x}" y="{y + 25}" text-anchor="middle" class="fill-gray text-[10px]">{node["name"][:10]}...</text>'
            )
            
        svg_graph = (
            f'<svg viewBox="0 0 600 400" class="w-full h-full">\n'
            f'  {"".join(svg_elements)}\n'
            f'</svg>'
        )
        
        return {
            "nodes": nodes,
            "links": links,
            "svg_graph": svg_graph
        }

    @staticmethod
    def simulate_gdt_scraper_check(seller_mst: str) -> dict:
        """
        US-514: Simulates checking partner tax status against high-risk taxpayer database (scraping simulator).
        """
        gdt_info = check_mst_status(seller_mst)
        status = gdt_info.get("status") or STATUS_ACTIVE
        
        # Check if blacklisted in database
        blacklisted = BlacklistedMST.query.filter_by(mst=seller_mst).first()
        if blacklisted:
            status = "BLACKLISTED"
            
        # Update local catalog cache
        partner = Partner.query.filter_by(mst=seller_mst).first()
        if partner:
            partner.mst_status = status
            partner.mst_last_checked = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            db.session.commit()
            
        return {
            "mst": seller_mst,
            "taxpayer_name": partner.name if partner else "Không rõ",
            "gdt_status": status,
            "last_checked": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "compliance_message": f"MST {seller_mst} hoạt động bình thường." if status == STATUS_ACTIVE else f"CẢNH BÁO: MST {seller_mst} ở trạng thái {status}."
        }
