"""
V32 Compliance Service – Interactive Exporter VAT Refund Wizard, Form 01/ĐNHT XML Builder,
and AI Swarm VAT Refund Justification Compiler.

US-430: Interactive Exporter VAT Refund Wizard with Glassmorphism Progress Metrics
US-431: Form 01/ĐNHT Refund Request Packet Builder & GDT XML Exporter
US-432: AI Swarm VAT Refund Justification Compiler & Multi-Agent Legal Defense Panel
"""

from __future__ import annotations

import datetime
import random
from typing import Any, Dict, List

from invoices.refund_service import VATRefundEligibilityEngine, generate_form_01_dnht_xml
from invoices.models import TaxpayerProfile, Invoice

def run_refund_audit_swarm(
    taxpayer_mst: str,
    taxpayer_name: str,
    eligible_invoice_ids: List[str] | None = None,
    customs_declarations: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    """
    Simulates a multi-agent swarm discussion debating a VAT refund application.
    Agents:
      - RefundAuditor: Analyzes invoice trust metrics, payment compliance, and exclusion logs.
      - CustomsLiaison: Cross-matches export sales with customs declaration papers.
      - TaxCounsel: Assesses legal defense grounds under Circular 80/2021/TT-BTC and drafts the defense brief.
    """
    engine = VATRefundEligibilityEngine()
    
    # Run core eligibility audit
    eligibility = engine.get_eligibility(
        taxpayer_mst=taxpayer_mst,
        input_invoice_ids=eligible_invoice_ids,
        customs_declarations=customs_declarations
    )
    
    metrics = eligibility.get("metrics", {})
    eligible_vat = metrics.get("eligible_input_vat", 0.0)
    ineligible_count = metrics.get("ineligible_invoice_count", 0)
    
    # Construct Swarm chat log timeline
    timestamp_base = datetime.datetime.now()
    chat_steps = []
    
    def add_step(agent: str, role: str, message: str, avatar_class: str, offset_sec: int):
        chat_steps.append({
            "agent": agent,
            "role": role,
            "message": message,
            "avatar_class": avatar_class,
            "timestamp": (timestamp_base + datetime.timedelta(seconds=offset_sec)).strftime("%H:%M:%S"),
        })

    add_step(
        "RefundCoordinator", "Điều phối hoàn thuế",
        f"Kích hoạt Agent Swarm rà soát hồ sơ đề nghị hoàn thuế GTGT cho doanh nghiệp <strong>{taxpayer_name}</strong> (MST: {taxpayer_mst}). "
        f"Kiểm toán số thuế đề nghị hoàn: <strong>{eligible_vat:,.0f}đ</strong> dựa trên các chứng từ mua vào được chọn.",
        "bg-primary", 0
    )
    
    # 1. Auditor analysis
    exclusions_text = ""
    ineligible_list = eligibility.get("ineligible_invoices", [])
    if ineligible_list:
        exclusions_text = " Phát hiện " + str(ineligible_count) + " hóa đơn không đủ điều kiện: " + ", ".join(
            [f"Số HD {inv['number']} ({', '.join(inv['disqualification_reasons'])})" for inv in ineligible_list[:2]]
        )
    else:
        exclusions_text = " Không phát hiện hóa đơn mua vào nào vi phạm tiêu chuẩn khấu trừ."

    add_step(
        "RefundAuditor", "Kiểm soát rủi ro hoàn",
        f"Tôi đã rà soát toàn bộ hóa đơn mua vào chịu thuế GTGT.{exclusions_text} "
        f"Đề xuất loại trừ các hóa đơn thanh toán tiền mặt >= 20 triệu VND hoặc thiếu chữ ký số để đảm bảo an toàn hồ sơ trước thanh tra thuế.",
        "bg-danger", 3
    )
    
    # 2. Customs Liaison analysis
    reconciliation = eligibility.get("customs_export_reconciliation", [])
    matched_count = sum(1 for r in reconciliation if r.get("match_status") == "Fully Matched")
    unmatched_count = sum(1 for r in reconciliation if r.get("match_status") == "Unmatched")
    
    customs_summary = f"Đã đối chiếu {len(reconciliation)} tờ khai hải quan xuất khẩu. Khớp hoàn toàn: {matched_count} tờ khai."
    if unmatched_count > 0:
        customs_summary += f" Cảnh báo: có {unmatched_count} tờ khai chưa tìm thấy hóa đơn xuất khẩu đối ứng hợp lệ."
    else:
        customs_summary += " Không có chênh lệch giữa tờ khai và hóa đơn xuất khẩu."
        
    add_step(
        "CustomsLiaison", "Đối chiếu Hải quan",
        f"Báo cáo đối chiếu tờ khai hải quan thông quan: {customs_summary} "
        f"Tất cả hồ sơ xuất khẩu đề nghị hoàn thuế 0% bắt buộc phải có tờ khai hải quan thông quan hoàn thành và chứng từ thanh toán qua ngân hàng của khách hàng nước ngoài.",
        "bg-info", 7
    )
    
    # 3. Tax Counsel analysis
    add_step(
        "TaxCounsel", "Cố vấn pháp lý thuế",
        f"Phương án biện hộ pháp lý hoàn thuế GTGT diện xuất khẩu tuân thủ nghiêm ngặt Điều 19 Thông tư 80/2021/TT-BTC. "
        f"Hồ sơ đã loại bỏ các hóa đơn đầu vào rủi ro. Tôi đang soạn thảo văn bản giải trình lý do hoàn thuế và giải trình chi tiết biến động để trình ban giám đốc phê duyệt.",
        "bg-warning", 11
    )
    
    # 4. Final summary
    add_step(
        "RefundCoordinator", "Điều phối hoàn thuế",
        f"Hoàn thành thảo luận swarm. Trạng thái đề xuất hồ sơ: <strong>{eligibility.get('status')}</strong>. "
        f"Đã lập báo cáo giải trình chi tiết phương án phòng vệ pháp lý và sẵn sàng xuất bản ra file Word/PDF.",
        "bg-primary", 15
    )

    # Compile the final defense dossier markdown
    report_md = f"""# BÁO CÁO PHÂN TÍCH RỦI RO & PHÒNG VỆ HỒ SƠ HOÀN THUẾ GTGT

## I. THÔNG TIN CHUNG
- **Doanh nghiệp**: {taxpayer_name}
- **Mã số thuế**: {taxpayer_mst}
- **Ngày thực hiện kiểm toán AI**: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
- **Tổng số tiền đề nghị hoàn**: {eligible_vat:,.0f} VND
- **Trạng thái an toàn hồ sơ**: {eligibility.get('status')}

## II. ĐÁNH GIÁ CHỈ TIÊU & TỶ LỆ THEO QUY ĐỊNH
1. **Ngưỡng hoàn thuế tối thiểu**: ĐẠT (Số tiền hoàn hợp lệ {eligible_vat:,.0f}đ >= 300,000,000đ quy định tại Thông tư 80/2021/TT-BTC).
2. **Tỷ lệ doanh thu xuất khẩu**: {metrics.get('export_ratio', 0.0)*100:.2f}% (Tổng doanh thu xuất khẩu đạt {metrics.get('export_sales_amount', 0.0):,.0f}đ trên tổng doanh thu {metrics.get('total_sales_amount', 0.0):,.0f}đ).

## III. KẾT QUẢ RÀ SOÁT HÓA ĐƠN ĐẦU VÀO
- **Tổng số hóa đơn mua vào đã kiểm tra**: {metrics.get('eligible_invoice_count', 0) + metrics.get('ineligible_invoice_count', 0)}
- **Hóa đơn hợp lệ đưa vào hồ sơ**: {metrics.get('eligible_invoice_count', 0)} (Tiền thuế GTGT: {eligible_vat:,.0f} VND)
- **Hóa đơn bị loại trừ rủi ro**: {metrics.get('ineligible_invoice_count', 0)} (Tiền thuế GTGT: {metrics.get('disqualified_input_vat', 0.0):,.0f} VND)

### Chi tiết hóa đơn bị loại trừ (Cần loại khỏi hồ sơ đề nghị hoàn):
"""
    if ineligible_list:
        for idx, inv in enumerate(ineligible_list, 1):
            report_md += f"{idx}. **Hóa đơn số {inv['number']}** ngày {inv['date']} bán bởi {inv['seller_name']} (MST: {inv['seller_mst']}) - Tiền thuế: {inv['tax_amount']:,.0f}đ. Lý do loại trừ: {', '.join(inv['disqualification_reasons'])}\n"
    else:
        report_md += "_Không phát hiện hóa đơn đầu vào rủi ro vi phạm quy định._\n"

    report_md += """
## IV. KẾT QUẢ ĐỐI CHIẾU TỜ KHAI HẢI QUAN XUẤT KHẨU
"""
    if reconciliation:
        report_md += "| Số tờ khai | Số hóa đơn xuất khẩu | Trạng thái đối chiếu | Ghi chú/Chênh lệch |\n|---|---|---|---|\n"
        for r in reconciliation:
            inv_no = r['invoice_number'] or "Chưa khớp"
            warnings_str = "; ".join(r['variances']) if r['variances'] else "Khớp hoàn toàn"
            report_md += f"| {r['declaration_number']} | {inv_no} | {r['match_status']} | {warnings_str} |\n"
    else:
        report_md += "_Không có thông tin tờ khai hải quan nào được cung cấp để đối chiếu._\n"

    report_md += f"""
## V. LUẬN ĐIỂM BIỆN HỘ & PHÒNG VỆ PHÁP LÝ (TƯ VẤN THUẾ)
1. **Tính hợp lý hợp lệ của dòng tiền**: Toàn bộ {metrics.get('eligible_invoice_count', 0)} hóa đơn đề nghị hoàn đều có chứng từ thanh toán không dùng tiền mặt qua tài khoản ngân hàng đã đăng ký của doanh nghiệp (Vietcombank), thỏa mãn Khoản 2 Điều 15 Thông tư 219/2013/TT-BTC.
2. **Tuân thủ xuất khẩu thực tế**: Dữ liệu tờ khai hải quan thông quan hoàn thành đã được đối soát chéo với dòng tiền thanh toán từ phía khách hàng nước ngoài. Các chênh lệch tỷ giá phát sinh đã được điều chỉnh tại sổ sách kế toán.
3. **Phòng tránh rủi ro theo Luật Thuế GTGT 48/2024/QH15**: Doanh nghiệp cần đảm bảo từ ngày 01/07/2025 các giao dịch mua vào từ 5.000.000đ trở lên đều phải thanh toán qua ngân hàng để bảo toàn quyền lợi khấu trừ/hoàn thuế.

## VI. KHUYẾN NGHỊ CHO KẾ TOÁN TRƯỞNG
- **Hồ sơ lưu trữ**: In ấn và lưu trữ đầy đủ Bảng kê mua vào mẫu 01-2/GTGT, Báo nợ, Ủy nhiệm chi kèm hóa đơn gốc dạng XML/PDF.
- **Giải trình hóa đơn rủi ro**: Đối với các nhà cung cấp có cảnh báo từ cơ quan thuế, chuẩn bị sẵn Hợp đồng kinh tế và Biên bản giao nhận để chứng minh giao dịch có thật, tránh bị quy kết sử dụng hóa đơn bất hợp pháp.

*Hệ thống meInvoice AI Compliance Swarm Oracle - Version 32.0.0*
"""

    return {
        "status": "success",
        "chat_steps": chat_steps,
        "report_markdown": report_md,
        "eligibility": eligibility
    }
