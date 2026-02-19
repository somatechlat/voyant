"""
Flink Client for Voyant.

This module provides a Python wrapper around the Apache Flink REST API to submit,
monitor, and cancel streaming jobs. It is used by the Temporal worker to manage
the lifecycle of streaming analytics pipelines.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

from voyant.core.config import get_settings

logger = logging.getLogger(__name__)


class FlinkClientError(Exception):
    """Base exception for Flink client errors."""


class FlinkClient:
    """
    Client for interacting with the Apache Flink JobManager REST API.
    """

    def __init__(self, jobmanager_url: Optional[str] = None):
        """
        Initialize the Flink client.

        Args:
            jobmanager_url: Base URL of the Flink JobManager. Defaults to settings.
        """
        settings = get_settings()
        resolved_url = jobmanager_url or settings.flink_jobmanager_url
        if not resolved_url:
            raise ValueError("FLINK_JOBMANAGER_URL must be configured")
        self.base_url = resolved_url.rstrip("/")

    def get_overview(self) -> Dict[str, Any]:
        """Get cluster overview."""
        url = f"{self.base_url}/overview"
        try:
            response = httpx.get(url, timeout=5.0)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to Flink JobManager: {e}")
            raise FlinkClientError(f"Connection failed: {e}")
        except httpx.HTTPStatusError as e:
            logger.error(f"Flink JobManager returned error: {e}")
            raise FlinkClientError(f"API error: {e}")

    def list_jobs(self) -> Dict[str, Any]:
        """List all jobs."""
        url = f"{self.base_url}/jobs/overview"
        try:
            response = httpx.get(url, timeout=5.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise FlinkClientError(f"Failed to list jobs: {e}")

    def submit_jar(
        self,
        jar_id: str,
        entry_class: Optional[str] = None,
        program_args: Optional[str] = None,
        parallelism: Optional[int] = None,
    ) -> str:
        """
        Submit a job from an uploaded JAR.
        """
        payload: Dict[str, Any] = {}
        if entry_class:
            payload["entryClass"] = entry_class
        if program_args:
            payload["programArgs"] = program_args
        if parallelism is not None:
            payload["parallelism"] = parallelism

        url = f"{self.base_url}/jars/{jar_id}/run"
        try:
            response = httpx.post(url, json=payload, timeout=30.0)
            response.raise_for_status()
            data = response.json()
            job_id = data.get("jobid")
            if not job_id:
                raise FlinkClientError("Flink run response did not include jobid.")
            return job_id
        except Exception as e:
            raise FlinkClientError(f"Failed to submit JAR {jar_id}: {e}") from e

    def upload_jar(self, jar_path: str) -> str:
        """Upload a JAR file."""
        path = Path(jar_path)
        if not path.exists() or not path.is_file():
            raise FlinkClientError(f"JAR file not found: {jar_path}")

        url = f"{self.base_url}/jars/upload"
        try:
            with path.open("rb") as file_obj:
                response = httpx.post(
                    url,
                    files={"jarfile": (path.name, file_obj, "application/java-archive")},
                    timeout=60.0,
                )
            response.raise_for_status()
            data = response.json()
            filename = data.get("filename", "")
            if not filename:
                raise FlinkClientError("Flink upload response missing filename.")
            return filename.rsplit("/", 1)[-1]
        except Exception as e:
            raise FlinkClientError(f"Failed to upload JAR {jar_path}: {e}") from e
