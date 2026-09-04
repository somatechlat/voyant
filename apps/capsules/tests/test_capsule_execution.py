"""
Capsule Execution Service Tests.

Tests parameter validation, merging, and substitution using REAL Capsule model
instances — no fakes, no mocks. If PostgreSQL is offline, DB-dependent tests
are skipped after a single connection attempt.
"""

from __future__ import annotations

import socket

import pytest

from apps.capsules.models import Capsule, CapsuleInstallation
from apps.capsules.services.capsule_execution import (
    merge_parameters,
    substitute_parameters,
    validate_parameters,
)

# --- Check DB availability at import time (no ORM connection needed) ---
DB_AVAILABLE = False
_db_host = "localhost"
_db_port = 45432
try:
    _sock = socket.create_connection((_db_host, _db_port), timeout=1)
    _sock.close()
    DB_AVAILABLE = True
except Exception:
    pass


def _make_unsaved_capsule(**kwargs) -> Capsule:
    """Return a real Capsule instance without persisting to the database.

    This is NOT a fake — it is a genuine Django model instance.  Only
    attribute reads are exercised, so no DB round-trip is required.
    """
    defaults = {
        "name": "test-capsule",
        "version": "1.0.0",
        "tenant_id": "default",
        "realm": "default",
        "status": Capsule.STATUS_ACTIVE,
    }
    defaults.update(kwargs)
    return Capsule(**defaults)


class TestValidateParameters:
    def test_empty_schema_always_valid(self):
        capsule = _make_unsaved_capsule(parameters_schema={})
        valid, error = validate_parameters(capsule, {})
        assert valid is True
        assert error is None

    def test_missing_required_parameter(self):
        capsule = _make_unsaved_capsule(
            parameters_schema={"topic": {"type": "string", "required": True}}
        )
        valid, error = validate_parameters(capsule, {})
        assert valid is False
        assert error is not None
        assert "Missing required parameter: topic" in error

    def test_wrong_type_string(self):
        capsule = _make_unsaved_capsule(
            parameters_schema={"topic": {"type": "string", "required": True}}
        )
        valid, error = validate_parameters(capsule, {"topic": 123})
        assert valid is False
        assert error is not None
        assert "must be a string" in error

    def test_wrong_type_integer(self):
        capsule = _make_unsaved_capsule(
            parameters_schema={"count": {"type": "integer", "required": True}}
        )
        valid, error = validate_parameters(capsule, {"count": "five"})
        assert valid is False
        assert error is not None
        assert "must be an integer" in error

    def test_wrong_type_number(self):
        capsule = _make_unsaved_capsule(
            parameters_schema={"threshold": {"type": "number", "required": True}}
        )
        valid, error = validate_parameters(capsule, {"threshold": "0.5"})
        assert valid is False
        assert error is not None
        assert "must be a number" in error

    def test_wrong_type_boolean(self):
        capsule = _make_unsaved_capsule(
            parameters_schema={"enabled": {"type": "boolean", "required": True}}
        )
        valid, error = validate_parameters(capsule, {"enabled": "yes"})
        assert valid is False
        assert error is not None
        assert "must be a boolean" in error

    def test_options_constraint(self):
        capsule = _make_unsaved_capsule(
            parameters_schema={
                "format": {"type": "string", "required": True, "options": ["pdf", "csv"]}
            }
        )
        valid, error = validate_parameters(capsule, {"format": "json"})
        assert valid is False
        assert error is not None
        assert "must be one of" in error

    def test_valid_parameters(self):
        capsule = _make_unsaved_capsule(
            parameters_schema={
                "topic": {"type": "string", "required": True},
                "count": {"type": "integer", "default": 10},
            }
        )
        valid, error = validate_parameters(capsule, {"topic": "climate", "count": 5})
        assert valid is True
        assert error is None


class TestMergeParameters:
    def test_defaults_only(self):
        capsule = _make_unsaved_capsule(
            parameters_schema={"limit": {"type": "integer", "default": 100}}
        )
        merged = merge_parameters(capsule, None, {})
        assert merged["limit"] == 100

    def test_installation_override(self):
        capsule = _make_unsaved_capsule(
            parameters_schema={"limit": {"type": "integer", "default": 100}}
        )
        installation = CapsuleInstallation(
            capsule=capsule, tenant_id="default", parameter_overrides={"limit": 50}
        )
        merged = merge_parameters(capsule, installation, {})
        assert merged["limit"] == 50

    def test_runtime_wins(self):
        capsule = _make_unsaved_capsule(
            parameters_schema={"limit": {"type": "integer", "default": 100}}
        )
        installation = CapsuleInstallation(
            capsule=capsule, tenant_id="default", parameter_overrides={"limit": 50}
        )
        merged = merge_parameters(capsule, installation, {"limit": 25})
        assert merged["limit"] == 25


class TestSubstituteParameters:
    def test_simple_substitution(self):
        template = {"query": "{{topic}}"}
        result = substitute_parameters(template, {"topic": "climate"})
        assert result["query"] == "climate"

    def test_nested_substitution(self):
        template = {"config": {"url": "https://api.example.com/{{endpoint}}"}}
        result = substitute_parameters(template, {"endpoint": "search"})
        assert result["config"]["url"] == "https://api.example.com/search"

    def test_list_substitution(self):
        template = {"items": ["{{a}}", "{{b}}"]}
        result = substitute_parameters(template, {"a": "x", "b": "y"})
        assert result["items"] == ["x", "y"]

    def test_default_filter(self):
        template = {"query": "{{topic | default('general')}}"}
        result = substitute_parameters(template, {})
        assert result["query"] == "general"

    def test_step_results_access(self):
        template = {"output": "Result: {{steps.step1.value}}"}
        result = substitute_parameters(template, {}, step_results={"step1": {"value": 42}})
        assert result["output"] == "Result: 42"

    def test_invalid_template_returns_original(self):
        template = {"query": "{{undefined.attr.}}"}
        result = substitute_parameters(template, {})
        assert "{{undefined.attr.}}" in result["query"]


@pytest.mark.skipif(not DB_AVAILABLE, reason="Database unavailable")
@pytest.mark.django_db(transaction=True)
class TestCapsuleExecutionDB:
    """Tests requiring a live database.  Skipped if PostgreSQL is offline."""

    def test_create_instance_increments_execution_count(self):
        from apps.capsules.services.capsule_core import create_capsule_instance

        capsule = Capsule.objects.create(
            name="db-test",
            version="1.0.0",
            tenant_id="test",
            realm="default",
            status=Capsule.STATUS_ACTIVE,
        )
        before = capsule.execution_count
        instance = create_capsule_instance(
            capsule=capsule,
            session_id="sess-123",
            parameter_values={"topic": "x"},
        )
        capsule.refresh_from_db()
        assert instance.status == "running"
        assert capsule.execution_count == before + 1
