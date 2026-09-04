"""Semantic search API — Milvus vector store with tenant-isolated embeddings."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from django.http import HttpRequest
from ninja import Router, Schema
from ninja.errors import HttpError
from pydantic import Field

from admin.common.messages import get_message
from apps.core.middleware import get_tenant_id
from apps.core.security.auth import require_permission
from apps.search.lib.embeddings import get_embedding_extractor, get_sparse_embedder
from apps.search.lib.milvus_store import get_vector_store

logger = logging.getLogger(__name__)

router = Router(tags=["Search"], auth=require_permission("read:*"))


# =============================================================================
# Request/Response Schemas
# =============================================================================


class SearchQuery(Schema):
    """Request schema for semantic search query."""

    query: str = Field(
        ...,
        description="The search query text to find similar items",
        min_length=1,
        max_length=10000,
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Maximum number of results to return",
    )
    filters: dict[str, Any] | None = Field(
        default=None,
        description="Optional metadata filters for exact match filtering",
    )


class SemanticSearchResult(Schema):
    """Response schema for a single search result."""

    id: str = Field(..., description="Unique identifier of the indexed item")
    score: float = Field(..., description="Similarity score (0.0 to 1.0, higher is more similar)")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata associated with the indexed item",
    )


class IndexRequest(Schema):
    """Request schema for indexing a new item."""

    text: str = Field(
        ...,
        description="The text content to index",
        min_length=1,
        max_length=100000,
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Optional metadata to store with the indexed item",
    )
    item_id: str | None = Field(
        default=None,
        description="Optional custom ID for the item (auto-generated if not provided)",
    )


class IndexResponse(Schema):
    """Response schema after indexing an item."""

    id: str = Field(..., description="The unique identifier assigned to the indexed item")
    status: str = Field(..., description="Status of the indexing operation")
    dimensions: int = Field(..., description="Dimensionality of the generated embedding vector")


# =============================================================================
# Search Endpoints
# =============================================================================


@router.post("/query", response=list[SemanticSearchResult], summary="Semantic Search Query")
def search(request: HttpRequest, payload: SearchQuery) -> list[SemanticSearchResult]:
    """
    Execute a semantic search query to find similar indexed items.

    This endpoint:
    1. Extracts an embedding vector from the query text
    2. Searches the vector store for similar items
    3. Returns ranked results by similarity score

    The search uses cosine similarity to measure relevance between the query
    and indexed items. Results are filtered by tenant_id to ensure isolation.

    Args:
        request: The HTTP request containing tenant context
        payload: The search query parameters

    Returns:
        A list of SemanticSearchResult objects ranked by similarity (highest first)

    Raises:
        HttpError 400: If the query is invalid
        HttpError 500: If the search operation fails
    """
    try:
        tenant_id = get_tenant_id(request)

        # Get vector store and embedding extractors
        store = get_vector_store()
        dense_extractor = get_embedding_extractor(model="dense", dimensions=1536)
        sparse_extractor = get_sparse_embedder()

        # Extract dense and sparse embeddings from query text
        dense_result = dense_extractor.embed([payload.query])
        if not dense_result.embeddings or len(dense_result.embeddings) == 0:
            raise HttpError(400, get_message("ERR_SEARCH_EMBEDDING"))

        query_vector = dense_result.embeddings[0]
        query_sparse = sparse_extractor.embed([payload.query])[0]

        # Add tenant_id to filters for isolation
        filters = payload.filters or {}
        filters["tenant_id"] = tenant_id

        # Hybrid search (dense + sparse) with tenant/realm filtering
        results = store.search(
            query_vector=query_vector,
            k=payload.limit,
            filter_metadata=filters,
            query_sparse_vector=query_sparse,
        )

        # Convert to response schema
        return [
            SemanticSearchResult(
                id=item.id,
                score=round(score, 6),
                metadata=item.metadata,
            )
            for item, score in results
        ]

    except HttpError:
        raise
    except ValueError as exc:
        logger.error(f"Invalid search query: {exc}")
        raise HttpError(400, get_message("ERR_SEARCH_INVALID", error=str(exc))) from exc
    except Exception as exc:
        logger.exception("Search operation failed")
        raise HttpError(500, get_message("ERR_SEARCH_FAILED", error=str(exc))) from exc


@router.post(
    "/index",
    response=IndexResponse,
    summary="Index New Item",
    auth=require_permission("write:documents"),
)
def index_item(request: HttpRequest, payload: IndexRequest) -> IndexResponse:
    """
    Index a new text item for semantic search.

    This endpoint:
    1. Extracts an embedding vector from the provided text
    2. Stores the vector in the vector store with metadata
    3. Associates the item with the current tenant for isolation

    The indexed item becomes immediately searchable via the /query endpoint.

    Args:
        request: The HTTP request containing tenant context
        payload: The item to index with text and optional metadata

    Returns:
        An IndexResponse with the assigned item ID and status

    Raises:
        HttpError 400: If the text is invalid or embedding extraction fails
        HttpError 500: If the indexing operation fails
    """
    try:
        tenant_id = get_tenant_id(request)

        # Get vector store and embedding extractors
        store = get_vector_store()
        dense_extractor = get_embedding_extractor(model="dense", dimensions=1536)
        sparse_extractor = get_sparse_embedder()

        # Extract dense and sparse embeddings from text
        dense_result = dense_extractor.embed([payload.text])
        if not dense_result.embeddings or len(dense_result.embeddings) == 0:
            raise HttpError(400, get_message("ERR_INDEX_EMBEDDING"))

        dense_vector = dense_result.embeddings[0]
        sparse_vector = sparse_extractor.embed([payload.text])[0]

        # Generate or use provided item ID
        item_id = payload.item_id or str(uuid.uuid4())

        # Prepare metadata with tenant isolation
        metadata = payload.metadata or {}
        metadata["tenant_id"] = tenant_id
        metadata["text_preview"] = payload.text[:200]

        # Add item to vector store (Milvus only)
        store.add(
            id=item_id,
            vector=dense_vector,
            metadata=metadata,
            sparse_vector=sparse_vector,
        )

        logger.info(
            f"Indexed item {item_id} for tenant {tenant_id} (dimensions={dense_result.dimensions})"
        )

        return IndexResponse(
            id=item_id,
            status="indexed",
            dimensions=dense_result.dimensions,
        )

    except HttpError:
        raise
    except ValueError as exc:
        logger.error(f"Invalid index request: {exc}")
        raise HttpError(400, get_message("ERR_INDEX_INVALID", error=str(exc))) from exc
    except Exception as exc:
        logger.exception("Indexing operation failed")
        raise HttpError(500, get_message("ERR_INDEX_FAILED", error=str(exc))) from exc


@router.delete(
    "/{item_id}",
    response={200: dict[str, str]},
    summary="Delete Indexed Item",
    auth=require_permission("write:documents"),
)
def delete_item(request: HttpRequest, item_id: str) -> dict[str, str]:
    """
    Delete an indexed item from the vector store.

    This endpoint removes an item by its ID. For security, it verifies that
    the item belongs to the current tenant before deletion.

    Args:
        request: The HTTP request containing tenant context
        item_id: The unique identifier of the item to delete

    Returns:
        A confirmation message with the deleted item ID

    Raises:
        HttpError 403: If the item does not belong to the current tenant
        HttpError 404: If the item is not found
        HttpError 500: If the deletion operation fails
    """
    try:
        tenant_id = get_tenant_id(request)
        store = get_vector_store()

        # Verify item exists and belongs to tenant
        item = store.get(item_id)
        if not item:
            raise HttpError(404, get_message("ERR_ITEM_NOT_FOUND", item_id=item_id))

        item_tenant = item.metadata.get("tenant_id")
        if item_tenant != tenant_id:
            raise HttpError(403, get_message("ERR_ITEM_DENIED"))

        # Delete item
        store.delete(item_id)

        logger.info(f"Deleted item {item_id} for tenant {tenant_id}")

        return {
            "status": "deleted",
            "item_id": item_id,
        }

    except HttpError:
        raise
    except Exception as exc:
        logger.exception(f"Failed to delete item {item_id}")
        raise HttpError(500, get_message("ERR_DELETE_FAILED", error=str(exc))) from exc


@router.get("/{item_id}", response=SemanticSearchResult, summary="Get Indexed Item")
def get_item(request: HttpRequest, item_id: str) -> SemanticSearchResult:
    """
    Retrieve an indexed item by its ID.

    This endpoint fetches the metadata of a specific indexed item.
    For security, it verifies that the item belongs to the current tenant.

    Args:
        request: The HTTP request containing tenant context
        item_id: The unique identifier of the item to retrieve

    Returns:
        A SemanticSearchResult with the item's metadata

    Raises:
        HttpError 403: If the item does not belong to the current tenant
        HttpError 404: If the item is not found
        HttpError 500: If the retrieval operation fails
    """
    try:
        tenant_id = get_tenant_id(request)
        store = get_vector_store()

        # Get item
        item = store.get(item_id)
        if not item:
            raise HttpError(404, get_message("ERR_ITEM_NOT_FOUND", item_id=item_id))

        # Verify tenant access
        item_tenant = item.metadata.get("tenant_id")
        if item_tenant != tenant_id:
            raise HttpError(403, get_message("ERR_ITEM_DENIED"))

        return SemanticSearchResult(
            id=item.id,
            score=1.0,  # Exact match
            metadata=item.metadata,
        )

    except HttpError:
        raise
    except Exception as exc:
        logger.exception(f"Failed to retrieve item {item_id}")
        raise HttpError(500, get_message("ERR_RETRIEVAL_FAILED", error=str(exc))) from exc
