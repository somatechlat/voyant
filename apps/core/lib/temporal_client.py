"""
Temporal Client Management Module.

This module provides a standardized, singleton client for connecting to the
Temporal cluster. It ensures that only one connection to the Temporal frontend
is established and reused throughout the application's lifecycle, which is
critical for performance and resource management.
"""

import logging
from typing import Optional

from temporalio.client import Client

from apps.core.config import get_settings
from apps.core.lib.errors import ExternalServiceError

logger = logging.getLogger(__name__)

# Global singleton instance of the Temporal client.
_client: Optional[Client] = None


async def get_temporal_client() -> Client:
    """
    Get, or create and connect, a singleton Temporal client instance.

    This asynchronous function is the sole entrypoint for accessing the Temporal
    client. On its first call, it establishes a connection using settings from
    the environment. Subsequent calls return the existing connected client.

    Security Note:
        In a production environment, the connection to Temporal MUST be secured
        using TLS. This involves passing a `tls_config` argument to
        `Client.connect()` with the appropriate certificates. The default
        configuration here is suitable only for local, insecure development.

    Returns:
        A connected `temporalio.client.Client` instance.

    Raises:
        ExternalServiceError: If a connection to the Temporal server cannot be
                              established after exhausting retries.
    """
    global _client

    # If the client already exists, return it immediately.
    if _client is not None:
        return _client

    settings = get_settings()
    target_host = settings.temporal_host
    namespace = settings.temporal_namespace

    logger.info(f"Connecting to Temporal at {target_host} (namespace: {namespace})...")

    try:
        # Establish the connection to the Temporal frontend.
        _client = await Client.connect(
            target_host,
            namespace=namespace,
        )
        logger.info("Successfully connected to Temporal.")
        return _client

    except Exception as e:
        # Pragmatic error handling: temporalio's connection error types can be
        # inconsistent. We check the string representation for common network
        # failure indicators to provide a more specific application error.
        error_str = str(e).lower()
        if "connect" in error_str or "refused" in error_str or "timeout" in error_str:
            logger.error(f"Failed to connect to Temporal: {e}")
            raise ExternalServiceError(
                "VYNT-5001",
                message=f"Could not connect to Temporal Orchestrator at {target_host}",
                details={"host": target_host, "error": str(e)},
                resolution="Ensure the Temporal service is running and accessible from the application.",
            ) from e
        # For any other unexpected exception, log it and re-raise.
        logger.exception("An unexpected error occurred while connecting to Temporal.")
        raise
