"""Temporal activities for data profiling."""

import logging
from typing import Any

import duckdb
import pandas as pd
from temporalio import activity
from temporalio.exceptions import ApplicationError

from apps.analysis.lib.adaptive_sampling import SamplingStrategy, sample_table
from apps.core.config import get_settings

logger = logging.getLogger(__name__)


class ProfileActivities:
    def __init__(self):
        self.settings = get_settings()

    @activity.defn(name="profile_data")
    def profile_data(self, params: dict[str, Any]) -> dict[str, Any]:
        source_id = params.get("source_id")
        table_name = params.get("table") or source_id
        requested_sample_size = params.get("sample_size", 10000)

        activity.logger.info(
            f"Profiling '{table_name}' (target sample size: {requested_sample_size} rows)."
        )

        try:
            # 1. Connect to DuckDB and determine total row count.
            conn = duckdb.connect(database=self.settings.duckdb_path, read_only=True)
            total_rows = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[  # type: ignore[index]
                0
            ]

            # 2. Adaptive Data Fetching/Sampling Strategy.
            # For local DuckDB, loading up to ~100k rows into Pandas is efficient.
            # For larger datasets, SQL-based sampling is preferred to minimize memory usage.
            query = f"SELECT * FROM {table_name}"
            if total_rows > requested_sample_size * 2:
                # Use SQL-based Bernoulli sampling for very large tables.
                # A buffer (1.5x) is added to ensure enough data for Python-side adaptive sampling.
                percentage = (requested_sample_size / total_rows) * 100 * 1.5
                query = f"SELECT * FROM {table_name} USING SAMPLE {percentage:.2f}%"
                activity.logger.info(f"Applying SQL sampling to DuckDB: {percentage:.2f}%")
            else:
                activity.logger.info(
                    f"Fetching full dataset (total rows: {total_rows}) as it's within limits."
                )

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

            # 4. Compute per-column descriptive statistics from the final sample.
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
            raise ApplicationError(
                f"Profiling failed due to an unexpected error: {e}", non_retryable=False
            ) from e
