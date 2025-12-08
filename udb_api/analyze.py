"""Analysis artifact generation (profiling + quality/drift)."""
from __future__ import annotations
import duckdb
from typing import Optional, List, Dict
import os

try:
    from ydata_profiling import ProfileReport  # type: ignore
except ImportError:
    ProfileReport = None

try:  # Evidently optional (present in requirements but keep safe)
    from evidently.report import Report  # type: ignore
    from evidently.metric_preset import DataDriftPreset, DataQualityPreset  # type: ignore
except Exception:  # pragma: no cover - fallback if import changes
    Report = None  # type: ignore
    DataDriftPreset = None  # type: ignore
    DataQualityPreset = None  # type: ignore


def run_kpi_sql(con: duckdb.DuckDBPyConnection, sql: Optional[str]) -> List[Dict]:
    if not sql:
        return []
    df = con.execute(sql).df()
    return df.to_dict("records")


def _pick_table(con: duckdb.DuckDBPyConnection, explicit: Optional[str]) -> Optional[str]:
    if explicit:
        return explicit
    tables = con.execute("SHOW TABLES").fetchall()
    if not tables:
        return None
    return tables[0][0]


def _generate_profile(df, job_dir: str) -> Dict[str, Optional[str]]:
    if ProfileReport is None:
        return {"profileHtml": None, "profileJson": None}

    profile_html_path = os.path.join(job_dir, "profile.html")
    profile_json_path = os.path.join(job_dir, "profile.json")
    profile = ProfileReport(df, title="Profile", minimal=True)
    profile.to_file(profile_html_path)
    profile_json = profile.to_json()
    with open(profile_json_path, "w") as f:
        f.write(profile_json)
    return {
        "profileHtml": "profile.html",
        "profileJson": "profile.json",
    }


def _generate_quality_and_drift(df, baseline_dir: str, job_dir: str, table: str | None = None) -> Dict[str, Optional[str]]:
    """Create quality + drift reports using Evidently.

    A baseline dataframe snapshot is stored (parquet) if absent. Subsequent runs
    compare current df to baseline for drift. Both HTML and JSON artifacts are produced.
    """
    results: Dict[str, Optional[str]] = {
        "qualityHtml": None,
        "qualityJson": None,
        "driftHtml": None,
        "driftJson": None,
    }
    if Report is None:
        return results
    os.makedirs(baseline_dir, exist_ok=True)
    if table:
        baseline_path = os.path.join(baseline_dir, f"baseline_{table}.parquet")
    else:
        baseline_path = os.path.join(baseline_dir, "baseline.parquet")
    try:
        if not os.path.isfile(baseline_path):
            # Persist first snapshot as baseline
            df.to_parquet(baseline_path)
        # Load baseline
        import pandas as _pd  # type: ignore
        baseline_df = _pd.read_parquet(baseline_path)

        # Quality Report
        quality_report = Report(metrics=[DataQualityPreset()])
        quality_report.run(current_data=df)
        quality_html_path = os.path.join(job_dir, "quality.html")
        quality_json_path = os.path.join(job_dir, "quality.json")
        quality_report.save_html(quality_html_path)
        with open(quality_json_path, "w") as f:
            f.write(quality_report.json())
        results["qualityHtml"] = "quality.html"
        results["qualityJson"] = "quality.json"

        # Drift Report
        drift_report = Report(metrics=[DataDriftPreset()])
        drift_report.run(reference_data=baseline_df, current_data=df)
        drift_html_path = os.path.join(job_dir, "drift.html")
        drift_json_path = os.path.join(job_dir, "drift.json")
        drift_report.save_html(drift_html_path)
        with open(drift_json_path, "w") as f:
            f.write(drift_report.json())
        results["driftHtml"] = "drift.html"
        results["driftJson"] = "drift.json"
    except Exception:  # pragma: no cover - do not fail analysis on quality errors
        return results
    return results


def generate_artifacts(
    job_id: str,
    con: duckdb.DuckDBPyConnection,
    artifacts_root: str,
    table: Optional[str] = None,
    quality: bool = True,
) -> dict:
    job_dir = os.path.join(artifacts_root, job_id)
    os.makedirs(job_dir, exist_ok=True)
    selected_table = _pick_table(con, table)
    if not selected_table:
        return {
            "profileHtml": None,
            "profileJson": None,
            "qualityHtml": None,
            "qualityJson": None,
            "driftHtml": None,
            "driftJson": None,
            "charts": [],
        }
    df = con.execute(f"SELECT * FROM {selected_table} LIMIT 50000").df()

    profile_meta = _generate_profile(df, job_dir)

    quality_meta: Dict[str, Optional[str]] = {
        "qualityHtml": None,
        "qualityJson": None,
        "driftHtml": None,
        "driftJson": None,
    }
    if quality:
        quality_meta = _generate_quality_and_drift(df, os.path.join(artifacts_root, "baseline"), job_dir, selected_table)

    # Build artifact response paths (served via /artifact route)
    response = {
        "profileHtml": f"/artifact/{job_id}/{profile_meta['profileHtml']}" if profile_meta["profileHtml"] else None,
        "profileJson": f"/artifact/{job_id}/{profile_meta['profileJson']}" if profile_meta["profileJson"] else None,
        "qualityHtml": f"/artifact/{job_id}/{quality_meta['qualityHtml']}" if quality_meta["qualityHtml"] else None,
        "qualityJson": f"/artifact/{job_id}/{quality_meta['qualityJson']}" if quality_meta["qualityJson"] else None,
        "driftHtml": f"/artifact/{job_id}/{quality_meta['driftHtml']}" if quality_meta["driftHtml"] else None,
        "driftJson": f"/artifact/{job_id}/{quality_meta['driftJson']}" if quality_meta["driftJson"] else None,
        "charts": [],
    }
    return response
