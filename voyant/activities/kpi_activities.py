"""
KPI Activities

Temporal activities for executing KPI SQL against Trino.
"""
import logging
from typing import Any, Dict, List

from temporalio import activity

from voyant.core.trino import get_trino_client

logger = logging.getLogger(__name__)

class KPIActivities:
    """Activities for KPI execution."""

    @activity.defn(name="run_kpis")
    def run_kpis(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute KPI SQL queries.

        Args:
            params: {"kpis": [{"name": str, "sql": str}]}
        """
        kpis = params.get("kpis", [])
        if not kpis:
            return []

        trino = get_trino_client()
        results: List[Dict[str, Any]] = []

        for kpi in kpis:
            sql = kpi.get("sql")
            name = kpi.get("name", "kpi")
            if not sql:
                raise activity.ApplicationError("KPI sql is required", non_retryable=True)
            try:
                result = trino.execute(sql)
            except Exception as e:
                logger.error(f"KPI execution failed for {name}: {e}")
                raise activity.ApplicationError(f"KPI execution failed: {e}")

            results.append({
                "name": name,
                "columns": result.columns,
                "rows": result.rows,
                "row_count": result.row_count,
                "query_id": result.query_id,
            })

        return results
