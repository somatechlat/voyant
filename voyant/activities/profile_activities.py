"""
Profiling Activities

Temporal activities for profiling data.
Adheres to VIBE Coding Rules: Uses Real Implementations (DuckDB + Adaptive Sampling).
"""
import logging
import duckdb
import pandas as pd
from typing import Any, Dict, List

from temporalio import activity
from voyant.core.config import get_settings
from voyant.core.adaptive_sampling import sample_table, SamplingStrategy
from voyant.core.retry_config import DATA_PROCESSING_RETRY, TIMEOUTS

logger = logging.getLogger(__name__)

class ProfileActivities:
    def __init__(self):
        self.settings = get_settings()

    @activity.defn(
        name="profile_data",
        start_to_close_timeout=TIMEOUTS["processing_long"],
        retry_policy=DATA_PROCESSING_RETRY
    )
    def profile_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Profile a dataset with adaptive sampling.
        
        PhD Analyst: Ensures representative samples.
        Performance Engineer: Avoids full table scans on massive data.
        """
        source_id = params.get("source_id")
        table_name = params.get("table") or source_id
        requested_sample_size = params.get("sample_size", 10000)
        
        activity.logger.info(f"Profiling {table_name} (target sample: {requested_sample_size})")
        
        try:
            # 1. Fetch Data
            # Connect to DuckDB (read-only)
            conn = duckdb.connect(database=self.settings.duckdb_path, read_only=True)
            
            # Get total count first for sampling decision
            total_rows = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            
            # Fetch data (if small, fetch all; if large, use LIMIT or fetch all then sample?)
            # Adaptive Sampling module works on list of dicts currently, so we need to fetch.
            # In a real massively scalable system, "push-down" sampling to SQL is better.
            # For this implementation (DuckDB local), fetching 100k rows is fast.
            # If total_rows is huge, we should use SQL sampling.
            
            if total_rows > requested_sample_size * 2:
                # Use SQL-based sampling (Bernoulli) to avoid loading everything
                # DuckDB supports TABLESAMPLE SYSTEM (x%)
                percentage = (requested_sample_size / total_rows) * 100 * 1.5 # 1.5x buffer
                query = f"SELECT * FROM {table_name} USING SAMPLE {percentage}%"
                activity.logger.info(f"Using SQL sampling: {percentage:.2f}%")
            else:
                query = f"SELECT * FROM {table_name}"
            
            df = conn.execute(query).df()
            conn.close()
            
            data_list = df.to_dict(orient="records")
            
            # 2. Apply Adaptive Sampling (Python side refinement)
            # This handles the sophisticated strategy selection (Stratified, etc.) if needed
            sample_result = sample_table(
                data=data_list,
                sample_size=requested_sample_size,
                strategy=SamplingStrategy.ADAPTIVE
            )
            
            sampled_data = sample_result.data
            stats = sample_result.stats
            
            activity.logger.info(f"Sampled {len(sampled_data)} records using {stats.strategy}")
            
            # 3. Generate Profile (Mocking the heavyweight profiling for speed/vibe, 
            # ideally would call ydata_profiling here but avoiding heavy dependency install for now 
            # unless user specifically asked. We'll do a "light" profile manually).
            
            profile_summary = {
                "columns": {},
                "rows_analyzed": len(sampled_data),
                "total_rows_estimated": total_rows,
                "sampling_stats": stats.to_dict()
            }
            
            if sampled_data:
                sample_df = pd.DataFrame(sampled_data)
                description = sample_df.describe(include='all').to_dict()
                
                # Check for nulls
                null_counts = sample_df.isnull().sum().to_dict()
                
                for col in sample_df.columns:
                    profile_summary["columns"][col] = {
                        "type": str(sample_df[col].dtype),
                        "null_count": null_counts.get(col, 0),
                        "unique_count": sample_df[col].nunique(),
                        "stats": description.get(col, {})
                    }
            
            return {
                "source_id": source_id,
                "table": table_name,
                "profile": profile_summary,
                "generated_at": pd.Timestamp.now().isoformat()
            }
            
        except Exception as e:
            activity.logger.error(f"Profiling failed: {e}")
            raise activity.ApplicationError(f"Profiling failed: {e}", non_retryable=False)
