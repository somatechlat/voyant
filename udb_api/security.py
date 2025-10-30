"""Security utilities: SQL guard, masking stubs."""
from __future__ import annotations
import re

SELECT_ONLY = re.compile(r"^\s*(with\s+[^;]+)?select\s", re.I | re.S)

ALLOWED_PREFIXES = ("select", "with", "create view", "create or replace view")

def validate_sql(sql: str) -> None:
    lowered = sql.lower().strip()
    if not any(lowered.startswith(p) for p in ALLOWED_PREFIXES):
        raise ValueError("Only SELECT / WITH / CREATE VIEW statements allowed")
    if lowered.count(";") > 0 and not lowered.endswith(";"):
        # Basic heuristic to limit statement stacking
        raise ValueError("Multiple statements not allowed")
