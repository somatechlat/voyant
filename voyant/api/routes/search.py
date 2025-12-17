"""
Search API Routes

Endpoints for semantic search using VectorStore.
Adheres to Vibe Coding Rules: Uses VectorStore real implementation.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from voyant.core.vector_store import get_vector_store
from voyant.core.embeddings import get_embedding_extractor

router = APIRouter(prefix="/search")

class SearchQuery(BaseModel):
    query: str
    limit: int = 5
    filters: Optional[Dict[str, Any]] = None

class SearchResult(BaseModel):
    id: str
    score: float
    text: Optional[str] = None
    metadata: Dict[str, Any] = {}

@router.post("/query", response_model=List[SearchResult])
async def search(request: SearchQuery):
    """
    Semantic search over vector store.
    """
    try:
        store = get_vector_store()
        
        # 1. Generate embedding for query
        # Currently VectorStore.search(query_vector) requires a vector.
        # We need to embed the query text first.
        extractor = get_embedding_extractor()
        query_vector = extractor.extract_text_embedding(request.query)
        
        # 2. Search
        results = store.search(
            query_vector=query_vector,
            limit=request.limit,
            filters=request.filters
        )
        
        # 3. Format response
        return [
            SearchResult(
                id=r.id,
                score=r.score,
                text=r.text,
                metadata=r.metadata
            )
            for r in results
        ]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/index")
async def index_item(text: str, metadata: Dict[str, Any] = None):
    """
    Index a text item (Ad-hoc).
    """
    try:
        store = get_vector_store()
        extractor = get_embedding_extractor()
        
        # Generate embedding
        vector = extractor.extract_text_embedding(text)
        
        # Add to store
        import uuid
        item_id = str(uuid.uuid4())
        
        from voyant.core.vector_store import VectorItem
        item = VectorItem(
            id=item_id,
            vector=vector,
            text=text,
            metadata=metadata or {}
        )
        
        store.add_item(item)
        return {"id": item_id, "status": "indexed"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
