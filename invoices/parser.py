"""Utilities for date validation and response normalization."""

from __future__ import annotations

from datetime import date, datetime


class DateValidationError(ValueError):
    """Raised when a date range is missing or invalid."""


def validate_date_range(date_from: str, date_to: str) -> tuple[date, date]:
    """Validate date range strings and return parsed date objects."""

    if not date_from or not date_to:
        raise DateValidationError("Ban phai nhap ca tu ngay va den ngay.")

    try:
        parsed_from = datetime.strptime(date_from, "%Y-%m-%d").date()
        parsed_to = datetime.strptime(date_to, "%Y-%m-%d").date()
    except ValueError as error:
        raise DateValidationError("Ngay phai dung dinh dang YYYY-MM-DD.") from error

    if parsed_from > parsed_to:
        raise DateValidationError("Tu ngay phai nho hon hoac bang den ngay.")

    if parsed_from > date.today() or parsed_to > date.today():
        raise DateValidationError("Khong duoc tim hoa don trong tuong lai.")

    return parsed_from, parsed_to


import xml.etree.ElementTree as ET


def normalize_invoice(raw_invoice: dict) -> dict:
    """Map a raw invoice payload into the UI/API shape required by the spec."""

    return {
        "id": raw_invoice["id"],
        "date": raw_invoice["date"],
        "amount": raw_invoice["amount"],
        "status": raw_invoice["status"],
        "issuer": raw_invoice["issuer"],
        "description": raw_invoice.get("description", ""),
        "is_cancelled": raw_invoice.get("is_cancelled", False),
        "cancellation_date": raw_invoice.get("cancellation_date"),
        "cancellation_reason": raw_invoice.get("cancellation_reason"),
        "line_items": raw_invoice.get("line_items", []),
        "msttcgp": raw_invoice.get("msttcgp", ""),
    }



def parse_xml_line_items(xml_bytes: bytes) -> list[dict]:
    """Parse nested line items from a raw GDT XML invoice."""

    try:
        root = ET.fromstring(xml_bytes)
        # Strip XML namespaces for easier XPath searching
        for elem in root.iter():
            if "}" in elem.tag:
                elem.tag = elem.tag.split("}", 1)[1]

        line_items = []
        for hhdvu in root.findall(".//HHDVu"):
            item_name = hhdvu.findtext("Ten") or hhdvu.findtext("TChat") or ""
            if not item_name.strip():
                continue

            quantity_text = hhdvu.findtext("SLuong") or "0"
            price_text = hhdvu.findtext("DGia") or "0"
            amount_text = hhdvu.findtext("ThTien") or "0"
            tax_rate = hhdvu.findtext("TSuat") or "0%"
            tax_amount_text = hhdvu.findtext("TThue") or "0"

            try:
                quantity = float(quantity_text.replace(",", ""))
                unit_price = float(price_text.replace(",", ""))
                amount_before_tax = float(amount_text.replace(",", ""))
                tax_amount = float(tax_amount_text.replace(",", ""))
            except ValueError:
                quantity = 0.0
                unit_price = 0.0
                amount_before_tax = 0.0
                tax_amount = 0.0

            line_items.append(
                {
                    "item_name": item_name.strip(),
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "amount_before_tax": amount_before_tax,
                    "tax_rate": tax_rate.strip(),
                    "tax_amount": tax_amount,
                }
            )
        return line_items
    except Exception:
        return []


PROVIDER_LOOKUP_MAP = {
    "0100100417-007": "https://bill.payoo.vn/tra-tien-thanh-toan-hoa-don-dien-evn?AspxAutoDetectCookieSupport=1",
    "0100109106": "https://vinvoice.viettel.vn/utilities/invoice-search",
    "0100684378": "https://portaltool-miennam.vnpt-invoice.com.vn/",
    "0100686209": "http://tracuuhoadon.mobifoneinvoice.vn/trang-chu",
    "0100687474": "https://hoadondientu-ptp.vn/tra-cuu/",
    "0100727825": "https://einvoice.fast.com.vn/",
    "0101162173": "https://asiainvoice.vn/tra-cuu",
    "0101243150": "https://www.meinvoice.vn/tra-cuu/",
    "0101289966": "https://tracuu.e-hoadon.cloud/",
    "0101300842": "https://einvoice.vn/tra-cuu",
    "0101352495": "https://tracuu.v50.vninvoice.vn/",
    "0101360697": "https://van.ehoadon.vn/Lookup?InvoiceGUID=",
    "0101659906": "https://tracuu.kaike.vn/-/",
    "0102182292": "https://einvoice.vnpay.vn/",
    "0102454468": "https://tax24.com.vn/thuedientu/xac-minh-hoa-don",
    "0102519041": "https://ihoadon.vn/kiem-tra/?lang=vn",
    "102519041": "https://ihoadon.vn/kiem-tra/?lang=vn",
    "0103018807": "https://abcsys.vn/Invoice/Search",
    "0103019524": "https://einvoice.aits.vn/",
    "0103770970": "https://www.bitware.vn/tracuuhoadon/",
    "0103930279": "https://hoadon78_logigo.nacencomm.vn/",
    "0104128565": "https://hoadon.ftg.vn/",
    "0104359717": "https://tracuuhoadon.kiotviet.vn/",
    "0104614692": "https://hoadontvan.com/TraCuu",
    "0104908371": "https://hoadondientu.acman.vn/tra-cuu/hoa-don.html",
    "0105232093": "https://tracuu.cyberbill.vn/",
    "0105844836": "https://tracuu.vinvoice.vn/",
    "0105937449": "https://newinvoice.com.vn/tra-cuu/",
    "0105958921": "https://tracuu.cloudinvoice.vn/",
    "0105987432": "https://{seller_mst}hd.easyinvoice.com.vn",
    "0106026495": "https://tracuuhoadon.minvoice.com.vn/single/invoice",
    "0106026495-001": "https://tracuuhoadon.minvoice.com.vn/single/invoice",
    "0106249501": "https://tracuuhoadon.minvoice.com.vn/single/invoice",
    "0106361479": "https://tracuu.ahoadon.com/",
    "0106713804": "https://tracuuhddt78.hilo.com.vn/",
    "0106820789": "https://tracuu.hoadondientuvn.info/",
    "0106858609": "https://tracuuhoadon.vetc.com.vn/?s",
    "0106870211": "https://tracuu.vietinvoice.vn/",
    "0107500414": "https://tracuuhoadon.vetc.com.vn/",
    "0108516079": "http://hddt.3asoft.vn/",
    "0108971656": "https://tracuu.myinvoice.vn/",
    "0109266456": "https://giaothongso.com.vn/tra-cuu-hoa-don-mtc/",
    "0109282176": "https://tracuu.vininvoice.vn/",
    "0200638946": "https://oinvoice.vn/tracuu/",
    "0200784873": "https://hoadonbachkhoa.pmbk.vn/tra-cuu-hoa-don",
    "0201802839": "https://tracuu.homecasta.vn/",
    "0202029650": "https://hdbk.pmbk.vn/tra-cuu-hoa-don",
    "0301448733": "https://accnet.vn/hoa-don-dien-tu",
    "0301452923": "https://tracuu.lienson.vn/",
    "0302431595": "https://tracuu.hoadon30s.vn",
    "0302712571": "https://matbao.in/tra-cuu-hoa-don/",
    "0302999571": "https://eip.lcssoft.com.vn/desktop/",
    "0303430876": "http://trahoadon.vn/SearchOne",
    "0303609305": "https://ihoadondientu.com/Tra-cuu",
    "0305795054": "https://hoadon.pvoil.vn/Invoice/search",
    "0306784030": "https://ehoadon.online/einvoice/lookup",
    "0309478306": "https://tracuu.xuathoadon.vn/",
    "0309612872": "https://tracuuhd.smartsign.com.vn/",
    "0310151739": "https://news.yoinvoice.vn/search-invoice",
    "0310768095": "http://hoadondientu.link/tracuutt78",
    "0310926922": "https://invoice.ehcm.vn/",
    "0311928954": "https://tracuuhoadon.vietinfo.tech/",
    "0311942758": "https://tracuuonline78.ngogiaphat.vn/Search",
    "0312270160": "https://ameinvoice.vn/tra-cuu-hoa-don-dien-tu/",
    "0312303803": "https://tracuu.wininvoice.vn/",
    "0312942260": "https://ihoadondientu.net/Tracuu.aspx",
    "0312961577": "http://tracuuhoadon.benthanhinvoice.vn/",
    "0313844107": "http://voice.hoadondientu.net.vn/tra-cuu",
    "0313906508": "https://nguyenminhvat.vn/hddt/sinv/sinv00101",
    "0313950909": "https://koffi.vn/outbound/lookup-invoice",
    "0313963672": "https://tracuuhoadon.kkvat.com.vn/",
    "0314185087": "https://hoadon.onlinevina.com.vn/invoice",
    "0314209362": "https://hoadondientuvat.com/Tracuu.aspx",
    "0314743623": "https://ehoadondientu.com/Tra-cuu",
    "0315151651": "https://ei.pvssolution.com/",
    "0315191291": "https://hoadonsovn.evat.vn/",
    "0315298333": "https://tctinvoice.com/",
    "0315467091": "https://www.acconline.vn/vn/tra-cuu-hoa-don.htm",
    "0315638251": "https://htinvoice.com.vn/TraCuu",
    "0316642395": "https://phuongnam.evat.vn/",
    "0400462489": "https://e-invoicetuanchau.com/Tra-cuu",
    "0401486901": "https://tracuu.vin-hoadon.com/tracuuhoadon/tracuuxacthuc/tracuuhd",
    "0110269067": "https://gsm-einvoice.hilo.com.vn/",
    "0110269067-002": "https://gsm-einvoice.hilo.com.vn/",
}

def resolve_lookup_url(msttcgp: str, seller_mst: str, mccqt: str, invoice_number: str) -> str:
    """Resolve lookup portal verification link from provider tax code and invoice metadata."""
    if not msttcgp:
        return ""
    
    msttcgp_clean = msttcgp.strip()
    seller_mst_clean = seller_mst.strip()
    mccqt_clean = mccqt.strip() if mccqt else ""

    # VNPT Special Case
    if msttcgp_clean == "0100684378":
        if mccqt_clean:
            return f"https://{seller_mst_clean}-tt78.vnpt-invoice.com.vn/?strFkey={mccqt_clean}"
        return "https://portaltool-miennam.vnpt-invoice.com.vn/"
    
    # BKAV Special Case
    if msttcgp_clean == "0101360697":
        return f"https://van.ehoadon.vn/Lookup?InvoiceGUID={invoice_number}"

    # Softdreams / EasyInvoice Special Case
    if msttcgp_clean == "0105987432":
        return f"https://{seller_mst_clean}hd.easyinvoice.com.vn"

    # Match in mapping table
    base_url = PROVIDER_LOOKUP_MAP.get(msttcgp_clean, "")
    return base_url


def parse_complete_xml(xml_bytes: bytes) -> dict:
    """Parse all detailed fields and line items from a GDT standard XML invoice."""

    try:
        root = ET.fromstring(xml_bytes)
        # Strip XML namespaces for easier XPath searching
        for elem in root.iter():
            if "}" in elem.tag:
                elem.tag = elem.tag.split("}", 1)[1]

        # Extract general info
        title = root.findtext(".//THDon") or root.findtext(".//tenHDon") or "Hóa đơn giá trị gia tăng"
        template = root.findtext(".//KHMSHDon") or root.findtext(".//khmshdon") or "1"
        symbol = root.findtext(".//KHHDon") or root.findtext(".//khhdon") or "C26TBA"

        # Number: pad with zeros to make it 8 digits if it's a numeric string less than 8 digits
        number_raw = root.findtext(".//SHDon") or root.findtext(".//shdon") or "00000000"
        try:
            number = f"{int(number_raw):08d}"
        except ValueError:
            number = number_raw

        # Date: try multiple formats
        date_raw = root.findtext(".//NLap") or root.findtext(".//ngay") or ""
        invoice_date = ""
        if date_raw:
            try:
                # E.g. 2026-05-21T10:00:00 or 2026-05-21
                invoice_date = date_raw.split("T")[0]
            except Exception:
                invoice_date = date_raw
        if not invoice_date:
            invoice_date = date.today().isoformat()

        currency = root.findtext(".//DVTTe") or root.findtext(".//dvtte") or "VND"
        payment_method = root.findtext(".//HTTToan") or root.findtext(".//htttoan") or ""

        # GDT and Provider info
        mccqt = (root.findtext(".//MCCQT") or root.findtext(".//mccqt") or "").strip()
        msttcgp = (root.findtext(".//MSTTCGP") or root.findtext(".//msttcgp") or "").strip()
        
        exchange_rate_raw = root.findtext(".//TGia") or root.findtext(".//tgia") or "1.0"
        try:
            exchange_rate = float(exchange_rate_raw.replace(",", ""))
        except ValueError:
            exchange_rate = 1.0

        # Seller
        seller_node = root.find(".//NBan")
        if seller_node is None:
            seller_node = root.find(".//nban")
        seller_name = ""
        seller_mst = ""
        seller_address = ""
        seller_phone = ""
        if seller_node is not None:
            seller_name = seller_node.findtext("Ten") or seller_node.findtext("ten") or ""
            seller_mst = seller_node.findtext("MST") or seller_node.findtext("mst") or ""
            seller_address = seller_node.findtext("DChi") or seller_node.findtext("dchi") or ""
            seller_phone = seller_node.findtext("SDThoai") or seller_node.findtext("sdt") or ""

        # Buyer
        buyer_node = root.find(".//NMua")
        if buyer_node is None:
            buyer_node = root.find(".//nmua")
        buyer_name = ""
        buyer_mst = ""
        buyer_address = ""
        if buyer_node is not None:
            buyer_name = buyer_node.findtext("TenDonVi") or buyer_node.findtext("tenDonVi") or buyer_node.findtext("Ten") or buyer_node.findtext("ten") or ""
            buyer_mst = buyer_node.findtext("MST") or buyer_node.findtext("mst") or ""
            buyer_address = buyer_node.findtext("DChi") or buyer_node.findtext("dchi") or ""

        # Financial totals
        amount_before_tax_text = root.findtext(".//TgTCThue") or root.findtext(".//tgtcThue") or "0"
        tax_amount_text = root.findtext(".//TgTThue") or root.findtext(".//tgtThue") or "0"
        total_amount_text = root.findtext(".//TgTTTBSo") or root.findtext(".//tgtttbSo") or "0"

        try:
            amount_before_tax = float(amount_before_tax_text.replace(",", ""))
            tax_amount = float(tax_amount_text.replace(",", ""))
            total_amount = float(total_amount_text.replace(",", ""))
        except ValueError:
            amount_before_tax = 0.0
            tax_amount = 0.0
            total_amount = 0.0

        # Items
        items = []
        for hhdvu in root.findall(".//HHDVu"):
            item_name = hhdvu.findtext("Ten") or hhdvu.findtext("ten") or hhdvu.findtext("TChat") or ""
            if not item_name.strip():
                continue

            unit = hhdvu.findtext("DVT") or hhdvu.findtext("dvt") or ""
            quantity_text = hhdvu.findtext("SLuong") or "0"
            price_text = hhdvu.findtext("DGia") or "0"
            amount_text = hhdvu.findtext("ThTien") or "0"
            tax_rate = hhdvu.findtext("TSuat") or "10%"
            item_tax_amount_text = hhdvu.findtext("TThue") or "0"

            # Discount values
            discount_rate_text = hhdvu.findtext("TLCKhau") or hhdvu.findtext("tlckhau") or "0"
            discount_amount_text = hhdvu.findtext("STCKhau") or hhdvu.findtext("stckhau") or "0"
            amount_after_tax_text = hhdvu.findtext("ThTcthue") or hhdvu.findtext("thtcthue") or "0"

            try:
                quantity = float(quantity_text.replace(",", ""))
                unit_price = float(price_text.replace(",", ""))
                item_amount_before_tax = float(amount_text.replace(",", ""))
                item_tax_amount = float(item_tax_amount_text.replace(",", ""))
                
                discount_rate = float(discount_rate_text.replace(",", ""))
                discount_amount = float(discount_amount_text.replace(",", ""))
                amount_after_tax = float(amount_after_tax_text.replace(",", ""))
            except ValueError:
                quantity = 0.0
                unit_price = 0.0
                item_amount_before_tax = 0.0
                item_tax_amount = 0.0
                discount_rate = 0.0
                discount_amount = 0.0
                amount_after_tax = 0.0

            # Fallback calculation if amount after tax is missing/zero
            if amount_after_tax == 0.0:
                amount_after_tax = item_amount_before_tax - discount_amount + item_tax_amount

            items.append({
                "item_name": item_name.strip(),
                "unit": unit.strip(),
                "quantity": quantity,
                "unit_price": unit_price,
                "amount_before_tax": item_amount_before_tax,
                "tax_rate": tax_rate.strip(),
                "tax_amount": item_tax_amount,
                "discount_rate": discount_rate,
                "discount_amount": discount_amount,
                "amount_after_tax": amount_after_tax
            })

        # fallbacks
        if amount_before_tax == 0.0 and items:
            amount_before_tax = sum(item["amount_before_tax"] for item in items)
        if tax_amount == 0.0 and items:
            tax_amount = sum(item["tax_amount"] for item in items)
        if total_amount == 0.0:
            total_amount = amount_before_tax + tax_amount

        # Signature
        has_signature = root.find(".//Signature") is not None or root.find(".//SignatureValue") is not None

        # Try to parse signing date (NgayKy, SigningTime, etc.)
        signing_date_raw = None
        for tag in [".//SigningTime", ".//signingTime", ".//NgayKy", ".//ngayKy", ".//NgayKyHDon"]:
            node = root.find(tag)
            if node is not None and node.text:
                signing_date_raw = node.text.strip()
                break

        signing_date = None
        if signing_date_raw:
            try:
                # E.g. "2026-05-22T10:00:00" or "2026-05-22" or "2026/05/22"
                # Strip time part if present
                clean_date = signing_date_raw.split("T")[0].replace("/", "-")
                # Ensure it fits YYYY-MM-DD
                datetime.strptime(clean_date[:10], "%Y-%m-%d")
                signing_date = clean_date[:10]
            except Exception:
                pass

        # Extract Lookup Code from TTKhac/TTChung/TTKhac
        lookup_code = ""
        lookup_keys_whitelist = {
            "tendviquly", "mã số bí mật", "masobimat", "reservationcode", "fkey", 
            "keysearch", "matc", "transactionid", "searchkey", "mã hóa đơn", "mahoadon",
            "matracuu", "mtcuu", "quanly_sobaomat", "client_id", "mã tra cứu", "mã tra cứu hóa đơn"
        }
        for tt_khac in root.findall(".//TTKhac"):
            # Try finding direct TTruong and DLieu children (flat format)
            ttruong_flat = tt_khac.find("TTruong")
            dlieu_flat = tt_khac.find("DLieu")
            if ttruong_flat is not None and dlieu_flat is not None:
                t_val = (ttruong_flat.text or "").strip().lower()
                if t_val in lookup_keys_whitelist:
                    lookup_code = (dlieu_flat.text or "").strip()
                    break
            
            # Try finding nested DLieuBsung/etc. containers
            for child in tt_khac:
                ttruong_elem = child.find("TTruong")
                dlieu_elem = child.find("DLieu")
                if ttruong_elem is not None and dlieu_elem is not None:
                    ttruong_val = (ttruong_elem.text or "").strip().lower()
                    if ttruong_val in lookup_keys_whitelist:
                        lookup_code = (dlieu_elem.text or "").strip()
                        break
            if lookup_code:
                break

        # Generate lookup link
        lookup_url = resolve_lookup_url(msttcgp, seller_mst, mccqt, number)

        # Tax Breakdown (THTTLTSuat)
        tax_breakdown = []
        thttltsuat = root.find(".//THTTLTSuat")
        if thttltsuat is None:
            thttltsuat = root.find(".//thttltsuat")
        if thttltsuat is not None:
            for ltsuat in thttltsuat.findall(".//LTSuat") or thttltsuat.findall(".//ltsuat"):
                tsuat = ltsuat.findtext("TSuat") or ltsuat.findtext("tsuat") or ""
                thtien_txt = ltsuat.findtext("ThTien") or ltsuat.findtext("thtien") or "0"
                tthue_txt = ltsuat.findtext("TThue") or ltsuat.findtext("tthue") or "0"
                gttsuat_txt = ltsuat.findtext("GTTSuat") or ltsuat.findtext("gttsuat") or "0"
                try:
                    thtien = float(thtien_txt.replace(",", ""))
                    tthue = float(tthue_txt.replace(",", ""))
                    gttsuat = float(gttsuat_txt.replace(",", ""))
                except ValueError:
                    thtien = 0.0
                    tthue = 0.0
                    gttsuat = 0.0
                tax_breakdown.append({
                    "tsuat": tsuat.strip(),
                    "thtien": thtien,
                    "tthue": tthue,
                    "gttsuat": gttsuat
                })

        # Fees/Surcharges Breakdown (THTTLPhi)
        fees_breakdown = []
        thttlphi = root.find(".//THTTLPhi")
        if thttlphi is None:
            thttlphi = root.find(".//thttlphi")
        if thttlphi is not None:
            for ltphi in thttlphi.findall(".//LTPhi") or thttlphi.findall(".//ltphi"):
                tlphi = ltphi.findtext("TLPhi") or ltphi.findtext("tlphi") or ""
                tphi_txt = ltphi.findtext("TPhi") or ltphi.findtext("tphi") or "0"
                try:
                    tphi = float(tphi_txt.replace(",", ""))
                except ValueError:
                    tphi = 0.0
                fees_breakdown.append({
                    "tlphi": tlphi.strip(),
                    "tphi": tphi
                })

        return {
            "invoice_type": title.strip(),
            "template_code": template.strip(),
            "symbol": symbol.strip(),
            "number": number.strip(),
            "date": invoice_date,
            "currency": currency.strip(),
            "seller_name": seller_name.strip(),
            "seller_mst": seller_mst.strip(),
            "seller_address": seller_address.strip(),
            "seller_phone": seller_phone.strip(),
            "buyer_name": buyer_name.strip(),
            "buyer_mst": buyer_mst.strip(),
            "buyer_address": buyer_address.strip(),
            "amount_before_tax": amount_before_tax,
            "tax_amount": tax_amount,
            "total_amount": total_amount,
            "items": items,
            "has_signature": has_signature,
            "signing_date": signing_date,
            "payment_method": payment_method.strip(),
            "mccqt": mccqt,
            "msttcgp": msttcgp,
            "exchange_rate": exchange_rate,
            "lookup_code": lookup_code,
            "lookup_url": lookup_url,
            "tax_breakdown": tax_breakdown,
            "fees_breakdown": fees_breakdown
        }
    except Exception as error:
        raise ValueError(f"Loi cu phap tep XML: {str(error)}")

