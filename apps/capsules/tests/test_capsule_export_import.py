"""
Capsule Export/Import Tests.

Tests somaAgent01-compatible bundle serialization.
"""

from __future__ import annotations

from apps.capsules.services.capsule_export import _compute_checksum, verify_export_checksum


class TestExportChecksum:
    def test_checksum_computation(self):
        data = {"capsule": {"name": "test", "version": "1.0.0"}}
        checksum = _compute_checksum(data)
        # Should be deterministic
        assert _compute_checksum(data) == checksum
        # Should be a hex string
        assert len(checksum) == 64

    def test_checksum_verification(self):
        data: dict[str, object] = {"capsule": {"name": "test", "version": "1.0.0"}}
        checksum = _compute_checksum(data)
        data["export_checksum"] = checksum
        assert verify_export_checksum(data) is True

    def test_checksum_tampered(self):
        data: dict[str, object] = {"capsule": {"name": "test", "version": "1.0.0"}}
        checksum = _compute_checksum(data)
        data["export_checksum"] = checksum
        data["capsule"]["name"] = "tampered"  # type: ignore[index]
        assert verify_export_checksum(data) is False

    def test_checksum_missing(self):
        data = {"capsule": {"name": "test", "version": "1.0.0"}}
        assert verify_export_checksum(data) is False
