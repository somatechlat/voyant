"""
Unit tests for apps.ontology.function_runner — Function execution sandbox.

Covers:
  - Python function execution (success, timeout, crash, invalid output)
  - Input validation (valid, missing required, wrong type)
  - Output validation (valid, missing fields)
  - Function caching (cache hit, cache invalidation)
  - Entry point not found error
  - TypeScript runtime detection

Uses @pytest.mark.django_db for ORM access.
"""

from __future__ import annotations

import json
import pytest
from unittest.mock import patch

from apps.ontology.function_runner import (
    FunctionRunner,
    FunctionResult,
    _FunctionCache,
    _build_python_wrapper,
    _parse_output,
    _ExecutionError,
    _detect_ts_runtime,
    invalidate_function_cache,
    clear_function_cache,
    _function_cache,
)
from apps.ontology.models import Function

TENANT = "test-tenant-runner"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def runner():
    """Fresh FunctionRunner without cache."""
    return FunctionRunner(use_cache=False)


@pytest.fixture
def cached_runner():
    """FunctionRunner with caching enabled."""
    return FunctionRunner(use_cache=True)


@pytest.fixture
def python_add_function(db):
    """A Python function that adds two numbers."""
    return Function.objects.create(
        tenant_id=TENANT,
        name="add_numbers",
        status=Function.STATUS_PUBLISHED,
        language=Function.LANGUAGE_PYTHON,
        source_code="def handler(input):\n    return {'sum': input['a'] + input['b']}\n",
        entry_point="handler",
        input_schema={
            "params": [
                {"name": "a", "type": "integer", "required": True},
                {"name": "b", "type": "integer", "required": True},
            ]
        },
        output_schema={
            "type": "object",
            "required": ["sum"],
            "properties": {"sum": {"type": "integer"}},
        },
        timeout_seconds=10,
        memory_limit_mb=64,
    )


@pytest.fixture
def python_timeout_function(db):
    """A Python function that runs forever."""
    return Function.objects.create(
        tenant_id=TENANT,
        name="forever",
        status=Function.STATUS_PUBLISHED,
        language=Function.LANGUAGE_PYTHON,
        source_code="import time\ndef handler(input):\n    while True:\n        time.sleep(1)\n",
        entry_point="handler",
        input_schema={},
        output_schema={},
        timeout_seconds=2,
        memory_limit_mb=64,
    )


@pytest.fixture
def python_crash_function(db):
    """A Python function that raises an exception."""
    return Function.objects.create(
        tenant_id=TENANT,
        name="crasher",
        status=Function.STATUS_PUBLISHED,
        language=Function.LANGUAGE_PYTHON,
        source_code="def handler(input):\n    raise ValueError('intentional crash')\n",
        entry_point="handler",
        input_schema={},
        output_schema={},
        timeout_seconds=10,
        memory_limit_mb=64,
    )


@pytest.fixture
def python_bad_output_function(db):
    """A Python function that returns non-JSON-serializable data."""
    return Function.objects.create(
        tenant_id=TENANT,
        name="bad_output",
        status=Function.STATUS_PUBLISHED,
        language=Function.LANGUAGE_PYTHON,
        source_code="def handler(input):\n    return set([1, 2, 3])\n",
        entry_point="handler",
        input_schema={},
        output_schema={},
        timeout_seconds=10,
        memory_limit_mb=64,
    )


@pytest.fixture
def python_wrong_entry_point(db):
    """A Python function where the entry point doesn't exist."""
    return Function.objects.create(
        tenant_id=TENANT,
        name="wrong_ep",
        status=Function.STATUS_PUBLISHED,
        language=Function.LANGUAGE_PYTHON,
        source_code="def not_the_handler(input):\n    return 42\n",
        entry_point="handler",
        input_schema={},
        output_schema={},
        timeout_seconds=10,
        memory_limit_mb=64,
    )


@pytest.fixture
def python_output_schema_function(db):
    """A Python function with strict output schema."""
    return Function.objects.create(
        tenant_id=TENANT,
        name="strict_output",
        status=Function.STATUS_PUBLISHED,
        language=Function.LANGUAGE_PYTHON,
        source_code=(
            "def handler(input):\n"
            "    return {'name': input['name'], 'score': input['score']}\n"
        ),
        entry_point="handler",
        input_schema={
            "params": [
                {"name": "name", "type": "string", "required": True},
                {"name": "score", "type": "integer", "required": True},
            ]
        },
        output_schema={
            "type": "object",
            "required": ["name", "score", "grade"],
            "properties": {
                "name": {"type": "string"},
                "score": {"type": "integer"},
                "grade": {"type": "string"},
            },
        },
        timeout_seconds=10,
        memory_limit_mb=64,
    )


@pytest.fixture
def deprecated_function(db):
    """A deprecated function that should not execute."""
    return Function.objects.create(
        tenant_id=TENANT,
        name="old_func",
        status=Function.STATUS_DEPRECATED,
        language=Function.LANGUAGE_PYTHON,
        source_code="def handler(input):\n    return 42\n",
        entry_point="handler",
        input_schema={},
        output_schema={},
    )


# =========================================================================
# 1. Python function execution
# =========================================================================


class TestPythonExecution:
    """ONT-F-029: Python subprocess execution tests."""

    def test_success_basic_execution(self, runner, python_add_function):
        """Function adds two integers correctly."""
        result = runner.run(TENANT, str(python_add_function.id), {"a": 3, "b": 7})
        assert result.success is True
        assert result.output == {"sum": 10}
        assert result.duration_ms > 0
        assert result.error == ""

    def test_timeout_kills_process(self, runner, python_timeout_function):
        """Function that exceeds timeout is killed and reports error."""
        result = runner.run(TENANT, str(python_timeout_function.id), {})
        assert result.success is False
        assert "timed out" in result.error

    def test_crash_reports_traceback(self, runner, python_crash_function):
        """Function that raises an exception returns failure with error."""
        result = runner.run(TENANT, str(python_crash_function.id), {})
        assert result.success is False
        assert "crashed" in result.error
        assert "intentional crash" in result.error

    def test_invalid_json_output(self, runner, python_bad_output_function):
        """Function returning non-serializable output is caught."""
        result = runner.run(TENANT, str(python_bad_output_function.id), {})
        assert result.success is False
        # set() is not JSON-serializable, so it crashes
        assert "crashed" in result.error or "not valid JSON" in result.error

    def test_deprecated_function_rejected(self, runner, deprecated_function):
        """Deprecated functions cannot be executed."""
        result = runner.run(TENANT, str(deprecated_function.id), {})
        assert result.success is False
        assert "deprecated" in result.error.lower()

    def test_nonexistent_function(self, runner, db):
        """Executing a non-existent function returns clear error."""
        result = runner.run(TENANT, "00000000-0000-0000-0000-000000000000", {})
        assert result.success is False
        assert "not found" in result.error


# =========================================================================
# 2. Input validation
# =========================================================================


class TestInputValidation:
    """ONT-F-032: Input schema validation."""

    def test_valid_input(self, runner, python_add_function):
        """Valid input passes without errors."""
        errors = runner.validate_input(python_add_function, {"a": 1, "b": 2})
        assert errors == []

    def test_missing_required_param(self, runner, python_add_function):
        """Missing required parameter produces error."""
        errors = runner.validate_input(python_add_function, {"a": 1})
        assert len(errors) == 1
        assert "b" in errors[0]
        assert "required" in errors[0].lower()

    def test_wrong_type_param(self, runner, python_add_function):
        """Wrong type for a parameter produces error."""
        errors = runner.validate_input(python_add_function, {"a": "not_int", "b": 2})
        assert len(errors) == 1
        assert "a" in errors[0]
        assert "integer" in errors[0]

    def test_optional_param_missing_ok(self, runner, db):
        """Missing optional parameters are fine."""
        func = Function.objects.create(
            tenant_id=TENANT,
            name="optional_params",
            status=Function.STATUS_PUBLISHED,
            language=Function.LANGUAGE_PYTHON,
            source_code="def handler(input):\n    return input.get('x', 0)\n",
            entry_point="handler",
            input_schema={
                "params": [
                    {"name": "x", "type": "integer", "required": False},
                ]
            },
            output_schema={},
        )
        errors = runner.validate_input(func, {})
        assert errors == []


# =========================================================================
# 3. Output validation
# =========================================================================


class TestOutputValidation:
    """ONT-F-032: Output schema validation."""

    def test_valid_output(self, runner, python_add_function):
        """Valid output passes without errors."""
        errors = runner.validate_output(python_add_function, {"sum": 42})
        assert errors == []

    def test_missing_required_field(self, runner, python_output_schema_function):
        """Missing required output field produces error."""
        errors = runner.validate_output(
            python_output_schema_function,
            {"name": "Alice", "score": 90},  # missing 'grade'
        )
        assert len(errors) == 1
        assert "grade" in errors[0]
        assert "required" in errors[0].lower()

    def test_wrong_output_type(self, runner, python_add_function):
        """Wrong output type produces error."""
        errors = runner.validate_output(python_add_function, "not a dict")
        assert len(errors) == 1
        assert "object" in errors[0]

    def test_no_schema_passes_anything(self, runner, db):
        """Functions without output schema accept any output."""
        func = Function.objects.create(
            tenant_id=TENANT,
            name="no_schema",
            status=Function.STATUS_PUBLISHED,
            language=Function.LANGUAGE_PYTHON,
            source_code="def handler(input):\n    return 42\n",
            entry_point="handler",
            input_schema={},
            output_schema={},
        )
        errors = runner.validate_output(func, "anything goes")
        assert errors == []


# =========================================================================
# 4. Function caching
# =========================================================================


class TestFunctionCaching:
    """ONT-F-031: In-memory function cache."""

    def test_cache_hit_avoids_db_query(self, cached_runner, python_add_function):
        """Second call should use cache (no extra DB query)."""
        fid = str(python_add_function.id)
        # First call loads from DB
        result1 = cached_runner.run(TENANT, fid, {"a": 1, "b": 2})
        assert result1.success is True

        with patch("apps.ontology.models.Function.objects.get") as mock_get:
            result2 = cached_runner.run(TENANT, fid, {"a": 3, "b": 4})
            assert result2.success is True
            assert result2.output == {"sum": 7}
            # DB was NOT called because cache was hit
            mock_get.assert_not_called()

    def test_cache_invalidation_on_version_change(self, cached_runner, python_add_function):
        """Cache is invalidated when function version changes."""
        fid = str(python_add_function.id)
        # Warm the cache
        cached_runner.run(TENANT, fid, {"a": 1, "b": 2})

        # Bump the version (simulates an update)
        python_add_function.version = 2
        python_add_function.save(update_fields=["version"])

        # Next call should reload from DB
        result = cached_runner.run(TENANT, fid, {"a": 5, "b": 6})
        assert result.success is True
        assert result.output == {"sum": 11}

    def test_explicit_cache_invalidation(self, db, python_add_function):
        """invalidate_function_cache evicts a specific entry."""
        fid = str(python_add_function.id)
        _function_cache.put(python_add_function)
        assert _function_cache.get(TENANT, fid) is not None

        invalidate_function_cache(TENANT, fid)
        assert _function_cache.get(TENANT, fid) is None

    def test_clear_entire_cache(self, db, python_add_function):
        """clear_function_cache drops all entries."""
        _function_cache.put(python_add_function)
        assert _function_cache.get(TENANT, str(python_add_function.id)) is not None

        clear_function_cache()
        assert _function_cache.get(TENANT, str(python_add_function.id)) is None


# =========================================================================
# 5. Entry point not found
# =========================================================================


class TestEntryPointErrors:
    """ONT-F-029: Entry point resolution errors."""

    def test_entry_point_not_found(self, runner, python_wrong_entry_point):
        """Missing entry point returns clear error."""
        result = runner.run(TENANT, str(python_wrong_entry_point.id), {})
        assert result.success is False
        assert "crashed" in result.error or "not found" in result.error.lower()


# =========================================================================
# 6. Python wrapper builder
# =========================================================================


class TestPythonWrapper:
    """Tests for _build_python_wrapper helper."""

    def test_wrapper_contains_entry_point(self):
        wrapper = _build_python_wrapper("x = 1", "my_fn", {"a": 1})
        assert "my_fn" in wrapper
        assert json.dumps({"a": 1}) in wrapper

    def test_wrapper_handles_entry_point_not_found(self):
        wrapper = _build_python_wrapper("x = 1", "handler", {})
        assert "not found" in wrapper


# =========================================================================
# 7. Output parser
# =========================================================================


class TestOutputParser:
    """Tests for _parse_output helper."""

    def test_parse_valid_json(self):
        result = _parse_output('{"key": "value"}\n', "")
        assert result == {"key": "value"}

    def test_parse_last_line_json(self):
        result = _parse_output("debug line\n[1, 2, 3]\n", "")
        assert result == [1, 2, 3]

    def test_parse_empty_output_raises(self):
        with pytest.raises(_ExecutionError, match="no output"):
            _parse_output("", "")

    def test_parse_no_json_raises(self):
        with pytest.raises(_ExecutionError, match="not valid JSON"):
            _parse_output("just plain text no json here\n", "")


# =========================================================================
# 8. TypeScript runtime detection
# =========================================================================


class TestTypeScriptRuntime:
    """ONT-F-033: TypeScript runtime detection."""

    def test_detection_returns_string_or_none(self):
        """_detect_ts_runtime returns a string or None."""
        result = _detect_ts_runtime()
        assert result is None or isinstance(result, str)

    @patch("shutil.which", return_value="/usr/bin/bun")
    def test_bun_preferred(self, mock_which):
        result = _detect_ts_runtime()
        assert result == "bun"

    @patch("shutil.which", side_effect=lambda x: "/usr/bin/npx" if x == "npx" else None)
    @patch("subprocess.run")
    def test_npx_tsx_fallback(self, mock_run, mock_which):
        mock_run.return_value = None  # tsx --version succeeds
        result = _detect_ts_runtime()
        assert result == "npx tsx"

    @patch("shutil.which", return_value=None)
    def test_no_runtime_returns_none(self, mock_which):
        result = _detect_ts_runtime()
        assert result is None


# =========================================================================
# 9. Integration: end-to-end output schema enforcement
# =========================================================================


class TestEndToEnd:
    """Integration tests running through the full pipeline."""

    def test_output_schema_enforced_in_run(self, runner, python_output_schema_function):
        """run() fails if function output violates output_schema."""
        result = runner.run(
            TENANT,
            str(python_output_schema_function.id),
            {"name": "Alice", "score": 95},
        )
        assert result.success is False
        assert "Output validation failed" in result.error
        assert "grade" in result.error

    def test_full_success_with_schemas(self, runner, python_add_function):
        """run() succeeds when both input and output schemas pass."""
        result = runner.run(TENANT, str(python_add_function.id), {"a": 10, "b": 20})
        assert result.success is True
        assert result.output == {"sum": 30}
        assert result.duration_ms > 0
        assert result.error == ""

    def test_function_result_dataclass_fields(self):
        """FunctionResult has all required fields."""
        r = FunctionResult(
            success=True,
            function_id="abc",
            output={"x": 1},
            duration_ms=123.45,
            memory_used_mb=0.0,
            error="",
            logs="",
        )
        assert r.success is True
        assert r.function_id == "abc"
        assert r.output == {"x": 1}
        assert r.duration_ms == 123.45
        assert r.memory_used_mb == 0.0
        assert r.error == ""
        assert r.logs == ""
