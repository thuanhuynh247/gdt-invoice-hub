"""Version 27.0.0 Advanced Delivery Compliance & Tax Risk Advisory Suite.

Includes:
- Electronic Delivery Notes (PXK) Sync, Validation & Parser (US-390)
- PXK to Commercial Invoice Reconciliation & Discrepancy Exporter (US-391)
- Circular 80 & Decree 123 Corporate Tax Pre-Audit Risk Scoring Engine (US-392)
- SVG Risk Radar Chart Generator & Advisory Panel (US-393)
- E-Contract XML Metadata Parser & Milestone Alignment Tracker (US-394)
- Smart Treasury Forecast & VAT Scenario Simulation Sandbox (US-395)
"""

from __future__ import annotations
import csv
import io
import math
import uuid
import datetime
import xml.etree.ElementTree as ET

# ── US-390: PXK XML Parser & Validation ──────────────────────────────────────

def parse_delivery_note_xml(xml_content: str) -> dict:
    """Parse and validate Electronic Delivery Note (PXK) conforming to Decree 123 regulations."""
    try:
        # Check signature presence
        has_signature = "<Signature" in xml_content or "<dscnhky" in xml_content.lower()
        
        # Parse XML tree
        root = ET.fromstring(xml_content)
        
        # Helper to safely find text
        def find_txt(tag_name, default="N/A"):
            elem = root.find(f".//{tag_name}")
            return elem.text if elem is not None and elem.text else default
            
        so_pxk = find_txt("SoPXK")
        ngay_xuat = find_txt("NgayXuat")
        kho_xuat = find_txt("KhoXuat")
        kho_nhap = find_txt("KhoNhap")
        nguoi_van_chuyen = find_txt("NguoiVanChuyen")
        phuong_tien = find_txt("PhuongTienVanChuyen")
        contract_ref = find_txt("ContractRef")
        
        # SKU Goods List
        goods_list = []
        for item in root.findall(".//GoodsItem"):
            goods_list.append({
                "sku": item.find("MaHang").text if item.find("MaHang") is not None else "N/A",
                "name": item.find("TenHang").text if item.find("TenHang") is not None else "N/A",
                "unit": item.find("DonViTinh").text if item.find("DonViTinh") is not None else "N/A",
                "quantity": float(item.find("SoLuong").text) if item.find("SoLuong") is not None else 0.0,
            })
            
        return {
            "status": "valid" if has_signature else "unsigned",
            "so_pxk": so_pxk,
            "ngay_xuat": ngay_xuat,
            "kho_xuat": kho_xuat,
            "kho_nhap": kho_nhap,
            "nguoi_van_chuyen": nguoi_van_chuyen,
            "phuong_tien": phuong_tien,
            "contract_ref": contract_ref,
            "goods": goods_list,
            "has_signature": has_signature
        }
    except Exception as e:
        raise ValueError(f"Malformed PXK XML schema template: {str(e)}")


# ── US-391: PXK to Commercial Invoice Reconciliation ───────────────────────

def reconcile_delivery_to_invoice(delivery_notes: list[dict], invoices: list[dict]) -> dict:
    """Match goods delivery records against commercial invoices and expose mismatches."""
    matched_records = []
    unmatched_deliveries = []
    unmatched_invoices = []
    
    # Quick lookup of invoice line items mapped by reference
    inv_map = {}
    for inv in invoices:
        ref = inv.get("reference_no") or inv.get("invoice_no")
        if ref:
            inv_map[ref] = inv
            
    # Keep track of matched invoice references to find unmatched invoices
    matched_inv_refs = set()
    
    for pxk in delivery_notes:
        ref = pxk.get("so_pxk")
        matching_inv = inv_map.get(ref)
        
        if not matching_inv:
            unmatched_deliveries.append({
                "so_pxk": ref,
                "ngay_xuat": pxk.get("ngay_xuat"),
                "reason": "Chưa xuất hóa đơn thương mại cho phiếu xuất kho này."
            })
            continue
            
        matched_inv_refs.add(ref)
        
        # Cross-examine goods SKUs and quantities
        pxk_goods = {item["sku"]: item for item in pxk.get("goods", [])}
        # Invoices list items under "line_items"
        inv_goods = {item.get("sku"): item for item in matching_inv.get("line_items", [])}
        
        item_discrepancies = []
        all_skus = set(pxk_goods.keys()) | set(inv_goods.keys())
        
        for sku in all_skus:
            p_qty = pxk_goods.get(sku, {}).get("quantity", 0.0)
            i_qty = inv_goods.get(sku, {}).get("quantity", 0.0)
            
            if abs(p_qty - i_qty) > 0.001:
                item_discrepancies.append({
                    "sku": sku,
                    "name": pxk_goods.get(sku, {}).get("name") or inv_goods.get(sku, {}).get("name") or "N/A",
                    "delivery_quantity": p_qty,
                    "invoice_quantity": i_qty,
                    "variance": i_qty - p_qty
                })
                
        status = "matched" if not item_discrepancies else "discrepancy"
        
        matched_records.append({
            "so_pxk": ref,
            "invoice_no": matching_inv.get("invoice_no"),
            "ngay_xuat": pxk.get("ngay_xuat"),
            "invoice_date": matching_inv.get("invoice_date"),
            "discrepancies": item_discrepancies,
            "status": status
        })
        
    for ref, inv in inv_map.items():
        if ref not in matched_inv_refs:
            unmatched_invoices.append({
                "invoice_no": inv.get("invoice_no"),
                "invoice_date": inv.get("invoice_date"),
                "reason": "Hóa đơn thương mại không tìm thấy phiếu xuất kho liên kết tương ứng."
            })
            
    has_flags = len(unmatched_deliveries) > 0 or len(unmatched_invoices) > 0 or any(r["status"] == "discrepancy" for r in matched_records)
    
    return {
        "matched_records": matched_records,
        "unmatched_deliveries": unmatched_deliveries,
        "unmatched_invoices": unmatched_invoices,
        "status": "flagged" if has_flags else "compliant",
        "reconciled_at": datetime.datetime.now().isoformat()
    }

def export_delivery_reconciliation_csv(recon_result: dict) -> str:
    """Export the delivery to invoice reconciliation report as a formatted CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(["BÁO CÁO ĐỐI CHIẾU PHIẾU XUẤT KHO VÀ HÓA ĐƠN THƯƠNG MẠI"])
    writer.writerow([f"Ngày thực hiện: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}"])
    writer.writerow([])
    
    # Matched Records Section
    writer.writerow(["1. DANH SÁCH ĐỐI CHIẾU ĐÃ GHÉP CẶP"])
    writer.writerow(["Mã Phiếu Xuất Kho", "Số Hóa Đơn", "Ngày Xuất Kho", "Ngày Hóa Đơn", "SKU Lệch", "Độ Lệch Số Lượng", "Trạng Thái"])
    for r in recon_result.get("matched_records", []):
        if r["status"] == "matched":
            writer.writerow([r["so_pxk"], r["invoice_no"], r["ngay_xuat"], r["invoice_date"], "-", "0", "KHỚP"])
        else:
            for d in r["discrepancies"]:
                writer.writerow([r["so_pxk"], r["invoice_no"], r["ngay_xuat"], r["invoice_date"], d["sku"], f"{d['variance']:.2f}", "LỆCH"])
                
    writer.writerow([])
    # Unmatched Deliveries Section
    writer.writerow(["2. PHIẾU XUẤT KHO CHƯA XUẤT HÓA ĐƠN"])
    writer.writerow(["Mã Phiếu Xuất Kho", "Ngày Xuất Kho", "Mô Tả Cảnh Báo"])
    for ud in recon_result.get("unmatched_deliveries", []):
        writer.writerow([ud["so_pxk"], ud["ngay_xuat"], ud["reason"]])
        
    writer.writerow([])
    # Unmatched Invoices Section
    writer.writerow(["3. HÓA ĐƠN CHƯA CÓ PHIẾU XUẤT KHO"])
    writer.writerow(["Số Hóa Đơn", "Ngày Hóa Đơn", "Mô Tả Cảnh Báo"])
    for ui in recon_result.get("unmatched_invoices", []):
        writer.writerow([ui["invoice_no"], ui["invoice_date"], ui["reason"]])
        
    return output.getvalue()


# ── US-392 & US-393: Pre-Audit Corporate Tax Risk Engine & SVG Radar ──────────

def calculate_pre_audit_risk(profile: dict, invoices: list[dict], related_party_context: dict) -> dict:
    """Calculate pre-audit tax risk scores (0-100) along 5 regulatory vectors."""
    # 1. Related Party Risk (Decree 132)
    # Cap limit of interest expense = 30% of EBITDA
    ebitda = related_party_context.get("ebitda", 0.0)
    net_interest = related_party_context.get("net_interest", 0.0)
    
    if ebitda > 0:
        interest_ratio = net_interest / ebitda
        if interest_ratio > 0.30:
            related_party_risk = 100.0
        else:
            related_party_risk = max(0.0, (interest_ratio / 0.30) * 100.0)
    else:
        related_party_risk = 100.0 if net_interest > 0 else 0.0
        
    # 2. Supplier Blacklist Risk
    # High risk if supplier tax status is non-active/flagged
    blacklist_suppliers = {"0109999999", "0202020202", "0303030303"} # Mock blacklisted MSTs
    purchase_invoices = [inv for inv in invoices if inv.get("direction") == "in"]
    blacklist_hits = sum(1 for inv in purchase_invoices if inv.get("seller_mst") in blacklist_suppliers)
    
    if purchase_invoices:
        supplier_blacklist_risk = min(100.0, (blacklist_hits / len(purchase_invoices)) * 200.0)
    else:
        supplier_blacklist_risk = 0.0
        
    # 3. Invoicing Latency Risk (Decree 123)
    # Delay between delivery and invoicing > 10 days
    delayed_invoices = 0
    total_reconciled = 0
    
    for inv in invoices:
        if inv.get("delivery_date") and inv.get("invoice_date"):
            try:
                fmt = "%Y-%m-%d"
                d_date = datetime.datetime.strptime(inv["delivery_date"], fmt)
                i_date = datetime.datetime.strptime(inv["invoice_date"], fmt)
                days = (i_date - d_date).days
                total_reconciled += 1
                if days > 10:
                    delayed_invoices += 1
            except Exception:
                pass
                
    if total_reconciled > 0:
        latency_risk = min(100.0, (delayed_invoices / total_reconciled) * 100.0)
    else:
        latency_risk = 0.0
        
    # 4. Cash Limit Risk (Circular 219)
    # Transactions >= 20M VND paid in cash
    cash_violations = sum(1 for inv in invoices if inv.get("amount", 0.0) >= 20000000.0 and inv.get("payment_method") == "CASH")
    if invoices:
        cash_limit_risk = min(100.0, cash_violations * 25.0)
    else:
        cash_limit_risk = 0.0
        
    # 5. Cancellation Rate Risk
    cancelled = sum(1 for inv in invoices if inv.get("status") == "CANCELLED")
    total_invoices = len(invoices)
    
    if total_invoices > 0:
        cancellation_rate = cancelled / total_invoices
        if cancellation_rate > 0.10:
            cancellation_risk = 100.0
        else:
            cancellation_risk = (cancellation_rate / 0.10) * 100.0
    else:
        cancellation_risk = 0.0
        
    # Overall Weighted Index
    weights = {
        "related_party": 0.30,
        "blacklist": 0.25,
        "latency": 0.15,
        "cash_limit": 0.15,
        "cancellation": 0.15
    }
    
    risk_index = (
        weights["related_party"] * related_party_risk +
        weights["blacklist"] * supplier_blacklist_risk +
        weights["latency"] * latency_risk +
        weights["cash_limit"] * cash_limit_risk +
        weights["cancellation"] * cancellation_risk
    )
    
    # Generate compliance suggestions
    advisory_notes = []
    if related_party_risk > 50:
        advisory_notes.append("Cảnh báo Giao dịch Liên kết: Chi phí lãi vay vượt trần 30% EBITDA theo Nghị định 132/2020/NĐ-CP. Cần thực hiện kê khai Phụ lục I và loại trừ phần chi phí lãi vay không được trừ khi quyết toán thuế TNDN.")
    if supplier_blacklist_risk > 0:
        advisory_notes.append("Rủi ro Hóa đơn Đầu vào: Phát hiện hóa đơn từ doanh nghiệp thuộc danh sách rủi ro cao về thuế. Cần lập tức đối chiếu thực tế giao dịch, chuẩn bị biên bản bàn giao hàng hóa và chứng từ thanh toán ngân hàng để giải trình.")
    if latency_risk > 30:
        advisory_notes.append("Vi phạm Thời điểm Lập Hóa đơn: Phát hiện hóa đơn lập sai thời điểm (trễ hơn 10 ngày so với biên bản bàn giao/xuất kho) theo quy định tại Nghị định 123/2020/NĐ-CP. Có thể bị phạt vi phạm hành chính từ 4 đến 8 triệu đồng.")
    if cash_limit_risk > 0:
        advisory_notes.append("Vi phạm Thanh toán Tiền mặt: Có hóa đơn mua vào trị giá từ 20 triệu đồng trở lên thanh toán bằng tiền mặt. Giao dịch này sẽ bị loại trừ quyền khấu trừ thuế GTGT đầu vào và không được tính vào chi phí hợp lý được trừ khi xác định thuế TNDN.")
    if cancellation_risk > 50:
        advisory_notes.append("Tần suất Hủy Hóa đơn Cao: Tỷ lệ hủy/thay thế hóa đơn vượt ngưỡng an toàn (10%). Có thể kích hoạt cơ chế tự động thanh tra của Cơ quan Thuế do nghi ngờ giao dịch ảo.")
        
    if not advisory_notes:
        advisory_notes.append("Hồ sơ tuân thủ thuế của doanh nghiệp đang ở mức an toàn. Tiếp tục duy trì chế độ kiểm soát hóa đơn định kỳ.")
        
    return {
        "taxpayer_mst": profile.get("mst", "N/A"),
        "scores": {
            "related_party": related_party_risk,
            "blacklist": supplier_blacklist_risk,
            "latency": latency_risk,
            "cash_limit": cash_limit_risk,
            "cancellation": cancellation_risk
        },
        "weights": weights,
        "risk_index": risk_index,
        "advisory_notes": advisory_notes,
        "status": "critical" if risk_index >= 70.0 else "warning" if risk_index >= 30.0 else "safe"
    }

def generate_svg_radar_chart(scores: dict) -> str:
    """Generate dynamic SVG radar chart plotting the 5 risk vectors."""
    # Radial dimensions for 5-axis chart
    # Center: (150, 150), Radius: 100
    cx, cy = 150, 150
    radius = 100
    
    # 5 Axes angles in radians: related_party, blacklist, latency, cash_limit, cancellation
    angles = [
        -math.pi / 2,                  # Related Party (Top)
        -math.pi / 2 + 2 * math.pi / 5,  # Blacklist (Top-Right)
        -math.pi / 2 + 4 * math.pi / 5,  # Latency (Bottom-Right)
        -math.pi / 2 + 6 * math.pi / 5,  # Cash Limit (Bottom-Left)
        -math.pi / 2 + 8 * math.pi / 5   # Cancellation (Top-Left)
    ]
    
    keys = ["related_party", "blacklist", "latency", "cash_limit", "cancellation"]
    
    # Calculate polygon points for the scores
    poly_points = []
    for i, key in enumerate(keys):
        score_val = scores.get(key, 0.0)
        # Map 0-100 to 0-radius
        r = (score_val / 100.0) * radius
        x = cx + r * math.cos(angles[i])
        y = cy + r * math.sin(angles[i])
        poly_points.append(f"{x:.1f},{y:.1f}")
        
    poly_str = " ".join(poly_points)
    
    # Grid concentric circles for 25%, 50%, 75%, 100%
    grid_circles = ""
    for scale in [0.25, 0.50, 0.75, 1.0]:
        r = scale * radius
        grid_circles += f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="rgba(255,255,255,0.1)" stroke-dasharray="2,2"/>\n'
        
    # Axis lines
    axis_lines = ""
    label_elements = ""
    labels = ["Giao dịch liên kết", "Rủi ro nhà cung cấp", "Trễ hóa đơn", "Hạn mức tiền mặt", "Hủy hóa đơn"]
    
    for i, angle in enumerate(angles):
        # Line from center to edge
        x_edge = cx + radius * math.cos(angle)
        y_edge = cy + radius * math.sin(angle)
        axis_lines += f'<line x1="{cx}" y1="{cy}" x2="{x_edge:.1f}" y2="{y_edge:.1f}" stroke="rgba(255,255,255,0.2)" />\n'
        
        # Label offset placement
        label_dist = radius + 25
        lx = cx + label_dist * math.cos(angle)
        ly = cy + label_dist * math.sin(angle)
        
        # Adjust text anchor alignment based on quadrant
        if abs(lx - cx) < 10:
            anchor = "middle"
        elif lx > cx:
            anchor = "start"
        else:
            anchor = "end"
            
        label_elements += f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" fill="#94a3b8" font-size="10" font-weight="bold">{labels[i]}</text>\n'
        
    svg_string = f"""<svg viewBox="0 0 300 300" width="100%" height="100%" style="max-width: 320px; background: transparent;">
    <!-- Concentric Grid Circles -->
    {grid_circles}
    
    <!-- Axes Lines -->
    {axis_lines}
    
    <!-- Labels -->
    {label_elements}
    
    <!-- Score Polygon (Semi-transparent Blue fill, Cyan border) -->
    <polygon points="{poly_str}" fill="rgba(59, 130, 246, 0.3)" stroke="#22d3ee" stroke-width="2" />
    
    <!-- Center Point -->
    <circle cx="{cx}" cy="{cy}" r="3" fill="#ffffff" />
</svg>"""
    return svg_string


# ── US-394: E-Contract Ingestion & Milestone Alignment ───────────────────────

def parse_econtract_metadata(json_content: str) -> dict:
    """Parse structured e-contract JSON payload (representing e-contract metadata)."""
    try:
        import json
        data = json.loads(json_content)
        
        # Validation checks
        required = ["contract_no", "effective_date", "contract_value", "milestones"]
        for field in required:
            if field not in data:
                raise ValueError(f"Missing mandatory e-contract parameter: {field}")
                
        return {
            "contract_no": data["contract_no"],
            "effective_date": data["effective_date"],
            "contract_value": float(data["contract_value"]),
            "supplier_name": data.get("supplier_name", "N/A"),
            "customer_name": data.get("customer_name", "N/A"),
            "milestones": [
                {
                    "milestone_id": m.get("milestone_id") or str(uuid.uuid4().hex[:6].upper()),
                    "due_date": m["due_date"],
                    "percentage": float(m["percentage"]),
                    "value": float(m["percentage"]) / 100.0 * float(data["contract_value"]),
                    "description": m.get("description", "")
                }
                for m in data["milestones"]
            ]
        }
    except Exception as e:
        raise ValueError(f"Failed to parse e-contract metadata: {str(e)}")

def reconcile_contract_milestones(contract: dict, invoices: list[dict], payments: list[dict]) -> dict:
    """Correlate e-contract payment milestones against issued commercial invoices and payment journals."""
    contract_no = contract.get("contract_no")
    reconciled_milestones = []
    
    # Filter invoices and payments linked to contract_no
    linked_invoices = [inv for inv in invoices if inv.get("contract_ref") == contract_no]
    linked_payments = [pay for pay in payments if pay.get("contract_ref") == contract_no]
    
    total_invoiced = sum(inv.get("amount", 0.0) for inv in linked_invoices)
    total_paid = sum(pay.get("amount", 0.0) for pay in linked_payments)
    
    # Accumulators
    running_invoiced = 0.0
    running_paid = 0.0
    
    for m in contract.get("milestones", []):
        m_val = m["value"]
        due_date_str = m["due_date"]
        
        # Allocate invoice credits to this milestone sequentially
        allocated_invoice = 0.0
        if total_invoiced > running_invoiced:
            remaining_inv = total_invoiced - running_invoiced
            allocated_invoice = min(m_val, remaining_inv)
            running_invoiced += allocated_invoice
            
        # Allocate payment credits to this milestone sequentially
        allocated_paid = 0.0
        if total_paid > running_paid:
            remaining_paid = total_paid - running_paid
            allocated_paid = min(m_val, remaining_paid)
            running_paid += allocated_paid
            
        # Determine status
        due_date = datetime.datetime.strptime(due_date_str, "%Y-%m-%d")
        is_overdue = datetime.datetime.now() > due_date
        
        if abs(allocated_paid - m_val) < 0.01:
            status = "paid"
        elif allocated_paid > 0.0:
            status = "partially_paid"
        else:
            status = "overdue" if is_overdue else "pending"
            
        reconciled_milestones.append({
            "milestone_id": m["milestone_id"],
            "description": m["description"],
            "due_date": m["due_date"],
            "milestone_value": m_val,
            "allocated_invoice": allocated_invoice,
            "allocated_paid": allocated_paid,
            "invoiced_deficit": m_val - allocated_invoice,
            "paid_deficit": m_val - allocated_paid,
            "status": status
        })
        
    return {
        "contract_no": contract_no,
        "contract_value": contract.get("contract_value"),
        "total_invoiced": total_invoiced,
        "total_paid": total_paid,
        "reconciled_milestones": reconciled_milestones,
        "status": "compliant" if all(rm["status"] in ["paid", "pending"] for rm in reconciled_milestones) else "flagged"
    }


# ── US-395: Smart Treasury & VAT Forecast Scenario Sandbox ──────────────────

def simulate_treasury_forecast(
    milestones: list[dict],
    invoices: list[dict],
    starting_cash: float,
    delay_days: int = 0,
    cit_discount: float = 0.0
) -> dict:
    """Project daily cash balance and VAT/CIT tax liabilities over a 60-day window."""
    today = datetime.date.today()
    timeline = []
    
    # Store dynamic daily events
    daily_cashflows = {today + datetime.timedelta(days=i): {"inflow": 0.0, "outflow": 0.0, "vat_liability": 0.0, "cit_liability": 0.0} for i in range(61)}
    
    # 1. Project Inflow from e-Contract Milestones
    for m in milestones:
        try:
            m_date = datetime.datetime.strptime(m["due_date"], "%Y-%m-%d").date()
            # Apply delay slider offset
            realized_date = m_date + datetime.timedelta(days=delay_days)
            if today <= realized_date <= (today + datetime.timedelta(days=60)):
                val = m["milestone_value"]
                # Inflow is raw cash milestone collection
                daily_cashflows[realized_date]["inflow"] += val
                # Approximate 10% VAT liability on milestone invoicing
                daily_cashflows[realized_date]["vat_liability"] += (val / 1.1) * 0.1
                # Approximate 20% CIT liability on net profit (assumed 25% margin) with discount
                cit_rate = 0.20 * (1.0 - cit_discount)
                daily_cashflows[realized_date]["cit_liability"] += (val * 0.25) * cit_rate
        except Exception:
            pass
            
    # 2. Project Outflow from Accounts Payable Invoices
    for inv in invoices:
        if inv.get("direction") == "in" and inv.get("status") != "CANCELLED":
            try:
                inv_date = datetime.datetime.strptime(inv["invoice_date"], "%Y-%m-%d").date()
                due_date = inv_date + datetime.timedelta(days=30)  # Standard Net 30 terms
                if today <= due_date <= (today + datetime.timedelta(days=60)):
                    val = inv.get("amount", 0.0)
                    daily_cashflows[due_date]["outflow"] += val
            except Exception:
                pass
                
    # 3. Simulate Daily Aggregates
    current_cash = starting_cash
    cumulative_vat = 0.0
    cumulative_cit = 0.0
    
    for day in sorted(daily_cashflows.keys()):
        flow = daily_cashflows[day]
        current_cash += flow["inflow"] - flow["outflow"]
        cumulative_vat += flow["vat_liability"]
        cumulative_cit += flow["cit_liability"]
        
        timeline.append({
            "date": day.isoformat(),
            "inflow": flow["inflow"],
            "outflow": flow["outflow"],
            "net_flow": flow["inflow"] - flow["outflow"],
            "cash_balance": current_cash,
            "vat_liability": cumulative_vat,
            "cit_liability": cumulative_cit
        })
        
    return {
        "starting_cash": starting_cash,
        "ending_cash": current_cash,
        "total_projected_inflow": sum(f["inflow"] for f in daily_cashflows.values()),
        "total_projected_outflow": sum(f["outflow"] for f in daily_cashflows.values()),
        "projected_vat_obligation": cumulative_vat,
        "projected_cit_obligation": cumulative_cit,
        "timeline": timeline
    }
