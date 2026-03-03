from __future__ import annotations

import logging
from typing import Any

from apps.core.api_utils import run_async
from apps.core.config import get_settings
from apps.core.lib.temporal_client import get_temporal_client
from apps.workflows.models import Job

logger = logging.getLogger(__name__)


def dispatch_workflow(
    workflow_cls: Any,
    job_type: str,
    source_id: str | None,
    parameters: dict[str, Any],
    tenant_id: str,
) -> Job:
    """
    Creates a Job in the database, starts the corresponding Temporal workflow,
    and updates the job status to running.

    This abstracts the repetitive 3-step boilerplate identified during architecture audit.
    """
    settings = get_settings()

    job = Job.objects.create(
        tenant_id=tenant_id,
        job_type=job_type,
        source_id=source_id,
        status="queued",
        progress=0,
        parameters=parameters,
    )

    workflow_id = f"{job_type}-{job.job_id}"

    payload = {"job_id": str(job.job_id)}
    if source_id:
        payload["source_id"] = source_id
    payload.update(parameters)

    client = run_async(get_temporal_client)
    run_async(
        client.start_workflow,
        workflow_cls.run,
        payload,
        id=workflow_id,
        task_queue=settings.temporal_task_queue,
    )

    job.status = "running"
    job.save(update_fields=["status"])

    return job
