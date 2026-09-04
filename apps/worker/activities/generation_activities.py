"""Temporal activities for artifact generation."""

import logging
import os
from typing import Any

from temporalio import activity
from temporalio.exceptions import ApplicationError

from apps.core.lib.plugin_registry import get_generators

logger = logging.getLogger(__name__)


class GenerationActivities:

    def __init__(self):
        pass

    @staticmethod
    def _feature_enabled(flag_name: str) -> bool:
        env_key = f"VOYANT_FEATURE_{flag_name.upper()}"
        return os.environ.get(env_key, "false").lower() in ("1", "true", "yes", "on")

    @activity.defn(name="run_generators")
    async def run_generators(self, params: dict[str, Any]) -> dict[str, Any]:
        results = {}
        errors = []

        # Retrieve all registered generator plugin metadata.
        generator_infos = get_generators()

        if not generator_infos:
            activity.logger.warning("No generator plugins registered or active.")
            return {}

        activity.logger.info(f"Running {len(generator_infos)} generator plugin(s).")

        for info in generator_infos:
            if info.feature_flag and not self._feature_enabled(info.feature_flag):
                activity.logger.info(
                    "Skipping generator '%s' because feature flag '%s' is disabled.",
                    info.name,
                    info.feature_flag,
                )
                continue

            try:
                # Dynamically load and instantiate the generator plugin.
                from apps.core.lib.plugin_registry import get_plugin

                generator = get_plugin(info.name)

                if not generator:
                    activity.logger.error(
                        f"Failed to load generator plugin '{info.name}'. Skipping."
                    )
                    continue

                activity.logger.info(
                    f"Executing generator: '{info.name}' (Category: {info.category.value})."
                )
                # Execute the generator's main method, passing the workflow parameters as context.
                result = generator.generate(params)  # type: ignore[union-attr]
                results[info.name] = result

            except Exception as e:
                error_msg = f"Generator '{info.name}' failed: {e}"
                activity.logger.error(error_msg)
                errors.append(error_msg)

                # If a 'core' generator (critical for business logic) fails, propagate the error
                # to the workflow to indicate a major issue.
                if info.is_core:
                    activity.logger.critical(
                        f"Core generator '{info.name}' failed. Halting artifact generation."
                    )
                    raise ApplicationError(
                        f"Core generator failed: {error_msg}", non_retryable=False
                    ) from e

        if errors:
            results["_errors"] = errors  # Aggregate non-critical errors.

        activity.logger.info("Generator execution completed.")
        return results
