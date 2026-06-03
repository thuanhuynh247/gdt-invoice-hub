"""Autonomous Joint Audit Coordinator and Specialist Agents Swarm (US-321)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from extensions import db
from invoices.models import AgentMessage, Invoice, Partner
from invoices.ai_tax_advisor import TaxAdvisoryAgent
from invoices.tax_forecaster import forecast_next_period_tax, TaxAlertManager


class SpecialistAgent:
    """Base class for specialist agents participating in the swarm."""

    def __init__(self, name: str):
        self.name = name

    def process_message(self, msg: AgentMessage) -> dict:
        """Handle incoming messages and return output payload."""
        raise NotImplementedError


class AuditorAgent(SpecialistAgent):
    """Specialist agent for VAT compliance audits."""

    def __init__(self):
        super().__init__("AuditorAgent")

    def process_message(self, msg: AgentMessage) -> dict:
        payload = json.loads(msg.payload) if isinstance(msg.payload, str) else msg.payload
        taxpayer_mst = payload.get("taxpayer_mst")

        # Query active invoices for this tenant
        query = Invoice.query
        if taxpayer_mst:
            query = query.filter(
                (Invoice.taxpayer_mst == taxpayer_mst) |
                (Invoice.seller_mst == taxpayer_mst) |
                (Invoice.buyer_mst == taxpayer_mst)
            )
        invoices = query.all()

        # Adapt models to dict list for LocalTaxAdvisor
        invoice_dicts = []
        for inv in invoices:
            invoice_dicts.append({
                "id": inv.id,
                "seller_name": inv.seller_name or "N/A",
                "seller_mst": inv.seller_mst or "N/A",
                "buyer_name": inv.buyer_name or "N/A",
                "buyer_mst": inv.buyer_mst or "N/A",
                "amount_before_tax": inv.amount_before_tax or 0.0,
                "tax_amount": inv.tax_amount or 0.0,
                "total_amount": inv.total_amount or 0.0,
                "date": inv.date or "",
                "t_score": inv.t_score or 100,
                "is_cancelled": getattr(inv, "is_cancelled", False),
                "is_employee_payment": getattr(inv, "is_employee_payment", False),
                "has_non_cash_proof": getattr(inv, "has_non_cash_proof", False),
                "payment_method": getattr(inv, "payment_method", "TM"),
            })

        advisor = TaxAdvisoryAgent()
        findings = advisor.run_audit_cycle(invoice_dicts)
        dossier = advisor.generate_dossier()

        return {
            "status": "success",
            "findings_count": len(findings),
            "summary": dossier.get("severity_summary", {}),
            "findings": findings[:10],  # limit to top 10 for payload size
            "recommendation": dossier.get("recommendation", ""),
            "confidence_score": 0.95 if invoices else 0.50
        }


class ClassifierAgent(SpecialistAgent):
    """Specialist agent for Decree 132 related-party classification."""

    def __init__(self):
        super().__init__("ClassifierAgent")

    def process_message(self, msg: AgentMessage) -> dict:
        payload = json.loads(msg.payload) if isinstance(msg.payload, str) else msg.payload
        taxpayer_mst = payload.get("taxpayer_mst")

        # Query all partners with active Decree 132 relationships
        related_partners = Partner.query.filter(Partner.decree_132_relationship.isnot(None)).all()
        related_msts = {p.mst: p for p in related_partners}

        # Query invoices involving these partners
        query = Invoice.query
        if taxpayer_mst:
            query = query.filter(
                (Invoice.taxpayer_mst == taxpayer_mst) |
                (Invoice.seller_mst == taxpayer_mst) |
                (Invoice.buyer_mst == taxpayer_mst)
            )
        invoices = query.all()

        flagged_transactions = []
        total_related_amount = 0.0

        for inv in invoices:
            partner_mst = None
            if inv.seller_mst != taxpayer_mst and inv.seller_mst in related_msts:
                partner_mst = inv.seller_mst
            elif inv.buyer_mst != taxpayer_mst and inv.buyer_mst in related_msts:
                partner_mst = inv.buyer_mst

            if partner_mst:
                partner = related_msts[partner_mst]
                flagged_transactions.append({
                    "invoice_id": inv.id,
                    "partner_name": partner.name,
                    "partner_mst": partner.mst,
                    "relationship_code": partner.decree_132_relationship,
                    "amount": inv.total_amount or 0.0
                })
                total_related_amount += inv.total_amount or 0.0

        return {
            "status": "success",
            "flagged_count": len(flagged_transactions),
            "total_related_amount": total_related_amount,
            "flagged_transactions": flagged_transactions,
            "confidence_score": 0.90 if related_partners else 0.80
        }


class ForecasterAgent(SpecialistAgent):
    """Specialist agent for tax forecasting."""

    def __init__(self):
        super().__init__("ForecasterAgent")

    def process_message(self, msg: AgentMessage) -> dict:
        payload = json.loads(msg.payload) if isinstance(msg.payload, str) else msg.payload
        taxpayer_mst = payload.get("taxpayer_mst")

        query = Invoice.query
        if taxpayer_mst:
            query = query.filter(
                (Invoice.taxpayer_mst == taxpayer_mst) |
                (Invoice.seller_mst == taxpayer_mst) |
                (Invoice.buyer_mst == taxpayer_mst)
            )
        invoices = query.all()

        # Aggregate VAT by month
        monthly_data = {}
        for inv in invoices:
            if not inv.date or len(inv.date) < 7:
                continue
            month = inv.date[:7]  # YYYY-MM
            if month not in monthly_data:
                monthly_data[month] = {"output_vat": 0.0, "input_vat": 0.0}

            # In Vietnamese VAT, selling invoice -> output VAT, purchasing invoice -> input VAT
            if inv.seller_mst == taxpayer_mst:
                monthly_data[month]["output_vat"] += inv.tax_amount or 0.0
            else:
                monthly_data[month]["input_vat"] += inv.tax_amount or 0.0

        sorted_months = sorted(monthly_data.keys())
        historical_series = []
        for m in sorted_months:
            historical_series.append({
                "period": m,
                "output_vat": monthly_data[m]["output_vat"],
                "input_vat": monthly_data[m]["input_vat"]
            })

        # Forecast next period (e.g. June 2026 or next month)
        next_month = "2026-07"
        if sorted_months:
            last_m = sorted_months[-1]
            try:
                yr, mn = map(int, last_m.split("-"))
                mn += 1
                if mn > 12:
                    mn = 1
                    yr += 1
                next_month = f"{yr:04d}-{mn:02d}"
            except Exception:
                pass

        forecast = forecast_next_period_tax(historical_series, next_month)
        alert_mgr = TaxAlertManager(budget_limit=200_000_000.0)  # 200M VND default limit
        alert_mgr.evaluate_forecast(forecast)

        return {
            "status": "success",
            "forecast": forecast.to_dict(),
            "historical_months_analyzed": len(historical_series),
            "confidence_score": 0.85 if len(historical_series) >= 3 else 0.50
        }


class JointAuditCoordinator:
    """The central swarm manager agent (US-321)."""

    def __init__(self):
        self.agents = {
            "AuditorAgent": AuditorAgent(),
            "ClassifierAgent": ClassifierAgent(),
            "ForecasterAgent": ForecasterAgent()
        }

    def execute_swarm(self, taxpayer_mst: str, user_prompt: str) -> dict:
        """Coordinate specialized agents to compile a comprehensive tax audit dossier."""
        now_str = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

        # 1. Dispatch messages to queue
        dispatched_messages = {}
        for agent_name in self.agents.keys():
            msg = AgentMessage(
                sender_agent="JointAuditCoordinator",
                receiver_agent=agent_name,
                subject="ExecuteAuditTask",
                payload=json.dumps({
                    "taxpayer_mst": taxpayer_mst,
                    "user_prompt": user_prompt,
                    "timestamp": now_str
                }),
                status="pending",
                timestamp=now_str
            )
            db.session.add(msg)
            db.session.commit()
            dispatched_messages[agent_name] = msg

        # 2. Run agent execution loop (mocked inline synchronous execution for local sandbox)
        results = {}
        for agent_name, msg in dispatched_messages.items():
            try:
                agent = self.agents[agent_name]
                out_payload = agent.process_message(msg)
                msg.status = "processed"
                db.session.commit()
                results[agent_name] = out_payload
            except Exception as e:
                db.session.rollback()
                msg.status = "failed"
                db.session.commit()
                results[agent_name] = {"status": "failed", "error": str(e)}

        # 3. Synthesize the reports into markdown
        report_md = self._generate_markdown_report(taxpayer_mst, user_prompt, results)

        # 4. Calculate weighted swarm confidence score
        confidence_sum = 0.0
        weight_total = 0.0
        weights = {"AuditorAgent": 0.4, "ClassifierAgent": 0.3, "ForecasterAgent": 0.3}

        for agent_name, weight in weights.items():
            agent_res = results.get(agent_name, {})
            c_score = agent_res.get("confidence_score", 0.5)
            confidence_sum += c_score * weight
            weight_total += weight

        swarm_confidence = round(confidence_sum / weight_total, 2) if weight_total > 0 else 0.0

        return {
            "success": True,
            "taxpayer_mst": taxpayer_mst,
            "swarm_confidence": swarm_confidence,
            "report_markdown": report_md,
            "timestamp": now_str
        }

    def _generate_markdown_report(self, mst: str, prompt: str, results: dict) -> str:
        audit_res = results.get("AuditorAgent", {})
        class_res = results.get("ClassifierAgent", {})
        forecast_res = results.get("ForecasterAgent", {})

        md = []
        md.append(f"# BÁO CÁO KIỂM TOÁN THUẾ HỢP NHẤT (SWARM AUDIT REPORT)")
        md.append(f"**Mã số thuế doanh nghiệp:** {mst}")
        md.append(f"**Yêu cầu kiểm toán:** *{prompt}*")
        md.append(f"**Thời gian thực hiện:** {datetime.now(timezone.utc).isoformat()[:19]}Z")
        md.append("")
        md.append("---")
        md.append("")
        md.append("## 🔍 1. Kết quả kiểm toán tuân thủ & Rủi ro (AuditorAgent)")
        
        if audit_res.get("status") == "success":
            summary = audit_res.get("summary", {})
            md.append(f"- **Tổng số rủi ro phát hiện:** {audit_res.get('findings_count', 0)}")
            md.append(f"  - Nghiêm trọng (Critical): `{summary.get('critical', 0)}` | Cao (High): `{summary.get('high', 0)}` | Trung bình (Medium): `{summary.get('medium', 0)}`")
            md.append(f"- **Khuyến nghị chính:** *{audit_res.get('recommendation', 'Không có')}*")
            md.append("")
            md.append("### Danh sách hóa đơn rủi ro tiêu biểu:")
            findings = audit_res.get("findings", [])
            if findings:
                for f in findings:
                    md.append(f"#### Hóa đơn ID: `{f['invoice_id']}` (Bên bán: {f['seller']} - MST: {f['seller_mst']})")
                    for r in f["risks"]:
                        md.append(f"- **[{r['severity']}]** {r['message']}")
                        if r.get("legal_refs"):
                            md.append(f"  *Cơ sở pháp lý:* {', '.join(r['legal_refs'])}")
            else:
                md.append("*Không phát hiện hóa đơn rủi ro.*")
        else:
            md.append(f"❌ *Lỗi thực thi kiểm toán tuân thủ: {audit_res.get('error')}*")

        md.append("")
        md.append("---")
        md.append("")
        md.append("## 🤝 2. Giao dịch liên kết theo Nghị định 132/2020/NĐ-CP (ClassifierAgent)")
        
        if class_res.get("status") == "success":
            md.append(f"- **Số lượng giao dịch liên kết phát hiện:** {class_res.get('flagged_count', 0)}")
            md.append(f"- **Tổng giá trị giao dịch liên kết:** `{class_res.get('total_related_amount', 0.0):,.0f} VND`")
            md.append("")
            transactions = class_res.get("flagged_transactions", [])
            if transactions:
                md.append("| Hóa đơn ID | Đối tác liên kết | MST | Mã liên kết | Giá trị (VND) |")
                md.append("| --- | --- | --- | --- | --- |")
                for t in transactions:
                    md.append(f"| `{t['invoice_id']}` | {t['partner_name']} | {t['partner_mst']} | `{t['relationship_code']}` | {t['amount']:,.0f} |")
            else:
                md.append("*Không phát hiện giao dịch liên kết với các đối tác đã thiết lập.*")
        else:
            md.append(f"❌ *Lỗi kiểm tra giao dịch liên kết: {class_res.get('error')}*")

        md.append("")
        md.append("---")
        md.append("")
        md.append("## 📈 3. Dự báo nghĩa vụ thuế & Cảnh báo ngân sách (ForecasterAgent)")
        
        if forecast_res.get("status") == "success":
            fc = forecast_res.get("forecast", {})
            md.append(f"- **Kỳ dự báo tiếp theo:** `{fc.get('projected_period', 'N/A')}`")
            md.append(f"- **Thuế GTGT đầu ra dự kiến (Output VAT):** `{fc.get('projected_output_vat', 0.0):,.0f} VND`")
            md.append(f"- **Thuế GTGT đầu vào dự kiến (Input VAT):** `{fc.get('projected_input_vat', 0.0):,.0f} VND`")
            md.append(f"- **Thuế GTGT phải nộp dự kiến (VAT Payable):** `{fc.get('projected_vat_payable', 0.0):,.0f} VND`")
            md.append("")
            if fc.get("alert_triggered"):
                md.append(f"⚠️ **CẢNH BÁO:** {fc.get('alert_message')}")
            else:
                md.append("✅ *Nghĩa vụ thuế dự kiến nằm trong tầm kiểm soát ngân sách.*")
        else:
            md.append(f"❌ *Lỗi thực thi dự báo thuế: {forecast_res.get('error')}*")

        return "\n".join(md)
