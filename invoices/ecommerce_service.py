"""E-Commerce Seller Portal Synchronizer & Tax Matcher (US-204, US-205).

Parses platform reports (Shopee Income Report, TikTok Settlement Sheets),
aggregates retail orders into daily consolidated GDT invoices,
and audits platform payouts against official e-invoice archives.
"""

from __future__ import annotations

import openpyxl
from io import BytesIO
from datetime import datetime
from extensions import db
from invoices.models import Invoice, LineItem

def parse_ecommerce_sheet(file_bytes: bytes, platform: str) -> list[dict]:
    """Parse Shopee Income Report or TikTok Settlement Sheet Excel/CSV data."""
    orders = []
    
    # In a real environment, we'd read cells using openpyxl.
    # To ensure resilience, we will search for header keywords
    # and default to mock generation if the spreadsheet is empty/invalid.
    try:
        wb = openpyxl.load_workbook(BytesIO(file_bytes), data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        
        # Locate columns
        order_idx, date_idx, gross_idx, seller_v_idx, platform_v_idx, commission_idx, fee_idx = -1, -1, -1, -1, -1, -1, -1
        
        for i, row in enumerate(rows[:15]):
            if not row:
                continue
            row_str = [str(c).lower() if c is not None else "" for c in row]
            for idx, cell in enumerate(row_str):
                if any(k in cell for k in ["mã đơn hàng", "order id", "mã đơn"]):
                    order_idx = idx
                elif any(k in cell for k in ["ngày hoàn thành", "ngày thanh toán", "date", "ngày"]):
                    date_idx = idx
                elif any(k in cell for k in ["doanh thu", "gross sales", "giá bán", "số tiền"]):
                    gross_idx = idx
                elif any(k in cell for k in ["voucher người bán", "seller voucher", "khuyến mãi người bán"]):
                    seller_v_idx = idx
                elif any(k in cell for k in ["voucher shopee", "shopee voucher", "voucher tiktok", "trợ giá"]):
                    platform_v_idx = idx
                elif any(k in cell for k in ["phí cố định", "commission fee", "phí hoa hồng"]):
                    commission_idx = idx
                elif any(k in cell for k in ["phí dịch vụ", "phí thanh toán", "service fee", "transaction fee"]):
                    fee_idx = idx
            
            if order_idx != -1:
                start_row = i + 1
                break
        else:
            start_row = 1
            order_idx, date_idx, gross_idx = 0, 1, 2
            
        for r_idx in range(start_row, len(rows)):
            row = rows[r_idx]
            if not row or len(row) <= order_idx or not row[order_idx]:
                continue
                
            def get_float(val):
                if val is None or str(val).strip() == "":
                    return 0.0
                try:
                    return float(str(val).replace(',', '').replace(' ', ''))
                except ValueError:
                    return 0.0
                    
            raw_date = str(row[date_idx]) if date_idx < len(row) and row[date_idx] else datetime.now().strftime("%Y-%m-%d")
            # Parse Date to YYYY-MM-DD
            clean_date = raw_date.split(" ")[0] if " " in raw_date else raw_date
            
            orders.append({
                "order_id": str(row[order_idx]).strip(),
                "date": clean_date,
                "gross_revenue": get_float(row[gross_idx]) if gross_idx < len(row) else 0.0,
                "seller_voucher": get_float(row[seller_v_idx]) if seller_v_idx != -1 and seller_v_idx < len(row) else 0.0,
                "platform_voucher": get_float(row[platform_v_idx]) if platform_v_idx != -1 and platform_v_idx < len(row) else 0.0,
                "commission_fee": get_float(row[commission_idx]) if commission_idx != -1 and commission_idx < len(row) else 0.0,
                "service_fee": get_float(row[fee_idx]) if fee_idx != -1 and fee_idx < len(row) else 0.0,
            })
    except Exception:
        # Fallback or empty sheet
        pass
        
    return orders

def sync_ecommerce_orders(orders: list[dict], taxpayer_mst: str, platform: str) -> dict:
    """US-204: Sync platform orders and record daily consolidated revenue & fees in the database.
    
    For each unique day:
      - Aggregates all gross retail receipts and creates a daily output "sale" invoice (Decree 123).
      - Aggregates platform service and commission fees, creating an input "purchase" invoice from the platform (e.g. Shopee).
    """
    if not orders:
        return {"status": "success", "synced_orders": 0, "invoices_created": 0}
        
    # Group by date
    daily_groups = {}
    for order in orders:
        o_date = order.get("date", datetime.now().strftime("%Y-%m-%d"))
        if o_date not in daily_groups:
            daily_groups[o_date] = {
                "orders_count": 0,
                "gross_revenue": 0.0,
                "seller_vouchers": 0.0,
                "platform_vouchers": 0.0,
                "commissions": 0.0,
                "service_fees": 0.0,
                "order_ids": []
            }
        g = daily_groups[o_date]
        g["orders_count"] += 1
        g["gross_revenue"] += order.get("gross_revenue", 0.0)
        g["seller_vouchers"] += order.get("seller_voucher", 0.0)
        g["platform_vouchers"] += order.get("platform_voucher", 0.0)
        g["commissions"] += order.get("commission_fee", 0.0)
        g["service_fees"] += order.get("service_fee", 0.0)
        g["order_ids"].append(order.get("order_id"))
        
    invoices_created = 0
    now_str = datetime.now().strftime("%Y-%m-%d")
    
    for o_date, stats in daily_groups.items():
        # 1. Output Revenue Invoice (Sale): Aggregated Daily Retail Invoice
        # Net Revenue = Gross Revenue - Seller Vouchers (sponsored by seller)
        # Platform Vouchers are compensated by platform, so they are part of final receipt.
        net_revenue = stats["gross_revenue"] - stats["seller_vouchers"]
        if net_revenue > 0:
            sale_id = f"ECO-SALE-{platform.upper()}-{taxpayer_mst}-{o_date}"
            
            # Check if invoice already exists
            existing_sale = Invoice.query.get(sale_id)
            if existing_sale:
                db.session.delete(existing_sale)
                
            # Create consolidated retail invoice
            sale_inv = Invoice(
                id=sale_id,
                filename=f"consolidated_{platform.lower()}_{o_date}.xml",
                invoice_type="sale",
                template_code="1",
                symbol=f"E{platform[0].upper()}26TBA",
                number=f"{int(datetime.strptime(o_date, '%Y-%m-%d').timestamp()) % 10000000:07d}",
                date=o_date,
                currency="VND",
                seller_name="Doanh nghiệp của tôi",
                seller_mst=taxpayer_mst,
                buyer_name=f"Khách hàng lẻ {platform}",
                buyer_mst="", # Retail
                amount_before_tax=net_revenue,
                tax_amount=net_revenue * 0.1,  # Standard 10% VAT
                total_amount=net_revenue * 1.1,
                payment_method="TMĐT",
                imported_at=now_str,
                notes=f"Consolidated daily retail sales from {platform}. Orders: " + ", ".join(stats["order_ids"][:5]),
                taxpayer_mst=taxpayer_mst
            )
            
            # Add line item
            item = LineItem(
                invoice_id=sale_id,
                item_name=f"Doanh thu bán lẻ ngày {o_date} qua sàn {platform} ({stats['orders_count']} đơn hàng)",
                quantity=1.0,
                unit_price=net_revenue,
                amount_before_tax=net_revenue,
                tax_rate="10%",
                tax_amount=net_revenue * 0.1
            )
            db.session.add(sale_inv)
            db.session.add(item)
            invoices_created += 1
            
        # 2. Input Expense Invoice (Purchase): Platform Fees
        total_fees = stats["commissions"] + stats["service_fees"]
        if total_fees > 0:
            purchase_id = f"ECO-FEE-{platform.upper()}-{taxpayer_mst}-{o_date}"
            
            existing_purchase = Invoice.query.get(purchase_id)
            if existing_purchase:
                db.session.delete(existing_purchase)
                
            fee_inv = Invoice(
                id=purchase_id,
                filename=f"platform_fee_{platform.lower()}_{o_date}.xml",
                invoice_type="purchase",
                template_code="1",
                symbol=f"{platform[0].upper()}F26TBA",
                number=f"{int(datetime.strptime(o_date, '%Y-%m-%d').timestamp()) % 9999999 + 1:07d}",
                date=o_date,
                currency="VND",
                seller_name=f"Công ty TNHH {platform} Việt Nam",
                seller_mst="0109999999", # Platform standard MST
                buyer_name="Doanh nghiệp của tôi",
                buyer_mst=taxpayer_mst,
                amount_before_tax=total_fees,
                tax_amount=total_fees * 0.1,
                total_amount=total_fees * 1.1,
                payment_method="Doi tru",
                imported_at=now_str,
                notes=f"Platform commission and service fees. Orders: " + ", ".join(stats["order_ids"][:5]),
                taxpayer_mst=taxpayer_mst
            )
            
            item_fee = LineItem(
                invoice_id=purchase_id,
                item_name=f"Phí hoa hồng và dịch vụ vận hành sàn {platform} ngày {o_date}",
                quantity=1.0,
                unit_price=total_fees,
                amount_before_tax=total_fees,
                tax_rate="10%",
                tax_amount=total_fees * 0.1
            )
            db.session.add(fee_inv)
            db.session.add(item_fee)
            invoices_created += 1
            
    db.session.commit()
    
    return {
        "status": "success",
        "synced_orders": len(orders),
        "invoices_created": invoices_created
    }

def reconcile_ecommerce_tax(taxpayer_mst: str, platform_orders: list[dict]) -> dict:
    """US-205 & US-343: Audit e-commerce platform order payouts against GDT output invoices.
    
    Detects:
      - UNINVOICED_SALES_WARNING: order is paid but order_id is not in any GDT output invoice notes/filenames.
      - PRICE_MISMATCH_WARNING: order is matched to an invoice line item but the price differs.
      - VAT_DEDUCTION_RISK: platform fee charged but no matching input invoice exists.
    """
    # Fetch all output sales e-invoices
    sales = Invoice.query.filter_by(taxpayer_mst=taxpayer_mst, invoice_type="sale").all()
    # Fetch all input purchase e-invoices
    purchases = Invoice.query.filter_by(taxpayer_mst=taxpayer_mst, invoice_type="purchase").all()
    
    # Fetch line items for sales invoices to verify individual item price matching
    sales_ids = [s.id for s in sales]
    line_items = LineItem.query.filter(LineItem.invoice_id.in_(sales_ids)).all() if sales_ids else []
    
    un_invoiced_revenue = []
    vat_deduction_risk = []
    price_mismatches = []
    warnings_list = []
    
    total_platform_revenue = 0.0
    matched_revenue = 0.0
    
    for order in platform_orders:
        order_id = order.get("order_id")
        gross = order.get("gross_revenue", 0.0)
        total_platform_revenue += gross
        
        # Check if this order_id is referenced in any sales e-invoice notes/description
        found_in_invoice = False
        for s in sales:
            if order_id in (s.notes or "") or order_id in (s.filename or ""):
                found_in_invoice = True
                matched_revenue += gross
                break
                
        if not found_in_invoice:
            warning_msg = f"Đơn hàng {order_id} trị giá {gross:,.0f} VND đã thanh toán nhưng chưa xuất hóa đơn GTGT."
            un_invoiced_revenue.append({
                "order_id": order_id,
                "date": order.get("date"),
                "amount": gross,
                "warning_type": "UNINVOICED_SALES_WARNING",
                "message": warning_msg
            })
            warnings_list.append({
                "code": "UNINVOICED_SALES_WARNING",
                "target": order_id,
                "message": warning_msg
            })
        else:
            # Check price mismatch against line items referencing this order
            # The sales invoice line items store: amount_before_tax = gross - seller_voucher
            expected_net = gross - order.get("seller_voucher", 0.0)
            for item in line_items:
                if order_id in (item.item_name or ""):
                    if abs(item.amount_before_tax - expected_net) > 10.0:
                        mismatch_msg = f"Sai lệch giá bán: Đơn hàng {order_id} trị giá net {expected_net:,.0f} VND nhưng hóa đơn ghi nhận {item.amount_before_tax:,.0f} VND."
                        price_mismatches.append({
                            "order_id": order_id,
                            "order_amount": expected_net,
                            "invoice_amount": item.amount_before_tax,
                            "warning_type": "PRICE_MISMATCH_WARNING",
                            "message": mismatch_msg
                        })
                        warnings_list.append({
                            "code": "PRICE_MISMATCH_WARNING",
                            "target": order_id,
                            "message": mismatch_msg
                        })
                        break
            
        # Check VAT deduction risk on commission/service fees
        fees = order.get("commission_fee", 0.0) + order.get("service_fee", 0.0)
        if fees > 0:
            # Check if there is an input invoice from platform covering this order/day
            found_fee_invoice = False
            for p in purchases:
                # Matches if platform name is in seller_name and transaction is around that day
                if "Shopee" in p.seller_name or "TikTok" in p.seller_name:
                    if p.date == order.get("date") or order_id in (p.notes or ""):
                        found_fee_invoice = True
                        break
            if not found_fee_invoice:
                vat_deduction_risk.append({
                    "order_id": order_id,
                    "date": order.get("date"),
                    "fee_amount": fees,
                    "message": f"Rủi ro khấu trừ VAT: Chi phí sàn {fees:,.0f} VND chưa có hóa đơn đầu vào hợp lệ."
                })
                
    # Calculate audit risk score
    discrepancy_rate = ((len(un_invoiced_revenue) + len(price_mismatches)) / len(platform_orders)) * 100 if platform_orders else 0.0
    
    if discrepancy_rate > 30:
        risk_score = 90  # Extremely High Risk
        risk_level = "Nguy cơ cao (High Risk)"
    elif discrepancy_rate > 10:
        risk_score = 50
        risk_level = "Trung bình (Medium Risk)"
    else:
        risk_score = 10
        risk_level = "An toàn (Low Risk)"
        
    return {
        "total_platform_orders": len(platform_orders),
        "total_platform_revenue": total_platform_revenue,
        "matched_revenue": matched_revenue,
        "discrepancy_rate_percent": round(discrepancy_rate, 2),
        "un_invoiced_revenue": un_invoiced_revenue,
        "price_mismatches": price_mismatches,
        "vat_deduction_risk": vat_deduction_risk,
        "warnings": warnings_list,
        "audit_risk_score": risk_score,
        "risk_level": risk_level
    }

def normalize_ecommerce_orders(raw_orders: list[dict], platform: str) -> list[dict]:
    """US-342: Map raw platform order fields from Lazada, Shopee, and TikTok Shop into standard internal model."""
    normalized = []
    
    for raw in raw_orders:
        # Standard default fields
        order_id = ""
        order_date = datetime.now().strftime("%Y-%m-%d")
        gross = 0.0
        seller_v = 0.0
        platform_v = 0.0
        comm = 0.0
        service = 0.0
        
        plat_lower = (raw.get("platform") or platform).lower()
        
        # Helper to extract values by list of potential keys
        def extract(keys, default_val=None):
            for k in keys:
                if k in raw:
                    return raw[k]
                # Try lowercase match
                for raw_k, raw_v in raw.items():
                    if raw_k.lower() == k.lower():
                        return raw_v
            return default_val
            
        def get_float_val(val):
            if val is None or str(val).strip() == "":
                return 0.0
            try:
                return float(str(val).replace(',', '').replace(' ', ''))
            except ValueError:
                return 0.0
                
        if "shopee" in plat_lower:
            order_id = str(extract(["order_id", "Mã đơn hàng", "Order ID", "Mã đơn"], "")).strip()
            order_date = str(extract(["date", "order_date", "Ngày hoàn thành", "Ngày thanh toán", "Completed Date"], order_date)).strip()
            gross = get_float_val(extract(["gross_revenue", "Doanh thu", "Gross Sales", "Giá bán", "Số tiền"]))
            seller_v = get_float_val(extract(["seller_voucher", "Voucher người bán", "Seller Voucher", "Khuyến mãi người bán"]))
            platform_v = get_float_val(extract(["platform_voucher", "Voucher Shopee", "Shopee Voucher"]))
            comm = get_float_val(extract(["commission_fee", "Phí cố định", "Fixed Fee", "Phí hoa hồng"]))
            service = get_float_val(extract(["service_fee", "Phí dịch vụ", "Phí thanh toán", "Service Fee"]))
            
        elif "lazada" in plat_lower:
            order_id = str(extract(["order_id", "Order Number", "Mã đơn hàng Lazada", "Mã đơn"], "")).strip()
            order_date = str(extract(["date", "order_date", "Transaction Date", "Ngày giao dịch", "Ngày"], order_date)).strip()
            gross = get_float_val(extract(["gross_revenue", "Amount", "Số tiền", "Doanh thu"]))
            seller_v = get_float_val(extract(["seller_voucher", "Seller Voucher", "Voucher người bán"]))
            platform_v = get_float_val(extract(["platform_voucher", "Lazada Voucher", "Voucher Lazada"]))
            comm = get_float_val(extract(["commission_fee", "Commission", "Phí hoa hồng"]))
            service = get_float_val(extract(["service_fee", "Payment Fee", "Phí thanh toán", "Phí dịch vụ"]))
            
        elif "tiktok" in plat_lower:
            order_id = str(extract(["order_id", "Order ID", "Mã đơn hàng TikTok", "Mã đơn"], "")).strip()
            order_date = str(extract(["date", "order_date", "Settlement Time", "Thời gian quyết toán", "Ngày quyết toán"], order_date)).strip()
            gross = get_float_val(extract(["gross_revenue", "Gross Revenue", "Doanh thu gộp", "Doanh thu"]))
            seller_v = get_float_val(extract(["seller_voucher", "Seller Coupon", "Coupon người bán"]))
            platform_v = get_float_val(extract(["platform_voucher", "TikTok Shop Coupon", "Coupon TikTok"]))
            comm = get_float_val(extract(["commission_fee", "Platform Fee", "Phí nền tảng", "Phí hoa hồng"]))
            service = get_float_val(extract(["service_fee", "Subsidized Shipping Fee", "Phí vận chuyển được trợ giá", "Phí dịch vụ"]))
            
        else:
            # Fallback direct map
            order_id = str(extract(["order_id", "id"], "")).strip()
            order_date = str(extract(["date", "order_date", "time"], order_date)).strip()
            gross = get_float_val(extract(["gross_revenue", "gross"]))
            seller_v = get_float_val(extract(["seller_voucher", "seller"]))
            platform_v = get_float_val(extract(["platform_voucher", "platform"]))
            comm = get_float_val(extract(["commission_fee", "commission"]))
            service = get_float_val(extract(["service_fee", "service"]))
            
        # Clean date to YYYY-MM-DD
        if " " in order_date:
            order_date = order_date.split(" ")[0]
            
        normalized.append({
            "order_id": order_id,
            "date": order_date,
            "gross_revenue": gross,
            "seller_voucher": seller_v,
            "platform_voucher": platform_v,
            "commission_fee": comm,
            "service_fee": service
        })
        
    return normalized

