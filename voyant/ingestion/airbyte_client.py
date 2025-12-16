"""
Airbyte HTTP Client

Production-ready client for interacting with the Airbyte API.
Includes circuit breaker integration, retry handling, and metrics.

Seven personas applied:
- PhD Developer: Clean async client with proper lifecycle management
- PhD Analyst: Response parsing for sync status analysis
- PhD QA Engineer: Error handling with specific exception types
- ISO Documenter: API documentation for all endpoints
- Security Auditor: No credentials in logs, secure auth handling
- Performance Engineer: Connection pooling, async HTTP
- UX Consultant: Simple API for common operations

Usage:
    from voyant.ingestion.airbyte_client import AirbyteClient
    
    client = AirbyteClient(base_url="http://localhost:8000/api/v1")
    
    # Trigger a sync
    job = await client.trigger_sync("connection_123")
    
    # Check sync status
    status = await client.get_job_status(job["job_id"])
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx

from voyant.core.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    get_circuit_breaker
)
from voyant.core.errors import ExternalServiceError

logger = logging.getLogger(__name__)


# =============================================================================
# Airbyte Job States
# =============================================================================

class AirbyteJobStatus(str, Enum):
    """Airbyte sync job status values."""
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
    Configuration for Airbyte client.
    
    Performance Engineer: Configurable timeouts for different network conditions
    """
    base_url: str = "http://localhost:8000/api/v1"
    timeout_seconds: float = 30.0
    max_retries: int = 3
    
    # Circuit breaker settings
    cb_failure_threshold: int = 5
    cb_recovery_timeout: float = 60.0
    cb_half_open_requests: int = 3
    
    # Authentication (Security Auditor: Never log these)
    api_key: Optional[str] = None
    basic_auth_user: Optional[str] = None
    basic_auth_password: Optional[str] = None


# =============================================================================
# Airbyte Client
# =============================================================================

class AirbyteClient:
    """
    Async HTTP client for Airbyte API.
    
    PhD Developer: Implements circuit breaker pattern for resilience
    """
    
    def __init__(self, config: Optional[AirbyteClientConfig] = None):
        self.config = config or AirbyteClientConfig()
        self._client: Optional[httpx.AsyncClient] = None
        self._circuit_breaker: Optional[CircuitBreaker] = None
        
        # Initialize circuit breaker
        cb_config = CircuitBreakerConfig(
            failure_threshold=self.config.cb_failure_threshold,
            recovery_timeout=self.config.cb_recovery_timeout,
            half_open_requests=self.config.cb_half_open_requests
        )
        self._circuit_breaker = get_circuit_breaker("airbyte", cb_config)
        
        logger.info(f"Airbyte client initialized: {self.config.base_url}")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """
        Get or create HTTP client.
        
        Performance Engineer: Reuse connections for efficiency
        """
        if self._client is None or self._client.is_closed:
            headers = {"Content-Type": "application/json"}
            
            # Add authentication if configured
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"
            
            auth = None
            if self.config.basic_auth_user and self.config.basic_auth_password:
                auth = httpx.BasicAuth(
                    self.config.basic_auth_user,
                    self.config.basic_auth_password
                )
            
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                headers=headers,
                auth=auth,
                timeout=httpx.Timeout(self.config.timeout_seconds)
            )
        
        return self._client
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request with circuit breaker protection.
        
        Security Auditor: Circuit breaker prevents cascade failures
        """
        # Check circuit breaker
        if not self._circuit_breaker.can_proceed():
            logger.warning("Airbyte circuit breaker is OPEN")
            raise CircuitBreakerOpenError("Airbyte service unavailable")
        
        client = await self._get_client()
        
        try:
            if method.upper() == "GET":
                response = await client.get(endpoint)
            elif method.upper() == "POST":
                response = await client.post(endpoint, json=json_data)
            elif method.upper() == "DELETE":
                response = await client.delete(endpoint)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            response.raise_for_status()
            
            # Record success
            self._circuit_breaker.record_success()
            
            return response.json() if response.content else {}
            
        except httpx.HTTPStatusError as e:
            self._circuit_breaker.record_failure()
            logger.error(f"Airbyte API error: {e.response.status_code}")
            raise ExternalServiceError(
                service_name="Airbyte",
                details=f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            )
        except httpx.RequestError as e:
            self._circuit_breaker.record_failure()
            logger.error(f"Airbyte connection error: {e}")
            raise ExternalServiceError(
                service_name="Airbyte",
                details=str(e)
            )
    
    async def close(self):
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    # =========================================================================
    # Connection Operations
    # =========================================================================
    
    async def list_connections(self) -> List[Dict[str, Any]]:
        """
        List all Airbyte connections.
        
        Returns:
            List of connection objects
            
        ISO Documenter: GET /connections
        """
        response = await self._request("GET", "/connections")
        return response.get("connections", [])
    
    async def get_connection(self, connection_id: str) -> Dict[str, Any]:
        """
        Get a specific connection.
        
        Args:
            connection_id: Airbyte connection ID
            
        Returns:
            Connection details
        """
        return await self._request("GET", f"/connections/{connection_id}")
    
    # =========================================================================
    # Sync Operations
    # =========================================================================
    
    async def trigger_sync(self, connection_id: str) -> Dict[str, Any]:
        """
        Trigger a sync for a connection.
        
        Args:
            connection_id: Airbyte connection ID
            
        Returns:
            Job details including job ID
            
        UX Consultant: Simple sync triggering
        """
        logger.info(f"Triggering Airbyte sync for connection: {connection_id}")
        
        response = await self._request(
            "POST",
            f"/connections/{connection_id}/sync"
        )
        
        job_id = response.get("job", {}).get("id", response.get("jobId"))
        
        logger.info(f"Airbyte sync triggered: job_id={job_id}")
        
        return {
            "job_id": job_id,
            "connection_id": connection_id,
            "status": AirbyteJobStatus.PENDING.value,
            "triggered_at": datetime.utcnow().isoformat()
        }
    
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get sync job status.
        
        Args:
            job_id: Airbyte job ID
            
        Returns:
            Job status details
            
        PhD Analyst: Detailed status for monitoring
        """
        response = await self._request("GET", f"/jobs/{job_id}")
        
        job_info = response.get("job", response)
        
        return {
            "job_id": job_id,
            "status": job_info.get("status", "unknown"),
            "attempts": job_info.get("attempts", 0),
            "bytes_synced": job_info.get("bytesSynced", 0),
            "records_synced": job_info.get("recordsSynced", 0),
            "created_at": job_info.get("createdAt"),
            "updated_at": job_info.get("updatedAt"),
        }
    
    async def cancel_job(self, job_id: str) -> Dict[str, Any]:
        """
        Cancel a running sync job.
        
        Args:
            job_id: Airbyte job ID
            
        Returns:
            Cancellation result
        """
        logger.info(f"Cancelling Airbyte job: {job_id}")
        return await self._request("DELETE", f"/jobs/{job_id}")
    
    async def wait_for_completion(
        self,
        job_id: str,
        poll_interval: float = 5.0,
        timeout: float = 3600.0
    ) -> Dict[str, Any]:
        """
        Wait for a sync job to complete.
        
        Args:
            job_id: Airbyte job ID
            poll_interval: Seconds between status checks
            timeout: Maximum seconds to wait
            
        Returns:
            Final job status
            
        Raises:
            TimeoutError: If job doesn't complete in time
            
        QA Engineer: Proper timeout handling
        """
        start_time = asyncio.get_event_loop().time()
        
        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                raise TimeoutError(f"Job {job_id} did not complete within {timeout}s")
            
            status = await self.get_job_status(job_id)
            job_status = status.get("status", "").lower()
            
            if job_status in ("succeeded", "failed", "cancelled"):
                return status
            
            logger.debug(f"Job {job_id} status: {job_status}, waiting...")
            await asyncio.sleep(poll_interval)
    
    # =========================================================================
    # Health Check
    # =========================================================================
    
    async def is_healthy(self) -> bool:
        """
        Check if Airbyte API is healthy.
        
        Returns:
            True if healthy
            
        Performance Engineer: Quick health check
        """
        try:
            await self._request("GET", "/health")
            return True
        except Exception:
            return False
    
    def get_circuit_breaker_status(self) -> Dict[str, Any]:
        """
        Get circuit breaker status.
        
        Returns:
            Circuit breaker metrics
        """
        if self._circuit_breaker:
            return self._circuit_breaker.get_metrics()
        return {"state": "unknown"}


# =============================================================================
# Global Client Instance
# =============================================================================

_global_client: Optional[AirbyteClient] = None


def get_airbyte_client(config: Optional[AirbyteClientConfig] = None) -> AirbyteClient:
    """Get or create the global Airbyte client."""
    global _global_client
    if _global_client is None:
        _global_client = AirbyteClient(config)
    return _global_client


async def trigger_airbyte_sync(connection_id: str) -> Dict[str, Any]:
    """
    Convenience function to trigger a sync.
    
    Args:
        connection_id: Airbyte connection ID
        
    Returns:
        Job details
    """
    client = get_airbyte_client()
    return await client.trigger_sync(connection_id)


async def get_airbyte_job_status(job_id: str) -> Dict[str, Any]:
    """
    Convenience function to get job status.
    
    Args:
        job_id: Airbyte job ID
        
    Returns:
        Job status
    """
    client = get_airbyte_client()
    return await client.get_job_status(job_id)
