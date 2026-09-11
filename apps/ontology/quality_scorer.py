"""
Data Quality Scorer — §4.4 Data Catalog.

Computes a five-dimension quality score for any dataset:

  - **Completeness** (weight 0.25): non-null cell ratio
  - **Uniqueness**   (weight 0.20): unique-value ratio in key columns
  - **Timeliness**   (weight 0.20): freshness vs. expected update cadence
  - **Consistency**  (weight 0.20): values matching expected format/type
  - **Accuracy**     (weight 0.15): values within expected range

Each dimension is scored 0–100; the overall score is the weighted average.
The scorer can operate on in-memory data or persist results to the
``QualityScore`` model.

Usage::

    scorer = DataQualityScorer()
    # From in-memory data
    score = scorer.compute_quality_score_from_data(
        columns=["id", "email", "age"],
        rows=[[1, "a@b.com", 25], [2, None, 30], ...],
        key_columns=["id"],
    )

    # Persist to DB
    score = scorer.compute_quality_score(
        dataset_id="urn:example:customers",
        columns=["id", "email", "age"],
        rows=[[1, "a@b.com", 25], ...],
        key_columns=["id"],
        tenant_id="tenant-1",
    )

    # Generate full report
    report = scorer.generate_quality_report(
        dataset_id="urn:example:customers",
        columns=["id", "email", "age"],
        rows=[[1, "a@b.com", 25], ...],
        key_columns=["id"],
        tenant_id="tenant-1",
    )
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Weights — §4.4 CATALOG Data Quality Scoring
# ---------------------------------------------------------------------------

_WEIGHTS = {
    "completeness": 0.25,
    "uniqueness": 0.20,
    "timeliness": 0.20,
    "consistency": 0.20,
    "accuracy": 0.15,
}

# Expected update frequency in hours (default: 24 h)
_DEFAULT_EXPECTED_UPDATE_HOURS = 24.0

# Type-checking regex patterns for consistency scoring
_TYPE_PATTERNS: dict[str, re.Pattern[str]] = {
    "integer": re.compile(r"^-?\d+$"),
    "float": re.compile(r"^-?\d+(\.\d+)?$"),
    "date": re.compile(r"^\d{4}-\d{2}-\d{2}$"),
    "datetime": re.compile(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}"),
    "boolean": re.compile(r"^(true|false|0|1|yes|no)$", re.IGNORECASE),
    "email": re.compile(r"^[\w.+\-]+@[\w.\-]+\.[a-zA-Z]{2,}$", re.IGNORECASE),
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class QualityScoreResult:
    """Result container for a quality score computation."""

    overall: float
    completeness: float
    uniqueness: float
    timeliness: float
    consistency: float
    accuracy: float

    def to_dict(self) -> dict[str, float]:
        return {
            "overall": self.overall,
            "completeness": self.completeness,
            "uniqueness": self.uniqueness,
            "timeliness": self.timeliness,
            "consistency": self.consistency,
            "accuracy": self.accuracy,
        }


@dataclass
class ColumnQualityReport:
    """Per-column quality breakdown."""

    column_name: str
    completeness: float
    uniqueness: float
    consistency: float
    accuracy: float
    null_count: int
    unique_count: int
    total_count: int
    invalid_format_count: int
    out_of_range_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "column_name": self.column_name,
            "completeness": round(self.completeness, 2),
            "uniqueness": round(self.uniqueness, 2),
            "consistency": round(self.consistency, 2),
            "accuracy": round(self.accuracy, 2),
            "null_count": self.null_count,
            "unique_count": self.unique_count,
            "total_count": self.total_count,
            "invalid_format_count": self.invalid_format_count,
            "out_of_range_count": self.out_of_range_count,
        }


@dataclass
class QualityReport:
    """Full quality report with per-column breakdown."""

    dataset_id: str
    score: QualityScoreResult
    columns: list[ColumnQualityReport] = field(default_factory=list)
    row_count: int = 0
    column_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "score": self.score.to_dict(),
            "row_count": self.row_count,
            "column_count": self.column_count,
            "columns": [c.to_dict() for c in self.columns],
        }


# ---------------------------------------------------------------------------
# Scorer
# ---------------------------------------------------------------------------


class DataQualityScorer:
    """
    Stateless data quality scorer.

    Operates on in-memory data (lists of rows) and can optionally persist
    results to the Django ``QualityScore`` model.
    """

    # -- Public API ---------------------------------------------------------

    def compute_quality_score(
        self,
        dataset_id: str,
        columns: list[str],
        rows: list[list[Any]],
        *,
        key_columns: list[str] | None = None,
        column_types: dict[str, str] | None = None,
        value_ranges: dict[str, tuple[float, float]] | None = None,
        expected_update_hours: float = _DEFAULT_EXPECTED_UPDATE_HOURS,
        last_updated_at: datetime | None = None,
        tenant_id: str = "",
    ) -> QualityScoreResult:
        """
        Compute quality score and persist to database.

        Args:
            dataset_id: URN or identifier of the dataset.
            columns: Column names.
            rows: Row data as list of lists (each inner list = one row).
            key_columns: Columns to evaluate for uniqueness (e.g. primary keys).
            column_types: ``{col_name: "integer"|"float"|"date"|…}`` for consistency.
            value_ranges: ``{col_name: (min, max)}`` for accuracy checks.
            expected_update_hours: Expected data freshness window in hours.
            last_updated_at: When the dataset was last updated.
            tenant_id: Tenant identifier.

        Returns:
            :class:`QualityScoreResult`
        """
        result = self.compute_quality_score_from_data(
            columns=columns,
            rows=rows,
            key_columns=key_columns,
            column_types=column_types,
            value_ranges=value_ranges,
            expected_update_hours=expected_update_hours,
            last_updated_at=last_updated_at,
        )

        # Persist to DB
        try:
            from apps.ontology.models import QualityScore

            QualityScore.objects.create(
                tenant_id=tenant_id,
                dataset_id=dataset_id,
                overall=result.overall,
                completeness=result.completeness,
                uniqueness=result.uniqueness,
                timeliness=result.timeliness,
                consistency=result.consistency,
                accuracy=result.accuracy,
            )
        except Exception:
            logger.warning("Failed to persist quality score for %s", dataset_id, exc_info=True)

        return result

    def compute_quality_score_from_data(
        self,
        columns: list[str],
        rows: list[list[Any]],
        *,
        key_columns: list[str] | None = None,
        column_types: dict[str, str] | None = None,
        value_ranges: dict[str, tuple[float, float]] | None = None,
        expected_update_hours: float = _DEFAULT_EXPECTED_UPDATE_HOURS,
        last_updated_at: datetime | None = None,
    ) -> QualityScoreResult:
        """
        Compute quality score from in-memory data (no persistence).

        Returns:
            :class:`QualityScoreResult` with all five dimensions.
        """
        if not rows or not columns:
            return QualityScoreResult(
                overall=0.0,
                completeness=0.0,
                uniqueness=0.0,
                timeliness=0.0,
                consistency=0.0,
                accuracy=0.0,
            )

        completeness = self._compute_completeness(columns, rows)
        uniqueness = self._compute_uniqueness(columns, rows, key_columns or [])
        timeliness = self._compute_timeliness(expected_update_hours, last_updated_at)
        consistency = self._compute_consistency(columns, rows, column_types or {})
        accuracy = self._compute_accuracy(columns, rows, value_ranges or {})

        overall = (
            completeness * _WEIGHTS["completeness"]
            + uniqueness * _WEIGHTS["uniqueness"]
            + timeliness * _WEIGHTS["timeliness"]
            + consistency * _WEIGHTS["consistency"]
            + accuracy * _WEIGHTS["accuracy"]
        )

        return QualityScoreResult(
            overall=round(overall, 2),
            completeness=round(completeness, 2),
            uniqueness=round(uniqueness, 2),
            timeliness=round(timeliness, 2),
            consistency=round(consistency, 2),
            accuracy=round(accuracy, 2),
        )

    def generate_quality_report(
        self,
        dataset_id: str,
        columns: list[str],
        rows: list[list[Any]],
        *,
        key_columns: list[str] | None = None,
        column_types: dict[str, str] | None = None,
        value_ranges: dict[str, tuple[float, float]] | None = None,
        expected_update_hours: float = _DEFAULT_EXPECTED_UPDATE_HOURS,
        last_updated_at: datetime | None = None,
        tenant_id: str = "",
    ) -> QualityReport:
        """
        Generate a full quality report with per-column breakdown.

        Returns:
            :class:`QualityReport` with dataset-level score and per-column details.
        """
        score = self.compute_quality_score(
            dataset_id=dataset_id,
            columns=columns,
            rows=rows,
            key_columns=key_columns,
            column_types=column_types,
            value_ranges=value_ranges,
            expected_update_hours=expected_update_hours,
            last_updated_at=last_updated_at,
            tenant_id=tenant_id,
        )

        col_reports: list[ColumnQualityReport] = []
        col_idx = {name: i for i, name in enumerate(columns)}
        total_rows = len(rows)

        for col_name in columns:
            idx = col_idx[col_name]
            col_values = [row[idx] if idx < len(row) else None for row in rows]

            null_count = sum(1 for v in col_values if v is None or str(v).strip() == "")
            non_null_values = [v for v in col_values if v is not None and str(v).strip() != ""]
            unique_count = len(set(str(v) for v in non_null_values))

            completeness = ((total_rows - null_count) / total_rows * 100) if total_rows > 0 else 0.0
            uniqueness = (unique_count / total_rows * 100) if total_rows > 0 else 0.0

            # Consistency
            invalid_count = 0
            if col_name in (column_types or {}):
                ctype = column_types[col_name]  # type: ignore[index]
                pattern = _TYPE_PATTERNS.get(ctype)
                if pattern:
                    for v in non_null_values:
                        if not pattern.match(str(v).strip()):
                            invalid_count += 1
            consistency = ((len(non_null_values) - invalid_count) / len(non_null_values) * 100) if non_null_values else 100.0

            # Accuracy
            out_of_range = 0
            if col_name in (value_ranges or {}):
                lo, hi = value_ranges[col_name]  # type: ignore[index]
                for v in non_null_values:
                    try:
                        fval = float(v)
                        if fval < lo or fval > hi:
                            out_of_range += 1
                    except (ValueError, TypeError):
                        out_of_range += 1
            accuracy = ((len(non_null_values) - out_of_range) / len(non_null_values) * 100) if non_null_values else 100.0

            col_reports.append(
                ColumnQualityReport(
                    column_name=col_name,
                    completeness=round(completeness, 2),
                    uniqueness=round(uniqueness, 2),
                    consistency=round(consistency, 2),
                    accuracy=round(accuracy, 2),
                    null_count=null_count,
                    unique_count=unique_count,
                    total_count=total_rows,
                    invalid_format_count=invalid_count,
                    out_of_range_count=out_of_range,
                )
            )

        return QualityReport(
            dataset_id=dataset_id,
            score=score,
            columns=col_reports,
            row_count=total_rows,
            column_count=len(columns),
        )

    # -- Dimension computations --------------------------------------------

    def _compute_completeness(
        self,
        columns: list[str],
        rows: list[list[Any]],
    ) -> float:
        """
        Completeness: (total_cells - null_cells) / total_cells * 100

        A cell is null if it is ``None`` or an empty/whitespace-only string.
        """
        total_cells = 0
        null_cells = 0

        for row in rows:
            for val in row:
                total_cells += 1
                if val is None or str(val).strip() == "":
                    null_cells += 1

        if total_cells == 0:
            return 0.0
        return (total_cells - null_cells) / total_cells * 100

    def _compute_uniqueness(
        self,
        columns: list[str],
        rows: list[list[Any]],
        key_columns: list[str],
    ) -> float:
        """
        Uniqueness: unique_values / total_values * 100 (for key columns).

        If no key columns are specified, defaults to using the first column
        as the assumed primary key.
        """
        if not key_columns:
            key_columns = [columns[0]] if columns else []

        if not key_columns or not rows:
            return 100.0

        col_idx = {name: i for i, name in enumerate(columns)}
        values: list[str] = []

        for col in key_columns:
            idx = col_idx.get(col)
            if idx is not None:
                for row in rows:
                    if idx < len(row) and row[idx] is not None:
                        values.append(str(row[idx]))

        if not values:
            return 0.0

        unique = len(set(values))
        return unique / len(values) * 100

    def _compute_timeliness(
        self,
        expected_update_hours: float,
        last_updated_at: datetime | None,
    ) -> float:
        """
        Timeliness: max(0, 100 - (age_hours / expected_hours * 100))

        If ``last_updated_at`` is None, assume data is fresh (100).
        """
        if last_updated_at is None:
            return 100.0

        now = datetime.now(UTC)
        if last_updated_at.tzinfo is None:
            last_updated_at = last_updated_at.replace(tzinfo=UTC)

        age_hours = (now - last_updated_at).total_seconds() / 3600.0
        score = max(0.0, 100.0 - (age_hours / expected_update_hours * 100.0))
        return min(score, 100.0)

    def _compute_consistency(
        self,
        columns: list[str],
        rows: list[list[Any]],
        column_types: dict[str, str],
    ) -> float:
        """
        Consistency: valid_values / total_values * 100

        A value is "valid" if it matches the expected type pattern
        defined in ``column_types``.  Columns without a type definition
        are skipped (assumed 100% consistent).
        """
        if not column_types:
            return 100.0

        col_idx = {name: i for i, name in enumerate(columns)}
        total = 0
        valid = 0

        for col_name, expected_type in column_types.items():
            idx = col_idx.get(col_name)
            if idx is None:
                continue

            pattern = _TYPE_PATTERNS.get(expected_type)
            if pattern is None:
                continue

            for row in rows:
                if idx >= len(row):
                    continue
                val = row[idx]
                if val is None or str(val).strip() == "":
                    continue  # Skip nulls — covered by completeness
                total += 1
                if pattern.match(str(val).strip()):
                    valid += 1

        if total == 0:
            return 100.0
        return valid / total * 100

    def _compute_accuracy(
        self,
        columns: list[str],
        rows: list[list[Any]],
        value_ranges: dict[str, tuple[float, float]],
    ) -> float:
        """
        Accuracy: in_range_values / total_values * 100

        A value is "accurate" if it falls within the expected range
        defined in ``value_ranges``.  Columns without a range are skipped.
        """
        if not value_ranges:
            return 100.0

        col_idx = {name: i for i, name in enumerate(columns)}
        total = 0
        in_range = 0

        for col_name, (lo, hi) in value_ranges.items():
            idx = col_idx.get(col_name)
            if idx is None:
                continue

            for row in rows:
                if idx >= len(row):
                    continue
                val = row[idx]
                if val is None or str(val).strip() == "":
                    continue
                total += 1
                try:
                    fval = float(val)
                    if lo <= fval <= hi:
                        in_range += 1
                except (ValueError, TypeError):
                    pass  # Non-numeric = out of range

        if total == 0:
            return 100.0
        return in_range / total * 100
