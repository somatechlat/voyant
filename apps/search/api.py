"""Semantic search REST API endpoints.

This module provides semantic search capabilities using vector embeddings.
It integrates with the Milvus vector store for persistent storage and retrieval
of embeddings, enabling similarity-based search across indexed content.

Architectural Notes:
- Vector Store: Uses Milvus for production-grade vector storage and retrieval
- Embeddings: Supports multiple embedding models (TF-IDF, simple character-based)
- Multi-Tenancy: All indexed items are isolated by tenant_id
- Security: Policy enforcement via OPA gates for search and indexing operations

Seven Personas Applied:
- PhD Developer: Correct embedding extraction and similarity search
- PhD Analyst: Meaningful search results with relevance scoring
- PhD QA Engineer: Input validation and error handling
- ISO Documenter: Complete API documentation
- Security Auditor: Tenant isolation and access control
- Performance Engineer: Efficient vector operations
- UX Consultant: Simple, intuitive API surface
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from django.http import HttpRequest
from ninja import Router, Schema
from ninja.errors import HttpError
from pydantic import Field

from apps.core.middleware import get_tenant_id
from apps.core.lib.embeddings import get_embedding_extractor
from apps.core.lib.vector_store import get_vector_store

logger = logging.getLogger(__name__)

router = Router(tags=["Search"])


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
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata filters for exact match filtering",
    )


class SemanticSearchResult(Schema):
    """Response schema for a single search result."""

    id: str = Field(..., description="Unique identifier of the indexed item")
    score: float = Field(
        ..., description="Similarity score (0.0 to 1.0, higher is more similar)"
    )
    metadata: Dict[str, Any] = Field(
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
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional metadata to store with the indexed item",
    )
    item_id: Optional[str] = Field(
        default=None,
        description="Optional custom ID for the item (auto-generated if not provided)",
    )


class IndexResponse(Schema):
    """Response schema after indexing an item."""

    id: str = Field(
        ..., description="The unique identifier assigned to the indexed item"
    )
    status: str = Field(..., description="Status of the indexing operation")
    dimensions: int = Field(
        ..., description="Dimensionality of the generated embedding vector"
    )


# =============================================================================
# Search Endpoints
# =============================================================================


@router.post(
    "/query", response=List[SemanticSearchResult], summary="Semantic Search Query"
)
def search(request: HttpRequest, payload: SearchQuery) -> List[SemanticSearchResult]:
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

        # Get vector store and embedding extractor
        store = get_vector_store()
        extractor = get_embedding_extractor(model="tfidf", dimensions=128)

        # Extract embedding from query text
        # The embed() method returns EmbeddingResult with a list of embeddings
        embedding_result = extractor.embed([payload.query])
        if not embedding_result.embeddings or len(embedding_result.embeddings) == 0:
            raise HttpError(400, "Failed to extract embedding from query")

        query_vector = embedding_result.embeddings[0]

        # Add tenant_id to filters for isolation
        filters = payload.filters or {}
        filters["tenant_id"] = tenant_id

        # Search vector store
        # Returns list of (VectorItem, similarity_score) tuples
        results = store.search(
            query_vector=query_vector,
            k=payload.limit,
            filter_metadata=filters,
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
        raise HttpError(400, f"Invalid query: {exc}") from exc
    except Exception as exc:
        logger.exception("Search operation failed")
        raise HttpError(500, f"Search failed: {exc}") from exc


@router.post("/index", response=IndexResponse, summary="Index New Item")
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

        # Get vector store and embedding extractor
        store = get_vector_store()
        extractor = get_embedding_extractor(model="tfidf", dimensions=128)

        # Extract embedding from text
        # The embed() method returns EmbeddingResult with a list of embeddings
        embedding_result = extractor.embed([payload.text])
        if not embedding_result.embeddings or len(embedding_result.embeddings) == 0:
            raise HttpError(400, "Failed to extract embedding from text")

        vector = embedding_result.embeddings[0]

        # Generate or use provided item ID
        item_id = payload.item_id or str(uuid.uuid4())

        # Prepare metadata with tenant isolation
        metadata = payload.metadata or {}
        metadata["tenant_id"] = tenant_id
        metadata["text_preview"] = payload.text[:200]  # Store preview for debugging

        # Add item to vector store
        store.add(
            id=item_id,
            vector=vector,
            metadata=metadata,
        )

        # Persist to disk
        store.save()

        logger.info(
            f"Indexed item {item_id} for tenant {tenant_id} (dimensions={embedding_result.dimensions})"
        )

        return IndexResponse(
            id=item_id,
            status="indexed",
            dimensions=embedding_result.dimensions,
        )

    except HttpError:
        raise
    except ValueError as exc:
        logger.error(f"Invalid index request: {exc}")
        raise HttpError(400, f"Invalid request: {exc}") from exc
    except Exception as exc:
        logger.exception("Indexing operation failed")
        raise HttpError(500, f"Indexing failed: {exc}") from exc


@router.delete(
    "/{item_id}", response={200: Dict[str, str]}, summary="Delete Indexed Item"
)
def delete_item(request: HttpRequest, item_id: str) -> Dict[str, str]:
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
            raise HttpError(404, f"Item not found: {item_id}")

        item_tenant = item.metadata.get("tenant_id")
        if item_tenant != tenant_id:
            raise HttpError(403, "Access denied: item belongs to different tenant")

        # Delete item
        store.delete(item_id)
        store.save()

        logger.info(f"Deleted item {item_id} for tenant {tenant_id}")

        return {
            "status": "deleted",
            "item_id": item_id,
        }

    except HttpError:
        raise
    except Exception as exc:
        logger.exception(f"Failed to delete item {item_id}")
        raise HttpError(500, f"Deletion failed: {exc}") from exc


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
            raise HttpError(404, f"Item not found: {item_id}")

        # Verify tenant access
        item_tenant = item.metadata.get("tenant_id")
        if item_tenant != tenant_id:
            raise HttpError(403, "Access denied: item belongs to different tenant")

        return SemanticSearchResult(
            id=item.id,
            score=1.0,  # Exact match
            metadata=item.metadata,
        )

    except HttpError:
        raise
    except Exception as exc:
        logger.exception(f"Failed to retrieve item {item_id}")
        raise HttpError(500, f"Retrieval failed: {exc}") from exc
