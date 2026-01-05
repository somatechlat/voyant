"""
[DEPRECATED] Celery Worker Module for Background Task Processing.

This module configures and initializes a Celery application for background
task processing.

**WARNING: This module is deprecated.** New tasks should **NOT** be added here.
All new background orchestration should utilize the Temporal workflow engine.
Refer to `voyant.worker.worker_main` and `voyant.core.temporal_client` for
the current recommended approach to task orchestration.
"""

from celery import Celery
from voyant.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "voyant",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["voyant.worker.tasks.ingest", "voyant.worker.tasks.quality"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
