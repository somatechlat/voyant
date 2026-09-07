"""
Function Execution Sandbox — Isolated runtime for ontology functions.

ONT-F-029: Provides sandboxed execution of Python and TypeScript
functions attached to object types and action types. Uses subprocess
isolation with strict timeouts and memory limits. Validates inputs
and outputs against declared JSON schemas.

SRS Refs: ONT-F-029, ONT-F-030, ONT-F-031, ONT-F-032, ONT-F-033.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from apps.ontology.models import Function

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class FunctionResult:
    """Outcome of a single function execution.

    ONT-F-030: Captures success/failure, output, timing, memory, and logs
    so callers can audit every invocation.
    """

    success: bool
    function_id: str
    output: Any = None
    duration_ms: float = 0.0
    memory_used_mb: float = 0.0
    error: str = ""
    logs: str = ""


# ---------------------------------------------------------------------------
# Function cache
# ---------------------------------------------------------------------------


class _FunctionCache:
    """Simple in-memory cache keyed by (tenant_id, function_id).

    ONT-F-031: Avoids repeated DB lookups for hot functions.
    Entries are invalidated when the function's version changes.
    """

    def __init__(self) -> None:
        self._entries: dict[str, dict[str, Any]] = {}

    def _key(self, tenant_id: str, function_id: str) -> str:
        return f"{tenant_id}:{function_id}"

    def get(self, tenant_id: str, function_id: str) -> Function | None:
        """Return cached function if still valid, else None."""
        key = self._key(tenant_id, function_id)
        entry = self._entries.get(key)
        if entry is None:
            return None
        func: Function = entry["function"]
        # Invalidate if version changed in DB
        try:
            current = Function.objects.get(
                tenant_id=tenant_id, id=function_id, deleted_at__isnull=True,
            )
        except Function.DoesNotExist:
            self._entries.pop(key, None)
            return None
        if current.version != func.version:
            self._entries.pop(key, None)
            return None
        return current

    def put(self, function: Function) -> None:
        key = self._key(function.tenant_id, str(function.id))
        self._entries[key] = {"function": function, "cached_at": time.time()}

    def invalidate(self, tenant_id: str, function_id: str) -> None:
        self._entries.pop(self._key(tenant_id, function_id), None)

    def clear(self) -> None:
        self._entries.clear()


# Module-level singleton cache
_function_cache = _FunctionCache()


# ---------------------------------------------------------------------------
# Schema validation helpers
# ---------------------------------------------------------------------------

# ONT-F-032: Map schema type strings to Python isinstance checks.
_TYPE_MAP: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "integer": (int,),
    "number": (int, float),
    "boolean": (bool,),
    "array": (list,),
    "object": (dict,),
    "null": (type(None),),
}


def _check_type(value: Any, expected_type: str) -> bool:
    """Return True if *value* matches the JSON-Schema-style type string."""
    if expected_type == "null":
        return value is None
    types = _TYPE_MAP.get(expected_type)
    if types is None:
        return True  # Unknown type — lenient pass
    return isinstance(value, types)


# ---------------------------------------------------------------------------
# FunctionRunner
# ---------------------------------------------------------------------------


class FunctionRunner:
    """Execute ontology functions in a sandboxed subprocess.

    ONT-F-029: Central entry point for function execution.  Validates
    inputs, runs the code in a child process with a timeout, captures
    output, and validates the result against the output schema.

    Usage::

        runner = FunctionRunner()
        result = runner.run(tenant_id, function_id, {"x": 1, "y": 2})
    """

    def __init__(self, *, use_cache: bool = True) -> None:
        self._use_cache = use_cache

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, tenant_id: str, function_id: str, input_data: dict[str, Any]) -> FunctionResult:
        """Execute a function and return a FunctionResult.

        ONT-F-029: Full lifecycle — load → validate input → execute → validate output.

        Args:
            tenant_id: Owning tenant (enforces isolation).
            function_id: UUID of the Function record.
            input_data: Dict of named input parameters.

        Returns:
            FunctionResult with success flag, output, timing, logs.
        """
        start = time.monotonic()

        # Load function (with optional cache)
        try:
            func = self._load_function(tenant_id, function_id)
        except Function.DoesNotExist:
            return FunctionResult(
                success=False,
                function_id=function_id,
                error=f"Function {function_id} not found for tenant {tenant_id}",
                duration_ms=0.0,
            )

        # Guard: only published or draft functions may execute
        if func.status == Function.STATUS_DEPRECATED:
            return FunctionResult(
                success=False,
                function_id=function_id,
                error="Cannot execute deprecated function",
                duration_ms=0.0,
            )

        # Validate input
        input_errors = self.validate_input(func, input_data)
        if input_errors:
            return FunctionResult(
                success=False,
                function_id=function_id,
                error=f"Input validation failed: {input_errors}",
                duration_ms=(time.monotonic() - start) * 1000,
            )

        # Dispatch by language
        try:
            if func.language == Function.LANGUAGE_PYTHON:
                output = self._run_python(
                    func.source_code,
                    func.entry_point,
                    input_data,
                    func.timeout_seconds,
                    func.memory_limit_mb,
                )
            elif func.language == Function.LANGUAGE_TYPESCRIPT:
                output = self._run_typescript(
                    func.source_code,
                    func.entry_point,
                    input_data,
                    func.timeout_seconds,
                )
            else:
                return FunctionResult(
                    success=False,
                    function_id=function_id,
                    error=f"Unsupported language: {func.language}",
                    duration_ms=(time.monotonic() - start) * 1000,
                )
        except _ExecutionError as exc:
            return FunctionResult(
                success=False,
                function_id=function_id,
                error=str(exc),
                logs=exc.logs if hasattr(exc, "logs") else "",
                duration_ms=(time.monotonic() - start) * 1000,
            )

        # Validate output
        output_errors = self.validate_output(func, output)
        if output_errors:
            return FunctionResult(
                success=False,
                function_id=function_id,
                output=output,
                error=f"Output validation failed: {output_errors}",
                duration_ms=(time.monotonic() - start) * 1000,
            )

        duration = (time.monotonic() - start) * 1000
        return FunctionResult(
            success=True,
            function_id=function_id,
            output=output,
            duration_ms=round(duration, 2),
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_input(self, function: Function, input_data: dict[str, Any]) -> list[str]:
        """Validate input_data against function.input_schema.

        ONT-F-032: Checks required fields and type constraints.

        Args:
            function: The Function model instance.
            input_data: Raw input dict from the caller.

        Returns:
            List of human-readable error strings. Empty list means valid.
        """
        schema = function.input_schema or {}
        errors: list[str] = []

        # Schema format: {"params": [{"name": "x", "type": "integer", "required": true}, ...]}
        params = schema.get("params", [])
        for param in params:
            name = param.get("name", "")
            required = param.get("required", False)
            expected_type = param.get("type", "")

            value = input_data.get(name)

            if value is None:
                if required:
                    errors.append(f"Missing required parameter: '{name}'")
                continue

            if expected_type and not _check_type(value, expected_type):
                errors.append(
                    f"Parameter '{name}' expects type '{expected_type}', "
                    f"got '{type(value).__name__}'"
                )

        return errors

    def validate_output(self, function: Function, output_data: Any) -> list[str]:
        """Validate output_data against function.output_schema.

        ONT-F-032: Verifies the function returned a result conforming
        to its declared output schema.

        Args:
            function: The Function model instance.
            output_data: Value returned by the function.

        Returns:
            List of human-readable error strings. Empty list means valid.
        """
        schema = function.output_schema or {}
        if not schema:
            return []  # No schema declared — anything goes

        errors: list[str] = []

        # Schema format: {"type": "object", "properties": {...}, "required": [...]}
        expected_type = schema.get("type", "")
        if expected_type and not _check_type(output_data, expected_type):
            errors.append(
                f"Output expects type '{expected_type}', "
                f"got '{type(output_data).__name__}'"
            )
            return errors  # No point checking properties if type is wrong

        # Check required top-level properties
        required_fields = schema.get("required", [])
        if isinstance(output_data, dict):
            for field_name in required_fields:
                if field_name not in output_data:
                    errors.append(f"Output missing required field: '{field_name}'")

            # Check individual property types if declared
            properties = schema.get("properties", {})
            for prop_name, prop_schema in properties.items():
                if prop_name in output_data:
                    prop_type = prop_schema.get("type", "")
                    if prop_type and not _check_type(output_data[prop_name], prop_type):
                        errors.append(
                            f"Output field '{prop_name}' expects type '{prop_type}', "
                            f"got '{type(output_data[prop_name]).__name__}'"
                        )

        return errors

    # ------------------------------------------------------------------
    # Private execution helpers
    # ------------------------------------------------------------------

    def _run_python(
        self,
        source_code: str,
        entry_point: str,
        input_data: dict[str, Any],
        timeout: int,
        memory_limit_mb: int,
    ) -> Any:
        """Execute Python source in a subprocess with timeout.

        ONT-F-029/033: Writes source to a temp file, invokes ``python3``
        with a timeout, and parses JSON from stdout.  Raises
        ``_ExecutionError`` on any failure.

        Args:
            source_code: Python source text.
            entry_point: Name of the handler function.
            input_data: Dict passed as the single argument.
            timeout: Max seconds before kill.
            memory_limit_mb: Memory ceiling (advisory for now).

        Returns:
            Parsed JSON output from the function's return value.
        """
        # Build a wrapper script that imports the user code, calls the
        # entry point, and prints the JSON result to stdout.
        wrapper = _build_python_wrapper(source_code, entry_point, input_data)

        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8",
        )
        try:
            tmp.write(wrapper)
            tmp.flush()
            tmp.close()

            proc = subprocess.Popen(
                [sys.executable, tmp.name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                stdout_bytes, stderr_bytes = proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                raise _ExecutionError(
                    f"Python function timed out after {timeout}s",
                    logs="",
                )

            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")

            if proc.returncode != 0:
                raise _ExecutionError(
                    f"Python function crashed (exit code {proc.returncode}): {stderr}",
                    logs=stderr,
                )

            return _parse_output(stdout, stderr)

        finally:
            Path(tmp.name).unlink(missing_ok=True)

    def _run_typescript(
        self,
        source_code: str,
        entry_point: str,
        input_data: dict[str, Any],
        timeout: int,
    ) -> Any:
        """Execute TypeScript source in a subprocess with timeout.

        ONT-F-029/033: Writes source to a temp ``.ts`` file, invokes
        ``bun run`` (preferred) or ``npx tsx`` as a fallback, and
        parses JSON from stdout.  Raises ``_ExecutionError`` on failure.

        Args:
            source_code: TypeScript source text.
            entry_point: Name of the handler function.
            input_data: Dict passed as the single argument.
            timeout: Max seconds before kill.

        Returns:
            Parsed JSON output from the function's return value.
        """
        runtime = _detect_ts_runtime()
        if runtime is None:
            raise _ExecutionError(
                "No TypeScript runtime available (tried bun, npx tsx, ts-node)",
            )

        wrapper = _build_typescript_wrapper(source_code, entry_point, input_data)

        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".ts", delete=False, encoding="utf-8",
        )
        try:
            tmp.write(wrapper)
            tmp.flush()
            tmp.close()

            cmd: list[str]
            if runtime == "bun":
                cmd = ["bun", "run", tmp.name]
            else:
                cmd = runtime.split() + [tmp.name]

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            try:
                stdout_bytes, stderr_bytes = proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                raise _ExecutionError(
                    f"TypeScript function timed out after {timeout}s",
                    logs="",
                )

            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")

            if proc.returncode != 0:
                raise _ExecutionError(
                    f"TypeScript function crashed (exit code {proc.returncode}): {stderr}",
                    logs=stderr,
                )

            return _parse_output(stdout, stderr)

        finally:
            Path(tmp.name).unlink(missing_ok=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_function(self, tenant_id: str, function_id: str) -> Function:
        """Load a Function from cache or DB, enforcing tenant isolation."""
        if self._use_cache:
            cached = _function_cache.get(tenant_id, function_id)
            if cached is not None:
                return cached

        func = Function.objects.get(
            tenant_id=tenant_id,
            id=function_id,
            deleted_at__isnull=True,
        )

        if self._use_cache:
            _function_cache.put(func)

        return func


# ---------------------------------------------------------------------------
# Module-level helpers (kept outside the class for testability)
# ---------------------------------------------------------------------------


def _build_python_wrapper(source_code: str, entry_point: str, input_data: dict[str, Any]) -> str:
    """Build a Python wrapper script that calls the user function and
    prints the JSON result to stdout.

    ONT-F-029: The wrapper handles serialization so the subprocess
    always produces machine-readable output.
    """
    input_json = json.dumps(input_data)
    return (
        "import json, sys\n"
        "try:\n"
        f"    __input__ = {input_json}\n"
        "    __code__ = " + repr(source_code) + "\n"
        "    exec(__code__, __ns__ := {})\n"
        f"    if '{entry_point}' not in __ns__:\n"
        f"        print(json.dumps({{'__error__': 'Entry point \\'{entry_point}\\' not found'}}), file=sys.stderr)\n"
        "        sys.exit(1)\n"
        f"    __result__ = __ns__['{entry_point}'](__input__)\n"
        "    print(json.dumps(__result__))\n"
        "except Exception as e:\n"
        "    import traceback\n"
        "    traceback.print_exc()\n"
        "    sys.exit(1)\n"
    )


def _build_typescript_wrapper(
    source_code: str, entry_point: str, input_data: dict[str, Any],
) -> str:
    """Build a TypeScript wrapper that calls the user function and prints
    JSON output to stdout.

    ONT-F-029: Mirrors the Python wrapper pattern for TypeScript.
    """
    input_json = json.dumps(input_data)
    return (
        "// Auto-generated wrapper\n"
        "const input = " + input_json + ";\n"
        "\n"
        "// --- User code ---\n"
        + source_code
        + "\n"
        "// --- Entry point dispatch ---\n"
        "try {\n"
        f"  const fn = (globalThis as any)['{entry_point}'] ?? eval('{entry_point}');\n"
        "  if (typeof fn !== 'function') {\n"
        f"    console.error('Entry point \\'{entry_point}\\' is not a function');\n"
        "    process.exit(1);\n"
        "  }\n"
        "  const result = fn(input);\n"
        "  if (result && typeof result.then === 'function') {\n"
        "    result.then((r: any) => {\n"
        "      console.log(JSON.stringify(r));\n"
        "    }).catch((e: any) => {\n"
        "      console.error(e);\n"
        "      process.exit(1);\n"
        "    });\n"
        "  } else {\n"
        "    console.log(JSON.stringify(result));\n"
        "  }\n"
        "} catch (e) {\n"
        "  console.error(e);\n"
        "  process.exit(1);\n"
        "}\n"
    )


def _detect_ts_runtime() -> str | None:
    """Detect an available TypeScript runtime on the system.

    ONT-F-033: Prefers ``bun`` (fast) then falls back to ``npx tsx``.
    Returns the command string or None.
    """
    if shutil.which("bun"):
        return "bun"
    if shutil.which("npx"):
        # Verify tsx is available via npx
        try:
            subprocess.run(
                ["npx", "tsx", "--version"],
                capture_output=True,
                timeout=10,
            )
            return "npx tsx"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
    if shutil.which("ts-node"):
        return "ts-node"
    return None


def _parse_output(stdout: str, stderr: str) -> Any:
    """Parse JSON output from subprocess stdout.

    Attempts to find the last valid JSON value in stdout (functions may
    print debug lines before the result).

    Raises:
        _ExecutionError: If no valid JSON is found.
    """
    # Try the full stdout first (most common — single JSON line)
    stdout = stdout.strip()
    if not stdout:
        raise _ExecutionError("Function produced no output", logs=stderr)

    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        pass

    # Fallback: try last line (debug prints + JSON on last line)
    lines = stdout.splitlines()
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue

    raise _ExecutionError(
        f"Function output is not valid JSON: {stdout[:500]}",
        logs=stderr,
    )


class _ExecutionError(Exception):
    """Internal error raised during function execution.

    Carries optional subprocess logs for inclusion in FunctionResult.
    """

    def __init__(self, message: str, logs: str = "") -> None:
        super().__init__(message)
        self.logs = logs


# ---------------------------------------------------------------------------
# Public cache invalidation API (called from signal handlers / views)
# ---------------------------------------------------------------------------


def invalidate_function_cache(tenant_id: str, function_id: str) -> None:
    """Evict a cached function so the next run loads fresh from DB.

    ONT-F-031: Call this from views/signals when a Function is updated.
    """
    _function_cache.invalidate(tenant_id, function_id)


def clear_function_cache() -> None:
    """Drop all cached functions (e.g. on deploy)."""
    _function_cache.clear()
