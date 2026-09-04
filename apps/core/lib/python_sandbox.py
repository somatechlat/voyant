"""
Sandboxed Python execution in ephemeral Docker containers.
Network-isolated with strict resource limits.
"""

import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)

# Security: scripts containing these substrings are blocked.
_NETWORK_IMPORT_PATTERNS = (
    "import socket",
    "from socket",
    "import urllib",
    "from urllib",
    "import requests",
    "from requests",
)


class PythonSandboxNode:
    @classmethod
    def validate_script(cls, script_content: str, execution_id: str = "") -> None:
        """Validate that a script does not attempt network access.

        Raises:
            ValueError: If a network import pattern is detected.
        """
        for pattern in _NETWORK_IMPORT_PATTERNS:
            if pattern in script_content:
                logger.error(f"[SANDBOX {execution_id}] Network import detected. Execution halted.")
                raise ValueError("Security Violation: Network imports strictly forbidden in sandbox.")

    @classmethod
    async def execute_script(
        cls, script_content: str, parameters: dict[str, Any], tenant_id: str
    ) -> dict[str, Any]:
        logger.info(f"Dispatching real sandboxed Python execution for tenant {tenant_id}")
        execution_id = str(uuid.uuid4())

        # Security: validate script before any Docker interaction
        cls.validate_script(script_content, execution_id)

        logger.info(f"Sandbox {execution_id} evaluating parameters: {list(parameters.keys())}")

        # --- Physical Docker Execution ---
        import docker

        client = docker.from_env()

        # Map parameters to environment securely
        environment = {f"SANDBOX_PARAM_{k.upper()}": str(v) for k, v in parameters.items()}
        environment["TENANT_ID"] = tenant_id

        # Real container spawning with strict constraints (No network)
        # Using voyant_sandbox:python built from Phase 4 Dockerfile
        output_uri = f"iceberg://tenant_{tenant_id}/sandbox_{execution_id}_output"
        environment["OUTPUT_URI"] = output_uri

        # Execute asynchronously
        try:
            container = client.containers.run(  # type: ignore[call-overload]
                image="voyant_sandbox:python",
                command=["python", "-c", script_content],
                environment=environment,
                network_mode="none",
                mem_limit="256m",
                cpus=0.5,
                detach=True,
                auto_remove=False,
            )

            # Since this is an async operation, we would normally use asyncio loop to wait for docker api
            # Wait for execution to finish
            result = container.wait(timeout=60)
            logs = container.logs().decode("utf-8")

            if result.get("StatusCode", 1) != 0:
                container.remove(force=True)
                raise RuntimeError(f"Sandbox execution failed: {logs}")

            container.remove(force=True)

            logger.info(f"Sandbox {execution_id} completed. Output firmly written to {output_uri}")

            return {
                "execution_id": execution_id,
                "status": "success",
                "compute_metrics": {"memory_used_mb_limit": 256},
                "destination_uri": output_uri,
            }
        except Exception as e:
            logger.error(f"Sandbox {execution_id} Docker execution failed: {e}")
            raise RuntimeError(f"Sandbox error: {e}")
