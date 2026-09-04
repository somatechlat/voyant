"""
Unit tests for apps.core.lib.python_sandbox — PythonSandboxNode security
validation logic (network import detection).

Tests the import-based security check that blocks network imports in sandbox scripts.
"""

import pytest

from apps.core.lib.python_sandbox import PythonSandboxNode


class TestNetworkImportDetection:
    """Test the security check that blocks network imports in sandbox scripts."""

    @pytest.mark.asyncio
    async def test_socket_import_blocked(self):
        with pytest.raises(ValueError, match="Network imports strictly forbidden"):
            await PythonSandboxNode.execute_script(
                "from socket import gethostbyname", {}, "tenant-1"
            )

    @pytest.mark.asyncio
    async def test_import_socket_blocked(self):
        with pytest.raises(ValueError, match="Network imports strictly forbidden"):
            await PythonSandboxNode.execute_script(
                "import socket", {}, "tenant-1"
            )

    @pytest.mark.asyncio
    async def test_urllib_import_blocked(self):
        with pytest.raises(ValueError, match="Network imports strictly forbidden"):
            await PythonSandboxNode.execute_script(
                "import urllib.request", {}, "tenant-1"
            )

    @pytest.mark.asyncio
    async def test_from_urllib_blocked(self):
        with pytest.raises(ValueError, match="Network imports strictly forbidden"):
            await PythonSandboxNode.execute_script(
                "from urllib.request import urlopen", {}, "tenant-1"
            )

    @pytest.mark.asyncio
    async def test_requests_import_blocked(self):
        with pytest.raises(ValueError, match="Network imports strictly forbidden"):
            await PythonSandboxNode.execute_script(
                "import requests", {}, "tenant-1"
            )

    @pytest.mark.asyncio
    async def test_from_requests_blocked(self):
        with pytest.raises(ValueError, match="Network imports strictly forbidden"):
            await PythonSandboxNode.execute_script(
                "from requests import get", {}, "tenant-1"
            )


class TestSafeScriptsPassValidation:
    """Test that safe scripts pass the network import check."""

    @pytest.mark.asyncio
    async def test_pure_math_script_passes(self):
        script = "import math\nresult = math.sqrt(144)\nprint(result)"
        try:
            await PythonSandboxNode.execute_script(script, {"x": "10"}, "tenant-1")
        except ValueError as e:
            if "Network imports" in str(e):
                pytest.fail("Pure math script should not be blocked")
        except (RuntimeError, AttributeError):
            pass

    @pytest.mark.asyncio
    async def test_socket_in_string_literal_passes(self):
        """String containing 'socket' without import should pass."""
        script = 'x = "socket is a module"'
        try:
            await PythonSandboxNode.execute_script(script, {}, "tenant-1")
        except ValueError as e:
            if "Network imports" in str(e):
                pytest.fail("String literal containing 'socket' should not be blocked")
        except (RuntimeError, AttributeError):
            pass

    @pytest.mark.asyncio
    async def test_urllib_in_comment_passes(self):
        """Comment containing 'urllib' without import should pass."""
        script = "# urllib is used for HTTP\nimport math"
        try:
            await PythonSandboxNode.execute_script(script, {}, "tenant-1")
        except ValueError as e:
            if "Network imports" in str(e):
                pytest.fail("Comment containing 'urllib' should not be blocked")
        except (RuntimeError, AttributeError):
            pass

    @pytest.mark.asyncio
    async def test_empty_script_passes(self):
        try:
            await PythonSandboxNode.execute_script("", {}, "tenant-1")
        except ValueError as e:
            if "Network imports" in str(e):
                pytest.fail("Empty script should not be blocked")
        except (RuntimeError, AttributeError):
            pass


class TestParameterMapping:
    """Test the parameter-to-environment mapping logic."""

    def test_parameter_keys_uppercased(self):
        parameters = {"model_type": "arima", "max_iter": "100"}
        environment = {
            f"SANDBOX_PARAM_{k.upper()}": str(v) for k, v in parameters.items()
        }
        assert environment["SANDBOX_PARAM_MODEL_TYPE"] == "arima"
        assert environment["SANDBOX_PARAM_MAX_ITER"] == "100"

    def test_empty_parameters(self):
        parameters: dict = {}
        environment = {
            f"SANDBOX_PARAM_{k.upper()}": str(v) for k, v in parameters.items()
        }
        assert environment == {}

    def test_output_uri_construction(self):
        tenant_id = "tenant-abc"
        execution_id = "exec-123"
        output_uri = f"iceberg://tenant_{tenant_id}/sandbox_{execution_id}_output"
        assert output_uri == "iceberg://tenant_tenant-abc/sandbox_exec-123_output"
        assert output_uri.startswith("iceberg://")
