"""
[DEPRECATED] Voyant Worker Tasks Package (Celery-based).

This package contains Celery-based tasks that are now deprecated.
New tasks should **NOT** be added here. For current task orchestration,
refer to the Temporal workflows and activities defined in `voyant.workflows`
and `voyant.activities`.
"""

from . import ingest, profile, quality, preset

__all__ = ["ingest", "profile", "quality", "preset"]
