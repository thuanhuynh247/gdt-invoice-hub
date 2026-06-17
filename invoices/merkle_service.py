"""Merkle Tree and sequential ledger security for database integrity verification (US-332)."""

from __future__ import annotations

import hashlib
from extensions import db
from invoices.models import Invoice


def compute_invoice_hash(invoice: Invoice) -> str:
    """Computes a SHA-256 hash of an invoice record to prevent tampering."""
    raw_str = (
        f"{invoice.id}:"
        f"{invoice.number or ''}:"
        f"{invoice.date or ''}:"
        f"{invoice.total_amount or 0.0}:"
        f"{invoice.seller_mst or ''}:"
        f"{invoice.buyer_mst or ''}"
    )
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()


class MerkleTree:
    """Constructs a Merkle Tree from invoice hashes."""

    def __init__(self, leaves: list[str]):
        self.leaves = leaves
        self.levels = []
        if leaves:
            self.build_tree()

    def build_tree(self):
        current_level = self.leaves[:]
        self.levels.append(current_level)

        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i+1] if i + 1 < len(current_level) else left
                combined = left + right
                parent = hashlib.sha256(combined.encode("utf-8")).hexdigest()
                next_level.append(parent)
            current_level = next_level
            self.levels.append(current_level)

    def get_root(self) -> str | None:
        if not self.levels:
            return None
        return self.levels[-1][0]


def rebuild_and_write_merkle_roots(taxpayer_mst: str) -> str | None:
    """Fetches all taxpayer invoices, builds sequential hashes, and records cumulative roots."""
    invoices = Invoice.query.filter_by(taxpayer_mst=taxpayer_mst).order_by(Invoice.date, Invoice.id).all()
    if not invoices:
        return None

    hashes = []
    for idx, inv in enumerate(invoices):
        inv_hash = compute_invoice_hash(inv)
        inv.merkle_hash = inv_hash
        inv.merkle_index = idx
        hashes.append(inv_hash)

        # Cumulative Merkle root at this point (0 to idx)
        subtree = MerkleTree(hashes[:idx+1])
        inv.merkle_root = subtree.get_root()

    db.session.commit()
    return invoices[-1].merkle_root


def verify_ledger_integrity(taxpayer_mst: str) -> tuple[bool, list[str]]:
    """Verifies that invoice records match their historical cryptographic hashes.

    Returns:
        tuple[bool, list[str]]: (is_valid, list of tampered invoice IDs)
    """
    invoices = Invoice.query.filter_by(taxpayer_mst=taxpayer_mst).order_by(Invoice.date, Invoice.id).all()
    if not invoices:
        return True, []

    tampered_ids = []
    running_hashes = []

    for idx, inv in enumerate(invoices):
        # 1. Recalculate invoice hash and compare with stored merkle_hash
        current_hash = compute_invoice_hash(inv)
        if inv.merkle_hash != current_hash:
            tampered_ids.append(inv.id)

        # 2. Verify cumulative Merkle root
        running_hashes.append(current_hash)
        subtree = MerkleTree(running_hashes)
        expected_root = subtree.get_root()

        if inv.merkle_root != expected_root:
            if inv.id not in tampered_ids:
                tampered_ids.append(inv.id)

    is_valid = len(tampered_ids) == 0
    return is_valid, tampered_ids
