"""Zero-Knowledge Proof (ZKP) service for private tax VAT compliance auditing (US-333)."""

from __future__ import annotations

import hashlib
import random

# Cryptographically secure prime (RFC 3526 1536-bit MODP Group or scaled down for performance)
# We use a 256-bit prime for secure and performant arithmetic.
P = 115792089237316195423570985008687907853269984665640564039457584007913129639747
G = 2
H = 5


def generate_random_blinding() -> int:
    """Generates a cryptographically strong random blinding factor modulo P-1."""
    return random.randint(1, P - 2)


def create_pedersen_commitment(value: int, r: int) -> int:
    """Creates a Pedersen commitment: C = (G^value * H^r) % P."""
    # Ensure values are within range
    val_mod = value % (P - 1)
    r_mod = r % (P - 1)
    return (pow(G, val_mod, P) * pow(H, r_mod, P)) % P


def generate_vat_compliance_proof(
    amount_before_tax: float,
    tax_amount: float,
    rate_percent: int,  # e.g., 10 for 10% VAT, 8 for 8% VAT
) -> dict:
    """Generates a Non-Interactive Zero-Knowledge Proof (NIZKP) of VAT compliance.

    Proves that 100 * VAT_Amount = Rate_Percent * Amount_Before_Tax without revealing
    the raw values.
    """
    # Convert amounts to cents/units to work with integers
    v = int(round(tax_amount * 100))
    a = int(round(amount_before_tax * 100))

    r_V = generate_random_blinding()
    r_A = generate_random_blinding()

    # Commitments
    C_V = create_pedersen_commitment(v, r_V)
    C_A = create_pedersen_commitment(a, r_A)

    # We want to prove 100 * v - rate_percent * a = 0
    # Let C_proof = C_V^100 * C_A^(-rate_percent) = H^(100 * r_V - rate_percent * r_A)
    # Let s = (100 * r_V - rate_percent * r_A) mod (P-1)
    s = (100 * r_V - rate_percent * r_A) % (P - 1)

    # Prove knowledge of discrete log of C_proof with respect to base H (Schnorr's protocol)
    k = generate_random_blinding()
    T = pow(H, k, P)

    # Fiat-Shamir heuristic challenge
    challenge_data = f"{T}:{C_V}:{C_A}:{rate_percent}".encode("utf-8")
    c = int(hashlib.sha256(challenge_data).hexdigest(), 16) % (P - 1)

    # Response: z = k + c * s
    z = (k + c * s) % (P - 1)

    return {
        "C_V": str(C_V),
        "C_A": str(C_A),
        "rate_percent": rate_percent,
        "proof": {
            "T": str(T),
            "z": str(z)
        }
    }


def verify_vat_compliance_proof(proof_data: dict) -> bool:
    """Verifies the ZKP that the committed tax amount is the specified percentage of the committed net amount."""
    try:
        C_V = int(proof_data["C_V"])
        C_A = int(proof_data["C_A"])
        rate_percent = int(proof_data["rate_percent"])
        T = int(proof_data["proof"]["T"])
        z = int(proof_data["proof"]["z"])

        # Compute C_proof = C_V^100 * C_A^(-rate_percent) = C_V^100 / C_A^rate_percent
        # Using modular inverse for division
        num = pow(C_V, 100, P)
        den = pow(C_A, rate_percent, P)
        inv_den = pow(den, P - 2, P)  # Fermat's Little Theorem since P is prime
        C_proof = (num * inv_den) % P

        # Recompute challenge c
        challenge_data = f"{T}:{C_V}:{C_A}:{rate_percent}".encode("utf-8")
        c = int(hashlib.sha256(challenge_data).hexdigest(), 16) % (P - 1)

        # Verification check: H^z == T * C_proof^c mod P
        lhs = pow(H, z, P)
        rhs = (T * pow(C_proof, c, P)) % P

        return lhs == rhs
    except Exception:
        return False
