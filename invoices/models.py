"""Relational database models for SQLite storage."""

from __future__ import annotations

import json
from extensions import db


class SystemConfig(db.Model):
    """Storage for SMTP settings, scheduler credentials, and intervals."""

    __tablename__ = "system_config"

    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.Text, nullable=False)

    def __repr__(self) -> str:
        return f"<SystemConfig {self.key}>"


class TaxpayerProfile(db.Model):
    """Profile configuration for a taxpayer (MST) with encrypted GDT credentials."""

    __tablename__ = "taxpayer_profile"

    mst = db.Column(db.String(20), primary_key=True)
    company_name = db.Column(db.String(255), nullable=False)
    gdt_username = db.Column(db.String(100), nullable=False)
    gdt_password_encrypted = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.String(50), nullable=False)

    invoices = db.relationship(
        "Invoice",
        backref="taxpayer",
        cascade="all, delete-orphan",
        passive_deletes=False,
    )

    def to_dict(self) -> dict:
        return {
            "mst": self.mst,
            "company_name": self.company_name,
            "gdt_username": self.gdt_username,
            "is_active": self.is_active,
            "created_at": self.created_at,
        }


class SchedulerLog(db.Model):
    """Execution logs for recurring background exports."""

    __tablename__ = "scheduler_log"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timestamp = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    details = db.Column(db.Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "status": self.status,
            "details": self.details,
        }


class Partner(db.Model):
    """Local catalog of vendors with cached tax code registration statuses."""

    __tablename__ = "partner"

    mst = db.Column(db.String(20), primary_key=True)
    name = db.Column(db.String(255), nullable=True)
    address = db.Column(db.Text, nullable=True)
    mst_status = db.Column(db.String(100), nullable=True)
    mst_last_checked = db.Column(db.String(50), nullable=True)
    decree_132_relationship = db.Column(db.String(10), nullable=True)

    def to_dict(self) -> dict:
        return {
            "mst": self.mst,
            "name": self.name or "",
            "address": self.address or "",
            "mst_status": self.mst_status or "",
            "mst_last_checked": self.mst_last_checked or "",
            "decree_132_relationship": self.decree_132_relationship or "",
        }


class Invoice(db.Model):
    """Relational representation of a parsed GDT invoice."""

    __tablename__ = "invoice"

    id = db.Column(db.String(100), primary_key=True)  # format: seller_mst-symbol-number
    filename = db.Column(db.String(255), nullable=True)
    invoice_type = db.Column(db.String(100), nullable=True)
    template_code = db.Column(db.String(50), nullable=True)
    symbol = db.Column(db.String(50), nullable=True)
    number = db.Column(db.String(50), nullable=True)
    date = db.Column(db.String(20), nullable=True)
    currency = db.Column(db.String(10), nullable=True)
    seller_name = db.Column(db.String(255), nullable=True)
    seller_mst = db.Column(db.String(20), nullable=True)
    seller_address = db.Column(db.Text, nullable=True)
    seller_phone = db.Column(db.String(50), nullable=True)
    buyer_name = db.Column(db.String(255), nullable=True)
    buyer_mst = db.Column(db.String(20), nullable=True)
    buyer_address = db.Column(db.Text, nullable=True)
    amount_before_tax = db.Column(db.Float, nullable=False, default=0.0)
    tax_amount = db.Column(db.Float, nullable=False, default=0.0)
    total_amount = db.Column(db.Float, nullable=False, default=0.0)
    has_signature = db.Column(db.Boolean, nullable=False, default=False)
    signing_date = db.Column(db.String(20), nullable=True)
    payment_method = db.Column(db.String(100), nullable=True)
    is_cancelled = db.Column(db.Boolean, nullable=False, default=False)
    cancellation_date = db.Column(db.String(20), nullable=True)
    cancellation_reason = db.Column(db.Text, nullable=True)
    warnings_json = db.Column(db.Text, nullable=True)  # List of strings encoded in JSON
    notes = db.Column(db.Text, nullable=True)
    signature_details_json = db.Column(db.Text, nullable=True)  # Detailed certificate audits
    amount_in_words = db.Column(db.Text, nullable=True)
    imported_at = db.Column(db.String(50), nullable=False)
    updated_at = db.Column(db.String(50), nullable=True)
    import_status = db.Column(db.String(20), nullable=False, default="imported")
    invoice_status = db.Column(db.String(50), nullable=True)
    ai_audited = db.Column(db.Boolean, default=False)
    due_date = db.Column(db.String(20), nullable=True)   # US-036: Ngày đến hạn thanh toán (YYYY-MM-DD)
    paid_date = db.Column(db.String(20), nullable=True)  # US-036: Ngày đã thanh toán thực tế (YYYY-MM-DD)
    t_score = db.Column(db.Integer, nullable=False, default=100)
    t_rating = db.Column(db.String(10), nullable=False, default="A++")
    taxpayer_mst = db.Column(
        db.String(20),
        db.ForeignKey("taxpayer_profile.mst", ondelete="CASCADE"),
        nullable=True,
    )
    erp_synced = db.Column(db.Boolean, default=False, nullable=False)
    erp_sync_date = db.Column(db.String(50), nullable=True)
    erp_sync_error = db.Column(db.Text, nullable=True)
    merkle_hash = db.Column(db.String(64), nullable=True)
    merkle_root = db.Column(db.String(64), nullable=True)
    merkle_index = db.Column(db.Integer, nullable=True)



    # Relationship with cascade delete
    items = db.relationship(
        "LineItem",
        backref="invoice",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    ai_audit_results = db.relationship(
        "AIAuditResult",
        backref="invoice",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


    @property
    def warnings(self) -> list[str]:
        if not self.warnings_json:
            return []
        try:
            return json.loads(self.warnings_json)
        except Exception:
            return []

    @warnings.setter
    def warnings(self, val: list[str]) -> None:
        self.warnings_json = json.dumps(val, ensure_ascii=False)

    @property
    def signature_details(self) -> dict | None:
        if not self.signature_details_json:
            return None
        try:
            return json.loads(self.signature_details_json)
        except Exception:
            return None

    @signature_details.setter
    def signature_details(self, val: dict | None) -> None:
        if val is None:
            self.signature_details_json = None
        else:
            self.signature_details_json = json.dumps(val, ensure_ascii=False)

    @property
    def is_valid(self) -> bool:
        return len(self.warnings) == 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "filename": self.filename,
            "invoice_type": self.invoice_type,
            "template_code": self.template_code,
            "symbol": self.symbol,
            "number": self.number,
            "date": self.date,
            "currency": self.currency,
            "seller_name": self.seller_name,
            "seller_mst": self.seller_mst,
            "seller_address": self.seller_address,
            "seller_phone": self.seller_phone,
            "buyer_name": self.buyer_name,
            "buyer_mst": self.buyer_mst,
            "buyer_address": self.buyer_address,
            "amount_before_tax": self.amount_before_tax,
            "tax_amount": self.tax_amount,
            "total_amount": self.total_amount,
            "has_signature": self.has_signature,
            "signing_date": self.signing_date,
            "payment_method": self.payment_method,
            "is_cancelled": self.is_cancelled,
            "cancellation_date": self.cancellation_date,
            "cancellation_reason": self.cancellation_reason,
            "warnings": self.warnings,
            "is_valid": self.is_valid,
            "notes": self.notes or "",
            "amount_in_words": self.amount_in_words or "",
            "imported_at": self.imported_at,
            "updated_at": self.updated_at,
            "import_status": self.import_status,
            "invoice_status": self.invoice_status or "Gốc",
            "items": [item.to_dict() for item in self.items],
            "ai_warnings": [w.to_dict() for w in self.ai_audit_results],
            "ai_audited": self.ai_audited,
            "t_score": self.t_score,
            "t_rating": self.t_rating,
            "taxpayer_mst": self.taxpayer_mst or "",
            "signature_details": self.signature_details,
            "erp_synced": self.erp_synced,
            "erp_sync_date": self.erp_sync_date or "",
            "erp_sync_error": self.erp_sync_error or "",
        }




class LineItem(db.Model):
    """An individual line item within an invoice."""

    __tablename__ = "line_item"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    invoice_id = db.Column(
        db.String(100),
        db.ForeignKey("invoice.id", ondelete="CASCADE"),
        nullable=False,
    )
    item_name = db.Column(db.String(255), nullable=False)
    unit = db.Column(db.String(50), nullable=True)
    quantity = db.Column(db.Float, nullable=False, default=0.0)
    unit_price = db.Column(db.Float, nullable=False, default=0.0)
    amount_before_tax = db.Column(db.Float, nullable=False, default=0.0)
    tax_rate = db.Column(db.String(20), nullable=False, default="0%")
    tax_amount = db.Column(db.Float, nullable=False, default=0.0)
    expense_category = db.Column(db.String(100), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "item_name": self.item_name,
            "unit": self.unit or "",
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "amount_before_tax": self.amount_before_tax,
            "tax_rate": self.tax_rate,
            "tax_amount": self.tax_amount,
            "expense_category": self.expense_category or "Chưa phân loại",
        }


class AIAuditResult(db.Model):
    """Storage for AI compliance warnings (VAT deductibility, price inflation)."""

    __tablename__ = "ai_audit_result"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    invoice_id = db.Column(
        db.String(100),
        db.ForeignKey("invoice.id", ondelete="CASCADE"),
        nullable=False,
    )
    warning_type = db.Column(db.String(50), nullable=False)  # 'personal_purchase', 'price_anomaly'
    explanation = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.String(50), nullable=False)

    def to_dict(self) -> dict:
        return {
            "warning_type": self.warning_type,
            "explanation": self.explanation,
            "created_at": self.created_at,
        }


class AIChatSession(db.Model):
    """Conversational session for the AI invoice assistant."""

    __tablename__ = "ai_chat_session"

    id = db.Column(db.String(36), primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.String(50), nullable=False)
    invoice_id = db.Column(
        db.String(100),
        db.ForeignKey("invoice.id", ondelete="SET NULL"),
        nullable=True,
    )

    messages = db.relationship(
        "AIChatMessage",
        backref="session",
        cascade="all, delete-orphan",
        passive_deletes=False,
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.created_at,
            "invoice_id": self.invoice_id,
            "messages": [msg.to_dict() for msg in self.messages]
        }



class AIChatMessage(db.Model):
    """An individual message within an AI chat session."""

    __tablename__ = "ai_chat_message"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    session_id = db.Column(
        db.String(36),
        db.ForeignKey("ai_chat_session.id", ondelete="CASCADE"),
        nullable=False,
    )
    role = db.Column(db.String(10), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.String(50), nullable=False)

    def to_dict(self) -> dict:
        return {
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at,
        }


class TaxRegulationChunk(db.Model):
    """Storage for dynamically ingested tax regulation PDF text chunks."""

    __tablename__ = "tax_regulation_chunk"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    document_source = db.Column(db.String(255), nullable=False)
    page_number = db.Column(db.Integer, nullable=False)
    effective_date = db.Column(db.String(20), nullable=True)  # YYYY-MM-DD
    chunk_content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.String(50), nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "document_source": self.document_source,
            "page_number": self.page_number,
            "effective_date": self.effective_date or "",
            "chunk_content": self.chunk_content,
            "created_at": self.created_at,
        }


class BlacklistedMST(db.Model):
    """High-risk/blacklisted tax codes (MST) for tax evasion prevention."""

    __tablename__ = "blacklisted_mst"

    mst = db.Column(db.String(20), primary_key=True)
    reason = db.Column(db.Text, nullable=True)
    blacklisted_at = db.Column(db.String(50), nullable=True)

    def to_dict(self) -> dict:
        return {
            "mst": self.mst,
            "reason": self.reason or "",
            "blacklisted_at": self.blacklisted_at or "",
        }


class GDTSyncLog(db.Model):
    """Execution log tracker for the background GDT synchronization daemon."""

    __tablename__ = "gdt_sync_log"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    taxpayer_mst = db.Column(
        db.String(20),
        db.ForeignKey("taxpayer_profile.mst"),
        nullable=False,
    )
    triggered_at = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # 'success', 'failed', 'partial'
    invoices_fetched = db.Column(db.Integer, default=0)
    captcha_attempts = db.Column(db.Integer, default=0)
    captcha_failures = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text, nullable=True)
    elapsed_seconds = db.Column(db.Float, nullable=False, default=0.0)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "taxpayer_mst": self.taxpayer_mst,
            "triggered_at": self.triggered_at,
            "status": self.status,
            "invoices_fetched": self.invoices_fetched,
            "captcha_attempts": self.captcha_attempts,
            "captcha_failures": self.captcha_failures,
            "error_message": self.error_message,
            "elapsed_seconds": self.elapsed_seconds,
        }

class BankTransaction(db.Model):
    """Stores parsed bank statement rows for reconciliation against invoices."""

    __tablename__ = "bank_transaction"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.String(50), primary_key=True)
    taxpayer_mst = db.Column(
        db.String(20),
        db.ForeignKey("taxpayer_profile.mst", ondelete="CASCADE"),
        nullable=True,
    )
    bank_name = db.Column(db.String(50), nullable=False)
    account_number = db.Column(db.String(50), nullable=True)
    transaction_date = db.Column(db.String(20), nullable=False)
    reference_number = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="unreconciled")  # 'unreconciled', 'matched', 'adjusted'
    matched_invoice_id = db.Column(
        db.String(100),
        db.ForeignKey("invoice.id", ondelete="SET NULL"),
        nullable=True,
    )
    confidence_score = db.Column(db.Float, default=0.0)
    imported_at = db.Column(db.String(30), nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "taxpayer_mst": self.taxpayer_mst or "",
            "bank_name": self.bank_name,
            "account_number": self.account_number or "",
            "transaction_date": self.transaction_date,
            "reference_number": self.reference_number or "",
            "description": self.description,
            "amount": self.amount,
            "status": self.status,
            "matched_invoice_id": self.matched_invoice_id or "",
            "confidence_score": self.confidence_score,
            "imported_at": self.imported_at,
        }


class AuditBlock(db.Model):
    """A cryptographic ledger block for tamper-proof tax audit trails."""

    __tablename__ = "audit_ledger"

    block_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timestamp = db.Column(db.String(30), nullable=False)
    action_type = db.Column(db.String(50), nullable=False)  # 'INVOICE_IMPORT', 'SIGNATURE_VERIFY', 'LEDGER_POST'
    mst = db.Column(db.String(20), nullable=False)
    payload_hash = db.Column(db.String(64), nullable=False)
    prev_block_hash = db.Column(db.String(64), nullable=False)
    block_hash = db.Column(db.String(64), nullable=False, unique=True)
    signature = db.Column(db.Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "block_id": self.block_id,
            "timestamp": self.timestamp,
            "action_type": self.action_type,
            "mst": self.mst,
            "payload_hash": self.payload_hash,
            "prev_block_hash": self.prev_block_hash,
            "block_hash": self.block_hash,
            "signature": self.signature,
        }


class ComplianceRulebook(db.Model):
    """Storage for corporate-defined compliance rulebooks (US-120)."""

    __tablename__ = "compliance_rulebook"

    id = db.Column(db.String(100), primary_key=True)  # unique string ID, e.g. rulebook_default, rulebook_tenant_mst
    taxpayer_mst = db.Column(db.String(20), nullable=True) # nullable for system-wide default rulebook
    name = db.Column(db.String(255), nullable=False)
    rulebook_json = db.Column(db.Text, nullable=False) # Full JSON representation of all rules
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    updated_at = db.Column(db.String(50), nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "taxpayer_mst": self.taxpayer_mst or "",
            "name": self.name,
            "rulebook_json": self.rulebook_json,
            "is_active": self.is_active,
            "updated_at": self.updated_at,
        }


class WebhookSubscription(db.Model):
    """Model to store webhook endpoints and signing secrets for tenants."""
    __tablename__ = "webhook_subscription"

    id = db.Column(db.String(100), primary_key=True)  # unique string ID, e.g. sub_default, sub_tenant_mst
    taxpayer_mst = db.Column(db.String(20), nullable=True) # nullable for system default
    url = db.Column(db.String(512), nullable=False)
    secret = db.Column(db.String(128), nullable=False) # HMAC signature key
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.String(50), nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "taxpayer_mst": self.taxpayer_mst or "",
            "url": self.url,
            "secret": self.secret,
            "is_active": self.is_active,
            "created_at": self.created_at,
        }


class WebhookDeliveryLog(db.Model):
    """Auditable log of webhook delivery attempts and results."""
    __tablename__ = "webhook_delivery_log"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    subscription_id = db.Column(db.String(100), nullable=False)
    event_topic = db.Column(db.String(100), nullable=False)
    payload = db.Column(db.Text, nullable=False)
    attempt_number = db.Column(db.Integer, nullable=False)
    status_code = db.Column(db.Integer, nullable=True)
    success = db.Column(db.Boolean, nullable=False)
    error_message = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.String(50), nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "subscription_id": self.subscription_id,
            "event_topic": self.event_topic,
            "payload": self.payload,
            "attempt_number": self.attempt_number,
            "status_code": self.status_code,
            "success": self.success,
            "error_message": self.error_message or "",
            "timestamp": self.timestamp,
        }


class InvoiceCorrectionProposal(db.Model):
    """Proposal for correcting an invoice, automatically generated by AI Auditor or suggested by user."""
    __tablename__ = "invoice_correction_proposal"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    invoice_id = db.Column(db.String(100), nullable=False)
    taxpayer_mst = db.Column(db.String(20), nullable=True)
    correction_type = db.Column(db.String(50), nullable=False)
    original_value = db.Column(db.Text, nullable=True)
    proposed_value = db.Column(db.Text, nullable=True)
    ai_explanation = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="pending")
    created_at = db.Column(db.String(50), nullable=False)
    updated_at = db.Column(db.String(50), nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "invoice_id": self.invoice_id,
            "taxpayer_mst": self.taxpayer_mst or "",
            "correction_type": self.correction_type,
            "original_value": self.original_value or "",
            "proposed_value": self.proposed_value or "",
            "ai_explanation": self.ai_explanation or "",
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class SecurityAuditLog(db.Model):
    """An immutable database log for tracking user and administrative events."""

    __tablename__ = "security_audit_log"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    timestamp = db.Column(db.String(30), nullable=False)
    username = db.Column(db.String(100), nullable=False)
    tax_code = db.Column(db.String(20), nullable=True)
    event_category = db.Column(db.String(50), nullable=False)  # AUTH, PROFILE, REPAIR, UPDATE, DELETE
    ip_address = db.Column(db.String(45), nullable=True)
    event_details = db.Column(db.Text, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "username": self.username,
            "tax_code": self.tax_code or "",
            "event_category": self.event_category,
            "ip_address": self.ip_address or "",
            "event_details": self.event_details,
        }
class TenantGroup(db.Model):
    """Represents a corporate group or organization managing multiple taxpayer profiles."""
    __tablename__ = "tenant_group"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    group_name = db.Column(db.String(100), nullable=False, unique=True)
    admin_username = db.Column(db.String(100), nullable=False)  # User managing this corporate group
    taxpayer_msts = db.Column(db.Text, nullable=False)  # JSON list of MSTs, e.g. '["0101234567", "0202345678"]'

    def get_mst_list(self) -> list[str]:
        try:
            return json.loads(self.taxpayer_msts)
        except Exception:
            return []

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "group_name": self.group_name,
            "admin_username": self.admin_username,
            "taxpayer_msts": self.get_mst_list(),
        }


class AgentMessage(db.Model):
    """Storage for communication messages between specialized AI agents."""
    __tablename__ = "agent_message"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sender_agent = db.Column(db.String(100), nullable=False)
    receiver_agent = db.Column(db.String(100), nullable=False)
    subject = db.Column(db.String(255), nullable=False)
    payload = db.Column(db.Text, nullable=False)  # JSON-serialized string
    status = db.Column(db.String(20), nullable=False, default="pending")  # pending, processed, failed
    timestamp = db.Column(db.String(50), nullable=False)

    def to_dict(self) -> dict:
        try:
            parsed_payload = json.loads(self.payload)
        except Exception:
            parsed_payload = self.payload
        return {
            "id": self.id,
            "sender_agent": self.sender_agent,
            "receiver_agent": self.receiver_agent,
            "subject": self.subject,
            "payload": parsed_payload,
            "status": self.status,
            "timestamp": self.timestamp,
        }


class CustomsDeclaration(db.Model):
    """Vietnamese VNACCS/VCIS customs import declaration."""
    __tablename__ = "customs_declaration"

    declaration_number = db.Column(db.String(50), primary_key=True)
    declaration_date = db.Column(db.String(20), nullable=False)
    taxpayer_mst = db.Column(db.String(20), nullable=False)
    customs_value_vnd = db.Column(db.Float, nullable=False, default=0.0)
    import_duty_vnd = db.Column(db.Float, nullable=False, default=0.0)
    import_vat_vnd = db.Column(db.Float, nullable=False, default=0.0)
    exchange_rate = db.Column(db.Float, nullable=False, default=1.0)
    currency = db.Column(db.String(10), nullable=False, default="VND")
    hs_codes_json = db.Column(db.Text, nullable=True)  # JSON list of HS codes
    xml_content = db.Column(db.Text, nullable=True)
    matching_invoice_id = db.Column(db.String(100), db.ForeignKey("invoice.id", ondelete="SET NULL"), nullable=True)
    status = db.Column(db.String(50), nullable=False, default="unreconciled")  # unreconciled, matched, variance_exceeded
    variance_notes = db.Column(db.Text, nullable=True)

    invoice = db.relationship("Invoice", backref="customs_declarations")

    @property
    def hs_codes(self) -> list[str]:
        if not self.hs_codes_json:
            return []
        try:
            return json.loads(self.hs_codes_json)
        except Exception:
            return []

    @hs_codes.setter
    def hs_codes(self, val: list[str]) -> None:
        self.hs_codes_json = json.dumps(val, ensure_ascii=False)

    def to_dict(self) -> dict:
        return {
            "declaration_number": self.declaration_number,
            "declaration_date": self.declaration_date,
            "taxpayer_mst": self.taxpayer_mst,
            "customs_value_vnd": self.customs_value_vnd,
            "import_duty_vnd": self.import_duty_vnd,
            "import_vat_vnd": self.import_vat_vnd,
            "exchange_rate": self.exchange_rate,
            "currency": self.currency,
            "hs_codes": self.hs_codes,
            "matching_invoice_id": self.matching_invoice_id,
            "status": self.status,
            "variance_notes": self.variance_notes or "",
        }


from sqlalchemy import event


@event.listens_for(SecurityAuditLog, "before_update")
def prevent_audit_log_update(mapper, connection, target):
    raise ValueError("SecurityAuditLog entries are immutable and cannot be updated.")


@event.listens_for(SecurityAuditLog, "before_delete")
def prevent_audit_log_delete(mapper, connection, target):
    raise ValueError("SecurityAuditLog entries are immutable and cannot be deleted.")


class TaxFilingRecord(db.Model):
    """US-492: Storage for tax calendar deadlines and tracking statuses."""

    __tablename__ = "tax_filing_record"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tax_type = db.Column(db.String(50), nullable=False)  # VAT, CIT_Q, CIT_A, PIT_A, FCT
    period = db.Column(db.String(50), nullable=False)  # e.g., '2026-05', '2026-Q1', '2026'
    deadline = db.Column(db.String(20), nullable=False)  # YYYY-MM-DD
    filed_date = db.Column(db.String(20), nullable=True)  # YYYY-MM-DD
    status = db.Column(db.String(20), nullable=False, default="Pending")  # Filed, Pending, Overdue
    xml_file_path = db.Column(db.Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tax_type": self.tax_type,
            "period": self.period,
            "deadline": self.deadline,
            "filed_date": self.filed_date or "",
            "status": self.status,
            "xml_file_path": self.xml_file_path or "",
        }


class FixedAsset(db.Model):
    """US-493: Fixed asset registry for depreciation calculations per TT45/2013."""

    __tablename__ = "fixed_asset"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    asset_code = db.Column(db.String(50), nullable=False, unique=True)
    name = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100), nullable=False)  # Computers, Vehicles, Buildings, etc.
    acquisition_date = db.Column(db.String(20), nullable=False)  # YYYY-MM-DD
    original_cost = db.Column(db.Float, nullable=False, default=0.0)
    residual_value = db.Column(db.Float, nullable=False, default=0.0)
    useful_life_months = db.Column(db.Integer, nullable=False)
    depreciation_method = db.Column(db.String(50), nullable=False, default="straight_line")  # straight_line, declining_balance, production_based
    linked_invoice_id = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(50), nullable=False, default="active")  # active, disposed, fully_depreciated
    disposed_date = db.Column(db.String(20), nullable=True)  # YYYY-MM-DD
    disposal_proceeds = db.Column(db.Float, nullable=False, default=0.0)

    depreciation_entries = db.relationship(
        "DepreciationEntry",
        backref="fixed_asset",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "asset_code": self.asset_code,
            "name": self.name,
            "category": self.category,
            "acquisition_date": self.acquisition_date,
            "original_cost": self.original_cost,
            "residual_value": self.residual_value,
            "useful_life_months": self.useful_life_months,
            "depreciation_method": self.depreciation_method,
            "linked_invoice_id": self.linked_invoice_id or "",
            "status": self.status,
            "disposed_date": self.disposed_date or "",
            "disposal_proceeds": self.disposal_proceeds,
        }


class DepreciationEntry(db.Model):
    """US-493: Monthly depreciation entries generated by the engine."""

    __tablename__ = "depreciation_entry"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    asset_id = db.Column(
        db.Integer,
        db.ForeignKey("fixed_asset.id", ondelete="CASCADE"),
        nullable=False,
    )
    period = db.Column(db.String(20), nullable=False)  # YYYY-MM
    depreciation_amount = db.Column(db.Float, nullable=False)
    accumulated_depreciation = db.Column(db.Float, nullable=False)
    net_book_value = db.Column(db.Float, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "asset_id": self.asset_id,
            "period": self.period,
            "depreciation_amount": self.depreciation_amount,
            "accumulated_depreciation": self.accumulated_depreciation,
            "net_book_value": self.net_book_value,
        }


class DeliveryNote(db.Model):
    """US-500: GDT-compliant Electronic Delivery Note representation."""

    __tablename__ = "delivery_note"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    note_number = db.Column(db.String(100), nullable=False, unique=True)
    note_date = db.Column(db.String(20), nullable=False)  # YYYY-MM-DD
    type = db.Column(db.String(50), nullable=False, default="internal_transfer")  # internal_transfer, agent_consignment
    sender_mst = db.Column(db.String(20), nullable=False)
    receiver_mst = db.Column(db.String(20), nullable=False)
    transport_contract = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(50), nullable=False, default="Pending")  # Pending, Invoiced, Overdue
    linked_invoice_id = db.Column(db.String(100), nullable=True)
    total_value = db.Column(db.Float, nullable=True, default=0.0)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "note_number": self.note_number,
            "note_date": self.note_date,
            "type": self.type,
            "sender_mst": self.sender_mst,
            "receiver_mst": self.receiver_mst,
            "transport_contract": self.transport_contract or "",
            "status": self.status,
            "linked_invoice_id": self.linked_invoice_id or "",
            "total_value": self.total_value,
        }


class LogisticsAllocation(db.Model):
    """US-503: VAS 02 Logistics/Freight Cost Allocation matching purchase items."""

    __tablename__ = "logistics_allocation"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    logistics_invoice_id = db.Column(db.String(100), nullable=False)
    purchase_invoice_id = db.Column(db.String(100), nullable=False)
    allocated_amount = db.Column(db.Float, nullable=False)
    allocation_method = db.Column(db.String(50), nullable=False, default="value_ratio")  # value_ratio, quantity_ratio
    created_at = db.Column(db.String(50), nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "logistics_invoice_id": self.logistics_invoice_id,
            "purchase_invoice_id": self.purchase_invoice_id,
            "allocated_amount": self.allocated_amount,
            "allocation_method": self.allocation_method,
            "created_at": self.created_at,
        }


class RelatedPartyRelationship(db.Model):
    """US-521: Related party relationships under Decree 132/2020/NĐ-CP."""

    __tablename__ = "related_party_relationship"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    taxpayer_mst = db.Column(
        db.String(20),
        db.ForeignKey("taxpayer_profile.mst", ondelete="CASCADE"),
        nullable=False,
    )
    partner_mst = db.Column(db.String(20), nullable=False)
    partner_name = db.Column(db.String(255), nullable=False)
    relationship_type = db.Column(db.String(100), nullable=False)  # ownership_ge_25, guarantee_ge_25_debt_ge_50, etc.
    ownership_percentage = db.Column(db.Float, default=0.0)
    details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.String(30), nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "taxpayer_mst": self.taxpayer_mst,
            "partner_mst": self.partner_mst,
            "partner_name": self.partner_name,
            "relationship_type": self.relationship_type,
            "ownership_percentage": self.ownership_percentage,
            "details": self.details or "",
            "created_at": self.created_at,
        }


class ExportCustomsDeclaration(db.Model):
    """US-530: Export Customs Declaration XML representation."""

    __tablename__ = "export_customs_declaration"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    declaration_num = db.Column(db.String(100), nullable=False, unique=True)
    registration_date = db.Column(db.String(20), nullable=False)  # YYYY-MM-DD
    clearance_date = db.Column(db.String(20), nullable=False)  # YYYY-MM-DD
    taxpayer_mst = db.Column(db.String(20), nullable=False)
    export_value_usd = db.Column(db.Float, nullable=False, default=0.0)
    exchange_rate = db.Column(db.Float, nullable=False, default=0.0)
    export_value_vnd = db.Column(db.Float, nullable=False, default=0.0)
    hs_codes = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(50), nullable=False, default="Pending")  # Pending, Reconciled, Discrepancy

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "declaration_num": self.declaration_num,
            "registration_date": self.registration_date,
            "clearance_date": self.clearance_date,
            "taxpayer_mst": self.taxpayer_mst,
            "export_value_usd": self.export_value_usd,
            "exchange_rate": self.exchange_rate,
            "export_value_vnd": self.export_value_vnd,
            "hs_codes": self.hs_codes or "",
            "status": self.status,
        }


class ExportDeclarationInvoiceMatch(db.Model):
    """US-531: Reconciliation matches between export customs declaration and export invoices."""

    __tablename__ = "export_declaration_invoice_match"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    declaration_id = db.Column(
        db.Integer,
        db.ForeignKey("export_customs_declaration.id", ondelete="CASCADE"),
        nullable=False,
    )
    invoice_id = db.Column(
        db.String(100),
        db.ForeignKey("invoice.id", ondelete="CASCADE"),
        nullable=False,
    )
    match_status = db.Column(db.String(50), nullable=False, default="matched")  # matched, value_mismatch
    value_difference = db.Column(db.Float, nullable=False, default=0.0)
    notes = db.Column(db.Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "declaration_id": self.declaration_id,
            "invoice_id": self.invoice_id,
            "match_status": self.match_status,
            "value_difference": self.value_difference,
            "notes": self.notes or "",
        }


class VatRefundApplication(db.Model):
    """US-533: Export VAT Refund Application Form 01/ĐNHT."""

    __tablename__ = "vat_refund_application"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    taxpayer_mst = db.Column(db.String(20), nullable=False)
    period_start = db.Column(db.String(20), nullable=False)  # YYYY-MM
    period_end = db.Column(db.String(20), nullable=False)  # YYYY-MM
    total_input_vat = db.Column(db.Float, nullable=False, default=0.0)
    allocated_export_vat = db.Column(db.Float, nullable=False, default=0.0)
    refund_requested_amount = db.Column(db.Float, nullable=False, default=0.0)
    status = db.Column(db.String(50), nullable=False, default="Draft")  # Draft, Submitted, Approved, Rejected
    created_at = db.Column(db.String(30), nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "taxpayer_mst": self.taxpayer_mst,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "total_input_vat": self.total_input_vat,
            "allocated_export_vat": self.allocated_export_vat,
            "refund_requested_amount": self.refund_requested_amount,
            "status": self.status,
            "created_at": self.created_at,
        }


class TransferPricingBenchmark(db.Model):
    """US-540: Transfer Pricing benchmarking comparison under Decree 132."""

    __tablename__ = "transfer_pricing_benchmark"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    taxpayer_mst = db.Column(db.String(20), nullable=False)
    transaction_type = db.Column(db.String(100), nullable=False)
    method_used = db.Column(db.String(50), nullable=False)
    taxpayer_margin = db.Column(db.Float, nullable=False)
    benchmark_p25 = db.Column(db.Float, nullable=False)
    benchmark_median = db.Column(db.Float, nullable=False)
    benchmark_p75 = db.Column(db.Float, nullable=False)
    adjustment_amount = db.Column(db.Float, nullable=False, default=0.0)
    status = db.Column(db.String(50), nullable=False, default="Compliant")  # Compliant, Adjusted

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "taxpayer_mst": self.taxpayer_mst,
            "transaction_type": self.transaction_type,
            "method_used": self.method_used,
            "taxpayer_margin": self.taxpayer_margin,
            "benchmark_p25": self.benchmark_p25,
            "benchmark_median": self.benchmark_median,
            "benchmark_p75": self.benchmark_p75,
            "adjustment_amount": self.adjustment_amount,
            "status": self.status,
        }


class ECommercePlatformTransaction(db.Model):
    """US-542: Simulated E-Commerce platform transaction log."""

    __tablename__ = "ecommerce_platform_transaction"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    taxpayer_mst = db.Column(db.String(20), nullable=False)
    platform_name = db.Column(db.String(100), nullable=False)
    transaction_id = db.Column(db.String(100), nullable=False)
    transaction_date = db.Column(db.String(20), nullable=False)  # YYYY-MM-DD
    buyer_name = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    vat_withheld = db.Column(db.Float, nullable=False, default=0.0)
    pit_withheld = db.Column(db.Float, nullable=False, default=0.0)
    invoice_matched_id = db.Column(db.String(100), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "taxpayer_mst": self.taxpayer_mst,
            "platform_name": self.platform_name,
            "transaction_id": self.transaction_id,
            "transaction_date": self.transaction_date,
            "buyer_name": self.buyer_name,
            "amount": self.amount,
            "vat_withheld": self.vat_withheld,
            "pit_withheld": self.pit_withheld,
            "invoice_matched_id": self.invoice_matched_id,
        }


class GlobalIfrsRule(db.Model):
    """US-550: Holds IFRS translation rules, global tax rates, and definitions."""

    __tablename__ = "global_ifrs_rules"

    rule_id = db.Column(db.String(100), primary_key=True)
    rule_type = db.Column(db.String(50), nullable=False)  # 'IAS_12', 'IFRS_15', 'IFRS_16', 'PILLAR_TWO'
    vas_code = db.Column(db.String(50), nullable=True)
    ifrs_treatment = db.Column(db.Text, nullable=False)
    config_json = db.Column(db.Text, nullable=True)

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "rule_type": self.rule_type,
            "vas_code": self.vas_code,
            "ifrs_treatment": self.ifrs_treatment,
            "config_json": self.config_json,
        }


class IntercompanyEntity(db.Model):
    """US-553: Defines intercompany entities and ownership percentages."""

    __tablename__ = "intercompany_entities"

    id = db.Column(db.String(100), primary_key=True)
    parent_mst = db.Column(db.String(20), nullable=False)
    subsidiary_mst = db.Column(db.String(20), nullable=False)
    relationship_type = db.Column(db.String(50), nullable=False)  # 'subsidiary', 'associate', 'joint_venture'
    ownership_percentage = db.Column(db.Float, nullable=False)
    transfer_pricing_method = db.Column(db.String(50), default="TNMM")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "parent_mst": self.parent_mst,
            "subsidiary_mst": self.subsidiary_mst,
            "relationship_type": self.relationship_type,
            "ownership_percentage": self.ownership_percentage,
            "transfer_pricing_method": self.transfer_pricing_method,
        }


class OecdGlobeRate(db.Model):
    """US-553: Defines country-specific tax parameters for OECD Pillar Two."""

    __tablename__ = "oecd_globe_rates"

    country_code = db.Column(db.String(10), primary_key=True)
    statutory_tax_rate = db.Column(db.Float, nullable=False)
    minimum_tax_rate = db.Column(db.Float, default=0.15)
    sbie_payroll_rate = db.Column(db.Float, default=0.05)
    sbie_assets_rate = db.Column(db.Float, default=0.05)

    def to_dict(self) -> dict:
        return {
            "country_code": self.country_code,
            "statutory_tax_rate": self.statutory_tax_rate,
            "minimum_tax_rate": self.minimum_tax_rate,
            "sbie_payroll_rate": self.sbie_payroll_rate,
            "sbie_assets_rate": self.sbie_assets_rate,
        }



class ECommerceReconciliationReport(db.Model):
    """US-542: Reconciliation report between e-commerce logs and invoices."""

    __tablename__ = "ecommerce_reconciliation_report"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    taxpayer_mst = db.Column(db.String(20), nullable=False)
    platform_name = db.Column(db.String(100), nullable=False)
    reconciliation_date = db.Column(db.String(20), nullable=False)  # YYYY-MM-DD
    total_platform_transactions = db.Column(db.Integer, nullable=False, default=0)
    matched_count = db.Column(db.Integer, nullable=False, default=0)
    mismatch_count = db.Column(db.Integer, nullable=False, default=0)
    total_platform_revenue = db.Column(db.Float, nullable=False, default=0.0)
    total_invoiced_revenue = db.Column(db.Float, nullable=False, default=0.0)
    gap_amount = db.Column(db.Float, nullable=False, default=0.0)
    compliance_status = db.Column(db.String(50), nullable=False, default="Compliant")  # Compliant, GapsFound

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "taxpayer_mst": self.taxpayer_mst,
            "platform_name": self.platform_name,
            "reconciliation_date": self.reconciliation_date,
            "total_platform_transactions": self.total_platform_transactions,
            "matched_count": self.matched_count,
            "mismatch_count": self.mismatch_count,
            "total_platform_revenue": self.total_platform_revenue,
            "total_invoiced_revenue": self.total_invoiced_revenue,
            "gap_amount": self.gap_amount,
            "compliance_status": self.compliance_status,
        }


class GroupFund(db.Model):
    """Represents a shared group fund (US-700+ / PRD-FUND)."""
    __tablename__ = "group_fund"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    group_id = db.Column(db.Integer, db.ForeignKey("tenant_group.id"), nullable=False, unique=True)
    name = db.Column(db.String(100), nullable=False)
    currency = db.Column(db.String(10), default="VND", nullable=False)
    created_at = db.Column(db.String(30), nullable=False)

    group = db.relationship("TenantGroup", backref=db.backref("fund", uselist=False, cascade="all, delete-orphan"))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "group_id": self.group_id,
            "name": self.name,
            "currency": self.currency,
            "created_at": self.created_at,
        }


class FundTransaction(db.Model):
    """Represents a transaction of deposit or expense in a group fund (PRD-FUND)."""
    __tablename__ = "fund_transaction"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fund_id = db.Column(db.Integer, db.ForeignKey("group_fund.id"), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # 'deposit' or 'expense'
    payer = db.Column(db.String(100), nullable=True)  # Name of the person depositing
    description = db.Column(db.String(255), nullable=True)  # Description of the expense
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.String(20), nullable=False)  # YYYY-MM-DD
    created_at = db.Column(db.String(30), nullable=False)

    fund = db.relationship("GroupFund", backref=db.backref("transactions", cascade="all, delete-orphan"))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "fund_id": self.fund_id,
            "transaction_type": self.transaction_type,
            "payer": self.payer or "",
            "description": self.description or "",
            "amount": self.amount,
            "date": self.date,
            "created_at": self.created_at,
        }






