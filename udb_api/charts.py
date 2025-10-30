"""Chart generation utilities.

Heuristics:
 - For KPI result with >=2 columns: if first column looks categorical (<50 distinct, non-numeric) and any numeric column -> bar chart.
 - For single numeric column -> histogram.
 - chartsSpec can override providing mapping: {kpi_name: {type: bar|hist, x: col, y: col}}.
"""
from __future__ import annotations
from typing import List, Dict, Any
import os
import plotly.express as px  # type: ignore


def _is_numeric(x):
    try:
        float(x)
        return True
    except Exception:
        return False


def build_charts(kpis: List[Dict[str, Any]], artifacts_root: str, job_id: str, charts_spec: Dict[str, Any] | None = None) -> List[str]:
    os.makedirs(os.path.join(artifacts_root, job_id, "charts"), exist_ok=True)
    chart_paths: List[str] = []
    spec = charts_spec or {}
    for kpi in kpis:
        name = kpi.get("name")
        cols = kpi.get("columns", [])
        rows = kpi.get("rows", [])
        if not cols or not rows:
            continue
        override = spec.get(name) if isinstance(spec, dict) else None
        chart_type = override.get("type") if override else None
        x_col = override.get("x") if override else None
        y_col = override.get("y") if override else None
        # Build row dicts
        dict_rows = [dict(zip(cols, r)) for r in rows]
        # Auto inference if not overridden
        if not chart_type:
            if len(cols) >= 2:
                # pick categorical + numeric
                for candidate in cols:
                    distinct = {dr[candidate] for dr in dict_rows}
                    if 0 < len(distinct) <= 50 and not all(_is_numeric(v) for v in distinct if v is not None):
                        # find numeric y
                        num_col = None
                        for c2 in cols:
                            if c2 == candidate:
                                continue
                            sample_val = next((dr[c2] for dr in dict_rows if dr.get(c2) is not None), None)
                            if sample_val is not None and _is_numeric(sample_val):
                                num_col = c2
                                break
                        if num_col:
                            chart_type = "bar"
                            x_col = candidate
                            y_col = num_col
                            break
            # fallback histogram first numeric
            if not chart_type:
                for c in cols:
                    sample_val = next((dr[c] for dr in dict_rows if dr.get(c) is not None), None)
                    if sample_val is not None and _is_numeric(sample_val):
                        chart_type = "hist"
                        x_col = c
                        break
        if not chart_type:
            continue
        fig = None
        try:
            if chart_type == "bar" and x_col and y_col:
                fig = px.bar(dict_rows, x=x_col, y=y_col, title=name)
            elif chart_type == "hist" and x_col:
                fig = px.histogram(dict_rows, x=x_col, title=name)
        except Exception:  # pragma: no cover
            continue
        if not fig:
            continue
        file_name = f"charts/{name}.html"
        full_path = os.path.join(artifacts_root, job_id, file_name)
        try:
            fig.write_html(full_path, include_plotlyjs="cdn")
            chart_paths.append(f"/artifact/{job_id}/{file_name}")
        except Exception:  # pragma: no cover
            pass
    return chart_paths
