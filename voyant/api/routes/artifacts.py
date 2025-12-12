"""
Artifacts API Routes

Artifact retrieval from MinIO.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from voyant.core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/artifacts")
settings = get_settings()


# =============================================================================
# Models
# =============================================================================

class ArtifactInfo(BaseModel):
    artifact_id: str
    job_id: str
    artifact_type: str
    format: str
    storage_path: str
    size_bytes: Optional[int] = None
    created_at: str


class ArtifactListResponse(BaseModel):
    artifacts: List[ArtifactInfo]


# =============================================================================
# MinIO Client
# =============================================================================

_minio_client = None

def get_minio_client():
    """Get MinIO client."""
    global _minio_client
    if _minio_client is None:
        try:
            from minio import Minio
            _minio_client = Minio(
                settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure,
            )
            logger.info(f"MinIO client connected to {settings.minio_endpoint}")
        except ImportError:
            logger.warning("minio package not installed")
        except Exception as e:
            logger.error(f"MinIO connection failed: {e}")
    return _minio_client


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/{job_id}", response_model=ArtifactListResponse)
async def list_artifacts(job_id: str):
    """List artifacts for a job."""
    client = get_minio_client()
    if not client:
        raise HTTPException(status_code=503, detail="Storage unavailable")
    
    try:
        prefix = f"artifacts/{job_id}/"
        objects = client.list_objects("artifacts", prefix=prefix, recursive=True)
        
        artifacts = []
        for obj in objects:
            path_parts = obj.object_name.split("/")
            filename = path_parts[-1] if path_parts else ""
            name_parts = filename.rsplit(".", 1)
            
            artifacts.append(ArtifactInfo(
                artifact_id=obj.object_name,
                job_id=job_id,
                artifact_type=name_parts[0] if name_parts else "unknown",
                format=name_parts[1] if len(name_parts) > 1 else "bin",
                storage_path=obj.object_name,
                size_bytes=obj.size,
                created_at=obj.last_modified.isoformat() if obj.last_modified else "",
            ))
        
        return ArtifactListResponse(artifacts=artifacts)
        
    except Exception as e:
        logger.exception(f"Failed to list artifacts for {job_id}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}/{artifact_type}")
async def get_artifact(job_id: str, artifact_type: str, format: str = "json"):
    """Get artifact metadata and download URL."""
    client = get_minio_client()
    if not client:
        raise HTTPException(status_code=503, detail="Storage unavailable")
    
    object_name = f"artifacts/{job_id}/{artifact_type}.{format}"
    
    try:
        # Generate presigned URL
        url = client.presigned_get_object("artifacts", object_name, expires=3600)
        
        return {
            "job_id": job_id,
            "artifact_type": artifact_type,
            "format": format,
            "download_url": url,
            "expires_in_seconds": 3600,
        }
        
    except Exception as e:
        logger.error(f"Artifact not found: {object_name}")
        raise HTTPException(status_code=404, detail="Artifact not found")


@router.get("/{job_id}/{artifact_type}/download")
async def download_artifact(job_id: str, artifact_type: str, format: str = "json"):
    """Download artifact file."""
    client = get_minio_client()
    if not client:
        raise HTTPException(status_code=503, detail="Storage unavailable")
    
    object_name = f"artifacts/{job_id}/{artifact_type}.{format}"
    
    try:
        response = client.get_object("artifacts", object_name)
        
        content_type_map = {
            "json": "application/json",
            "html": "text/html",
            "csv": "text/csv",
            "parquet": "application/octet-stream",
            "png": "image/png",
            "pdf": "application/pdf",
        }
        
        return StreamingResponse(
            response.stream(),
            media_type=content_type_map.get(format, "application/octet-stream"),
            headers={
                "Content-Disposition": f"attachment; filename={artifact_type}.{format}",
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to download: {object_name}")
        raise HTTPException(status_code=404, detail="Artifact not found")
