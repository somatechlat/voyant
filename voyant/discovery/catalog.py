"""
Discovery Catalog: Repository for Discovered Services and APIs.

This module implements a repository pattern for managing `ServiceDef` objects,
which represent discovered external services and their API specifications.
It currently maintains an in-memory catalog, allowing for registration, retrieval,
listing, and searching of services.

Architectural Note:
While currently in-memory, the `DiscoveryRepo` is designed to be extensible
and can be evolved to persist service definitions to a database (e.g., DuckDB,
PostgreSQL) for long-term storage and scalability.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from voyant.discovery.models import ApiEndpoint, ApiSpec

logger = logging.getLogger(__name__)


@dataclass
class ServiceDef:
    """
    Represents a definition of a discovered external service.

    Attributes:
        name (str): A unique identifier for the service (e.g., "Payments API").
        base_url (str): The base URL where the service's API can be accessed.
        version (str): The version of the service's API (e.g., "1.0.0").
        description (str): A human-readable description of the service.
        auth_type (str): The type of authentication the service uses (e.g., "OAuth2", "API_KEY").
        endpoints (List[Dict[str, str]]): A list of dictionaries, each describing an API endpoint.
                                           Derived from parsing the service's OpenAPI specification.
        metadata (Dict[str, str]): Additional metadata associated with the service.
        first_seen (float): Unix timestamp indicating when the service was first discovered.
        last_seen (float): Unix timestamp indicating when the service was last seen or updated.
    """

    name: str
    base_url: str
    version: str = "1.0.0"
    description: str = ""
    auth_type: str = "none"
    endpoints: List[ApiEndpoint] = field(default_factory=list) # Changed type from Dict[str,str] to ApiEndpoint
    metadata: Dict[str, str] = field(default_factory=dict)
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        """
        Converts the ServiceDef object into a dictionary for serialization.
        """
        return {
            "name": self.name,
            "base_url": self.base_url,
            "version": self.version,
            "description": self.description,
            "auth_type": self.auth_type,
            "endpoints": [e.to_dict() for e in self.endpoints], # Updated to call to_dict() on ApiEndpoint
            "metadata": self.metadata,
            "first_seen": datetime.fromtimestamp(self.first_seen).isoformat(),
            "last_seen": datetime.fromtimestamp(self.last_seen).isoformat(),
        }


class DiscoveryRepo:
    """
    An in-memory repository for managing discovered services.

    This class provides methods to register, retrieve, list, and search `ServiceDef` objects.
    It currently acts as an in-memory cache but is designed to be extensible for
    persistence to a database in future iterations.
    """

    def __init__(self):
        """
        Initializes the DiscoveryRepo.
        """
        self._services: Dict[str, ServiceDef] = {}

    def register(self, service: ServiceDef) -> ServiceDef:
        """
        Registers a new service or updates an existing one in the repository.

        Args:
            service (ServiceDef): The `ServiceDef` object to register or update.

        Returns:
            ServiceDef: The registered or updated `ServiceDef` object.

        Raises:
            ValueError: If the service name is empty.
        """
        if not service.name:
            raise ValueError("Service name is required for registration.")

        if service.name in self._services:
            # Update existing service definition.
            existing = self._services[service.name]
            existing.last_seen = time.time()
            existing.base_url = service.base_url
            existing.endpoints = service.endpoints
            existing.version = service.version
            existing.metadata.update(service.metadata)  # Merge new metadata.
            logger.info(f"Updated service definition for: '{service.name}'.")
            return existing
        else:
            # Register a new service.
            self._services[service.name] = service
            logger.info(f"Registered new service: '{service.name}'.")
            return service

    def get(self, name: str) -> Optional[ServiceDef]:
        """
        Retrieves a service definition by its unique name.

        Args:
            name (str): The unique name of the service.

        Returns:
            Optional[ServiceDef]: The `ServiceDef` object if found, otherwise None.
        """
        return self._services.get(name)

    def list_services(self) -> List[ServiceDef]:
        """
        Lists all service definitions currently registered in the repository.

        Returns:
            List[ServiceDef]: A list of all `ServiceDef` objects.
        """
        return list(self._services.values())

    def search(self, query: str) -> List[ServiceDef]:
        """
        Searches for services by matching a query against their name or description.

        Args:
            query (str): The search string.

        Returns:
            List[ServiceDef]: A list of `ServiceDef` objects that match the query.
        """
        query = query.lower()
        return [
            s
            for s in self._services.values()
            if query in s.name.lower() or query in s.description.lower()
        ]

    def clear(self):
        """
        Clears all service definitions from the repository.

        This method is primarily intended for use in testing environments to
        ensure a clean state between test runs.
        """
        self._services.clear()


# =============================================================================
# Global Instance
# =============================================================================

_repo: Optional[DiscoveryRepo] = None


def get_discovery_repo() -> DiscoveryRepo:
    """
    Retrieves the singleton instance of the `DiscoveryRepo`.

    This factory function ensures that only one `DiscoveryRepo` is instantiated
    per application process, acting as a centralized registry.

    Returns:
        DiscoveryRepo: The singleton `DiscoveryRepo` instance.
    """
    global _repo
    if _repo is None:
        _repo = DiscoveryRepo()
    return _repo
