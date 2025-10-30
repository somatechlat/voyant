"""Narrative summarizer: derive human-friendly summary from KPIs & drift.

Heuristic lightweight implementation to avoid heavy LLM dependency while providing
useful at-a-glance insights. Future: plug optional LLM provider.
"""
from __future__ import annotations

from typing import Dict, List

def summarize(kpis: List[Dict], artifacts: Dict) -> str:
    if not kpis:
        base = "No KPIs executed."
    else:
        base = f"{len(kpis)} KPI set(s) executed."
    quality = "qualityHtml" in artifacts and artifacts.get("qualityHtml") is not None
    drift = "driftHtml" in artifacts and artifacts.get("driftHtml") is not None
    parts = [base]
    if quality:
        parts.append("Quality report available")
    if drift:
        parts.append("Drift report available")
    if not quality and not drift:
        parts.append("No quality/drift artifacts")
    # Look for any KPI records exposing numeric anomalies (simple heuristic: columns with value > 1e6)
    big_numbers = 0
    for rowset in kpis:
        if not isinstance(rowset, dict):
            continue
        rows = rowset.get("rows", []) or []
        for row in rows:
            if isinstance(row, dict):
                iterable_vals = row.values()
            elif isinstance(row, (list, tuple)):
                iterable_vals = row
            else:
                continue
            for v in iterable_vals:
                if isinstance(v, (int, float)) and v > 1_000_000:
                    big_numbers += 1
    if big_numbers:
        parts.append(f"{big_numbers} large numeric value(s) detected (>1e6)")
    return "; ".join(parts)
