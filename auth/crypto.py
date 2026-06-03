"""Cryptography utilities for encrypting credentials in session.

Uses industry-standard symmetric key encryption (AES-128-CBC with HMAC via Fernet)
to secure taxpayer credentials inside the client's session cookie.
"""

from __future__ import annotations

import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from flask import current_app


def _get_fernet_key() -> bytes:
    """Derive a 32-byte URL-safe key from the application's SECRET_KEY.
    
    Uses PBKDF2 (Password-Based Key Derivation Function 2) with SHA256
    and a fixed salt. This ensures the key is cryptographically strong
    and remains identical across server restarts (as long as SECRET_KEY is stable),
    preventing user session decryption failures when the app restarts.
    """
    secret_key_str = "change-this-secret-key"
    try:
        from flask import has_app_context
        if has_app_context():
            secret_key_str = current_app.config.get("SECRET_KEY", secret_key_str)
    except Exception:
        pass

    secret_key = secret_key_str.encode("utf-8")
    # Fixed salt to ensure deterministic key derivation
    salt = b"gdt_invoice_hub_salt_12345"
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf.derive(secret_key))


def encrypt_password(password: str) -> str:
    """Encrypt a plaintext password and return a base64 encoded ciphertext string.
    
    This function takes the plaintext password, encrypts it using AES-128
    in CBC mode with a cryptographic signature (HMAC) to prevent tampering.
    """
    if not password:
        return ""
    
    key = _get_fernet_key()
    fernet = Fernet(key)
    ciphertext = fernet.encrypt(password.encode("utf-8"))
    return ciphertext.decode("utf-8")


def decrypt_password(ciphertext: str) -> str:
    """Decrypt a base64 encoded ciphertext string back to the plaintext password.
    
    Decrypts the ciphertext using the derived key and validates the signature
    to ensure the data was not modified.
    """
    if not ciphertext:
        return ""
    
    key = _get_fernet_key()
    fernet = Fernet(key)
    plaintext = fernet.decrypt(ciphertext.encode("utf-8"))
    return plaintext.decode("utf-8")
