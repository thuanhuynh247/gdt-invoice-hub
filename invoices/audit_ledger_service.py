"""Cryptographic audit ledger service for tamper-proof compliance trails."""

from __future__ import annotations

import json
import hashlib
from datetime import datetime
from extensions import db
from invoices.models import AuditBlock

GENESIS_HASH = "0" * 64


def compute_hash(text: str) -> str:
    """Compute the SHA-256 hex digest of a string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def serialize_payload(payload: dict) -> str:
    """Consistently serialize a payload dictionary to JSON."""
    return json.dumps(payload, sort_keys=True, ensure_ascii=False)


def add_audit_block(action_type: str, mst: str, payload_dict: dict, signature: str | None = None) -> AuditBlock:
    """Create, chain, and persist a new cryptographic audit block in the ledger."""
    # Find the last block to get the preceding block's hash
    last_block = AuditBlock.query.order_by(AuditBlock.block_id.desc()).first()
    prev_hash = last_block.block_hash if last_block else GENESIS_HASH

    # Serialize payload and hash it
    payload_str = serialize_payload(payload_dict)
    payload_hash = compute_hash(payload_str)

    from datetime import timezone
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Deterministic block hashing formula
    block_hash_inputs = f"{timestamp}|{action_type}|{mst}|{payload_hash}|{prev_hash}"
    block_hash = compute_hash(block_hash_inputs)

    # Generate a mock signature if none provided
    if not signature:
        # Mock signing using a simulated RSA-2048 private key
        signature = compute_hash(block_hash + "_private_key_sig")

    block = AuditBlock(
        timestamp=timestamp,
        action_type=action_type,
        mst=mst,
        payload_hash=payload_hash,
        prev_block_hash=prev_hash,
        block_hash=block_hash,
        signature=signature,
    )

    db.session.add(block)
    db.session.commit()
    return block


def verify_ledger_integrity() -> tuple[bool, int | None, str | None]:
    """Verify that every block in the ledger is intact and the cryptographic chain is unbroken."""
    blocks = AuditBlock.query.order_by(AuditBlock.block_id.asc()).all()
    
    prev_hash = GENESIS_HASH

    for block in blocks:
        # 1. Verify link back to the previous block
        if block.prev_block_hash != prev_hash:
            return (
                False,
                block.block_id,
                f"Chaining break at Block #{block.block_id}: expected prev_hash '{prev_hash}', got '{block.prev_block_hash}'."
            )

        # 2. Recalculate block hash and compare
        expected_hash_inputs = f"{block.timestamp}|{block.action_type}|{block.mst}|{block.payload_hash}|{block.prev_block_hash}"
        recalculated_hash = compute_hash(expected_hash_inputs)

        if block.block_hash != recalculated_hash:
            return (
                False,
                block.block_id,
                f"Integrity corruption at Block #{block.block_id}: recalculated hash '{recalculated_hash}' does not match stored hash '{block.block_hash}'."
            )

        prev_hash = block.block_hash

    return True, None, None
