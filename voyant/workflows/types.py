from datetime import timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

@dataclass
class IngestParams:
    job_id: str
    source_id: str
    mode: str = "full"
    tables: Optional[List[str]] = None

@dataclass
class IngestResult:
    job_id: str
    source_id: str
    status: str
    rows_ingested: int
    tables_synced: List[str]
    completed_at: str
