"""
Profiling Activities: Building Blocks for Data Profiling Workflows.

This module defines Temporal activities responsible for generating statistical
profiles of datasets. It employs adaptive sampling techniques and leverages
DuckDB for efficient data access, ensuring that profiling can be performed
effectively even on large datasets.
"""

import logging
from typing import Any, Dict

import duckdb
import pandas as pd
from temporalio import activity

from voyant.core.adaptive_sampling import SamplingStrategy, sample_table
from voyant.core.config import get_settings

logger = logging.getLogger(__name__)


class ProfileActivities:
    """
    A collection of Temporal activities related to data profiling processes.

    These activities encapsulate the logic for sampling data, calculating
    descriptive statistics, and generating comprehensive data profiles.
    """

    def __init__(self):
        """Initializes the ProfileActivities with application settings."""
        self.settings = get_settings()

    @activity.defn(name="profile_data")
    def profile_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Profiles a dataset, optionally using adaptive sampling for large volumes.

        This activity fetches data (potentially sampled), calculates key descriptive
        statistics, and returns a structured profile summary.

        It emphasizes the use of adaptive sampling techniques to ensure
        representative samples while efficiently handling large datasets.

        Args:
            params: A dictionary containing profiling parameters:
                - `source_id` (str): The identifier of the data source.
                - `table` (str, optional): The specific table to profile. Defaults to `source_id`.
                - `sample_size` (int, optional): The target number of rows for the sample. Defaults to 10000.

        Returns:
            A dictionary containing the profile summary, including column statistics,
            row counts, and sampling details.

        Raises:
            activity.ApplicationError: If an error occurs during data fetching or profiling.
        """
        source_id = params.get("source_id")
        table_name = params.get("table") or source_id
        requested_sample_size = params.get("sample_size", 10000)

        activity.logger.info(
            f"Profiling '{table_name}' (target sample size: {requested_sample_size} rows)."
        )

        try:
            # 1. Connect to DuckDB and determine total row count.
            conn = duckdb.connect(database=self.settings.duckdb_path, read_only=True)
            total_rows = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[
                0
            ]

            # 2. Adaptive Data Fetching/Sampling Strategy.
            # For local DuckDB, loading up to ~100k rows into Pandas is efficient.
            # For larger datasets, SQL-based sampling is preferred to minimize memory usage.
            query = f"SELECT * FROM {table_name}"
            if total_rows > requested_sample_size * 2:
                # Use SQL-based Bernoulli sampling for very large tables.
                # A buffer (1.5x) is added to ensure enough data for Python-side adaptive sampling.
                percentage = ((requested_sample_size / total_rows) * 100 * 1.5)
                query = f"SELECT * FROM {table_name} USING SAMPLE {percentage:.2f}%"
                activity.logger.info(f"Applying SQL sampling to DuckDB: {percentage:.2f}%")
            else:
                activity.logger.info(f"Fetching full dataset (total rows: {total_rows}) as it's within limits.")

            # Fetch data into a Pandas DataFrame, then convert to list of dicts for generic processing.
            df = conn.execute(query).df()
            conn.close()
            data_list = df.to_dict(orient="records")

            # 3. Apply Python-side Adaptive Sampling (refines SQL sample or entire small dataset).
            # This ensures the final sample adheres to the requested size and strategy (e.g., stratified).
            sample_result = sample_table(
                data=data_list,
                sample_size=requested_sample_size,
                strategy=SamplingStrategy.ADAPTIVE,
            )
            sampled_data = sample_result.data
            sampling_stats = sample_result.stats

            activity.logger.info(
                f"Obtained final sample of {len(sampled_data)} records using {sampling_stats.strategy} strategy."
            )

            # 4. Generate Profile Summary (Lightweight, manual profiling).
            # Note: While full-featured libraries like `ydata-profiling` exist,
            # this implementation provides a lighter, custom profile summary.
            profile_summary = {
                "columns": {},
                "rows_analyzed": len(sampled_data),
                "total_rows_estimated": total_rows,
                "sampling_stats": sampling_stats.to_dict(),
            }

            if sampled_data:
                sample_df = pd.DataFrame(sampled_data)
                descriptive_stats = sample_df.describe(include="all").to_dict()
                null_counts = sample_df.isnull().sum().to_dict()

                for col in sample_df.columns:
                    profile_summary["columns"][col] = {
                        "type": str(sample_df[col].dtype),
                        "null_count": null_counts.get(col, 0),
                        "unique_count": sample_df[col].nunique(),
                        "stats": descriptive_stats.get(col, {}),
                    }

            activity.logger.info(f"Data profiling for '{table_name}' completed.")
            return {
                "source_id": source_id,
                "table": table_name,
                "profile": profile_summary,
                "generated_at": pd.Timestamp.now().isoformat() + "Z",
            }

        except Exception as e:
            activity.logger.error(f"Profiling activity for '{table_name}' failed: {e}")
            raise activity.ApplicationError(
                f"Profiling failed due to an unexpected error: {e}", non_retryable=False
            ) from e
