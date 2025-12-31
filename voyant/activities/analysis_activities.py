"""
Analysis Activities

Temporal activities for executing data analysis plugins (AnalyzerPlugin).
Integrates Anomaly Detection, Forecasting, and other analytical services.
"""
import logging
from typing import Any, Dict, List, Optional

from temporalio import activity

from voyant.core.plugin_registry import get_analyzers, get_plugin
from voyant.core.errors import AnalysisError
from voyant.core.config import get_settings

logger = logging.getLogger(__name__)

class AnalysisActivities:
    """Activities for data analysis."""
    
    def __init__(self):
        self.settings = get_settings()

    @activity.defn(name="fetch_sample")
    def fetch_sample(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fetch a sample from DuckDB for analysis.
        """
        table = params.get("table")
        sample_size = params.get("sample_size", 10000)

        if not table:
            raise activity.ApplicationError(
                "table is required for sample fetch",
                non_retryable=True
            )

        try:
            import duckdb
            conn = duckdb.connect(database=self.settings.duckdb_path, read_only=True)
            df = conn.execute(f"SELECT * FROM {table} LIMIT {sample_size}").df()
            conn.close()
            return df.to_dict(orient="records")
        except Exception as e:
            raise activity.ApplicationError(
                f"Sample fetch failed: {e}",
                non_retryable=False
            )
        
    @activity.defn
    def run_analyzers(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run registered analyzer plugins.
        
        Args:
            params: Dict containing:
                - data: The data to analyze (List[Dict] or DataFrame-compatible)
                - analyzers: Optional List[str] names of specific analyzers to run.
                - context: Dict of shared context (e.g. feature columns)
            
        Returns:
            Dict of results {analyzer_name: result}
        """
        results = {}
        errors = []
        
        data = params.get("data")
        target_analyzers = params.get("analyzers") # If None, run all
        shared_context = params.get("context", {})
        
        # Get candidate analyzers
        all_infos = get_analyzers()
        
        # Filter if targets specified
        if target_analyzers:
            infos = [m for m in all_infos if m.name in target_analyzers]
        else:
            infos = all_infos
            
        if not infos:
            activity.logger.warning("No analyzer plugins found/selected")
            return {}
            
        activity.logger.info(f"Running {len(infos)} analyzers")
        
        for info in infos:
            # Check feature flag if present
            if info.feature_flag:
                # TODO: Check settings/launchdarkly
                pass

            try:
                # Load plugin
                analyzer = get_plugin(info.name)
                
                if not analyzer:
                    activity.logger.error(f"Failed to load analyzer {info.name}")
                    continue
                
                # Execute
                activity.logger.info(f"Executing analyzer: {info.name}")
                
                # Merge specific context for this analyzer if provided
                # e.g. params["context"]["anomaly_detector"] overrides
                plugin_context = shared_context.copy()
                if info.name in shared_context:
                    plugin_context.update(shared_context[info.name])
                    
                result = analyzer.analyze(data, plugin_context)
                results[info.name] = result
                
            except Exception as e:
                error_msg = f"Analyzer {info.name} failed: {e}"
                activity.logger.error(error_msg)
                errors.append(error_msg)
                
                if info.is_core:
                    activity.logger.error(f"Core analyzer {info.name} failed - halting")
                    raise activity.ApplicationError(f"Core analyzer failed: {error_msg}") from e

        if errors:
            results["_errors"] = errors
            
        return results
