"""
KPI Activities: Building Blocks for Key Performance Indicator Calculation.

This module defines Temporal activities responsible for executing SQL queries
to calculate Key Performance Indicators (KPIs). These activities leverage
the Trino client to run pre-defined or ad-hoc SQL statements, providing
structured results for analytical insights.
"""

import logging
from typing import Any, Dict, List

from temporalio import activity
from temporalio.exceptions import ApplicationError

from voyant.core.trino import get_trino_client

logger = logging.getLogger(__name__)


class KPIActivities:
    """
    A collection of Temporal activities related to Key Performance Indicator (KPI) calculations.

    These activities encapsulate the logic for executing SQL queries against
    the Trino engine to derive business-critical metrics.
    """

    def __init__(self):
        """Initializes the KPIActivities."""
        pass

    @activity.defn(name="run_kpis")
    def run_kpis(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Executes a list of KPI SQL queries and returns their results.

        Each KPI definition includes a name and a SQL query string. The SQL
        query is executed via the Trino client, which includes built-in
        security validation to ensure only safe, read-only statements are run.

        Args:
            params: A dictionary containing KPI execution parameters:
                - `kpis` (List[Dict[str, str]]): A list of dictionaries, where
                  each dictionary contains:
                    - `name` (str): The name of the KPI.
                    - `sql` (str): The SQL query string for the KPI.

        Returns:
            A list of dictionaries, where each dictionary contains the results
            for a single KPI, including its name, column headers, and data rows.

        Raises:
            activity.ApplicationError: If a KPI definition is missing SQL, or if
                                     any of the underlying Trino queries fail.
        """
        kpis = params.get("kpis", [])
        if not kpis:
            activity.logger.info("No KPIs provided to run. Returning empty list.")
            return []

        trino = get_trino_client()
        results: List[Dict[str, Any]] = []

        for kpi in kpis:
            sql = kpi.get("sql")
            name = kpi.get("name", "kpi_unnamed")
            if not sql:
                activity.logger.error(f"KPI '{name}' is missing a SQL query. Skipping.")
                raise activity.ApplicationError(
                    f"KPI '{name}' is missing a SQL query. Cannot execute.", non_retryable=True
                )
            try:
                activity.logger.info(f"Executing KPI: '{name}'")
                result = trino.execute(sql)
                results.append(
                    {
                        "name": name,
                        "columns": result.columns,
                        "rows": result.rows,
                        "row_count": result.row_count,
                        "query_id": result.query_id,
                    }
                )
            except Exception as e:
                logger.error(f"KPI execution failed for '{name}': {e}")
                raise activity.ApplicationError(
                    f"KPI execution failed for '{name}': {e}", non_retryable=False
                ) from e

        activity.logger.info(f"Successfully executed {len(results)} KPIs.")
        return results
