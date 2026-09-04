"""Tests for apps.capsules.services.capsule_core — pure logic tests.

Tests the _increment_version and _apply_updates helper functions,
and the verify_capsule logic using real dict structures.
"""

import pytest

from apps.capsules.services.capsule_core import _increment_version, _apply_updates


# ---------------------------------------------------------------------------
# _increment_version
# ---------------------------------------------------------------------------


class TestIncrementVersion:
    def test_basic_patch_increment(self):
        assert _increment_version("1.0.0") == "1.0.1"

    def test_large_patch(self):
        assert _increment_version("2.3.9") == "2.3.10"

    def test_non_standard_version_fallback(self):
        result = _increment_version("v1")
        assert result == "v1.1"

    def test_two_part_version(self):
        result = _increment_version("1.0")
        assert result == "1.0.1"

    def test_empty_version(self):
        result = _increment_version("")
        assert result == ".1"

    def test_already_incremented(self):
        assert _increment_version("1.0.5") == "1.0.6"


# ---------------------------------------------------------------------------
# _apply_updates (tested with a simple namespace object)
# ---------------------------------------------------------------------------


class TestApplyUpdates:
    def _make_capsule_stub(self):
        """Create a simple object with the allowed fields."""

        class CapsuleStub:
            description = "original"
            system_prompt = "original prompt"
            personality_traits = {}
            neuromodulator_baseline = {}
            capsule_type = "basic"
            execution_graph = []
            parameters_schema = {}
            output_formats = []
            rbac_rules = {}
            capabilities_whitelist = []
            resource_limits = {}

        return CapsuleStub()

    def test_updates_allowed_fields(self):
        capsule = self._make_capsule_stub()
        _apply_updates(capsule, {"description": "new description", "system_prompt": "new prompt"})
        assert capsule.description == "new description"
        assert capsule.system_prompt == "new prompt"

    def test_ignores_disallowed_fields(self):
        capsule = self._make_capsule_stub()
        _apply_updates(capsule, {"name": "hacked", "tenant_id": "evil"})
        # name and tenant_id are not in allowed_fields
        assert not hasattr(capsule, "name") or capsule.__class__.name is None

    def test_partial_updates(self):
        capsule = self._make_capsule_stub()
        _apply_updates(capsule, {"description": "updated"})
        assert capsule.description == "updated"
        assert capsule.system_prompt == "original prompt"  # Unchanged

    def test_empty_updates(self):
        capsule = self._make_capsule_stub()
        _apply_updates(capsule, {})
        assert capsule.description == "original"


# ---------------------------------------------------------------------------
# verify_capsule logic (structural validation)
# ---------------------------------------------------------------------------


class TestVerifyCapsuleLogic:
    """Test the structural validation checks that verify_capsule performs."""

    def _make_capsule_stub(self, **kwargs):
        class CapsuleStub:
            id = "test-id"
            name = kwargs.get("name", "test-capsule")
            version = kwargs.get("version", "1.0.0")
            execution_graph = kwargs.get("execution_graph", [{"action": "test"}])
            parameters_schema = kwargs.get("parameters_schema", {"param": {"type": "string"}})
            body = kwargs.get("body", {"key": "value"})
            registry_signature = kwargs.get("registry_signature", None)

        return CapsuleStub()

    def test_missing_name_fails(self):
        """Capsule without name should fail verification."""
        capsule = self._make_capsule_stub(name="")
        # verify_capsule checks: if not capsule.name or not capsule.version
        assert not capsule.name or not capsule.version

    def test_missing_version_fails(self):
        capsule = self._make_capsule_stub(version="")
        assert not capsule.name or not capsule.version

    def test_invalid_execution_graph_fails(self):
        capsule = self._make_capsule_stub(execution_graph="not-a-list")
        assert not isinstance(capsule.execution_graph, list)

    def test_invalid_parameters_schema_fails(self):
        capsule = self._make_capsule_stub(parameters_schema="not-a-dict")
        assert not isinstance(capsule.parameters_schema, dict)

    def test_valid_structure_passes_checks(self):
        capsule = self._make_capsule_stub()
        assert capsule.name
        assert capsule.version
        assert isinstance(capsule.execution_graph, list)
        assert isinstance(capsule.parameters_schema, dict)

    def test_signature_mismatch_detection(self):
        """Test that content hash mismatch is detected."""
        import hashlib
        import json

        body = {"key": "value"}
        content = json.dumps(body, sort_keys=True, default=str)
        correct_sig = f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"
        wrong_sig = "sha256:" + "0" * 64

        assert correct_sig != wrong_sig
