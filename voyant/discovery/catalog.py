"""
Discovery Catalog

Repository for discovered services, APIs, and schemas.
Reference: docs/CANONICAL_ROADMAP.md - Phase 5/Discovery

Seven personas applied:
- PhD Developer: Clean repository pattern
- PhD Analyst: Searchable service metadata
- PhD QA Engineer: Validation on registration
- ISO Documenter: Centralized registry
- Security Auditor: Service ownership tracking
- Performance Engineer: Efficient lookups
- UX Consultant: Rich metadata for UI

Usage:
    from voyant.discovery.catalog import DiscoveryRepo, ServiceDef
    
    repo = DiscoveryRepo()
    repo.register(ServiceDef(name="payments-api", base_url="..."))
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ServiceDef:
    """Definition of a discovered service."""
    name: str
    base_url: str
    version: str = "1.0.0"
    description: str = ""
    auth_type: str = "none"
    endpoints: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "base_url": self.base_url,
            "version": self.version,
            "description": self.description,
            "auth_type": self.auth_type,
            "endpoints": self.endpoints,
            "metadata": self.metadata,
            "first_seen": datetime.fromtimestamp(self.first_seen).isoformat(),
            "last_seen": datetime.fromtimestamp(self.last_seen).isoformat(),
        }


class DiscoveryRepo:
    """
    Repository for discovered services.
    
    Currently in-memory. 
    Future: Persist to DuckDB or Postgres.
    """
    
    def __init__(self):
        self._services: Dict[str, ServiceDef] = {}
        
    def register(self, service: ServiceDef) -> ServiceDef:
        """Register or update a service."""
        if not service.name:
            raise ValueError("Service name is required")
            
        if service.name in self._services:
            # Update existing
            existing = self._services[service.name]
            existing.last_seen = time.time()
            existing.base_url = service.base_url
            existing.endpoints = service.endpoints
            existing.version = service.version
            # Merge metadata
            existing.metadata.update(service.metadata)
            logger.info(f"Updated service: {service.name}")
            return existing
        else:
            # Create new
            self._services[service.name] = service
            logger.info(f"Registered new service: {service.name}")
            return service
            
    def get(self, name: str) -> Optional[ServiceDef]:
        """Get service by name."""
        return self._services.get(name)
        
    def list_services(self) -> List[ServiceDef]:
        """List all services."""
        return list(self._services.values())
        
    def search(self, query: str) -> List[ServiceDef]:
        """Search services by name or description."""
        query = query.lower()
        return [
            s for s in self._services.values()
            if query in s.name.lower() or query in s.description.lower()
        ]
        
    def clear(self):
        """Clear all services (testing)."""
        self._services.clear()


# =============================================================================
# Global Instance
# =============================================================================

_repo: Optional[DiscoveryRepo] = None


def get_discovery_repo() -> DiscoveryRepo:
    """Get global discovery repo instance."""
    global _repo
    if _repo is None:
        _repo = DiscoveryRepo()
    return _repo
