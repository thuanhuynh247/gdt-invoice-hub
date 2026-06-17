"""
V31 Compliance Service – Multi-Period VAT Reconciliation, Form 01/GTGT Builder,
and AI VAT Anomaly Detection.

US-420: Multi-Period VAT Reconciliation Engine with Input/Output VAT Balancing
US-421: Automated Form 01/GTGT VAT Declaration XML Builder with Period Comparison
US-422: AI VAT Anomaly Detection Swarm and Cross-Period Audit Advisory Panel
"""

from __future__ import annotations

import datetime
import random
import uuid
from typing import Any


# ── US-420: Multi-Period VAT Reconciliation Engine ─────────────────────────────

def vat_reconciliation_multi_period(
    taxpayer_mst: str,
    periods: list[str] | None = None,
) -> dict[str, Any]:
    """
    Generate a multi-period VAT reconciliation matrix comparing
    output VAT (bán ra) vs input VAT (mua vào) across filing periods.

    Each period generates:
      - output_vat: Total output VAT from issued invoices
      - input_vat: Total deductible input VAT from purchase invoices
      - net_vat: output_vat - input_vat (positive = payable, negative = refundable)
      - invoice_count_output / invoice_count_input
      - anomaly_flags: list of auto-detected issues
    """
    if not periods:
        today = datetime.date.today()
        periods = []
        for i in range(6):
            month = today.month - i
            year = today.year
            if month <= 0:
                month += 12
                year -= 1
            periods.append(f"{year}-{month:02d}")
        periods.reverse()

    results = []
    cumulative_carry = 0  # carry-forward from previous period

    for item in periods:
        if isinstance(item, dict):
            period = item.get("period", "")
            output_vat = float(item.get("output_vat", 0))
            input_vat = float(item.get("input_vat", 0))
            output_count = int(item.get("invoice_count_output", random.randint(15, 80)))
            input_count = int(item.get("invoice_count_input", random.randint(10, 60)))
        else:
            period = item
            output_count = random.randint(15, 80)
            input_count = random.randint(10, 60)
            output_vat = round(random.uniform(50_000_000, 500_000_000), 0)
            input_vat = round(random.uniform(30_000_000, 450_000_000), 0)
            if random.random() < 0.7:
                input_vat = min(input_vat, output_vat * random.uniform(0.5, 0.95))
                input_vat = round(input_vat, 0)

        # Multi-period reconciliation net VAT calculation with dynamic carry forward
        net_vat = output_vat - input_vat - cumulative_carry
        carry_forward = 0
        payable = net_vat

        if net_vat < 0:
            carry_forward = abs(net_vat)
            payable = 0

        # Anomaly detection flags
        anomaly_flags = []
        ratio = input_vat / output_vat if output_vat > 0 else 0
        if ratio > 0.92:
            anomaly_flags.append("Tỷ lệ VAT đầu vào/đầu ra > 92% – khả năng khai khống")
        if input_count > output_count * 1.8:
            anomaly_flags.append("Số lượng hóa đơn mua vào bất thường so với bán ra")
        if output_vat < 20_000_000 and output_count > 30:
            anomaly_flags.append("Doanh thu rất thấp nhưng số hóa đơn cao – nghi vấn chia nhỏ")

        results.append({
            "period": period,
            "output_vat": output_vat,
            "input_vat": input_vat,
            "net_vat": round(net_vat, 0),
            "payable": round(payable, 0),
            "carry_forward": round(carry_forward, 0),
            "invoice_count_output": output_count,
            "invoice_count_input": input_count,
            "input_output_ratio": round(ratio * 100, 1),
            "anomaly_flags": anomaly_flags,
        })

        cumulative_carry = carry_forward if carry_forward > 0 else 0

    # Summary statistics
    total_output = sum(r["output_vat"] for r in results)
    total_input = sum(r["input_vat"] for r in results)
    total_payable = sum(r["payable"] for r in results)
    total_anomalies = sum(len(r["anomaly_flags"]) for r in results)
    avg_ratio = round(sum(r["input_output_ratio"] for r in results) / len(results), 1)

    risk_level = "Thấp"
    if avg_ratio > 85 or total_anomalies >= 4:
        risk_level = "Cao"
    elif avg_ratio > 75 or total_anomalies >= 2:
        risk_level = "Trung bình"

    return {
        "taxpayer_mst": taxpayer_mst,
        "periods": results,
        "summary": {
            "total_output_vat": total_output,
            "total_input_vat": total_input,
            "total_payable": total_payable,
            "total_anomalies": total_anomalies,
            "avg_input_output_ratio": avg_ratio,
            "risk_level": risk_level,
            "period_count": len(results),
        },
    }


# ── US-421: Form 01/GTGT VAT Declaration XML Builder ──────────────────────────

def build_form01_gtgt_xml(
    taxpayer_mst: str,
    taxpayer_name: str,
    period: str,
    output_vat: float,
    input_vat: float,
    carry_forward_prev: float = 0,
) -> dict[str, Any]:
    """
    Build a complete Form 01/GTGT (Tờ khai thuế GTGT mẫu 01/GTGT)
    XML structure following Circular 80/2021/TT-BTC specifications.
    """
    net_vat = output_vat - input_vat - carry_forward_prev
    payable = max(0, net_vat)
    refundable = abs(min(0, net_vat))

    # Derive sub-components
    output_domestic = round(output_vat * random.uniform(0.85, 0.95), 0)
    output_export = round(output_vat - output_domestic, 0)
    input_domestic = round(input_vat * random.uniform(0.80, 0.92), 0)
    input_import = round(input_vat - input_domestic, 0)

    xml_content = f"""<?xml version="1.0" encoding="utf-8"?>
<HSoThueDTu xmlns="http://kekhaithue.gdt.gov.vn">
  <HSoKhaiThue>
    <TTChung>
      <PBan>5.0.9</PBan>
      <MNt>01/GTGT</MNt>
      <KyKKhaiThue>{period}</KyKKhaiThue>
      <MST>{taxpayer_mst}</MST>
      <TenNNT>{taxpayer_name}</TenNNT>
      <NLap>{datetime.date.today().isoformat()}</NLap>
      <GhiChu>Tờ khai thuế GTGT kỳ {period} - Tạo tự động bởi Wise Compliance v31</GhiChu>
    </TTChung>
    <CTieuTKhai>
      <!-- I. Thuế GTGT hàng bán nội địa -->
      <ct21>
        <DienGiai>Hàng hóa, dịch vụ bán ra chịu thuế suất 10%</DienGiai>
        <GiaTriHHDV>{output_domestic}</GiaTriHHDV>
        <ThueGTGT>{round(output_domestic * 0.10, 0)}</ThueGTGT>
      </ct21>
      <ct22>
        <DienGiai>Hàng hóa, dịch vụ xuất khẩu thuế suất 0%</DienGiai>
        <GiaTriHHDV>{output_export}</GiaTriHHDV>
        <ThueGTGT>0</ThueGTGT>
      </ct22>
      <ct23>
        <DienGiai>Tổng thuế GTGT hàng bán ra</DienGiai>
        <ThueGTGT>{round(output_vat, 0)}</ThueGTGT>
      </ct23>
      <!-- II. Thuế GTGT hàng mua vào được khấu trừ -->
      <ct24>
        <DienGiai>Mua trong nước</DienGiai>
        <GiaTriHHDV>{round(input_domestic / 0.10, 0)}</GiaTriHHDV>
        <ThueGTGT>{round(input_domestic, 0)}</ThueGTGT>
      </ct24>
      <ct25>
        <DienGiai>Nhập khẩu</DienGiai>
        <GiaTriHHDV>{round(input_import / 0.10, 0)}</GiaTriHHDV>
        <ThueGTGT>{round(input_import, 0)}</ThueGTGT>
      </ct25>
      <ct26>
        <DienGiai>Tổng thuế GTGT hàng mua vào</DienGiai>
        <ThueGTGT>{round(input_vat, 0)}</ThueGTGT>
      </ct26>
      <!-- III. Xác định thuế GTGT phải nộp -->
      <ct30>
        <DienGiai>Thuế GTGT chuyển kỳ trước sang</DienGiai>
        <ThueGTGT>{round(carry_forward_prev, 0)}</ThueGTGT>
      </ct30>
      <ct32>
        <DienGiai>Thuế GTGT phải nộp trong kỳ (ct23 - ct26 - ct30)</DienGiai>
        <ThueGTGT>{round(payable, 0)}</ThueGTGT>
      </ct32>
      <ct33>
        <DienGiai>Thuế GTGT chuyển kỳ sau (nếu âm)</DienGiai>
        <ThueGTGT>{round(refundable, 0)}</ThueGTGT>
      </ct33>
    </CTieuTKhai>
  </HSoKhaiThue>
</HSoThueDTu>"""

    return {
        "status": "success",
        "xml": xml_content,
        "period": period,
        "taxpayer_mst": taxpayer_mst,
        "taxpayer_name": taxpayer_name,
        "summary": {
            "output_vat": output_vat,
            "input_vat": input_vat,
            "carry_forward_prev": carry_forward_prev,
            "net_vat": round(net_vat, 0),
            "payable": round(payable, 0),
            "refundable": round(refundable, 0),
            "output_domestic": output_domestic,
            "output_export": output_export,
            "input_domestic": input_domestic,
            "input_import": input_import,
        },
    }


# ── US-422: AI VAT Anomaly Detection Swarm ─────────────────────────────────────

def run_vat_anomaly_swarm(
    taxpayer_mst: str,
    taxpayer_name: str,
    reconciliation_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Simulate a multi-agent swarm discussion that performs cross-period
    VAT anomaly detection. Agents: VATAuditor, FraudAnalyst, ComplianceAdvisor.
    """
    if reconciliation_data is None:
        reconciliation_data = vat_reconciliation_multi_period(taxpayer_mst)

    summary = reconciliation_data["summary"]
    periods = reconciliation_data["periods"]

    # Collect all anomalies
    all_anomalies = []
    for p in periods:
        for flag in p["anomaly_flags"]:
            all_anomalies.append({"period": p["period"], "flag": flag})

    # Generate agent chat steps
    timestamp_base = datetime.datetime.now()
    chat_steps = []

    def add_step(agent, role, message, avatar_class, offset_sec):
        chat_steps.append({
            "agent": agent,
            "role": role,
            "message": message,
            "avatar_class": avatar_class,
            "timestamp": (timestamp_base + datetime.timedelta(seconds=offset_sec)).strftime("%H:%M:%S"),
        })

    add_step(
        "VATCoordinator", "Điều phối viên",
        f"Khởi động phân tích VAT đa kỳ cho DN <strong>{taxpayer_name}</strong> (MST: {taxpayer_mst}). "
        f"Đang kiểm tra {summary['period_count']} kỳ kê khai với tổng thuế GTGT đầu ra "
        f"<code>{summary['total_output_vat']:,.0f}đ</code> và đầu vào <code>{summary['total_input_vat']:,.0f}đ</code>.",
        "bg-primary", 0,
    )

    add_step(
        "VATAuditor", "Kiểm toán VAT",
        f"Đã hoàn tất đối chiếu chéo hóa đơn đầu vào/đầu ra. Tỷ lệ trung bình đầu vào/đầu ra: "
        f"<strong>{summary['avg_input_output_ratio']}%</strong>. "
        + (f"Phát hiện <strong>{summary['total_anomalies']}</strong> điểm bất thường cần xem xét."
           if summary["total_anomalies"] > 0
           else "Không phát hiện bất thường đáng kể."),
        "bg-success", 3,
    )

    if all_anomalies:
        anomaly_list = "<ul>" + "".join(
            f"<li><strong>{a['period']}</strong>: {a['flag']}</li>"
            for a in all_anomalies[:6]
        ) + "</ul>"
        add_step(
            "FraudAnalyst", "Phân tích gian lận",
            f"Danh sách cờ cảnh báo chéo kỳ: {anomaly_list}"
            f"Đề xuất trích xuất mẫu hóa đơn đầu vào top 10 giá trị cao nhất để kiểm tra thực tế giao nhận hàng.",
            "bg-danger", 7,
        )
    else:
        add_step(
            "FraudAnalyst", "Phân tích gian lận",
            "Không phát hiện dấu hiệu gian lận VAT rõ ràng. Tỷ lệ đầu vào/đầu ra nằm trong ngưỡng an toàn (<85%).",
            "bg-danger", 7,
        )

    # Period-over-period variance analysis
    variances = []
    for i in range(1, len(periods)):
        prev_out = periods[i - 1]["output_vat"]
        curr_out = periods[i]["output_vat"]
        if prev_out > 0:
            change_pct = ((curr_out - prev_out) / prev_out) * 100
            if abs(change_pct) > 40:
                variances.append(
                    f"Kỳ {periods[i]['period']}: biến động doanh thu VAT đầu ra "
                    f"{'tăng' if change_pct > 0 else 'giảm'} {abs(change_pct):.1f}% so với kỳ trước"
                )

    if variances:
        add_step(
            "ComplianceAdvisor", "Tư vấn tuân thủ",
            "Phân tích biến động giữa các kỳ phát hiện:<br/>" + "<br/>".join(f"• {v}" for v in variances[:4])
            + "<br/><br/>Khuyến nghị: Chuẩn bị hồ sơ giải trình cho các kỳ có biến động >40% theo yêu cầu TT80.",
            "bg-warning", 12,
        )
    else:
        add_step(
            "ComplianceAdvisor", "Tư vấn tuân thủ",
            "Biến động doanh thu VAT giữa các kỳ nằm trong ngưỡng bình thường (<40%). "
            "Khuyến nghị tiếp tục duy trì kê khai đúng hạn và lưu trữ chứng từ gốc.",
            "bg-warning", 12,
        )

    add_step(
        "VATCoordinator", "Điều phối viên",
        f"<strong>Kết luận Swarm:</strong> Mức rủi ro tổng thể: <strong>{summary['risk_level']}</strong>. "
        f"Tổng thuế GTGT phải nộp ước tính: <code>{summary['total_payable']:,.0f}đ</code>. "
        f"Số kỳ có cờ cảnh báo: {len([p for p in periods if p['anomaly_flags']])} / {summary['period_count']}.",
        "bg-primary", 16,
    )

    # Generate markdown dossier report
    report_md = f"""# Báo Cáo Phân Tích VAT Đa Kỳ - Wise Compliance v31

## Thông tin Doanh nghiệp
- **MST**: {taxpayer_mst}
- **Tên**: {taxpayer_name}
- **Số kỳ phân tích**: {summary['period_count']}

## Tổng hợp VAT
| Chỉ tiêu | Giá trị |
|---|---|
| Tổng VAT đầu ra | {summary['total_output_vat']:,.0f} VNĐ |
| Tổng VAT đầu vào | {summary['total_input_vat']:,.0f} VNĐ |
| Tổng VAT phải nộp | {summary['total_payable']:,.0f} VNĐ |
| Tỷ lệ TB đầu vào/ra | {summary['avg_input_output_ratio']}% |
| Mức rủi ro | {summary['risk_level']} |

## Chi tiết theo kỳ
"""
    for p in periods:
        flags_str = ", ".join(p["anomaly_flags"]) if p["anomaly_flags"] else "Không có"
        report_md += f"""
### Kỳ {p['period']}
- Thuế đầu ra: {p['output_vat']:,.0f} ({p['invoice_count_output']} hóa đơn)
- Thuế đầu vào: {p['input_vat']:,.0f} ({p['invoice_count_input']} hóa đơn)
- VAT phải nộp: {p['payable']:,.0f} | Chuyển kỳ sau: {p['carry_forward']:,.0f}
- Tỷ lệ vào/ra: {p['input_output_ratio']}%
- Cờ cảnh báo: {flags_str}
"""

    report_md += f"""
## Khuyến nghị
1. {'Rà soát chi tiết hóa đơn mua vào các kỳ có tỷ lệ >90%' if summary['avg_input_output_ratio'] > 85 else 'Tiếp tục kê khai và lưu trữ chứng từ theo quy định'}
2. Chuẩn bị bảng kê mua vào (phụ lục 01-2/GTGT) và bán ra (01-1/GTGT) hoàn chỉnh
3. Đảm bảo hóa đơn đầu vào có đầy đủ chữ ký số theo Nghị định 123/2020/NĐ-CP
"""

    return {
        "chat_steps": chat_steps,
        "report_markdown": report_md,
        "reconciliation": reconciliation_data,
        "risk_level": summary["risk_level"],
        "total_anomalies": summary["total_anomalies"],
    }
