"""
Baseline Version Store Module

Versioned storage for baselines (quality, drift, profiles).
Reference: docs/CANONICAL_ROADMAP.md - P5 Governance & Contracts

Features:
- Version all baselines with semantic versioning
- Store drift comparison history
- Link baselines to data contracts
- Automatic baseline promotion

Usage:
    from voyant.core.baseline_store import (
        BaselineStore, get_baseline_store,
        create_baseline, get_latest_baseline, compare_baselines
    )
    
    store = get_baseline_store()
    
    # Create a new baseline
    baseline = await store.create(
        tenant_id="acme",
        source_id="orders",
        baseline_type="quality",
        data={"expectations": [...]}
    )
    
    # Get latest baseline
    latest = await store.get_latest("acme", "orders", "quality")
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


class BaselineType(str, Enum):
    """Types of baselines that can be stored."""
    QUALITY = "quality"          # Data quality expectations (Great Expectations)
    DRIFT = "drift"              # Drift detection reference (Evidently)
    PROFILE = "profile"          # Data profile snapshot (ydata-profiling)
    SCHEMA = "schema"            # Schema snapshot
    CONTRACT = "contract"        # Data contract version


class BaselineStatus(str, Enum):
    """Baseline lifecycle status."""
    DRAFT = "draft"              # Created but not validated
    ACTIVE = "active"            # Current active baseline
    DEPRECATED = "deprecated"    # Replaced by newer version
    ARCHIVED = "archived"        # No longer in use


@dataclass
class Baseline:
    """A versioned baseline record."""
    baseline_id: str
    tenant_id: str
    source_id: str
    baseline_type: BaselineType
    version: str  # Semantic version (e.g., "1.0.0")
    
    # Content
    data: Dict[str, Any]
    checksum: str  # SHA-256 of data
    
    # Metadata
    status: BaselineStatus = BaselineStatus.DRAFT
    description: str = ""
    created_at: float = 0
    created_by: str = ""
    parent_version: Optional[str] = None
    
    # Contract linkage
    contract_name: Optional[str] = None
    contract_version: Optional[str] = None
    
    # Drift tracking
    drift_from_parent: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.created_at == 0:
            self.created_at = time.time()
        if not self.checksum:
            self.checksum = self._compute_checksum()
    
    def _compute_checksum(self) -> str:
        """Compute SHA-256 checksum of data."""
        data_str = json.dumps(self.data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "baseline_id": self.baseline_id,
            "tenant_id": self.tenant_id,
            "source_id": self.source_id,
            "baseline_type": self.baseline_type.value,
            "version": self.version,
            "data": self.data,
            "checksum": self.checksum,
            "status": self.status.value,
            "description": self.description,
            "created_at": datetime.fromtimestamp(self.created_at).isoformat(),
            "created_by": self.created_by,
            "parent_version": self.parent_version,
            "contract_name": self.contract_name,
            "contract_version": self.contract_version,
            "drift_from_parent": self.drift_from_parent,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Baseline":
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at).timestamp()
        
        return cls(
            baseline_id=data["baseline_id"],
            tenant_id=data["tenant_id"],
            source_id=data["source_id"],
            baseline_type=BaselineType(data["baseline_type"]),
            version=data["version"],
            data=data["data"],
            checksum=data.get("checksum", ""),
            status=BaselineStatus(data.get("status", "draft")),
            description=data.get("description", ""),
            created_at=created_at or time.time(),
            created_by=data.get("created_by", ""),
            parent_version=data.get("parent_version"),
            contract_name=data.get("contract_name"),
            contract_version=data.get("contract_version"),
            drift_from_parent=data.get("drift_from_parent"),
        )


class InMemoryBaselineStore:
    """
    In-memory baseline store implementation.
    
    For production, use PostgreSQL or S3-backed implementation.
    """
    
    def __init__(self):
        # Key: (tenant_id, source_id, baseline_type, version)
        self._baselines: Dict[Tuple[str, str, str, str], Baseline] = {}
        self._counter = 0
    
    def _generate_id(self) -> str:
        """Generate unique baseline ID."""
        self._counter += 1
        return f"bl_{int(time.time())}_{self._counter:04d}"
    
    def _get_key(self, tenant_id: str, source_id: str, baseline_type: str, version: str) -> Tuple:
        return (tenant_id, source_id, baseline_type, version)
    
    async def create(
        self,
        tenant_id: str,
        source_id: str,
        baseline_type: BaselineType,
        data: Dict[str, Any],
        description: str = "",
        created_by: str = "",
        contract_name: Optional[str] = None,
        contract_version: Optional[str] = None,
    ) -> Baseline:
        """
        Create a new baseline version.
        
        Automatically increments version number.
        """
        # Get latest version to determine next version
        latest = await self.get_latest(tenant_id, source_id, baseline_type)
        
        if latest:
            # Increment patch version (simple for now)
            parts = latest.version.split(".")
            parts[-1] = str(int(parts[-1]) + 1)
            new_version = ".".join(parts)
            parent_version = latest.version
            
            # Compute drift from parent
            drift = self._compute_drift(latest.data, data)
        else:
            new_version = "1.0.0"
            parent_version = None
            drift = None
        
        baseline = Baseline(
            baseline_id=self._generate_id(),
            tenant_id=tenant_id,
            source_id=source_id,
            baseline_type=baseline_type,
            version=new_version,
            data=data,
            checksum="",  # Will be computed in __post_init__
            description=description,
            created_by=created_by,
            parent_version=parent_version,
            contract_name=contract_name,
            contract_version=contract_version,
            drift_from_parent=drift,
        )
        
        key = self._get_key(tenant_id, source_id, baseline_type.value, new_version)
        self._baselines[key] = baseline
        
        logger.info(f"Created baseline {baseline.baseline_id} v{new_version} for {source_id}")
        return baseline
    
    async def get(
        self,
        tenant_id: str,
        source_id: str,
        baseline_type: BaselineType,
        version: str,
    ) -> Optional[Baseline]:
        """Get a specific baseline version."""
        key = self._get_key(tenant_id, source_id, baseline_type.value, version)
        return self._baselines.get(key)
    
    async def get_latest(
        self,
        tenant_id: str,
        source_id: str,
        baseline_type: BaselineType,
    ) -> Optional[Baseline]:
        """Get the latest baseline version."""
        matching = [
            b for b in self._baselines.values()
            if b.tenant_id == tenant_id
            and b.source_id == source_id
            and b.baseline_type == baseline_type
        ]
        
        if not matching:
            return None
        
        # Sort by version (semantic versioning)
        matching.sort(key=lambda b: [int(p) for p in b.version.split(".")], reverse=True)
        return matching[0]
    
    async def list_versions(
        self,
        tenant_id: str,
        source_id: str,
        baseline_type: BaselineType,
    ) -> List[Dict[str, Any]]:
        """List all versions of a baseline."""
        matching = [
            b for b in self._baselines.values()
            if b.tenant_id == tenant_id
            and b.source_id == source_id
            and b.baseline_type == baseline_type
        ]
        
        matching.sort(key=lambda b: [int(p) for p in b.version.split(".")], reverse=True)
        
        return [
            {
                "version": b.version,
                "status": b.status.value,
                "created_at": datetime.fromtimestamp(b.created_at).isoformat(),
                "checksum": b.checksum,
                "parent_version": b.parent_version,
            }
            for b in matching
        ]
    
    async def activate(
        self,
        tenant_id: str,
        source_id: str,
        baseline_type: BaselineType,
        version: str,
    ) -> bool:
        """Activate a baseline version (deprecates previous active)."""
        key = self._get_key(tenant_id, source_id, baseline_type.value, version)
        baseline = self._baselines.get(key)
        
        if not baseline:
            return False
        
        # Deprecate current active
        for b in self._baselines.values():
            if (b.tenant_id == tenant_id
                and b.source_id == source_id
                and b.baseline_type == baseline_type
                and b.status == BaselineStatus.ACTIVE):
                b.status = BaselineStatus.DEPRECATED
        
        baseline.status = BaselineStatus.ACTIVE
        logger.info(f"Activated baseline {source_id} v{version}")
        return True
    
    async def compare(
        self,
        tenant_id: str,
        source_id: str,
        baseline_type: BaselineType,
        version_a: str,
        version_b: str,
    ) -> Dict[str, Any]:
        """Compare two baseline versions."""
        baseline_a = await self.get(tenant_id, source_id, baseline_type, version_a)
        baseline_b = await self.get(tenant_id, source_id, baseline_type, version_b)
        
        if not baseline_a or not baseline_b:
            return {"error": "Baseline not found"}
        
        return {
            "version_a": version_a,
            "version_b": version_b,
            "drift": self._compute_drift(baseline_a.data, baseline_b.data),
            "checksum_changed": baseline_a.checksum != baseline_b.checksum,
        }
    
    def _compute_drift(self, old_data: Dict, new_data: Dict) -> Dict[str, Any]:
        """Compute simple drift between two baselines."""
        old_keys = set(old_data.keys())
        new_keys = set(new_data.keys())
        
        return {
            "added_keys": list(new_keys - old_keys),
            "removed_keys": list(old_keys - new_keys),
            "common_keys": len(old_keys & new_keys),
            "total_keys_old": len(old_keys),
            "total_keys_new": len(new_keys),
        }
    
    async def get_drift_lineage(
        self,
        tenant_id: str,
        source_id: str,
        baseline_type: BaselineType,
    ) -> List[Dict[str, Any]]:
        """Get drift lineage for a baseline (version history with drift)."""
        versions = await self.list_versions(tenant_id, source_id, baseline_type)
        
        lineage = []
        for v_info in versions:
            baseline = await self.get(tenant_id, source_id, baseline_type, v_info["version"])
            if baseline:
                lineage.append({
                    "version": baseline.version,
                    "parent_version": baseline.parent_version,
                    "drift_from_parent": baseline.drift_from_parent,
                    "created_at": datetime.fromtimestamp(baseline.created_at).isoformat(),
                })
        
        return lineage
    
    async def clear_tenant(self, tenant_id: str) -> int:
        """Clear all baselines for a tenant (testing)."""
        to_remove = [
            key for key, b in self._baselines.items()
            if b.tenant_id == tenant_id
        ]
        for key in to_remove:
            del self._baselines[key]
        return len(to_remove)


# =============================================================================
# Singleton
# =============================================================================

_baseline_store: Optional[InMemoryBaselineStore] = None


def get_baseline_store() -> InMemoryBaselineStore:
    """Get or create the global baseline store instance."""
    global _baseline_store
    if _baseline_store is None:
        _baseline_store = InMemoryBaselineStore()
        logger.info("Initialized baseline store")
    return _baseline_store


def reset_baseline_store():
    """Reset the global baseline store (testing)."""
    global _baseline_store
    _baseline_store = None
