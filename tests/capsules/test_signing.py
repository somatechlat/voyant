"""Tests for apps.capsules.services.capsule_signing — Ed25519 signing and verification."""

import base64
import hashlib
import json

import pytest

from apps.capsules.services.capsule_signing import (
    SignatureResult,
    compute_content_hash,
    generate_keypair,
    sign_capsule,
    verify_signature,
)


# ---------------------------------------------------------------------------
# compute_content_hash
# ---------------------------------------------------------------------------


class TestComputeContentHash:
    def test_deterministic(self):
        data = {"name": "test", "version": "1.0.0"}
        h1 = compute_content_hash(data)
        h2 = compute_content_hash(data)
        assert h1 == h2

    def test_sha256_format(self):
        h = compute_content_hash({"key": "value"})
        assert len(h) == 64  # SHA-256 hex digest
        assert all(c in "0123456789abcdef" for c in h)

    def test_different_data_different_hash(self):
        h1 = compute_content_hash({"a": 1})
        h2 = compute_content_hash({"a": 2})
        assert h1 != h2

    def test_sorted_keys(self):
        """Hash should be the same regardless of key insertion order."""
        h1 = compute_content_hash({"b": 2, "a": 1})
        h2 = compute_content_hash({"a": 1, "b": 2})
        assert h1 == h2

    def test_empty_dict(self):
        h = compute_content_hash({})
        assert len(h) == 64

    def test_nested_data(self):
        data = {"outer": {"inner": [1, 2, 3]}, "flag": True}
        h = compute_content_hash(data)
        assert len(h) == 64


# ---------------------------------------------------------------------------
# generate_keypair
# ---------------------------------------------------------------------------


class TestGenerateKeypair:
    def test_returns_two_byte_strings(self):
        priv, pub = generate_keypair()
        assert isinstance(priv, bytes)
        assert isinstance(pub, bytes)

    def test_key_lengths(self):
        priv, pub = generate_keypair()
        assert len(priv) == 32  # Ed25519 private key is 32 bytes
        assert len(pub) == 32  # Ed25519 public key is 32 bytes

    def test_different_keypairs(self):
        priv1, pub1 = generate_keypair()
        priv2, pub2 = generate_keypair()
        assert priv1 != priv2
        assert pub1 != pub2


# ---------------------------------------------------------------------------
# sign_capsule and verify_signature
# ---------------------------------------------------------------------------


class TestSignAndVerify:
    def test_sign_and_verify_roundtrip(self):
        priv, pub = generate_keypair()
        capsule_data = {"name": "test-capsule", "version": "1.0.0", "body": {"key": "value"}}

        signature = sign_capsule(capsule_data, priv)
        assert isinstance(signature, str)

        result = verify_signature(capsule_data, signature, pub)
        assert result.valid is True
        assert result.algorithm == "Ed25519"
        assert result.public_key_fingerprint
        assert result.error == ""

    def test_tampered_data_fails_verification(self):
        priv, pub = generate_keypair()
        capsule_data = {"name": "original"}
        signature = sign_capsule(capsule_data, priv)

        tampered = {"name": "tampered"}
        result = verify_signature(tampered, signature, pub)
        assert result.valid is False
        assert result.error  # Should have an error message

    def test_wrong_key_fails_verification(self):
        priv1, pub1 = generate_keypair()
        priv2, pub2 = generate_keypair()

        capsule_data = {"name": "test"}
        signature = sign_capsule(capsule_data, priv1)

        result = verify_signature(capsule_data, signature, pub2)
        assert result.valid is False

    def test_invalid_signature_format(self):
        _, pub = generate_keypair()
        result = verify_signature({"name": "test"}, "not-a-valid-signature", pub)
        assert result.valid is False

    def test_signature_is_base64(self):
        priv, _ = generate_keypair()
        sig = sign_capsule({"name": "test"}, priv)
        # Should be valid base64
        decoded = base64.b64decode(sig)
        assert len(decoded) == 64  # Ed25519 signature is 64 bytes


# ---------------------------------------------------------------------------
# SignatureResult
# ---------------------------------------------------------------------------


class TestSignatureResult:
    def test_valid_result(self):
        r = SignatureResult(valid=True, public_key_fingerprint="abc123")
        assert r.valid is True
        assert r.algorithm == "Ed25519"
        assert r.error == ""

    def test_invalid_result(self):
        r = SignatureResult(valid=False, error="Verification failed")
        assert r.valid is False
        assert r.error == "Verification failed"


# ---------------------------------------------------------------------------
# Integration: full signing pipeline
# ---------------------------------------------------------------------------


class TestFullSigningPipeline:
    def test_sign_verify_with_complex_capsule(self):
        """Test with a realistic capsule data structure."""
        priv, pub = generate_keypair()
        capsule_data = {
            "name": "data-analyst",
            "version": "2.1.0",
            "body": {
                "execution_graph": [
                    {"action": "ingest", "params": {"source": "csv"}},
                    {"action": "analyze", "params": {"method": "pca"}},
                ],
                "parameters_schema": {
                    "source": {"type": "string", "required": True},
                },
            },
            "soul": {
                "system_prompt": "You are a data analyst.",
                "personality_traits": {"analytical": 0.9},
            },
        }

        sig = sign_capsule(capsule_data, priv)
        result = verify_signature(capsule_data, sig, pub)
        assert result.valid is True

    def test_content_hash_matches_manual_computation(self):
        data = {"key": "value"}
        expected = hashlib.sha256(
            json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest()
        assert compute_content_hash(data) == expected
