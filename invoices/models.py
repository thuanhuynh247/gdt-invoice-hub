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

    def to_dict(self) -> dict:
        return {
            "mst": self.mst,
            "name": self.name or "",
            "address": self.address or "",
            "mst_status": self.mst_status or "",
            "mst_last_checked": self.mst_last_checked or "",
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


