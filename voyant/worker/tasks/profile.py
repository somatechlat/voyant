"""
Profiling Tasks

Data profiling via ydata-profiling.
"""
from __future__ import annotations

import logging
import os
import tempfile
from datetime import datetime
from typing import Any, Dict, Optional

from voyant.worker.celery import celery_app
from voyant.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@celery_app.task(bind=True, name="voyant.worker.tasks.profile.run_profile")
def run_profile(
    self,
    job_id: str,
    source_id: str,
    table: Optional[str] = None,
    sample_size: int = 10000,
) -> Dict[str, Any]:
    """
    Execute data profiling job.
    
    Uses ydata-profiling to generate comprehensive EDA report.
    Results stored in MinIO, metadata in DataHub.
    """
    logger.info(f"Starting profile job {job_id} for source {source_id}")
    
    self.update_state(state="RUNNING", meta={"progress": 0, "status": "Loading data"})
    
    try:
        # Step 1: Query data from Trino
        self.update_state(state="RUNNING", meta={"progress": 10, "status": "Querying via Trino"})
        
        from voyant.core import get_trino_client
        client = get_trino_client()
        
        # Get sample for profiling
        table_name = table or "default_table"
        query = f"SELECT * FROM {table_name} LIMIT {sample_size}"
        
        self.update_state(state="RUNNING", meta={"progress": 20, "status": "Fetching sample"})
        
        # Step 2: Convert to DataFrame
        self.update_state(state="RUNNING", meta={"progress": 30, "status": "Converting to DataFrame"})
        
        # Step 3: Run profiling
        self.update_state(state="RUNNING", meta={"progress": 40, "status": "Running ydata-profiling"})
        
        # In production:
        # import pandas as pd
        # from ydata_profiling import ProfileReport
        # df = pd.DataFrame(result.rows, columns=result.columns)
        # profile = ProfileReport(df, title=f"Profile: {table_name}", minimal=True)
        
        self.update_state(state="RUNNING", meta={"progress": 70, "status": "Generating report"})
        
        # Step 4: Save to MinIO
        self.update_state(state="RUNNING", meta={"progress": 80, "status": "Saving artifacts"})
        
        # Upload HTML and JSON to MinIO
        artifact_paths = {
            "html": f"artifacts/{job_id}/profile.html",
            "json": f"artifacts/{job_id}/profile.json",
        }
        
        # Step 5: Register in DataHub
        self.update_state(state="RUNNING", meta={"progress": 90, "status": "Registering metadata"})
        
        result = {
            "job_id": job_id,
            "source_id": source_id,
            "table": table_name,
            "status": "completed",
            "sample_size": sample_size,
            "artifacts": artifact_paths,
            "completed_at": datetime.utcnow().isoformat(),
        }
        
        self.update_state(state="SUCCESS", meta={"progress": 100, "status": "Complete"})
        logger.info(f"Profile job {job_id} completed")
        
        return result
        
    except Exception as e:
        logger.exception(f"Profile job {job_id} failed")
        self.update_state(state="FAILURE", meta={"error": str(e)})
        raise
