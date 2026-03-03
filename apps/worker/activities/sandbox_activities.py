import logging
from typing import Any, Dict

from temporalio import activity

logger = logging.getLogger(__name__)


class SandboxActivities:

    @activity.defn(name="run_python_sandbox")
    async def run_python_sandbox(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Physical bridge to the PythonDockerNode.
        """
        from apps.core.lib.python_sandbox import PythonSandboxNode

        script = params.get("script", "")
        tenant_id = params.get("tenant_id", "default")
        dependencies = params.get("dependencies", [])

        # Execute genuine docker wrapper natively
        result = await PythonSandboxNode.execute_script(
            script_content=script,
            parameters={"deps": dependencies},
            tenant_id=tenant_id,
        )

        return result
