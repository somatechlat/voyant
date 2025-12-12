"""
Celery Worker Configuration for Voyant

Async task execution for:
- Data ingestion (Beam/Airbyte)
- Profiling (ydata-profiling)
- Quality checks (Great Expectations)
- Preset workflows
"""
from __future__ import annotations

import logging
import os

from celery import Celery

from voyant.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Celery configuration
celery_app = Celery(
    "voyant",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "voyant.worker.tasks.ingest",
        "voyant.worker.tasks.profile",
        "voyant.worker.tasks.quality",
        "voyant.worker.tasks.preset",
    ],
)

# Celery settings
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    worker_prefetch_multiplier=1,
    worker_concurrency=2,
    result_expires=86400,  # 24 hours
    task_routes={
        "voyant.worker.tasks.ingest.*": {"queue": "ingest"},
        "voyant.worker.tasks.profile.*": {"queue": "profile"},
        "voyant.worker.tasks.quality.*": {"queue": "quality"},
        "voyant.worker.tasks.preset.*": {"queue": "preset"},
    },
)
