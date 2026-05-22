"""
Milvus-backed vector store — the sole vector storage engine for Voyant.

Production-grade vector storage with hybrid search (dense + sparse),
tenant isolation via partition keys, and resilient connection management.

No fallback. No legacy JSON store. Milvus is the only backend.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from pymilvus import (
    CollectionSchema,
    DataType,
    FieldSchema,
    MilvusClient,
    MilvusException,
)

logger = logging.getLogger(__name__)

_COLLECTION_NAME = "voyant_documents"
_DENSE_DIM = 1536

# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class VectorItem:
    """A single document in the vector store."""

    id: str
    vector: List[float]
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_FIELDS = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    FieldSchema(name="doc_id", dtype=DataType.VARCHAR, max_length=256),
    FieldSchema(
        name="tenant_id",
        dtype=DataType.VARCHAR,
        max_length=64,
        is_partition_key=True,
    ),
    FieldSchema(name="realm", dtype=DataType.VARCHAR, max_length=64),
    FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=_DENSE_DIM),
    FieldSchema(name="sparse_embedding", dtype=DataType.SPARSE_FLOAT_VECTOR),
    FieldSchema(name="metadata", dtype=DataType.JSON),
    FieldSchema(name="source_type", dtype=DataType.VARCHAR, max_length=32),
    FieldSchema(name="created_at", dtype=DataType.INT64),
]

_SCHEMA = CollectionSchema(
    _FIELDS,
    description="Voyant semantic search documents with hybrid vectors",
    enable_dynamic_field=False,
)


# ---------------------------------------------------------------------------
# Resilient Milvus client
# ---------------------------------------------------------------------------

class _MilvusConnection:
    """Lazy, resilient Milvus connection manager."""

    def __init__(self) -> None:
        self._client: Optional[MilvusClient] = None
        self._last_fail: float = 0.0
        self._backoff: float = 1.0

    def _settings(self) -> Dict[str, Any]:
        # Delayed import so Django settings are ready.
        from apps.core.config import get_settings

        s = get_settings()
        uri = s.milvus_uri or f"http://{s.milvus_host}:{s.milvus_port}"
        return {
            "uri": uri,
            "token": s.milvus_token or None,
            "db_name": s.milvus_db_name or "default",
            "auto_create": s.milvus_auto_create,
        }

    def client(self) -> MilvusClient:
        """Return a live MilvusClient, reconnecting if necessary."""
        if self._client is not None:
            try:
                self._client.list_collections()
                self._backoff = 1.0
                return self._client
            except Exception:
                self._client = None

        cfg = self._settings()
        now = time.time()
        if now - self._last_fail < self._backoff:
            raise MilvusException(
                message=f"Milvus connection cooling down ({self._backoff:.1f}s)"
            )

        try:
            self._client = MilvusClient(
                uri=cfg["uri"],
                token=cfg["token"],
                db_name=cfg["db_name"],
            )
            # Heartbeat
            self._client.list_collections()
            self._backoff = 1.0
            logger.info("Milvus connected: %s", cfg["uri"])
            return self._client
        except Exception as exc:
            self._last_fail = time.time()
            self._backoff = min(self._backoff * 2, 30.0)
            raise MilvusException(
                message=f"Milvus connection failed ({cfg['uri']}): {exc}"
            ) from exc

    def ensure_collection(self) -> None:
        """Create collection and indexes if they do not exist."""
        client = self.client()
        if client.has_collection(_COLLECTION_NAME):
            return

        cfg = self._settings()
        if not cfg["auto_create"]:
            raise MilvusException(
                message=f"Collection '{_COLLECTION_NAME}' does not exist and auto_create=False"
            )

        index_params = client.prepare_index_params()
        index_params.add_index(
            field_name="embedding",
            index_type="HNSW",
            metric_type="COSINE",
            M=16,
            efConstruction=256,
        )
        index_params.add_index(
            field_name="sparse_embedding",
            index_type="SPARSE_INVERTED_INDEX",
            metric_type="IP",
            drop_ratio_build=0.2,
        )

        client.create_collection(
            collection_name=_COLLECTION_NAME,
            schema=_SCHEMA,
            index_params=index_params,
        )
        logger.info("Created Milvus collection '%s'", _COLLECTION_NAME)


_CONN = _MilvusConnection()


# ---------------------------------------------------------------------------
# Public VectorStore
# ---------------------------------------------------------------------------

class VectorStore:
    """
    Production vector store backed exclusively by Milvus 2.4+.

    Hybrid search (dense + sparse), tenant isolation via partition key,
    realm filtering, and resilient auto-reconnection.
    """

    def __init__(self) -> None:
        _CONN.ensure_collection()

    # -- CRUD ----------------------------------------------------------------

    def add(
        self,
        id: str,
        vector: List[float],
        metadata: Optional[Dict[str, Any]] = None,
        sparse_vector: Optional[Dict[int, float]] = None,
    ) -> None:
        """Insert or upsert a document."""
        meta = metadata or {}
        row: Dict[str, Any] = {
            "doc_id": id,
            "tenant_id": str(meta.get("tenant_id", "default")),
            "realm": str(meta.get("realm", "default")),
            "content": str(meta.get("text_preview", ""))[:65535],
            "embedding": vector,
            "sparse_embedding": sparse_vector or {},
            "metadata": meta,
            "source_type": str(meta.get("source_type", "unknown")),
            "created_at": int(time.time()),
        }
        client = _CONN.client()
        try:
            client.upsert(collection_name=_COLLECTION_NAME, data=[row])
        except Exception as exc:
            logger.warning("Upsert failed, retrying with insert: %s", exc)
            client.insert(collection_name=_COLLECTION_NAME, data=[row])

    def get(self, id: str) -> Optional[VectorItem]:
        """Retrieve a document by doc_id."""
        client = _CONN.client()
        results = client.query(
            collection_name=_COLLECTION_NAME,
            filter=f'doc_id == "{id}"',
            output_fields=["doc_id", "embedding", "metadata"],
            limit=1,
        )
        if not results:
            return None
        r = results[0]
        return VectorItem(
            id=r.get("doc_id", ""),
            vector=r.get("embedding", []),
            metadata=r.get("metadata", {}),
        )

    def delete(self, id: str, tenant_id: Optional[str] = None) -> None:
        """Delete by doc_id with optional tenant verification."""
        expr_parts = [f'doc_id == "{id}"']
        if tenant_id:
            expr_parts.append(f'tenant_id == "{tenant_id}"')
        expr = " and ".join(expr_parts)
        _CONN.client().delete(collection_name=_COLLECTION_NAME, filter=expr)

    # -- Search --------------------------------------------------------------

    def search(
        self,
        query_vector: List[float],
        k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
        query_sparse_vector: Optional[Dict[int, float]] = None,
    ) -> List[Tuple[VectorItem, float]]:
        """
        Hybrid search using dense + sparse vectors with weighted RRF merge.
        """
        filters = filter_metadata or {}
        tenant_id = str(filters.get("tenant_id", "default"))
        realm = filters.get("realm")

        expr_parts = [f'tenant_id == "{tenant_id}"']
        if realm:
            expr_parts.append(f'realm == "{realm}"')
        expr = " and ".join(expr_parts)

        client = _CONN.client()

        def _search(
            data: Any, anns_field: str, metric_type: str, search_params: Dict[str, Any]
        ) -> Dict[str, Tuple[VectorItem, float]]:
            raw = client.search(
                collection_name=_COLLECTION_NAME,
                data=[data],
                anns_field=anns_field,
                search_params=search_params,
                limit=k * 2,
                filter=expr,
                output_fields=["doc_id", "embedding", "metadata"],
            )
            out: Dict[str, Tuple[VectorItem, float]] = {}
            for query_result in raw:
                for hit in query_result:
                    entity_data = hit.get("entity", hit)
                    if not isinstance(entity_data, dict):
                        continue
                    score = float(hit.get("distance", 0.0) or 0.0)
                    doc_id = entity_data.get("doc_id", "")
                    if doc_id:
                        out[doc_id] = (
                            VectorItem(
                                id=doc_id,
                                vector=entity_data.get("embedding", []),
                                metadata=entity_data.get("metadata", {}),
                            ),
                            score,
                        )
            return out

        dense_results = _search(
            data=query_vector,
            anns_field="embedding",
            metric_type="COSINE",
            search_params={"metric_type": "COSINE", "params": {"ef": 64}},
        )

        sparse_results: Dict[str, Tuple[VectorItem, float]] = {}
        if query_sparse_vector:
            sparse_results = _search(
                data=query_sparse_vector,
                anns_field="sparse_embedding",
                metric_type="IP",
                search_params={"metric_type": "IP", "params": {"drop_ratio_search": 0.2}},
            )

        # Weighted RRF merge
        merged: Dict[str, float] = {}
        DENSE_WEIGHT = 0.7
        SPARSE_WEIGHT = 0.3
        RRF_K = 60

        for rank, (doc_id, _) in enumerate(dense_results.items(), start=1):
            merged[doc_id] = merged.get(doc_id, 0.0) + DENSE_WEIGHT / (RRF_K + rank)
        for rank, (doc_id, _) in enumerate(sparse_results.items(), start=1):
            merged[doc_id] = merged.get(doc_id, 0.0) + SPARSE_WEIGHT / (RRF_K + rank)

        all_items = {**dense_results, **sparse_results}
        sorted_ids = sorted(merged.keys(), key=lambda d: merged[d], reverse=True)

        output: List[Tuple[VectorItem, float]] = []
        for doc_id in sorted_ids[:k]:
            item, _ = all_items[doc_id]
            output.append((item, merged[doc_id]))
        return output


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Return the global Milvus-backed VectorStore singleton."""
    global _store
    if _store is None:
        _store = VectorStore()
    return _store
