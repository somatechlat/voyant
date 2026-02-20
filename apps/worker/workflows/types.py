"""
Workflow Types: Data Structures for Temporal Workflow Parameters and Results.

This module defines common data structures (dataclasses) used as parameters
for initiating Temporal workflows and activities, as well as for structuring
their return values. Centralizing these types ensures consistency, type safety,
and clear contracts across the workflow definitions.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class IngestParams:
    """
    Parameters required to initiate an `IngestDataWorkflow`.

    Attributes:
        job_id: The unique identifier for the ingestion job.
        source_id: The identifier for the data source from which data will be ingested.
        mode: The ingestion mode, typically "full" for a complete refresh or "incremental" for updates.
        tables: An optional list of specific table names to ingest. If None, all tables may be ingested.
    """

    job_id: str
    source_id: str
    mode: str = "full"
    tables: Optional[List[str]] = None


@dataclass
class IngestResult:
    """
    The result structure returned upon successful completion of an `IngestDataWorkflow`.

    Attributes:
        job_id: The unique identifier of the completed ingestion job.
        source_id: The identifier of the data source from which data was ingested.
        status: The final status of the ingestion job (e.g., "completed").
        rows_ingested: The total number of rows successfully ingested.
        tables_synced: A list of table names that were successfully synchronized.
        completed_at: The ISO 8601 timestamp indicating when the job completed.
    """

    job_id: str
    source_id: str
    status: str
    rows_ingested: int
    tables_synced: List[str]
    completed_at: str
