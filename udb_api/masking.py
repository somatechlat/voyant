"""PII masking stub: mask emails and simple SSN-like patterns."""
from __future__ import annotations
import re
from typing import Any

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
RAW9_RE = re.compile(r"\b\d{9}\b")


def mask_value(val: Any) -> Any:
    if not isinstance(val, str):
        return val
    original = val
    val = EMAIL_RE.sub("***@***", val)
    val = SSN_RE.sub("***-**-****", val)
    val = RAW9_RE.sub("*********", val)
    return val if val != original else val


def mask_kpi_rows(kpis):
    for k in kpis:
        rows = k.get("rows", [])
        new_rows = []
        for r in rows:
            new_rows.append(tuple(mask_value(v) for v in r))
        k["rows"] = new_rows
    return kpis