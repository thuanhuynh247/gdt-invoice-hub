import json
import logging
from datetime import datetime
from typing import Dict, List, Any

from extensions import db
from invoices.models import Invoice, LineItem, AIAuditResult, TaxpayerProfile
from invoices.ai_service import get_tax_rag_context, load_scheduler_settings

logger = logging.getLogger(__name__)

class VATRefundEligibilityEngine:
    """Engine to assess taxpayer eligibility for VAT refunds (Hoàn thuế GTGT) and generate compliance dossiers."""

    def get_eligibility(self, taxpayer_mst: str) -> Dict[str, Any]:
        """Calculates VAT refund eligibility and returns a detailed audit report."""
        profile = TaxpayerProfile.query.get(taxpayer_mst)
        if not profile:
            return {
                "error": f"Không tìm thấy MST người nộp thuế: {taxpayer_mst}",
                "is_eligible": False,
                "status": "High-Risk",
                "reason": "MST người nộp thuế không tồn tại.",
                "metrics": {},
                "eligible_invoices": [],
                "ineligible_invoices": []
            }

        # 1. Fetch all invoices for the MST
        invoices = Invoice.query.filter_by(taxpayer_mst=taxpayer_mst).all()
        
        purchase_invoices = [inv for inv in invoices if inv.invoice_type == "purchase"]
        sale_invoices = [inv for inv in invoices if inv.invoice_type == "sale"]

        # 2. Calculate Sales & Exports Metrics
        total_sales_amount = sum(inv.amount_before_tax for inv in sale_invoices)
        
        # Identify export sales (VAT rate is 0% or tax_amount == 0 and has 0% rate in items)
        export_sales_amount = 0.0
        for inv in sale_invoices:
            is_export = False
            # Check if total tax amount is zero and amount_before_tax > 0
            if inv.tax_amount == 0 and inv.amount_before_tax > 0:
                is_export = True
            else:
                # Or check items tax rate
                for item in inv.items:
                    if "0%" in item.tax_rate:
                        is_export = True
                        break
            if is_export:
                export_sales_amount += inv.amount_before_tax

        export_ratio = (export_sales_amount / total_sales_amount) if total_sales_amount > 0 else 0.0

        # 3. Categorize Purchase Invoices into Eligible vs Ineligible
        eligible_invoices = []
        ineligible_invoices = []
        
        total_input_vat = 0.0
        eligible_input_vat = 0.0
        disqualified_input_vat = 0.0

        for inv in purchase_invoices:
            vat = inv.tax_amount
            total_input_vat += vat
            
            disqualification_reasons = []

            # Rule 1: Cancelled invoices are ineligible
            if inv.is_cancelled:
                disqualification_reasons.append("Hóa đơn đã bị hủy (Cancelled)")

            # Rule 2: Signature requirement
            if not inv.has_signature:
                disqualification_reasons.append("Thiếu chữ ký số hợp lệ")

            # Rule 3: Blacklisted supplier or low T-Score
            if inv.t_score < 50:
                disqualification_reasons.append(f"Điểm tin cậy nhà cung cấp thấp (T-Score: {inv.t_score}/100)")
            
            warnings = inv.warnings or []
            if any("BLACKLIST" in w or "CẢNH BÁO" in w for w in warnings):
                disqualification_reasons.append("Nhà cung cấp nằm trong danh sách đen/rủi ro cao của Tổng cục Thuế")

            # Rule 4: Cryptographic tampering warning
            for audit in inv.ai_audit_results:
                if audit.warning_type == "CRITICAL_SIGNATURE_TAMPER":
                    disqualification_reasons.append("Phát hiện giả mạo cấu trúc XML hoặc chữ ký số bị thay đổi")

            # Rule 5: Non-cash payment compliance (Threshold >= 20M VND)
            if inv.total_amount >= 20000000:
                payment_method = (inv.payment_method or "").lower()
                is_cash = any(kw in payment_method for kw in ["tm", "tiền mặt", "cash"])
                
                # Check for cash payment warnings from AI Auditor
                has_cash_risk = any(audit.warning_type == "cash_payment_risk" for audit in inv.ai_audit_results)
                
                if is_cash or has_cash_risk:
                    disqualification_reasons.append("Vi phạm thanh toán bằng tiền mặt đối với hóa đơn trị giá từ 20 triệu VND trở lên")

            if disqualification_reasons:
                disqualified_input_vat += vat
                inv_dict = inv.to_dict()
                inv_dict["disqualification_reasons"] = disqualification_reasons
                ineligible_invoices.append(inv_dict)
            else:
                eligible_input_vat += vat
                eligible_invoices.append(inv.to_dict())

        # 4. Apply Vietnam Tax Policy Eligibility Rules
        # Eligible if accumulated eligible input VAT >= 300,000,000 VND
        general_eligible = eligible_input_vat >= 300000000
        
        # Or if export ratio >= 10% and eligible input VAT >= 300,000,000 VND
        export_eligible = (export_ratio >= 0.10) and (eligible_input_vat >= 300000000)

        is_eligible = general_eligible or export_eligible

        # 5. Define UX Status Rating (Safe, Caution, High-Risk)
        if is_eligible:
            # Safe if ineligible VAT is low (< 10% of total input VAT)
            if total_input_vat > 0 and (disqualified_input_vat / total_input_vat) < 0.10:
                status = "Safe"
                reason_detail = "Doanh nghiệp đủ điều kiện hoàn thuế. Tỷ lệ hóa đơn lỗi thấp, mức độ an toàn hồ sơ cao."
            else:
                status = "Caution"
                reason_detail = "Đủ điều kiện hoàn thuế về mặt tổng số tiền, nhưng phát hiện một số hóa đơn rủi ro cao bị loại trừ. Cần kiểm tra kỹ danh sách loại trừ."
        else:
            status = "High-Risk"
            if eligible_input_vat >= 250000000:
                status = "Caution"
                reason_detail = "Chưa đạt ngưỡng hoàn thuế tối thiểu 300 triệu VND (Hiện tại đạt {:.1f} triệu VND). Hãy tiếp tục tích lũy hóa đơn đầu vào.".format(eligible_input_vat / 1000000)
            else:
                reason_detail = "Chưa đủ điều kiện hoàn thuế. Số thuế GTGT đầu vào hợp lệ hiện tại ({:.1f} triệu VND) chưa đạt ngưỡng tối thiểu 300 triệu VND.".format(eligible_input_vat / 1000000)

        reason = f"Trạng thái: {status}. {reason_detail}"
        if export_eligible:
            reason += " (Đủ điều kiện theo diện Doanh nghiệp Xuất khẩu với tỷ lệ xuất khẩu đạt {:.1f}%).".format(export_ratio * 100)
        elif general_eligible:
            reason += " (Đủ điều kiện theo diện Dự án đầu tư / Tích lũy sản xuất kinh doanh)."

        return {
            "mst": taxpayer_mst,
            "company_name": profile.company_name,
            "is_eligible": is_eligible,
            "status": status,
            "reason": reason,
            "metrics": {
                "total_sales_amount": total_sales_amount,
                "export_sales_amount": export_sales_amount,
                "export_ratio": export_ratio,
                "total_input_vat": total_input_vat,
                "eligible_input_vat": eligible_input_vat,
                "disqualified_input_vat": disqualified_input_vat,
                "eligible_invoice_count": len(eligible_invoices),
                "ineligible_invoice_count": len(ineligible_invoices),
            },
            "eligible_invoices": eligible_invoices,
            "ineligible_invoices": ineligible_invoices
        }

    def generate_dossier(self, taxpayer_mst: str) -> Dict[str, Any]:
        """Generates the official Circular 80 Mẫu 01/HT refund dossier and AI justification letter."""
        eligibility = self.get_eligibility(taxpayer_mst)
        if "error" in eligibility:
            return eligibility

        metrics = eligibility["metrics"]
        eligible_vat = metrics.get("eligible_input_vat", 0.0)
        company_name = eligibility["company_name"]
        
        # 1. Gather Legal RAG Context
        rag_context = get_tax_rag_context("hoàn thuế giá trị gia tăng thông tư 80/2021/tt-btc xuất khẩu dự án đầu tư")
        
        # 2. Rules-based template generation (fallback)
        now = datetime.now()
        date_str = f"ngày {now.day} tháng {now.month} năm {now.year}"
        
        mau_01_ht = f"""CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Độc lập - Tự do - Hạnh phúc
----------------

MẪU 01/HT
(Ban hành kèm theo Thông tư số 80/2021/TT-BTC ngày 29/9/2021 của Bộ Tài chính)

GIẤY ĐỀ NGHỊ HOÀN TRẢ KHOẢN THU NGÂN SÁCH NHÀ NƯỚC

Kính gửi: Cục Thuế Tỉnh/Thành phố nơi đặt trụ sở chính.

1. Tên người nộp thuế: {company_name.upper()}
2. Mã số thuế: {taxpayer_mst}
3. Địa chỉ trụ sở chính: Địa chỉ đăng ký kinh doanh của doanh nghiệp
4. Điện thoại: 024.xxxx.xxxx
5. Tài khoản ngân hàng số: 190xxxxxxxxxx tại Ngân hàng Thương mại Cổ phần Ngoại thương Việt Nam (Vietcombank)

ĐỀ NGHỊ HOÀN TRẢ KHOẢN THU NGÂN SÁCH NHÀ NƯỚC NHƯ SAU:

I. Thông tin về khoản thu đề nghị hoàn trả:
1. Loại thuế đề nghị hoàn: Thuế Giá trị gia tăng (GTGT) đầu vào tích lũy.
2. Lý do đề nghị hoàn thuế: 
   {"- Hoàn thuế đối với hàng hóa, dịch vụ xuất khẩu theo quy định tại Điều 16 Thông tư 219/2013/TT-BTC." if metrics.get("export_ratio", 0) >= 0.10 else "- Hoàn thuế đối với dự án đầu tư / hoạt động sản xuất kinh doanh tích lũy vượt ngưỡng quy định tại Thông tư 80/2021/TT-BTC."}
3. Kỳ tính thuế đề nghị hoàn: Từ tháng 01/2026 đến tháng 05/2026.
4. Số tiền đề nghị hoàn trả: {eligible_vat:,.0f} VND (Bằng chữ: {self._spell_amount(eligible_vat)} đồng).

II. Hồ sơ đính kèm:
1. Bảng kê hóa đơn, chứng từ hàng hóa dịch vụ mua vào hợp lệ (Số lượng: {metrics.get("eligible_invoice_count", 0)} hóa đơn).
2. Chứng từ thanh toán qua ngân hàng không dùng tiền mặt đối với các hóa đơn có giá trị từ 20 triệu VND trở lên.
3. Hợp đồng xuất khẩu và tờ khai hải quan (đối với diện xuất khẩu).

Chúng tôi xin cam đoan số liệu khai báo trên là hoàn toàn trung thực, chính xác và chịu trách nhiệm trước pháp luật về tính hợp pháp của toàn bộ hồ sơ này.

 Hà Nội, {date_str}
ĐẠI DIỆN HỢP PHÁP CỦA DOANH NGHIỆP
(Ký, ghi rõ họ tên và đóng dấu)
"""

        # Generate the AI Audit Justification letter
        ineligible_list = eligibility["ineligible_invoices"]
        anomalies_str = ""
        if ineligible_list:
            anomalies_str = "\n".join(
                f"- Hóa đơn số {inv['number']} mua của {inv['seller_name']} (MST: {inv['seller_mst']}), tiền thuế {inv['tax_amount']:,.0f} VND: bị loại trừ do {', '.join(inv['disqualification_reasons'])}."
                for inv in ineligible_list[:5]
            )
            if len(ineligible_list) > 5:
                anomalies_str += f"\n- Và {len(ineligible_list) - 5} hóa đơn khác bị loại trừ rủi ro..."
        else:
            anomalies_str = "- Không phát hiện hóa đơn rủi ro cao bị loại trừ trong kỳ."

        # Construct Prompt for LLM
        prompt = f"""Bạn là một chuyên gia tư vấn thuế và kiểm toán cao cấp tại Việt Nam. 
Hãy soạn thảo một bản GIẢI TRÌNH PHƯƠNG ÁN AN TOÀN HỒ SƠ HOÀN THUẾ (Audit Defense & Justification Dossier) gửi cho Ban giám đốc doanh nghiệp {company_name} (MST: {taxpayer_mst}).

Thông tin hồ sơ hoàn thuế:
- Số tiền thuế GTGT đề nghị hoàn hợp lệ: {eligible_vat:,.0f} VND.
- Tổng số hóa đơn hợp lệ: {metrics.get('eligible_invoice_count', 0)}.
- Số hóa đơn bị loại trừ do rủi ro: {metrics.get('ineligible_invoice_count', 0)}.
- Danh sách các hóa đơn bị loại trừ/cần giải trình:
{anomalies_str}

Cơ sở pháp lý tham khảo:
{rag_context}

Yêu cầu bản giải trình:
1. Viết bằng tiếng Việt chuyên nghiệp, ngôn từ trang trọng của ngành kiểm toán/luật thuế.
2. Nêu rõ phương án xử lý đối với các hóa đơn bị loại trừ (ví dụ: liên hệ nhà cung cấp phát hành hóa đơn điều chỉnh/thay thế, tìm kiếm chứng từ thanh toán ngân hàng bị thất lạc, loại hẳn khỏi hồ sơ hoàn thuế để tránh bị phạt trốn thuế).
3. Đưa ra khuyến nghị chi tiết cho Kế toán trưởng để chuẩn bị đón đoàn thanh tra thuế (kiểm tra trước hoàn sau).
4. Phân tích cụ thể các rủi ro từ Luật Thuế GTGT 48/2024/QH15 mới hiệu lực từ 01/07/2025.
"""

        justification_letter = ""
        settings = load_scheduler_settings()
        ai_enabled = settings.get("ai_enabled", False)
        
        if ai_enabled:
            try:
                # Call local LLM or Gemini API
                provider = settings.get("ai_provider", "ollama")
                url = settings.get("ai_api_url", "http://localhost:11434/api/chat" if provider == "ollama" else "")
                
                if provider == "ollama":
                    payload = {
                        "model": settings.get("ai_model", "gemma:2b"),
                        "messages": [{"role": "user", "content": prompt}],
                        "stream": False
                    }
                    resp = requests.post(url, json=payload, timeout=30)
                    resp.raise_for_status()
                    justification_letter = resp.json().get("message", {}).get("content", "").strip()
                elif provider == "gemini":
                    headers = {"Content-Type": "application/json"}
                    api_key = decrypt_password(settings.get("ai_api_key_encrypted", ""))
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
                    payload = {
                        "contents": [{"parts": [{"text": prompt}]}]
                    }
                    resp = requests.post(url, json=payload, headers=headers, timeout=30)
                    resp.raise_for_status()
                    justification_letter = resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
            except Exception as e:
                logger.warning(f"LLM refund dossier generation failed: {e}. Falling back to rule-based explanation letter.")

        if not justification_letter:
            # Rules-based fallback dossier
            justification_letter = f"""BÁO CÁO PHÂN TÍCH RỦI RO & BẢO VỆ HỒ SƠ HOÀN THUẾ GTGT
Kính gửi: Ban Giám đốc và Kế toán trưởng - {company_name}

Căn cứ vào dữ liệu hóa đơn điện tử được đồng bộ từ Tổng cục Thuế (GDT) và lịch sử thanh toán ngân hàng, chúng tôi xin gửi báo cáo đánh giá rủi ro cho hồ sơ đề nghị hoàn thuế GTGT kỳ này:

1. Đánh giá tính khả thi và Hồ sơ Hợp lệ:
   - Tổng số thuế đề nghị hoàn hợp lệ: {eligible_vat:,.0f} VND.
   - Hồ sơ đủ điều kiện pháp lý để nộp cơ quan thuế quản lý trực tiếp theo hướng dẫn tại Thông tư 80/2021/TT-BTC.
   - Tỷ lệ hồ sơ đạt mức đánh giá: {eligibility['status']} (Mức độ tin cậy cao).

2. Phân tích chi tiết và Phương án xử lý các hóa đơn bị loại trừ:
{anomalies_str}

Khuyến nghị xử lý:
   - Đối với hóa đơn bị loại trừ do thanh toán tiền mặt >= 20M VND: Kế toán cần rà soát lại sổ phụ ngân hàng xem có giao dịch chuyển khoản đối ứng bị sót hay không. Nếu thực tế đã thanh toán tiền mặt, bắt buộc phải loại khỏi hồ sơ hoàn thuế kỳ này theo quy định tại Điều 15 Thông tư 219/2013/TT-BTC.
   - Đối với hóa đơn có nhà cung cấp rủi ro cao (T-Score < 50): Cần chủ động chuẩn bị sẵn bộ hồ sơ chứng minh tính thực tế của giao dịch (Hợp đồng mua bán, biên bản giao nhận hàng hóa, phiếu nhập kho, chứng từ thanh toán ngân hàng) để giải trình khi cơ quan thuế yêu cầu.

3. Khuyến nghị chuẩn bị thanh tra thuế ("Kiểm trước hoàn sau"):
   - Sắp xếp hồ sơ hóa đơn mua vào theo thứ tự bảng kê kèm theo chứng từ thanh toán không dùng tiền mặt (giấy báo nợ, ủy nhiệm chi).
   - Kiểm tra kỹ thời điểm ký số của người bán trên hóa đơn. Rà soát rủi ro ký chậm (ký muộn quá 10 ngày kể từ ngày lập) để sẵn sàng giải trình chênh lệch thời gian ghi nhận thuế GTGT.
   - Đặc biệt lưu ý quy định mới tại Luật Thuế GTGT 48/2024/QH15 hiệu lực từ 01/07/2025: Ngưỡng thanh toán không dùng tiền mặt bắt buộc được hạ xuống còn từ 5 triệu VND trở lên đối với các giao dịch phát sinh từ thời điểm này.

Người lập báo cáo: Hệ thống Trí tuệ Nhân tạo meInvoice AI Compliance Oracle.
"""

        return {
            "status": "success",
            "mst": taxpayer_mst,
            "company_name": company_name,
            "is_eligible": eligibility["is_eligible"],
            "eligibility_status": eligibility["status"],
            "eligible_vat": eligible_vat,
            "mau_01_ht": mau_01_ht,
            "justification_letter": justification_letter
        }

    def _spell_amount(self, amount: float) -> str:
        """Helper to spell monetary amount in Vietnamese words."""
        try:
            from invoices.ai_service import spell_money_vietnamese
            return spell_money_vietnamese(int(amount))
        except Exception:
            # Fallback spell
            return f"Bằng số: {amount:,.0f}"
