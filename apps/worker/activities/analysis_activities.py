"""Temporal activities for data analysis."""

import logging
import os
from typing import Any

from temporalio import activity
from temporalio.exceptions import ApplicationError

from apps.core.config import get_settings
from apps.core.lib.plugin_registry import get_analyzers, get_plugin

logger = logging.getLogger(__name__)


class AnalysisActivities:

    def __init__(self):
        self.settings = get_settings()

    @staticmethod
    def _feature_enabled(flag_name: str) -> bool:
        env_key = f"VOYANT_FEATURE_{flag_name.upper()}"
        return os.environ.get(env_key, "false").lower() in ("1", "true", "yes", "on")

    @activity.defn(name="fetch_sample")
    def fetch_sample(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        table = params.get("table")
        sample_size = params.get("sample_size", 10000)

        if not table:
            raise ApplicationError(
                "table is required for sample fetch activity.", non_retryable=True
            )

        activity.logger.info(
            f"Fetching sample from table '{table}' (size: {sample_size})."
        )

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
            raise ApplicationError(
                f"Failed to fetch sample from '{table}': {e}", non_retryable=False
            ) from e

    @activity.defn(name="run_analyzers")
    def run_analyzers(self, params: dict[str, Any]) -> dict[str, Any]:
        results = {}
        errors = []

        data = params.get("data")
        target_analyzers = params.get(
            "analyzers"
        )  # If None, attempt to run all active analyzers.
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
                    activity.logger.error(
                        f"Failed to load analyzer plugin '{info.name}'. Skipping."
                    )
                    continue

                activity.logger.info(f"Executing analyzer: '{info.name}'.")

                # Merge shared context with any plugin-specific context.
                plugin_context = shared_context.copy()
                if info.name in shared_context:
                    plugin_context.update(shared_context[info.name])

                # Execute the analyzer's main analysis method.
                result = analyzer_instance.analyze(data, plugin_context)  # type: ignore[union-attr]
                results[info.name] = result

            except Exception as e:
                error_msg = f"Analyzer '{info.name}' failed: {e}"
                activity.logger.error(error_msg)
                errors.append(error_msg)

                # If a 'core' analyzer (critical for business logic) fails, propagate the error
                # to the workflow to indicate a major issue.
                if info.is_core:
                    activity.logger.critical(
                        f"Core analyzer '{info.name}' failed. Halting analysis."
                    )
                    raise ApplicationError(
                        f"Core analyzer failed: {error_msg}", non_retryable=False
                    ) from e

        if errors:
            results["_errors"] = errors  # Aggregate non-critical errors.

        activity.logger.info("Analyzer execution completed.")
        return results
