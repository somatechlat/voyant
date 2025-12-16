"""
Temporal Client Module

Provides a singleton client for connecting to the Temporal cluster.
Adheres to Vibe Coding Rules: Real implementations, no mocks.
"""
import logging
from typing import Optional

from temporalio.client import Client
from temporalio.service import ConnectError

from voyant.core.config import get_settings
from voyant.core.errors import ExternalServiceError

logger = logging.getLogger(__name__)

_client: Optional[Client] = None

async def get_temporal_client() -> Client:
    """
    Get or create a Temporal client instance.
    
    Returns:
        Client: Connected Temporal client.
        
    Raises:
        ExternalServiceError: If connection fails.
    """
    global _client
    
    if _client is not None:
        return _client
        
    settings = get_settings()
    target_host = settings.temporal_host
    namespace = settings.temporal_namespace
    
    logger.info(f"Connecting to Temporal at {target_host} (namespace: {namespace})...")
    
    try:
        # Connect to Temporal server
        # In production, we might need TLS config here
        _client = await Client.connect(
            target_host,
            namespace=namespace,
        )
        logger.info("Successfully connected to Temporal.")
        return _client
        
    except ConnectError as e:
        logger.error(f"Failed to connect to Temporal: {e}")
        raise ExternalServiceError(
            "VYNT-5001",
            message=f"Could not connect to Temporal Orchestrator at {target_host}",
            details={"host": target_host, "error": str(e)},
            resolution="Ensure Temporal service is running and accessible."
        )
    except Exception as e:
        logger.exception("Unexpected error connecting to Temporal")
        raise
