"""
Analysis Activities: Building Blocks for Data Analysis Workflows.

This module defines Temporal activities that perform core data analysis tasks,
including fetching data samples for in-memory processing and dynamically
executing registered analyzer plugins. These activities are designed to be
flexible and extensible, supporting a wide range of analytical operations.
"""

import logging
import os
from typing import Any, Dict, List

from temporalio import activity
from temporalio.exceptions import ApplicationError

from voyant.core.config import get_settings
from voyant.core.plugin_registry import get_analyzers, get_plugin

logger = logging.getLogger(__name__)


class AnalysisActivities:
    """
    A collection of Temporal activities related to data analysis processes.

    These activities encapsulate the logic for preparing data for analysis and
    executing various analytical plugins against that data.
    """

    def __init__(self):
        """Initializes the AnalysisActivities with application settings."""
        self.settings = get_settings()

    @staticmethod
    def _feature_enabled(flag_name: str) -> bool:
        env_key = f"VOYANT_FEATURE_{flag_name.upper()}"
        return os.environ.get(env_key, "false").lower() in ("1", "true", "yes", "on")

    @activity.defn(name="fetch_sample")
    def fetch_sample(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fetches a data sample from DuckDB for in-memory analysis.

        Args:
            params: A dictionary containing parameters for fetching the sample:
                - `table` (str): The name of the table to fetch the sample from.
                - `sample_size` (int, optional): The maximum number of rows to fetch. Defaults to 10000.

        Returns:
            A list of dictionaries, where each dictionary represents a row of the sampled data.

        Raises:
            activity.ApplicationError: If the table name is missing or if data fetching fails.
        """
        table = params.get("table")
        sample_size = params.get("sample_size", 10000)

        if not table:
            raise activity.ApplicationError(
                "table is required for sample fetch activity.", non_retryable=True
            )

        activity.logger.info(f"Fetching sample from table '{table}' (size: {sample_size}).")

        try:
            import duckdb

            conn = duckdb.connect(database=self.settings.duckdb_path, read_only=True)
            # Execute a query to get a sample, respecting the configured limit.
            df = conn.execute(f"SELECT * FROM {table} LIMIT {sample_size}").df()
            conn.close()
            activity.logger.info(f"Fetched {len(df)} rows from '{table}'.")
            return df.to_dict(orient="records")
        except Exception as e:
            activity.logger.error(f"Sample fetch from '{table}' failed: {e}")
            raise activity.ApplicationError(
                f"Failed to fetch sample from '{table}': {e}", non_retryable=False
            ) from e

    @activity.defn(name="run_analyzers")
    def run_analyzers(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Dynamically runs a set of registered analyzer plugins against provided data.

        Analyzers are loaded from the plugin registry and executed based on their
        configuration and any provided feature flags.

        Args:
            params: A dictionary containing parameters for running analyzers:
                - `data` (Any): The data to be analyzed (e.g., a list of dicts or a Pandas DataFrame).
                - `analyzers` (Optional[List[str]]): A list of specific analyzer plugin names to run.
                                                   If None, all active analyzer plugins will be considered.
                - `context` (Dict[str, Any], optional): A dictionary of shared context
                                                      (e.g., specific columns, parameters)
                                                      to pass to the analyzers.

        Returns:
            A dictionary where keys are analyzer names and values are their respective
            analysis results. Includes an "_errors" key if any analyzers failed.

        Raises:
            activity.ApplicationError: If a 'core' analyzer fails, halting the analysis.
        """
        results = {}
        errors = []

        data = params.get("data")
        target_analyzers = params.get("analyzers")  # If None, attempt to run all active analyzers.
        shared_context = params.get("context", {})

        # Retrieve all available analyzer plugins from the registry.
        all_analyzer_metadata = get_analyzers()

        # Filter analyzers if a specific list of target_analyzers is provided.
        if target_analyzers:
            infos = [m for m in all_analyzer_metadata if m.name in target_analyzers]
        else:
            infos = all_analyzer_metadata

        if not infos:
            activity.logger.warning("No analyzer plugins found or selected to run.")
            return {}

        activity.logger.info(f"Attempting to run {len(infos)} analyzer plugin(s).")

        for info in infos:
            if info.feature_flag and not self._feature_enabled(info.feature_flag):
                activity.logger.info(
                    "Skipping analyzer '%s' because feature flag '%s' is disabled.",
                    info.name,
                    info.feature_flag,
                )
                continue

            try:
                # Dynamically load and instantiate the analyzer plugin.
                analyzer_instance = get_plugin(info.name)

                if not analyzer_instance:
                    activity.logger.error(f"Failed to load analyzer plugin '{info.name}'. Skipping.")
                    continue

                activity.logger.info(f"Executing analyzer: '{info.name}'.")

                # Merge shared context with any plugin-specific context.
                plugin_context = shared_context.copy()
                if info.name in shared_context:
                    plugin_context.update(shared_context[info.name])

                # Execute the analyzer's main analysis method.
                result = analyzer_instance.analyze(data, plugin_context)
                results[info.name] = result

            except Exception as e:
                error_msg = f"Analyzer '{info.name}' failed: {e}"
                activity.logger.error(error_msg)
                errors.append(error_msg)

                # If a 'core' analyzer (critical for business logic) fails, propagate the error
                # to the workflow to indicate a major issue.
                if info.is_core:
                    activity.logger.critical(f"Core analyzer '{info.name}' failed. Halting analysis.")
                    raise activity.ApplicationError(
                        f"Core analyzer failed: {error_msg}", non_retryable=False
                    ) from e

        if errors:
            results["_errors"] = errors # Aggregate non-critical errors.

        activity.logger.info("Analyzer execution completed.")
        return results
