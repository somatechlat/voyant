"""
Flink Client for Voyant.

This module provides a Python wrapper around the Apache Flink REST API to submit,
monitor, and cancel streaming jobs. It is used by the Temporal worker to manage
the lifecycle of streaming analytics pipelines.
"""

import logging
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
        # Default to internal docker DNS if not provided, or fallback to localhost mapping
        if not jobmanager_url:
            # Check if FLINK_JOBMANAGER_URL is in settings, otherwise guess based on infra
            # Since we didn't add FLINK_JOBMANAGER_URL to config.py yet, we use a sensible default
            # internal to the docker network: http://voyant_flink_jobmanager:8081
            self.base_url = "http://voyant_flink_jobmanager:8081"
        else:
            self.base_url = jobmanager_url.rstrip("/")

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

    def submit_jar(self, jar_id: str, entry_class: Optional[str] = None, program_args: Optional[str] = None) -> str:
        """
        Submit a job from an uploaded JAR.
        
        Note: For PyFlink, we often communicate via the table API or CLI, but REST submission
        supports jars. Python script submission usually requires the remote environment execution.
        """
        # Placeholder for JAR submission logic
        raise NotImplementedError("JAR submission not yet implemented.")

    def upload_jar(self, jar_path: str) -> str:
        """Upload a JAR file."""
        url = f"{self.base_url}/jars/upload"
        # Implementation skipped for now as we focus on PyFlink runner
        raise NotImplementedError("JAR upload not yet implemented.")
