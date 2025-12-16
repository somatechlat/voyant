"""
Content-Addressable Artifact Store

Efficient artifact storage using content hashing for deduplication.
Reference: docs/CANONICAL_ROADMAP.md - Future Investigation Backlog

Seven personas applied:
- PhD Developer: Clean content hashing with pluggable backends
- PhD Analyst: Artifact metadata and lineage tracking
- PhD QA Engineer: Integrity verification with checksums
- ISO Documenter: Clear storage format documentation
- Security Auditor: Tamper detection via hash verification
- Performance Engineer: Deduplication, compression, lazy loading
- UX Consultant: Simple store/retrieve API

Usage:
    from voyant.core.artifact_store import (
        ArtifactStore,
        store_artifact,
        retrieve_artifact,
        verify_artifact
    )
    
    # Store an artifact
    ref = store_artifact(
        content=data_bytes,
        artifact_type="profile",
        metadata={"job_id": "123"}
    )
    print(ref.hash)  # "sha256:abc123..."
    
    # Retrieve
    content = retrieve_artifact(ref.hash)
    
    # Verify integrity
    is_valid = verify_artifact(ref.hash)
"""
from __future__ import annotations

import gzip
import hashlib
import json
import logging
import os
import shutil
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

class HashAlgorithm(str, Enum):
    """Supported hash algorithms."""
    SHA256 = "sha256"
    SHA512 = "sha512"
    BLAKE2B = "blake2b"


class CompressionType(str, Enum):
    """Supported compression types."""
    NONE = "none"
    GZIP = "gzip"


@dataclass
class StoreConfig:
    """
    Configuration for artifact store.
    
    Performance Engineer: Tunable for different workloads
    """
    base_path: str = "./artifacts"
    hash_algorithm: HashAlgorithm = HashAlgorithm.SHA256
    compression: CompressionType = CompressionType.GZIP
    
    # Sharding for large stores
    shard_depth: int = 2  # Number of subdirectory levels
    shard_width: int = 2  # Characters per shard level
    
    # Deduplication
    enable_dedup: bool = True
    
    # Metadata
    store_metadata: bool = True
    
    # Limits
    max_artifact_size_mb: int = 100
    
    def get_storage_path(self, hash_value: str) -> Path:
        """Get storage path for a hash."""
        shards = []
        for i in range(self.shard_depth):
            start = i * self.shard_width
            end = start + self.shard_width
            shards.append(hash_value[start:end])
        
        return Path(self.base_path) / Path(*shards) / hash_value


# =============================================================================
# Artifact Reference
# =============================================================================

@dataclass
class ArtifactRef:
    """
    Reference to a stored artifact.
    
    Security Auditor: Content-addressable means tamper-evident
    """
    hash: str  # "algorithm:hash" format
    size_bytes: int
    artifact_type: str
    compression: CompressionType
    created_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat() + "Z"
    
    @property
    def algorithm(self) -> str:
        return self.hash.split(":")[0]
    
    @property
    def hash_value(self) -> str:
        return self.hash.split(":")[1] if ":" in self.hash else self.hash
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "hash": self.hash,
            "size_bytes": self.size_bytes,
            "artifact_type": self.artifact_type,
            "compression": self.compression.value,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ArtifactRef":
        return cls(
            hash=data["hash"],
            size_bytes=data["size_bytes"],
            artifact_type=data["artifact_type"],
            compression=CompressionType(data.get("compression", "none")),
            created_at=data.get("created_at", ""),
            metadata=data.get("metadata", {}),
        )


# =============================================================================
# Artifact Store
# =============================================================================

class ArtifactStore:
    """
    Content-addressable artifact store.
    
    PhD Developer: Clean storage abstraction with deduplication
    """
    
    def __init__(self, config: Optional[StoreConfig] = None):
        self.config = config or StoreConfig()
        self._lock = threading.RLock()
        self._refs: Dict[str, ArtifactRef] = {}
        
        # Ensure base path exists
        Path(self.config.base_path).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Artifact store initialized: {self.config.base_path}")
    
    def _compute_hash(self, content: bytes) -> str:
        """
        Compute hash of content.
        
        Security Auditor: Cryptographic hash for integrity
        """
        if self.config.hash_algorithm == HashAlgorithm.SHA256:
            h = hashlib.sha256(content)
        elif self.config.hash_algorithm == HashAlgorithm.SHA512:
            h = hashlib.sha512(content)
        elif self.config.hash_algorithm == HashAlgorithm.BLAKE2B:
            h = hashlib.blake2b(content)
        else:
            h = hashlib.sha256(content)
        
        return f"{self.config.hash_algorithm.value}:{h.hexdigest()}"
    
    def _compress(self, content: bytes) -> bytes:
        """Compress content if configured."""
        if self.config.compression == CompressionType.GZIP:
            return gzip.compress(content)
        return content
    
    def _decompress(self, content: bytes, compression: CompressionType) -> bytes:
        """Decompress content."""
        if compression == CompressionType.GZIP:
            return gzip.decompress(content)
        return content
    
    def store(
        self,
        content: bytes,
        artifact_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ArtifactRef:
        """
        Store an artifact.
        
        Args:
            content: Raw artifact content
            artifact_type: Type of artifact (profile, chart, etc.)
            metadata: Optional metadata
            
        Returns:
            ArtifactRef pointing to stored content
            
        Performance Engineer: Deduplication via content hash
        """
        # Check size limit
        size_mb = len(content) / (1024 * 1024)
        if size_mb > self.config.max_artifact_size_mb:
            raise ValueError(
                f"Artifact size {size_mb:.1f}MB exceeds limit {self.config.max_artifact_size_mb}MB"
            )
        
        # Compute hash
        content_hash = self._compute_hash(content)
        hash_value = content_hash.split(":")[1]
        
        with self._lock:
            # Check for existing (deduplication)
            if self.config.enable_dedup and content_hash in self._refs:
                logger.debug(f"Artifact deduplicated: {content_hash[:24]}...")
                return self._refs[content_hash]
            
            # Compress
            compressed = self._compress(content)
            
            # Get storage path
            storage_path = self.config.get_storage_path(hash_value)
            storage_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write content
            content_file = storage_path.with_suffix(".bin")
            with open(content_file, "wb") as f:
                f.write(compressed)
            
            # Create reference
            ref = ArtifactRef(
                hash=content_hash,
                size_bytes=len(content),
                artifact_type=artifact_type,
                compression=self.config.compression,
                metadata=metadata or {},
            )
            
            # Write metadata
            if self.config.store_metadata:
                meta_file = storage_path.with_suffix(".json")
                with open(meta_file, "w") as f:
                    json.dump(ref.to_dict(), f, indent=2)
            
            # Cache reference
            self._refs[content_hash] = ref
            
            logger.info(f"Stored artifact: {content_hash[:24]}... ({len(content)} bytes)")
            
            return ref
    
    def retrieve(self, hash_value: str) -> Optional[bytes]:
        """
        Retrieve artifact content by hash.
        
        Args:
            hash_value: Full hash ("algo:hash") or just hash
            
        Returns:
            Raw content or None if not found
        """
        # Parse hash
        if ":" in hash_value:
            hash_only = hash_value.split(":")[1]
        else:
            hash_only = hash_value
        
        with self._lock:
            # Get storage path
            storage_path = self.config.get_storage_path(hash_only)
            content_file = storage_path.with_suffix(".bin")
            
            if not content_file.exists():
                logger.warning(f"Artifact not found: {hash_value[:24]}...")
                return None
            
            # Read content
            with open(content_file, "rb") as f:
                compressed = f.read()
            
            # Get compression type from metadata or use default
            ref = self._refs.get(hash_value)
            compression = ref.compression if ref else self.config.compression
            
            # Decompress
            content = self._decompress(compressed, compression)
            
            return content
    
    def verify(self, hash_value: str) -> bool:
        """
        Verify artifact integrity.
        
        Args:
            hash_value: Hash to verify
            
        Returns:
            True if content matches hash
            
        PhD QA Engineer: Ensure data integrity
        """
        content = self.retrieve(hash_value)
        if content is None:
            return False
        
        expected = hash_value if ":" in hash_value else f"sha256:{hash_value}"
        actual = self._compute_hash(content)
        
        return expected == actual
    
    def get_ref(self, hash_value: str) -> Optional[ArtifactRef]:
        """Get artifact reference without retrieving content."""
        if ":" in hash_value:
            return self._refs.get(hash_value)
        
        # Try to find by hash only
        for key, ref in self._refs.items():
            if ref.hash_value == hash_value:
                return ref
        
        # Try loading from disk
        storage_path = self.config.get_storage_path(hash_value)
        meta_file = storage_path.with_suffix(".json")
        
        if meta_file.exists():
            with open(meta_file) as f:
                data = json.load(f)
                return ArtifactRef.from_dict(data)
        
        return None
    
    def delete(self, hash_value: str) -> bool:
        """
        Delete an artifact.
        
        Args:
            hash_value: Hash to delete
            
        Returns:
            True if deleted
        """
        if ":" in hash_value:
            hash_only = hash_value.split(":")[1]
        else:
            hash_only = hash_value
        
        with self._lock:
            storage_path = self.config.get_storage_path(hash_only)
            
            deleted = False
            for suffix in [".bin", ".json"]:
                file_path = storage_path.with_suffix(suffix)
                if file_path.exists():
                    file_path.unlink()
                    deleted = True
            
            # Remove from cache
            to_remove = [k for k in self._refs if hash_only in k]
            for k in to_remove:
                del self._refs[k]
            
            return deleted
    
    def list_artifacts(
        self,
        artifact_type: Optional[str] = None,
        limit: int = 100
    ) -> List[ArtifactRef]:
        """
        List stored artifacts.
        
        Args:
            artifact_type: Filter by type
            limit: Maximum number to return
            
        Returns:
            List of artifact references
        """
        refs = list(self._refs.values())
        
        if artifact_type:
            refs = [r for r in refs if r.artifact_type == artifact_type]
        
        # Sort by creation time (newest first)
        refs.sort(key=lambda r: r.created_at, reverse=True)
        
        return refs[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get store statistics."""
        with self._lock:
            total_size = sum(r.size_bytes for r in self._refs.values())
            by_type: Dict[str, int] = {}
            for ref in self._refs.values():
                by_type[ref.artifact_type] = by_type.get(ref.artifact_type, 0) + 1
        
        return {
            "total_artifacts": len(self._refs),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "by_type": by_type,
            "dedup_enabled": self.config.enable_dedup,
            "compression": self.config.compression.value,
        }
    
    def gc(self, keep_hashes: Optional[set] = None) -> int:
        """
        Garbage collect unreferenced artifacts.
        
        Args:
            keep_hashes: Set of hashes to keep
            
        Returns:
            Number of artifacts removed
        """
        if keep_hashes is None:
            return 0
        
        removed = 0
        to_delete = []
        
        with self._lock:
            for hash_val in self._refs:
                if hash_val not in keep_hashes and hash_val.split(":")[1] not in keep_hashes:
                    to_delete.append(hash_val)
        
        for hash_val in to_delete:
            if self.delete(hash_val):
                removed += 1
        
        logger.info(f"Garbage collected {removed} artifacts")
        return removed


# =============================================================================
# Global Instance
# =============================================================================

_artifact_store: Optional[ArtifactStore] = None
_store_lock = threading.Lock()


def get_artifact_store(config: Optional[StoreConfig] = None) -> ArtifactStore:
    """Get or create global artifact store."""
    global _artifact_store
    if _artifact_store is None:
        with _store_lock:
            if _artifact_store is None:
                _artifact_store = ArtifactStore(config)
    return _artifact_store


# =============================================================================
# Convenience Functions
# =============================================================================

def store_artifact(
    content: Union[bytes, str, Dict[str, Any]],
    artifact_type: str,
    metadata: Optional[Dict[str, Any]] = None
) -> ArtifactRef:
    """
    Store an artifact.
    
    Args:
        content: Content (bytes, string, or dict)
        artifact_type: Type of artifact
        metadata: Optional metadata
        
    Returns:
        ArtifactRef
        
    UX Consultant: Simple store API
    """
    # Convert to bytes
    if isinstance(content, str):
        content_bytes = content.encode("utf-8")
    elif isinstance(content, dict):
        content_bytes = json.dumps(content, indent=2).encode("utf-8")
    else:
        content_bytes = content
    
    return get_artifact_store().store(content_bytes, artifact_type, metadata)


def retrieve_artifact(hash_value: str) -> Optional[bytes]:
    """Retrieve artifact content."""
    return get_artifact_store().retrieve(hash_value)


def verify_artifact(hash_value: str) -> bool:
    """Verify artifact integrity."""
    return get_artifact_store().verify(hash_value)


def get_artifact_ref(hash_value: str) -> Optional[ArtifactRef]:
    """Get artifact reference."""
    return get_artifact_store().get_ref(hash_value)


def list_artifacts(artifact_type: Optional[str] = None) -> List[ArtifactRef]:
    """List stored artifacts."""
    return get_artifact_store().list_artifacts(artifact_type)


def get_store_stats() -> Dict[str, Any]:
    """Get artifact store statistics."""
    return get_artifact_store().get_stats()
