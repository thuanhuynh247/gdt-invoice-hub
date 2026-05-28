"""Tests for multi-tenant database routing and encrypted backup (US-092, US-093)."""

from __future__ import annotations

import os
import sqlite3
import tempfile
import shutil
import pytest

from invoices.multitenant_service import (
    get_tenant_db_path,
    tenant_db_exists,
    bootstrap_tenant_db,
    list_tenant_databases,
    encrypt_file_aes256,
    decrypt_file_aes256,
    create_encrypted_backup,
    compute_file_checksum,
)


@pytest.fixture
def tenant_dir(tmp_path):
    """Provide a temporary directory for tenant database files."""
    d = tmp_path / "tenants"
    d.mkdir()
    return str(d)


class TestDynamicTenantRouter:
    """US-092: Dynamic Multi-Tenant SQLite Database Router & Bootstrapper."""

    def test_get_tenant_db_path(self, tenant_dir):
        """Verify correct file path generation for a given MST."""
        path = get_tenant_db_path("0109998887", base_dir=tenant_dir)
        assert path.endswith("tenant_0109998887.db")
        assert tenant_dir in path

    def test_get_tenant_db_path_sanitizes_input(self, tenant_dir):
        """Verify that dashes and spaces in MST are stripped."""
        path = get_tenant_db_path("010-999 8887", base_dir=tenant_dir)
        assert "tenant_0109998887.db" in path

    def test_get_tenant_db_path_empty_mst_raises(self, tenant_dir):
        """Empty MST must raise ValueError."""
        with pytest.raises(ValueError, match="MST cannot be empty"):
            get_tenant_db_path("", base_dir=tenant_dir)

    def test_tenant_db_exists_false_initially(self, tenant_dir):
        """Non-bootstrapped tenant should not exist yet."""
        assert tenant_db_exists("9999999999", base_dir=tenant_dir) is False

    def test_bootstrap_creates_db_file(self, tenant_dir):
        """Bootstrap should create the .db file with correct schema."""
        path = bootstrap_tenant_db("0109998887", base_dir=tenant_dir)
        assert os.path.isfile(path)

        # Verify tables exist
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [r[0] for r in cur.fetchall()]
        conn.close()

        assert "tenant_meta" in tables
        assert "invoice" in tables
        assert "audit_ledger" in tables

    def test_bootstrap_seeds_metadata(self, tenant_dir):
        """Bootstrap should seed the created_at and mst metadata keys."""
        path = bootstrap_tenant_db("0109998887", base_dir=tenant_dir)
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        cur.execute("SELECT key, value FROM tenant_meta ORDER BY key")
        meta = {k: v for k, v in cur.fetchall()}
        conn.close()

        assert meta["mst"] == "0109998887"
        assert "created_at" in meta

    def test_tenant_db_exists_after_bootstrap(self, tenant_dir):
        """After bootstrapping, tenant_db_exists should return True."""
        bootstrap_tenant_db("0109998887", base_dir=tenant_dir)
        assert tenant_db_exists("0109998887", base_dir=tenant_dir) is True

    def test_tenant_isolation(self, tenant_dir):
        """Tenant A's data must NOT be accessible from Tenant B's database."""
        path_a = bootstrap_tenant_db("1111111111", base_dir=tenant_dir)
        path_b = bootstrap_tenant_db("2222222222", base_dir=tenant_dir)

        # Insert a record into tenant A
        conn_a = sqlite3.connect(path_a)
        conn_a.execute(
            "INSERT INTO invoice (id, seller_name, seller_mst, amount_before_tax, tax_amount, total_amount, imported_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("INV-A-001", "Seller A", "1111111111", 1000, 100, 1100, "2026-05-28"),
        )
        conn_a.commit()
        conn_a.close()

        # Query tenant B — should have zero invoices
        conn_b = sqlite3.connect(path_b)
        count = conn_b.execute("SELECT COUNT(*) FROM invoice").fetchone()[0]
        conn_b.close()

        assert count == 0

    def test_list_tenant_databases(self, tenant_dir):
        """list_tenant_databases should return all bootstrapped tenants."""
        bootstrap_tenant_db("1111111111", base_dir=tenant_dir)
        bootstrap_tenant_db("2222222222", base_dir=tenant_dir)

        tenants = list_tenant_databases(base_dir=tenant_dir)
        msts = [t["mst"] for t in tenants]
        assert "1111111111" in msts
        assert "2222222222" in msts
        assert all(t["size_bytes"] > 0 for t in tenants)


class TestEncryptedBackup:
    """US-093: AES-256 Encrypted Tenant Cloud Snapshot Worker."""

    def test_encrypt_decrypt_roundtrip(self, tenant_dir):
        """Encrypting and decrypting must return identical content."""
        # Create a small test file
        test_file = os.path.join(tenant_dir, "test_plaintext.db")
        original_data = b"Hello, this is secret taxpayer data! MST: 0109998887"
        with open(test_file, "wb") as f:
            f.write(original_data)

        key = b"0123456789abcdef0123456789abcdef"  # 32 bytes = AES-256

        encrypted = encrypt_file_aes256(test_file, key)
        assert encrypted != original_data
        assert len(encrypted) > 0

        decrypted = decrypt_file_aes256(encrypted, key)
        assert decrypted == original_data

    def test_wrong_key_fails_decryption(self, tenant_dir):
        """Decryption with wrong key should NOT produce original content."""
        test_file = os.path.join(tenant_dir, "test_secret.db")
        original_data = b"Highly confidential invoice data"
        with open(test_file, "wb") as f:
            f.write(original_data)

        correct_key = b"0123456789abcdef0123456789abcdef"
        wrong_key = b"xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

        encrypted = encrypt_file_aes256(test_file, correct_key)
        decrypted_wrong = decrypt_file_aes256(encrypted, wrong_key)
        assert decrypted_wrong != original_data

    def test_create_encrypted_backup(self, tenant_dir):
        """Full backup pipeline: bootstrap → encrypt → verify file exists."""
        bootstrap_tenant_db("0109998887", base_dir=tenant_dir)

        backup_dir = os.path.join(tenant_dir, "backups")
        key = b"0123456789abcdef0123456789abcdef"

        backup_path = create_encrypted_backup(
            mst="0109998887",
            key=key,
            output_dir=backup_dir,
            base_dir=tenant_dir,
        )

        assert os.path.isfile(backup_path)
        assert backup_path.endswith(".enc")
        assert os.path.getsize(backup_path) > 0

    def test_backup_decrypts_to_valid_sqlite(self, tenant_dir):
        """Decrypted backup must be a valid SQLite database."""
        path = bootstrap_tenant_db("0109998887", base_dir=tenant_dir)

        # Insert test data
        conn = sqlite3.connect(path)
        conn.execute(
            "INSERT INTO invoice (id, seller_name, seller_mst, amount_before_tax, tax_amount, total_amount, imported_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("INV-BACKUP-001", "Test Corp", "0109998887", 5000, 500, 5500, "2026-05-28"),
        )
        conn.commit()
        conn.close()

        backup_dir = os.path.join(tenant_dir, "backups")
        key = b"0123456789abcdef0123456789abcdef"

        backup_path = create_encrypted_backup("0109998887", key, backup_dir, tenant_dir)

        # Read and decrypt
        with open(backup_path, "rb") as f:
            encrypted = f.read()
        decrypted = decrypt_file_aes256(encrypted, key)

        # Write decrypted to a temp file and verify it's valid SQLite
        restored_path = os.path.join(tenant_dir, "restored.db")
        with open(restored_path, "wb") as f:
            f.write(decrypted)

        conn2 = sqlite3.connect(restored_path)
        count = conn2.execute("SELECT COUNT(*) FROM invoice").fetchone()[0]
        inv = conn2.execute("SELECT id FROM invoice WHERE id='INV-BACKUP-001'").fetchone()
        conn2.close()

        assert count == 1
        assert inv[0] == "INV-BACKUP-001"

    def test_file_checksum(self, tenant_dir):
        """compute_file_checksum should return consistent SHA-256 hash."""
        test_file = os.path.join(tenant_dir, "checksum_test.txt")
        with open(test_file, "w") as f:
            f.write("Consistent data for checksum")

        hash1 = compute_file_checksum(test_file)
        hash2 = compute_file_checksum(test_file)
        assert hash1 == hash2
        assert len(hash1) == 64

    def test_backup_missing_db_raises(self, tenant_dir):
        """Attempting to backup a non-existent tenant should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            create_encrypted_backup(
                mst="9999999999",
                key=b"0123456789abcdef0123456789abcdef",
                base_dir=tenant_dir,
            )
