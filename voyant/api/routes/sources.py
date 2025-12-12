"""
Sources API Routes

Endpoints for data source management.
"""
from __future__ import annotations

import uuid
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from voyant.db import get_session
from voyant.api.middleware import get_tenant_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sources")


# =============================================================================
# Models
# =============================================================================

class DiscoverRequest(BaseModel):
    hint: str = Field(..., description="Data source hint (URL, path, connection string)")


class DiscoverResponse(BaseModel):
    source_type: str
    detected_properties: Dict[str, Any]
    suggested_connector: str
    confidence: float


class CreateSourceRequest(BaseModel):
    name: str
    source_type: str
    connection_config: Dict[str, Any]
    credentials: Optional[Dict[str, Any]] = None
    sync_schedule: Optional[str] = None


class SourceResponse(BaseModel):
    source_id: str
    tenant_id: str
    name: str
    source_type: str
    status: str
    created_at: str
    datahub_urn: Optional[str] = None


# =============================================================================
# Auto-detection logic
# =============================================================================

def detect_source_type(hint: str) -> Dict[str, Any]:
    """Detect source type from hint."""
    hint_lower = hint.lower()
    
    if hint_lower.startswith("postgresql://") or hint_lower.startswith("postgres://"):
        return {
            "source_type": "postgresql",
            "connector": "airbyte/source-postgres",
            "properties": {"host": hint.split("@")[-1].split("/")[0] if "@" in hint else "unknown"},
            "confidence": 0.95,
        }
    elif hint_lower.startswith("mysql://"):
        return {
            "source_type": "mysql",
            "connector": "airbyte/source-mysql",
            "properties": {},
            "confidence": 0.95,
        }
    elif hint_lower.startswith("mongodb://") or hint_lower.startswith("mongodb+srv://"):
        return {
            "source_type": "mongodb",
            "connector": "airbyte/source-mongodb-v2",
            "properties": {},
            "confidence": 0.95,
        }
    elif "snowflake" in hint_lower:
        return {
            "source_type": "snowflake",
            "connector": "airbyte/source-snowflake",
            "properties": {},
            "confidence": 0.9,
        }
    elif hint_lower.endswith(".csv"):
        return {
            "source_type": "csv",
            "connector": "file",
            "properties": {"format": "csv"},
            "confidence": 0.9,
        }
    elif hint_lower.endswith(".parquet"):
        return {
            "source_type": "parquet",
            "connector": "file",
            "properties": {"format": "parquet"},
            "confidence": 0.9,
        }
    elif hint_lower.endswith(".json") or hint_lower.endswith(".jsonl"):
        return {
            "source_type": "json",
            "connector": "file",
            "properties": {"format": "json"},
            "confidence": 0.9,
        }
    elif "s3://" in hint_lower:
        return {
            "source_type": "s3",
            "connector": "airbyte/source-s3",
            "properties": {"bucket": hint.split("/")[2] if len(hint.split("/")) > 2 else ""},
            "confidence": 0.9,
        }
    elif "sheets.google.com" in hint_lower or "docs.google.com/spreadsheets" in hint_lower:
        return {
            "source_type": "google_sheets",
            "connector": "airbyte/source-google-sheets",
            "properties": {},
            "confidence": 0.9,
        }
    elif hint_lower.startswith("http://") or hint_lower.startswith("https://"):
        return {
            "source_type": "api",
            "connector": "airbyte/source-http",
            "properties": {"url": hint},
            "confidence": 0.5,
        }
    else:
        return {
            "source_type": "unknown",
            "connector": "unknown",
            "properties": {},
            "confidence": 0.1,
        }


# =============================================================================
# In-memory store (will be PostgreSQL)
# =============================================================================

_sources: Dict[str, Dict[str, Any]] = {}


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/discover", response_model=DiscoverResponse)
async def discover_source(request: DiscoverRequest):
    """Auto-detect source type from hint."""
    detected = detect_source_type(request.hint)
    return DiscoverResponse(
        source_type=detected["source_type"],
        detected_properties=detected["properties"],
        suggested_connector=detected["connector"],
        confidence=detected["confidence"],
    )


@router.post("", response_model=SourceResponse)
async def create_source(request: CreateSourceRequest):
    """Create a new data source."""
    source_id = str(uuid.uuid4())
    tenant_id = get_tenant_id()
    now = datetime.utcnow().isoformat()
    
    source = {
        "source_id": source_id,
        "tenant_id": tenant_id,
        "name": request.name,
        "source_type": request.source_type,
        "connection_config": request.connection_config,
        "credentials": request.credentials,
        "sync_schedule": request.sync_schedule,
        "status": "pending",
        "created_at": now,
        "updated_at": now,
    }
    
    _sources[source_id] = source
    logger.info(f"Created source {source_id} for tenant {tenant_id}")
    
    return SourceResponse(
        source_id=source_id,
        tenant_id=tenant_id,
        name=request.name,
        source_type=request.source_type,
        status="pending",
        created_at=now,
    )


@router.get("", response_model=List[SourceResponse])
async def list_sources():
    """List all sources for current tenant."""
    tenant_id = get_tenant_id()
    return [
        SourceResponse(
            source_id=s["source_id"],
            tenant_id=s["tenant_id"],
            name=s["name"],
            source_type=s["source_type"],
            status=s["status"],
            created_at=s["created_at"],
            datahub_urn=s.get("datahub_urn"),
        )
        for s in _sources.values()
        if s["tenant_id"] == tenant_id
    ]


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(source_id: str):
    """Get source by ID."""
    if source_id not in _sources:
        raise HTTPException(status_code=404, detail="Source not found")
    
    s = _sources[source_id]
    tenant_id = get_tenant_id()
    
    if s["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return SourceResponse(
        source_id=s["source_id"],
        tenant_id=s["tenant_id"],
        name=s["name"],
        source_type=s["source_type"],
        status=s["status"],
        created_at=s["created_at"],
        datahub_urn=s.get("datahub_urn"),
    )


@router.delete("/{source_id}")
async def delete_source(source_id: str):
    """Delete a source."""
    if source_id not in _sources:
        raise HTTPException(status_code=404, detail="Source not found")
    
    s = _sources[source_id]
    tenant_id = get_tenant_id()
    
    if s["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    del _sources[source_id]
    logger.info(f"Deleted source {source_id}")
    
    return {"status": "deleted", "source_id": source_id}
