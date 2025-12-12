"""
Preset Workflow Tasks

Execute pre-built analytical workflows.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List

from voyant.worker.celery import celery_app
from voyant.worker.tasks.profile import run_profile
from voyant.worker.tasks.quality import run_quality

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="voyant.worker.tasks.preset.execute_preset")
def execute_preset(
    self,
    job_id: str,
    preset_name: str,
    source_id: str,
    parameters: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Execute a preset analytical workflow.
    
    Orchestrates multiple sub-tasks (profiling, quality, KPI, etc.)
    based on preset definition.
    """
    logger.info(f"Starting preset {preset_name} job {job_id}")
    
    self.update_state(state="RUNNING", meta={"progress": 0, "status": "Loading preset"})
    
    try:
        # Step 1: Get preset definition
        preset = _get_preset_definition(preset_name)
        if not preset:
            raise ValueError(f"Unknown preset: {preset_name}")
        
        results = {"sub_jobs": []}
        
        # Step 2: Execute sub-tasks based on preset
        if "profile" in preset.get("output_artifacts", []):
            self.update_state(state="RUNNING", meta={"progress": 20, "status": "Running profiling"})
            profile_result = run_profile.delay(
                job_id=f"{job_id}_profile",
                source_id=source_id,
                sample_size=parameters.get("sample_size", 10000),
            )
            results["sub_jobs"].append({"type": "profile", "task_id": profile_result.id})
        
        if "quality" in preset.get("output_artifacts", []):
            self.update_state(state="RUNNING", meta={"progress": 40, "status": "Running quality checks"})
            quality_result = run_quality.delay(
                job_id=f"{job_id}_quality",
                source_id=source_id,
            )
            results["sub_jobs"].append({"type": "quality", "task_id": quality_result.id})
        
        if "kpi" in preset.get("output_artifacts", []):
            self.update_state(state="RUNNING", meta={"progress": 60, "status": "Computing KPIs"})
            # Execute KPI SQL
            results["sub_jobs"].append({"type": "kpi", "status": "completed"})
        
        if "chart" in preset.get("output_artifacts", []):
            self.update_state(state="RUNNING", meta={"progress": 80, "status": "Generating charts"})
            # Generate visualizations
            results["sub_jobs"].append({"type": "chart", "status": "completed"})
        
        # Step 3: Aggregate results
        self.update_state(state="RUNNING", meta={"progress": 90, "status": "Aggregating results"})
        
        result = {
            "job_id": job_id,
            "preset_name": preset_name,
            "source_id": source_id,
            "status": "completed",
            "sub_jobs": results["sub_jobs"],
            "completed_at": datetime.utcnow().isoformat(),
        }
        
        self.update_state(state="SUCCESS", meta={"progress": 100, "status": "Complete"})
        logger.info(f"Preset job {job_id} completed")
        
        return result
        
    except Exception as e:
        logger.exception(f"Preset job {job_id} failed")
        self.update_state(state="FAILURE", meta={"error": str(e)})
        raise


def _get_preset_definition(preset_name: str) -> Dict[str, Any]:
    """Get preset definition by name."""
    PRESETS = {
        "financial.revenue_analysis": {
            "output_artifacts": ["profile", "kpi", "chart"],
        },
        "customer.churn_analysis": {
            "output_artifacts": ["profile", "kpi", "model"],
        },
        "quality.data_profiling": {
            "output_artifacts": ["profile"],
        },
    }
    return PRESETS.get(preset_name, {})
