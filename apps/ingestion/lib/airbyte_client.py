"""
Airbyte HTTP Client: Production-Ready Integration for Data Ingestion.

This module provides an asynchronous, resilient client for interacting with the
Airbyte API. It enables Voyant to programmatically manage data synchronization
jobs, monitor their status, and orchestrate data ingestion from various sources.

Key features include:
-   Asynchronous HTTP communication using `httpx`.
-   Integration with a circuit breaker pattern for enhanced fault tolerance.
-   Robust error handling with specific exception types.
-   Support for common Airbyte operations such as listing connections,
    triggering syncs, and monitoring job status.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx
from apps.core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    get_circuit_breaker,
)
from apps.core.errors import ExternalServiceError

logger = logging.getLogger(__name__)


# =============================================================================
# Airbyte Job States
# =============================================================================


class AirbyteJobStatus(str, Enum):
    """
    Enumeration representing the possible states of an Airbyte synchronization job.
    """

    PENDING = "pending"
    RUNNING = "running"
    INCOMPLETE = "incomplete"
    FAILED = "failed"
    SUCCEEDED = "succeeded"
    CANCELLED = "cancelled"


# =============================================================================
# Client Configuration
# =============================================================================


@dataclass
class AirbyteClientConfig:
    """
    Configuration settings for the Airbyte client.

    Attributes:
        base_url (str): The base URL for the Airbyte API.
        timeout_seconds (float): Default timeout for HTTP requests in seconds.
        max_retries (int): Maximum number of retries for transient HTTP errors.
        cb_failure_threshold (int): Number of consecutive failures before the circuit opens.
        cb_recovery_timeout (float): Time (in seconds) the circuit stays open before trying to close.
        cb_success_threshold (int): Number of successful requests in half-open state required to close.
        api_key (Optional[str]): API key for bearer token authentication.
        basic_auth_user (Optional[str]): Username for basic authentication.
        basic_auth_password (Optional[str]): Password for basic authentication.
    """

    base_url: str = ""
    timeout_seconds: float = 30.0
    max_retries: int = 3

    # Circuit breaker settings.
    cb_failure_threshold: int = 5
    cb_recovery_timeout: float = 60.0
    cb_success_threshold: int = 3

    # Authentication credentials.
    api_key: Optional[str] = None
    basic_auth_user: Optional[str] = None
    basic_auth_password: Optional[str] = None


# =============================================================================
# Airbyte Client
# =============================================================================


class AirbyteClient:
    """
    An asynchronous HTTP client for programmatic interaction with the Airbyte API.

    This client provides a high-level interface to manage Airbyte connections,
    trigger and monitor data synchronization jobs, and perform health checks.
    It incorporates a circuit breaker pattern to enhance resilience against
    temporary Airbyte service unavailability.
    """

    def __init__(self, config: Optional[AirbyteClientConfig] = None):
        """
        Initializes the AirbyteClient with specified or default configuration.

        Args:
            config (Optional[AirbyteClientConfig]): Configuration object for the client.
                                                    If None, a default configuration is used.
        """
        self.config = config or AirbyteClientConfig()
        if not self.config.base_url:
            raise ValueError("Airbyte base_url must be configured")
        self._client: Optional[httpx.AsyncClient] = None
        self._circuit_breaker: CircuitBreaker

        # Initialize circuit breaker for Airbyte API calls.
        cb_config = CircuitBreakerConfig(
            failure_threshold=self.config.cb_failure_threshold,
            recovery_timeout=self.config.cb_recovery_timeout,
            success_threshold=self.config.cb_success_threshold,
        )
        self._circuit_breaker = get_circuit_breaker("airbyte", cb_config)

        logger.info(f"Airbyte client initialized for base URL: {self.config.base_url}")

    async def _get_client(self) -> httpx.AsyncClient:
        """
        Lazily gets or creates an asynchronous HTTP client instance for Airbyte API calls.

        The client is configured with base URL, authentication headers, and timeout settings.
        Connections are reused for efficiency.

        Returns:
            httpx.AsyncClient: An asynchronous HTTP client instance.
        """
        if self._client is None or self._client.is_closed:
            headers = {"Content-Type": "application/json"}

            # Configure authentication headers if API key is provided.
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"

            auth = None
            # Configure basic authentication if credentials are provided.
            if self.config.basic_auth_user and self.config.basic_auth_password:
                auth = httpx.BasicAuth(
                    self.config.basic_auth_user, self.config.basic_auth_password
                )

            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                headers=headers,
                auth=auth,
                timeout=httpx.Timeout(self.config.timeout_seconds),
            )

        return self._client

    async def _request(
        self, method: str, endpoint: str, json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Makes an HTTP request to the Airbyte API, protected by a circuit breaker.

        Args:
            method (str): The HTTP method (e.g., "GET", "POST", "DELETE").
            endpoint (str): The API endpoint path relative to the base URL.
            json_data (Optional[Dict[str, Any]]): JSON payload for POST requests.

        Returns:
            Dict[str, Any]: The JSON response from the Airbyte API.

        Raises:
            CircuitBreakerOpenError: If the circuit breaker is open, indicating Airbyte is unavailable.
            ExternalServiceError: For HTTP status errors or network connection errors.
            ValueError: If an unsupported HTTP method is used.
        """
        # Check circuit breaker state before proceeding with the request.
        if not self._circuit_breaker.can_proceed():
            logger.warning("Airbyte API circuit breaker is OPEN. Failing fast.")
            raise CircuitBreakerOpenError(
                "Airbyte service is currently unavailable (circuit breaker is open)."
            )

        client = await self._get_client()

        try:
            # Perform the HTTP request based on the specified method.
            if method.upper() == "GET":
                response = await client.get(endpoint)
            elif method.upper() == "POST":
                response = await client.post(endpoint, json=json_data)
            elif method.upper() == "DELETE":
                response = await client.delete(endpoint)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx).

            # Record a successful request with the circuit breaker.
            self._circuit_breaker.record_success()

            return response.json() if response.content else {}

        except httpx.HTTPStatusError as e:
            # Record a failure with the circuit breaker and raise a specific error.
            self._circuit_breaker.record_failure()
            logger.error(
                f"Airbyte API returned HTTP error: {e.response.status_code} for {endpoint}."
            )
            raise ExternalServiceError(
                service_name="Airbyte",
                details=f"HTTP {e.response.status_code}: {e.response.text[:200]}...",
            ) from e
        except httpx.RequestError as e:
            # Record a failure with the circuit breaker and raise a specific error for network issues.
            self._circuit_breaker.record_failure()
            logger.error(f"Airbyte connection error for {endpoint}: {e}.")
            raise ExternalServiceError(service_name="Airbyte", details=str(e)) from e
        except Exception as e:
            # Catch other unexpected errors and record as failure.
            self._circuit_breaker.record_failure()
            logger.error(
                f"An unexpected error occurred during Airbyte API request to {endpoint}: {e}."
            )
            raise ExternalServiceError(
                service_name="Airbyte", details=f"Unexpected error: {e}"
            ) from e

    async def close(self):
        """
        Closes the underlying HTTP client session.

        This method should be called when the client instance is no longer needed
        to release network resources gracefully.
        """
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    # =========================================================================
    # Connection Operations
    # =========================================================================

    async def list_connections(self) -> List[Dict[str, Any]]:
        """
        Retrieves a list of all existing Airbyte connections.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, where each dictionary
                                  represents an Airbyte connection.
        """
        response = await self._request("GET", "/connections")
        return response.get("connections", [])

    async def get_connection(self, connection_id: str) -> Dict[str, Any]:
        """
        Retrieves details for a specific Airbyte connection by its ID.

        Args:
            connection_id (str): The unique identifier of the Airbyte connection.

        Returns:
            Dict[str, Any]: A dictionary containing the detailed information about the connection.

        Raises:
            ExternalServiceError: If the connection is not found or API request fails.
        """
        return await self._request("GET", f"/connections/{connection_id}")

    # =========================================================================
    # Sync Operations
    # =========================================================================

    async def trigger_sync(self, connection_id: str) -> Dict[str, Any]:
        """
        Triggers a data synchronization job for a given Airbyte connection.

        Args:
            connection_id (str): The unique identifier of the Airbyte connection to sync.

        Returns:
            Dict[str, Any]: A dictionary containing details about the triggered job,
                            including its ID, connection ID, status, and trigger timestamp.
        """
        logger.info(f"Triggering Airbyte sync for connection: {connection_id}")

        response = await self._request("POST", f"/connections/{connection_id}/sync")

        job_id = response.get("job", {}).get("id", response.get("jobId"))

        logger.info(
            f"Airbyte sync triggered: job_id={job_id} for connection {connection_id}."
        )

        return {
            "job_id": job_id,
            "connection_id": connection_id,
            "status": AirbyteJobStatus.PENDING.value,
            "triggered_at": datetime.utcnow().isoformat(),
        }

    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Retrieves the current status and metrics of an Airbyte synchronization job.

        Args:
            job_id (str): The unique identifier of the Airbyte job.

        Returns:
            Dict[str, Any]: A dictionary containing detailed job status,
                            including bytes synced, records synced, and timestamps.
        """
        response = await self._request("GET", f"/jobs/{job_id}")

        job_info = response.get("job", response)

        return {
            "job_id": job_id,
            "status": job_info.get("status", "unknown").lower(),
            "attempts": job_info.get("attempts", 0),
            "bytes_synced": job_info.get("bytesSynced", 0),
            "records_synced": job_info.get("recordsSynced", 0),
            "created_at": job_info.get("createdAt"),
            "updated_at": job_info.get("updatedAt"),
        }

    async def cancel_job(self, job_id: str) -> Dict[str, Any]:
        """
        Cancels a running Airbyte synchronization job.

        Args:
            job_id (str): The unique identifier of the Airbyte job to cancel.

        Returns:
            Dict[str, Any]: A dictionary containing the result of the cancellation request.
        """
        logger.info(f"Cancelling Airbyte job: {job_id}")
        return await self._request("DELETE", f"/jobs/{job_id}")

    async def wait_for_completion(
        self, job_id: str, poll_interval: float = 5.0, timeout: float = 3600.0
    ) -> Dict[str, Any]:
        """
        Waits for an Airbyte synchronization job to complete, polling its status periodically.

        Args:
            job_id (str): The unique identifier of the Airbyte job.
            poll_interval (float, optional): The interval (in seconds) between status checks. Defaults to 5.0.
            timeout (float, optional): The maximum time (in seconds) to wait for job completion.
                                       Defaults to 3600.0 (1 hour).

        Returns:
            Dict[str, Any]: The final status details of the completed job.

        Raises:
            TimeoutError: If the job does not complete within the specified timeout.
            ExternalServiceError: If an Airbyte API error occurs during polling.
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                raise TimeoutError(
                    f"Airbyte job {job_id} did not complete within {timeout} seconds."
                )

            status = await self.get_job_status(job_id)
            job_status = status.get("status", "unknown").lower()

            if job_status in ("succeeded", "failed", "cancelled"):
                logger.info(
                    f"Airbyte job {job_id} completed with status: {job_status}."
                )
                return status

            logger.debug(
                f"Airbyte job {job_id} status: {job_status}, waiting for completion..."
            )
            await asyncio.sleep(poll_interval)

    # =========================================================================
    # Health Check
    # =========================================================================

    async def is_healthy(self) -> bool:
        """
        Performs a health check against the Airbyte API.

        Returns:
            bool: True if the Airbyte API is reachable and returns a healthy status, False otherwise.
        """
        try:
            await self._request("GET", "/health")
            return True
        except Exception as e:
            logger.warning(f"Airbyte health check failed: {e}.")
            return False

    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """
        Retrieves the current status and metrics of the internal circuit breaker.

        Returns:
            Dict[str, Any]: A dictionary containing circuit breaker state and metrics.
                            Returns {"state": "unknown"} if the circuit breaker is not initialized.
        """
        if self._circuit_breaker:
            return self._circuit_breaker.get_metrics()
        return {"state": "unknown"}


# =============================================================================
# Global Client Instance & Convenience Functions
# =============================================================================

_global_client: Optional[AirbyteClient] = None


def get_airbyte_client(config: Optional[AirbyteClientConfig] = None) -> AirbyteClient:
    """
    Retrieves the singleton instance of the AirbyteClient.

    This factory function ensures that only one AirbyteClient is instantiated
    per application process, promoting efficient use of network resources
    and consistent configuration.

    Args:
        config (Optional[AirbyteClientConfig]): Optional configuration to use
                                                if the client is being initialized for the first time.

    Returns:
        AirbyteClient: The singleton AirbyteClient instance.
    """
    global _global_client
    if _global_client is None:
        _global_client = AirbyteClient(config)
    return _global_client


async def trigger_airbyte_sync(connection_id: str) -> Dict[str, Any]:
    """
    Convenience function to trigger an Airbyte synchronization job.

    Args:
        connection_id (str): The unique identifier of the Airbyte connection to sync.

    Returns:
        Dict[str, Any]: A dictionary containing details about the triggered job.
    """
    client = get_airbyte_client()
    return await client.trigger_sync(connection_id)


async def get_airbyte_job_status(job_id: str) -> Dict[str, Any]:
    """
    Convenience function to retrieve the status of an Airbyte synchronization job.

    Args:
        job_id (str): The unique identifier of the Airbyte job.

    Returns:
        Dict[str, Any]: A dictionary containing detailed job status.
    """
    client = get_airbyte_client()
    return await client.get_job_status(job_id)
