"""
[DEPRECATED] Celery Worker Module

This module is deprecated in favor of Temporal Orchestration.
See voyant.worker.worker_main and voyant.core.temporal_client.

Do not add new tasks here.
"""
from celery import Celery
from voyant.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "voyant",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["voyant.worker.tasks.ingest", "voyant.worker.tasks.quality"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
