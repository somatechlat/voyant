"""
Quality Activities

Temporal activities for data quality validation using rule-based checks.
"""

import logging
from typing import Any, Dict, List, Optional

import duckdb
import pandas as pd
from temporalio import activity

from apps.core.config import get_settings
from apps.core.lib.quality_rules import (
    NullCheck,
    QualityEngine,
    QualityRule,
    RangeCheck,
    UniqueCheck,
)

logger = logging.getLogger(__name__)


class QualityActivities:
    """Activities to sample data and run quality rules."""

    def __init__(self):
        self.settings = get_settings()

    @activity.defn(name="quality_fetch_sample")
    def fetch_sample(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fetch a sample from DuckDB for quality checks.
        """
        table = params.get("table") or params.get("source_id")
        sample_size = params.get("sample_size", 5000)

        if not table:
            raise activity.ApplicationError(
                "table or source_id is required for quality sampling",
                non_retryable=True,
            )

        try:
            conn = duckdb.connect(database=self.settings.duckdb_path, read_only=True)
            df = conn.execute(f"SELECT * FROM {table} LIMIT {sample_size}").df()
            conn.close()
            return df.to_dict(orient="records")
        except Exception as exc:
            logger.error("Quality sampling failed for table %s: %s", table, exc)
            raise activity.ApplicationError(
                f"Failed to sample data for quality: {exc}", non_retryable=False
            ) from exc

    @activity.defn(name="run_quality_checks")
    def run_quality_checks(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute quality rules against sampled data.
        """
        data = params.get("data") or []
        checks = params.get("checks")

        df = pd.DataFrame(data)
        if df.empty:
            return {
                "is_valid": True,
                "total_checks": 0,
                "passed": 0,
                "failed": 0,
                "results": [],
                "rows_analyzed": 0,
            }

        rules = self._build_rules(df, checks)
        engine = QualityEngine(rules)
        summary = engine.validate(df)
        summary["rows_analyzed"] = len(df)
        return summary

    def _build_rules(
        self, df: pd.DataFrame, checks: Optional[List[Dict[str, Any]]]
    ) -> List[QualityRule]:
        """
        Build a ruleset from user-provided checks or sensible defaults.
        """
        if not checks:
            # Default: null check for every column (20% threshold) and unique check for id-like columns
            rules: List[QualityRule] = [
                NullCheck(col, max_null_pct=0.2) for col in df.columns
            ]
            for col in df.columns:
                if col.lower().endswith("id") or col.lower() == "id":
                    rules.append(UniqueCheck(col))
            return rules

        rules = []
        for spec in checks:
            # Expect dicts: {"type": "null|range|unique", "column": "...", ...}
            if not isinstance(spec, dict):
                logger.warning("Skipping invalid check spec (not a dict): %s", spec)
                continue
            rule_type = spec.get("type")
            column = spec.get("column")
            if not rule_type or not column:
                logger.warning(
                    "Skipping invalid check spec (missing type/column): %s", spec
                )
                continue

            if rule_type == "null":
                rules.append(
                    NullCheck(column, max_null_pct=float(spec.get("max_null_pct", 0.0)))
                )
            elif rule_type == "range":
                rules.append(
                    RangeCheck(
                        column,
                        min_val=spec.get("min"),
                        max_val=spec.get("max"),
                    )
                )
            elif rule_type == "unique":
                rules.append(UniqueCheck(column))
            else:
                logger.warning("Unknown quality rule type: %s", rule_type)
        return rules
