# pyright: ignore[reportArgumentType]
"""
Capsule Service Unit Tests.

No database required — all tests use inline minimal objects with required
attributes only.  Follows the No-Mocks rule: no MagicMock, no monkeypatch.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

import pytest

from apps.capsules.services.capsule_core import (
    _increment_version,
    verify_capsule,
)
from apps.capsules.services.capsule_execution import (
    _check_capabilities,
    merge_parameters,
    substitute_parameters,
    validate_parameters,
)
from apps.capsules.services.capsule_export import (
    _compute_checksum,
    verify_export_checksum,
)

# ---------------------------------------------------------------------------
# Helpers: inline minimal objects
# ---------------------------------------------------------------------------

@dataclass
class FakeCapsule:
    """Minimal stand-in for Capsule model."""

    id: Any = field(default_factory=uuid4)
    name: str = "test-capsule"
    version: str = "1.0.0"
    description: str = ""
    status: str = "draft"
    tenant_id: str = "test-tenant"
    realm: str = "default"
    is_active: bool = True
    execution_graph: list = field(default_factory=list)
    parameters_schema: dict = field(default_factory=dict)
    capabilities_whitelist: list = field(default_factory=list)
    registry_signature: str | None = None
    constitution_ref: dict = field(default_factory=dict)
    body: dict = field(default_factory=dict)
    system_prompt: str = ""
    personality_traits: dict = field(default_factory=dict)
    neuromodulator_baseline: dict = field(default_factory=dict)
    capsule_type: str = "voyant.intelligence_recipe"
    output_formats: list = field(default_factory=lambda: ["pdf"])
    rbac_rules: dict = field(default_factory=dict)
    resource_limits: dict = field(default_factory=dict)
    install_count: int = 0
    execution_count: int = 0


@dataclass
class FakeInstallation:
    """Minimal stand-in for CapsuleInstallation model."""

    parameter_overrides: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# validate_parameters
# ---------------------------------------------------------------------------

class TestValidateParameters:
    def test_empty_schema_always_valid(self):
        capsule: Any = FakeCapsule(parameters_schema={})
        assert validate_parameters(capsule, {"foo": "bar"}) == (True, None)

    def test_missing_required_param(self):
        capsule: Any = FakeCapsule(
            parameters_schema={"query": {"required": True, "type": "string"}}
        )
        valid, error = validate_parameters(capsule, {})
        assert valid is False
        assert error is not None
        assert "Missing required parameter: query" in error

    def test_type_string(self):
        capsule: Any = FakeCapsule(parameters_schema={"name": {"type": "string"}})
        valid, error = validate_parameters(capsule, {"name": 123})
        assert valid is False
        assert error is not None
        assert "must be a string" in error

    def test_type_integer(self):
        capsule: Any = FakeCapsule(parameters_schema={"limit": {"type": "integer"}})
        assert validate_parameters(capsule, {"limit": 10}) == (True, None)
        valid, error = validate_parameters(capsule, {"limit": "ten"})
        assert valid is False
        assert error is not None
        assert "must be an integer" in error

    def test_type_number(self):
        capsule: Any = FakeCapsule(parameters_schema={"threshold": {"type": "number"}})
        assert validate_parameters(capsule, {"threshold": 3.14}) == (True, None)
        assert validate_parameters(capsule, {"threshold": 42}) == (True, None)
        valid, error = validate_parameters(capsule, {"threshold": "high"})
        assert valid is False
        assert error is not None
        assert "must be a number" in error

    def test_type_boolean(self):
        capsule: Any = FakeCapsule(parameters_schema={"verbose": {"type": "boolean"}})
        assert validate_parameters(capsule, {"verbose": True}) == (True, None)
        valid, error = validate_parameters(capsule, {"verbose": "yes"})
        assert valid is False
        assert error is not None
        assert "must be a boolean" in error

    def test_options_constraint(self):
        capsule: Any = FakeCapsule(
            parameters_schema={"format": {"type": "string", "options": ["pdf", "json"]}}
        )
        assert validate_parameters(capsule, {"format": "pdf"}) == (True, None)
        valid, error = validate_parameters(capsule, {"format": "xml"})
        assert valid is False
        assert error is not None
        assert "must be one of" in error

    def test_optional_param_not_required(self):
        capsule: Any = FakeCapsule(
            parameters_schema={"query": {"type": "string", "required": False}}
        )
        assert validate_parameters(capsule, {}) == (True, None)


# ---------------------------------------------------------------------------
# merge_parameters
# ---------------------------------------------------------------------------

class TestMergeParameters:
    def test_defaults_only(self):
        capsule: Any = FakeCapsule(
            parameters_schema={"limit": {"default": 10}, "format": {"default": "json"}}
        )
        merged = merge_parameters(capsule, None, {})
        assert merged == {"limit": 10, "format": "json"}

    def test_installation_overrides_defaults(self):
        capsule: Any = FakeCapsule(parameters_schema={"limit": {"default": 10}})
        inst: Any = FakeInstallation(parameter_overrides={"limit": 50})
        merged = merge_parameters(capsule, inst, {})
        assert merged["limit"] == 50

    def test_runtime_overrides_all(self):
        capsule: Any = FakeCapsule(parameters_schema={"limit": {"default": 10}})
        inst: Any = FakeInstallation(parameter_overrides={"limit": 50})
        merged = merge_parameters(capsule, inst, {"limit": 100})
        assert merged["limit"] == 100

    def test_no_schema_no_merge(self):
        capsule: Any = FakeCapsule(parameters_schema={})
        merged = merge_parameters(capsule, None, {"x": 1})
        assert merged == {"x": 1}


# ---------------------------------------------------------------------------
# substitute_parameters
# ---------------------------------------------------------------------------

class TestSubstituteParameters:
    def test_simple_substitution(self):
        template = {"query": "{{search_term}}"}
        result = substitute_parameters(template, {"search_term": "climate"})
        assert result["query"] == "climate"

    def test_nested_dict_substitution(self):
        template = {"params": {"q": "{{query}}", "limit": "{{max}}"}}
        result = substitute_parameters(template, {"query": "AI", "max": "10"})
        assert result["params"]["q"] == "AI"
        assert result["params"]["limit"] == "10"

    def test_list_substitution(self):
        template = {"items": ["{{a}}", "{{b}}"]}
        result = substitute_parameters(template, {"a": "x", "b": "y"})
        assert result["items"] == ["x", "y"]

    def test_step_results_access(self):
        template = {"summary": "Found {{steps.search.count}} results"}
        result = substitute_parameters(
            template, {}, step_results={"search": {"count": 42}}
        )
        assert result["summary"] == "Found 42 results"

    def test_missing_variable_keeps_template(self):
        template = {"query": "{{missing}}"}
        result = substitute_parameters(template, {})
        # Jinja2 sandbox renders undefined as empty string
        assert result["query"] == ""

    def test_no_template_strings_unchanged(self):
        template = {"num": 42, "flag": True, "data": {"a": 1}}
        result = substitute_parameters(template, {})
        assert result == {"num": 42, "flag": True, "data": {"a": 1}}


# ---------------------------------------------------------------------------
# _check_capabilities
# ---------------------------------------------------------------------------

class TestCheckCapabilities:
    def test_no_whitelist_allows_all(self):
        capsule: Any = FakeCapsule(capabilities_whitelist=[])
        _check_capabilities(capsule, "sql_query")  # should not raise

    def test_whitelisted_action_allowed(self):
        capsule: Any = FakeCapsule(capabilities_whitelist=["sql_query", "search"])
        _check_capabilities(capsule, "sql_query")  # should not raise

    def test_non_whitelisted_action_blocked(self):
        capsule: Any = FakeCapsule(
            name="restricted",
            capabilities_whitelist=["search"],
        )
        with pytest.raises(PermissionError) as exc:
            _check_capabilities(capsule, "sql_query")
        assert "sql_query" in str(exc.value)
        assert "restricted" in str(exc.value)

    def test_none_whitelist_treated_as_empty(self):
        capsule: Any = FakeCapsule(capabilities_whitelist=None)  # type: ignore[call-arg]
        _check_capabilities(capsule, "any_action")  # should not raise


# ---------------------------------------------------------------------------
# verify_capsule
# ---------------------------------------------------------------------------

class TestVerifyCapsule:
    def test_valid_capsule(self):
        capsule: Any = FakeCapsule(
            name="valid", version="1.0.0", execution_graph=[], parameters_schema={}
        )
        assert verify_capsule(capsule) is True

    def test_missing_name(self):
        capsule: Any = FakeCapsule(name="", version="1.0.0")
        assert verify_capsule(capsule) is False

    def test_missing_version(self):
        capsule: Any = FakeCapsule(name="test", version="")
        assert verify_capsule(capsule) is False

    def test_invalid_execution_graph(self):
        capsule: Any = FakeCapsule(execution_graph="not-a-list")  # type: ignore[call-arg]
        assert verify_capsule(capsule) is False

    def test_invalid_parameters_schema(self):
        capsule: Any = FakeCapsule(parameters_schema="not-a-dict")  # type: ignore[call-arg]
        assert verify_capsule(capsule) is False


# ---------------------------------------------------------------------------
# Export checksum
# ---------------------------------------------------------------------------

class TestExportChecksum:
    def test_compute_checksum_deterministic(self):
        data = {"a": 1, "b": [2, 3]}
        c1 = _compute_checksum(data)
        c2 = _compute_checksum(data)
        assert c1 == c2
        assert len(c1) == 64  # sha256 hex

    def test_verify_correct_checksum(self):
        data = {"capsule": {"name": "test"}, "instances": []}
        data["export_checksum"] = _compute_checksum(data)
        assert verify_export_checksum(data) is True

    def test_verify_tampered_data(self):
        data = {"capsule": {"name": "test"}, "instances": []}
        data["export_checksum"] = _compute_checksum(data)
        data["capsule"]["name"] = "tampered"
        assert verify_export_checksum(data) is False

    def test_verify_missing_checksum(self):
        data = {"capsule": {"name": "test"}}
        assert verify_export_checksum(data) is False


# ---------------------------------------------------------------------------
# Version increment
# ---------------------------------------------------------------------------

class TestIncrementVersion:
    def test_patch_increment(self):
        assert _increment_version("1.0.0") == "1.0.1"
        assert _increment_version("2.3.9") == "2.3.10"

    def test_non_semver_fallback(self):
        assert _increment_version("v1") == "v1.1"
        assert _increment_version("2024.01") == "2024.01.1"
