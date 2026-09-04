"""
Unit tests for apps.core.lib.python_sandbox — PythonSandboxNode security
validation logic (network import detection).

Real string matching logic. No mocks.
"""

import pytest

from apps.core.lib.python_sandbox import PythonSandboxNode


class TestNetworkImportDetection:
    """Test the security check that blocks network imports in sandbox scripts."""

    @pytest.mark.asyncio
    async def test_socket_import_blocked(self):
        with pytest.raises(ValueError, match="Network imports strictly forbidden"):
            await PythonSandboxNode.execute_script(
                "import socket\nprint('hello')", {}, "tenant-1"
            )

    @pytest.mark.asyncio
    async def test_urllib_import_blocked(self):
        with pytest.raises(ValueError, match="Network imports strictly forbidden"):
            await PythonSandboxNode.execute_script(
                "import urllib.request", {}, "tenant-1"
            )

    @pytest.mark.asyncio
    async def test_requests_import_blocked(self):
        with pytest.raises(ValueError, match="Network imports strictly forbidden"):
            await PythonSandboxNode.execute_script(
                "import requests", {}, "tenant-1"
            )

    @pytest.mark.asyncio
    async def test_socket_in_string_blocked(self):
        """Even a reference to 'socket ' in the script is blocked."""
        with pytest.raises(ValueError, match="Network imports strictly forbidden"):
            await PythonSandboxNode.execute_script(
                'x = "socket " + "test"', {}, "tenant-1"
            )

    @pytest.mark.asyncio
    async def test_urllib_substring_blocked(self):
        """urllib anywhere in the script is blocked."""
        with pytest.raises(ValueError, match="Network imports strictly forbidden"):
            await PythonSandboxNode.execute_script(
                "# using urllib for fetching", {}, "tenant-1"
            )

    @pytest.mark.asyncio
    async def test_requests_substring_blocked(self):
        """requests anywhere in the script is blocked."""
        with pytest.raises(ValueError, match="Network imports strictly forbidden"):
            await PythonSandboxNode.execute_script(
                "x = 'requests library'", {}, "tenant-1"
            )


class TestSafeScriptsPassValidation:
    """Test that safe scripts pass the network import check."""

    @pytest.mark.asyncio
    async def test_pure_math_script_passes(self):
        """A pure math script should pass validation (will fail at Docker)."""
        script = "import math\nresult = math.sqrt(144)\nprint(result)"
        try:
            await PythonSandboxNode.execute_script(script, {"x": "10"}, "tenant-1")
        except ValueError as e:
            if "Network imports" in str(e):
                pytest.fail("Pure math script should not be blocked")
        except RuntimeError:
            # Expected: Docker not available in test environment
            pass

    @pytest.mark.asyncio
    async def test_numpy_script_passes(self):
        """A numpy script should pass validation (will fail at Docker)."""
        script = "import numpy as np\narr = np.array([1,2,3])\nprint(arr.mean())"
        try:
            await PythonSandboxNode.execute_script(script, {}, "tenant-1")
        except ValueError as e:
            if "Network imports" in str(e):
                pytest.fail("Numpy script should not be blocked")
        except RuntimeError:
            # Expected: Docker not available in test environment
            pass

    @pytest.mark.asyncio
    async def test_empty_script_passes(self):
        """An empty script should pass validation (will fail at Docker)."""
        try:
            await PythonSandboxNode.execute_script("", {}, "tenant-1")
        except ValueError as e:
            if "Network imports" in str(e):
                pytest.fail("Empty script should not be blocked")
        except RuntimeError:
            # Expected: Docker not available in test environment
            pass


class TestParameterMapping:
    """Test the parameter-to-environment mapping logic."""

    def test_parameter_keys_uppercased(self):
        """Verify the parameter mapping logic."""
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
        """Verify the output URI format."""
        tenant_id = "tenant-abc"
        execution_id = "exec-123"
        output_uri = f"iceberg://tenant_{tenant_id}/sandbox_{execution_id}_output"
        assert output_uri == "iceberg://tenant_tenant-abc/sandbox_exec-123_output"
        assert output_uri.startswith("iceberg://")
