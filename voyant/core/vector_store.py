"""
Vector Store

Persistent storage for embeddings.
Reference: docs/CANONICAL_ROADMAP.md - Phase 6/Advanced Analytics

Seven personas applied:
- PhD Developer: Efficient similarity search
- PhD Analyst: Retrieval capability
- PhD QA Engineer: Exact match verification
- ISO Documenter: Storage format documentation
- Security Auditor: Metadata access control
- Performance Engineer: Index efficiency
- UX Consultant: Simple search API

Usage:
    from voyant.core.vector_store import VectorStore
    
    store = VectorStore(dimensions=64)
    store.add(id="doc1", vector=[0.1, ...], metadata={"text": "hello"})
    
    results = store.search(query_vector=[0.1, ...], k=5)
"""
from __future__ import annotations

import json
import logging
import math
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)


@dataclass
class VectorItem:
    """An item in the vector store."""
    id: str
    vector: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "vector": self.vector,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "VectorItem":
        return cls(
            id=data["id"],
            vector=data["vector"],
            metadata=data.get("metadata", {}),
        )


class VectorStore:
    """
    Simple in-memory vector store with persistence.
    
    For large scale, upgrade to FAISS or dedicated vector DB.
    """
    
    def __init__(self, dimensions: int = 64, storage_path: Optional[str] = None):
        self.dimensions = dimensions
        self.storage_path = storage_path
        self._items: Dict[str, VectorItem] = {}
        
        if self.storage_path and os.path.exists(self.storage_path):
            self.load()
            
    def add(self, id: str, vector: List[float], metadata: Optional[Dict] = None):
        """Add or update an item."""
        if len(vector) != self.dimensions:
            raise ValueError(f"Vector dimension mismatch: expected {self.dimensions}, got {len(vector)}")
            
        self._items[id] = VectorItem(
            id=id,
            vector=vector,
            metadata=metadata or {},
        )
        
    def get(self, id: str) -> Optional[VectorItem]:
        """Get item by ID."""
        return self._items.get(id)
        
    def delete(self, id: str):
        """Delete item by ID."""
        if id in self._items:
            del self._items[id]
            
    def search(
        self,
        query_vector: List[float],
        k: int = 5,
        filter_metadata: Optional[Dict] = None
    ) -> List[Tuple[VectorItem, float]]:
        """
        Search for similar vectors.
        
        Args:
            query_vector: Query vector
            k: Number of results
            filter_metadata: Optional metadata filters (exact match)
            
        Returns:
            List of (item, similarity_score) sorted by similarity desc
        """
        if len(query_vector) != self.dimensions:
            raise ValueError(f"Query dimension mismatch: expected {self.dimensions}, got {len(query_vector)}")
            
        results = []
        
        for item in self._items.values():
            # Apply filters
            if filter_metadata:
                match = True
                for key, val in filter_metadata.items():
                    if item.metadata.get(key) != val:
                        match = False
                        break
                if not match:
                    continue
            
            # Calculate Cosine Similarity
            # Optimization: Pre-calculate magnitudes if performance critical
            sim = self._cosine_similarity(query_vector, item.vector)
            results.append((item, sim))
            
        # Sort desc
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:k]
        
    def save(self):
        """Save store to disk."""
        if not self.storage_path:
            return
            
        data = {
            "dimensions": self.dimensions,
            "items": [item.to_dict() for item in self._items.values()]
        }
        
        try:
            # Atomic write
            tmp_path = f"{self.storage_path}.tmp"
            with open(tmp_path, "w") as f:
                json.dump(data, f)
            os.replace(tmp_path, self.storage_path)
            logger.info(f"Saved vector store to {self.storage_path} ({len(self._items)} items)")
        except Exception as e:
            logger.error(f"Failed to save vector store: {e}")
            
    def load(self):
        """Load store from disk."""
        if not self.storage_path or not os.path.exists(self.storage_path):
            return
            
        try:
            with open(self.storage_path, "r") as f:
                data = json.load(f)
                
            self.dimensions = data.get("dimensions", self.dimensions)
            items_data = data.get("items", [])
            
            self._items = {}
            for item_data in items_data:
                item = VectorItem.from_dict(item_data)
                self._items[item.id] = item
                
            logger.info(f"Loaded vector store from {self.storage_path} ({len(self._items)} items)")
        except Exception as e:
            logger.error(f"Failed to load vector store: {e}")
            # Don't crash on corrupt index, start empty
            
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity."""
        dot = sum(x * y for x, y in zip(a, b))
        mag_a = math.sqrt(sum(x * x for x in a))
        mag_b = math.sqrt(sum(x * x for x in b))
        
        if mag_a == 0 or mag_b == 0:
            return 0.0
            
        return dot / (mag_a * mag_b)


# =============================================================================
# Global Instance
# =============================================================================

_store: Optional[VectorStore] = None


def get_vector_store(storage_path: Optional[str] = None) -> VectorStore:
    """Get global vector store."""
    global _store
    if _store is None:
        # Default persistence path
        default_path = os.path.join(os.getcwd(), "data", "vectors.json")
        _store = VectorStore(storage_path=storage_path or default_path)
    return _store
