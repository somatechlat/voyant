"""Sufficiency scoring for dataset readiness.

Computes a composite score based on:
- Row coverage (log-scaled row count)
- Cleanliness (1 - weighted null ratio)
- Joinability (candidate key distinct ratios)
- Freshness (time decay)

Outputs score (0..1) plus a list of need messages if under thresholds.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Dict, List

import duckdb

ROW_TARGET = 100_000  # diminishing returns beyond this
FRESHNESS_HALF_LIFE_HOURS = 72.0

@dataclass
class SufficiencyResult:
    score: float
    components: Dict[str, float]
    needs: List[str]


def _log_row_score(rows: int) -> float:
    if rows <= 0:
        return 0.0
    return min(1.0, math.log10(rows + 10) / math.log10(ROW_TARGET))


def _freshness_score(hours_old: float | None) -> float:
    if hours_old is None:
        return 0.5  # unknown freshness -> neutral-mid
    # Exponential decay: score = exp(-ln(2) * age / half_life)
    return math.exp(-math.log(2) * (hours_old / FRESHNESS_HALF_LIFE_HOURS))


def compute_sufficiency(con: duckdb.DuckDBPyConnection, tables: List[str]) -> SufficiencyResult:
    # Aggregate stats across provided tables (simple additive heuristics)
    total_rows = 0
    total_nulls = 0
    total_cells = 0
    joinability_scores: List[float] = []
    newest_ts = None

    for tbl in tables:
        try:
            df = con.execute(f"SELECT * FROM {tbl} LIMIT 0").df()
        except Exception:
            continue
        # Basic row count
        try:
            rc = con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        except Exception:
            rc = 0
        total_rows += rc
        # Null counts per column (sampled if large)
        try:  # placeholder simplified null computation path
            con.execute("SELECT 1")
        except Exception:  # pragma: no cover - defensive branch
            # Fallback per-column scan
            nulls_tbl = 0
            for col in df.columns:
                try:
                    nulls_tbl += con.execute(f"SELECT COUNT(*) FROM {tbl} WHERE {col} IS NULL").fetchone()[0]
                except Exception:
                    pass
            total_nulls += nulls_tbl
        else:
            # Fallback path above increments; here we need to approximate more safely.
            # Simpler: compute per-column counts individually (balance correctness & simplicity)
            per_col_nulls = 0
            for col in df.columns:
                try:
                    per_col_nulls += con.execute(f"SELECT COUNT(*) FROM {tbl} WHERE {col} IS NULL").fetchone()[0]
                except Exception:
                    pass
            total_nulls += per_col_nulls
        # Distinct ratio for potential key candidates (first 3 columns heuristic)
        sample_cols = df.columns[:3]
        for col in sample_cols:
            try:
                distinct = con.execute(f"SELECT COUNT(DISTINCT {col}) FROM {tbl}").fetchone()[0]
                ratio = 0.0 if rc == 0 else min(1.0, distinct / rc)
                if ratio > 0:  # ignore zero-information columns
                    joinability_scores.append(ratio)
            except Exception:
                continue
        # Freshness heuristic: look for common timestamp column names
        if newest_ts is None:
            for cand in ["updated_at", "modified_at", "last_modified", "ingested_at", "timestamp", "ts"]:
                try:
                    ts_val = con.execute(
                        f"SELECT MAX({cand}) FROM {tbl}"
                    ).fetchone()[0]
                    if ts_val:
                        # convert to epoch seconds if possible
                        try:
                            epoch = con.execute(f"SELECT strftime('%s', MAX({cand})) FROM {tbl}").fetchone()[0]
                        except Exception:
                            epoch = None
                        if epoch:
                            newest_ts = float(epoch)
                            break
                except Exception:
                    continue
        # Cell accounting (approx): row_count * column_count
        total_cells += rc * len(df.columns)

    row_score = _log_row_score(total_rows)
    cleanliness = 1.0 if total_cells == 0 else max(0.0, 1.0 - (total_nulls / total_cells))
    joinability = 0.0 if not joinability_scores else sum(joinability_scores) / len(joinability_scores)
    freshness = _freshness_score(
        None if newest_ts is None else (max(0.0, (time.time() - newest_ts) / 3600.0))
    )

    # Weighted composite
    score = (
        0.30 * row_score
        + 0.30 * cleanliness
        + 0.20 * joinability
        + 0.20 * freshness
    )

    needs: List[str] = []
    if row_score < 0.5:
        needs.append("Increase data volume (row coverage low)")
    if cleanliness < 0.75:
        needs.append("Reduce null density (cleanliness low)")
    if joinability < 0.6:
        needs.append("Improve join keys (distinct ratios low)")
    if freshness < 0.7:
        needs.append("Refresh source data (staleness detected)")

    return SufficiencyResult(
        score=round(score, 4),
        components={
            "rowCount": round(row_score, 4),
            "cleanliness": round(cleanliness, 4),
            "joinability": round(joinability, 4),
            "freshness": round(freshness, 4),
        },
        needs=needs,
    )
