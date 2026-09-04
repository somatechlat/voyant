"""
Capsule Ed25519 Signature Verification.

Provides cryptographic signing and verification for capsules using Ed25519
digital signatures. Ensures capsule integrity and authenticity before execution.

Capsules are signed at certification time. Before execution, the signature is
verified against the capsule's canonical content hash to detect tampering.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SignatureResult:
    """Result of a signing or verification operation."""

    valid: bool
    algorithm: str = "Ed25519"
    public_key_fingerprint: str = ""
    error: str = ""


def _canonicalize(data: dict[str, Any]) -> bytes:
    """Produce deterministic JSON bytes for signing (sorted keys, no whitespace)."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def compute_content_hash(capsule_data: dict[str, Any]) -> str:
    """Compute a SHA-256 content hash of the canonical capsule data."""
    canonical = _canonicalize(capsule_data)
    return hashlib.sha256(canonical).hexdigest()


def sign_capsule(
    capsule_data: dict[str, Any],
    private_key_bytes: bytes,
) -> str:
    """
    Sign a capsule's canonical content with an Ed25519 private key.

    Returns:
        Base64-encoded Ed25519 signature string.
    """
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    private_key = Ed25519PrivateKey.from_private_bytes(private_key_bytes)
    content_hash = compute_content_hash(capsule_data)
    signature = private_key.sign(content_hash.encode("utf-8"))
    return base64.b64encode(signature).decode("ascii")


def verify_signature(
    capsule_data: dict[str, Any],
    signature_b64: str,
    public_key_bytes: bytes,
) -> SignatureResult:
    """
    Verify an Ed25519 signature against a capsule's canonical content.

    Returns:
        SignatureResult with valid=True if signature is authentic.
    """
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    try:
        public_key = Ed25519PublicKey.from_public_bytes(public_key_bytes)
        content_hash = compute_content_hash(capsule_data)
        signature = base64.b64decode(signature_b64)

        public_key.verify(signature, content_hash.encode("utf-8"))

        fingerprint = hashlib.sha256(public_key_bytes).hexdigest()[:16]
        return SignatureResult(valid=True, public_key_fingerprint=fingerprint)
    except Exception as exc:
        return SignatureResult(valid=False, error=str(exc))


def generate_keypair() -> tuple[bytes, bytes]:
    """
    Generate a new Ed25519 keypair for capsule signing.

    Returns:
        Tuple of (private_key_bytes, public_key_bytes), each 32 bytes.
    """
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    private_key = Ed25519PrivateKey.generate()
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return private_bytes, public_bytes
