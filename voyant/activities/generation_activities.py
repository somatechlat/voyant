"""
Generation Activities: Building Blocks for Artifact Generation Workflows.

This module defines Temporal activities responsible for dynamically executing
registered artifact generator plugins. These activities transform analysis
results into user-consumable formats, such as charts, reports, or narrative
summaries, based on the specific context and generator capabilities.
"""

import logging
from typing import Any, Dict, List

from temporalio import activity
from temporalio.exceptions import ApplicationError

from voyant.core.errors import ArtifactGenerationError
from voyant.core.plugin_registry import PluginCategory, get_generators

logger = logging.getLogger(__name__)


class GenerationActivities:
    """
    A collection of Temporal activities related to artifact generation processes.

    These activities encapsulate the logic for dynamically loading and executing
    registered generator plugins based on a given context.
    """

    def __init__(self):
        """Initializes the GenerationActivities."""
        pass

    @activity.defn(name="run_generators")
    async def run_generators(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dynamically runs all active artifact generator plugins based on the provided context.

        Args:
            params: A dictionary containing the context required by generators, which typically includes:
                - `table_name` (str): The name of the table being analyzed.
                - `job_id` (str): The ID of the analysis job.
                - `tenant_id` (str): The ID of the tenant.
                - `profile` (Dict[str, Any], optional): The data profile summary.
                - `kpis` (List[Dict[str, Any]], optional): List of calculated KPI results.
                - `analyzers` (Dict[str, Any], optional): Results from analyzer plugins.

        Returns:
            A dictionary where keys are generator names and values are their respective
            generated artifact results. Includes an "_errors" key if any generators failed.

        Raises:
            ApplicationError: If a 'core' generator fails, halting the artifact generation process.
        """
        results = {}
        errors = []

        # Retrieve all registered generator plugin metadata.
        generator_infos = get_generators()

        if not generator_infos:
            activity.logger.warning("No generator plugins registered or active.")
            return {}

        activity.logger.info(f"Running {len(generator_infos)} generator plugin(s).")

        for info in generator_infos:
            # Limitation/Future Work: Feature flags are currently not dynamically evaluated.
            # TODO: Integrate with a feature flag service (e.g., LaunchDarkly) here
            # to enable/disable generators at runtime based on flags defined in `info.feature_flag`.
            if info.feature_flag:
                activity.logger.debug(f"Generator '{info.name}' is associated with feature flag '{info.feature_flag}'.")

            try:
                # Dynamically load and instantiate the generator plugin.
                from voyant.core.plugin_registry import get_plugin

                generator = get_plugin(info.name)

                if not generator:
                    activity.logger.error(f"Failed to load generator plugin '{info.name}'. Skipping.")
                    continue

                activity.logger.info(
                    f"Executing generator: '{info.name}' (Category: {info.category.value})."
                )
                # Execute the generator's main method, passing the workflow parameters as context.
                result = generator.generate(params)
                results[info.name] = result

            except Exception as e:
                error_msg = f"Generator '{info.name}' failed: {e}"
                activity.logger.error(error_msg)
                errors.append(error_msg)

                # If a 'core' generator (critical for business logic) fails, propagate the error
                # to the workflow to indicate a major issue.
                if info.is_core:
                    activity.logger.critical(f"Core generator '{info.name}' failed. Halting artifact generation.")
                    raise ApplicationError(
                        f"Core generator failed: {error_msg}", non_retryable=False
                    ) from e

        if errors:
            results["_errors"] = errors  # Aggregate non-critical errors.

        activity.logger.info("Generator execution completed.")
        return results
