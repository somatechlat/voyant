"""
Discovery API Routes

Endpoints for service discovery and schema management.
Adheres to Vibe Coding Rules: Uses DiscoveryRepo and SpecParser.
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from voyant.discovery.catalog import DiscoveryRepo, ServiceDef
from voyant.discovery.spec_parser import SpecParser
from voyant.api.middleware import get_tenant_id

router = APIRouter(prefix="/discovery")
repo = DiscoveryRepo()
parser = SpecParser()

class ServiceRegisterRequest(BaseModel):
    name: str
    base_url: str
    spec_url: Optional[str] = None
    version: str = "1.0.0"
    owner: str = "unknown"
    tags: List[str] = []

class SpecScanRequest(BaseModel):
    url: str

@router.post("/services", response_model=ServiceDef)
async def register_service(request: ServiceRegisterRequest):
    """
    Register a new service in the catalog.
    
    PhD Developer: "Platform of Platforms" pattern.
    """
    try:
        service = ServiceDef(
            name=request.name,
            base_url=request.base_url,
            spec_url=request.spec_url,
            version=request.version,
            owner=request.owner,
            tags=request.tags,
            endpoints=[] # Initial empty list
        )
        
        # If spec URL provided, try to auto-populate
        if request.spec_url:
            try:
                spec = parser.parse_from_url(request.spec_url)
                service.endpoints = spec.endpoints
                service.version = spec.version or service.version
            except Exception as e:
                # Log warning but allow registration
                pass
                
        repo.register_service(service)
        return service
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/services", response_model=List[ServiceDef])
async def list_services(tag: Optional[str] = None):
    """List registered services."""
    if tag:
        return repo.search_services(tag)
    return repo.list_services()

@router.get("/services/{name}", response_model=ServiceDef)
async def get_service(name: str):
    """Get service details."""
    service = repo.get_service(name)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service

@router.post("/scan")
async def scan_spec(request: SpecScanRequest):
    """
    Scan an OpenAPI/Swagger spec URL.
    """
    try:
        spec = parser.parse_from_url(request.url)
        return {
            "title": spec.title,
            "version": spec.version,
            "endpoint_count": len(spec.endpoints),
            "endpoints": [e.path for e in spec.endpoints[:10]] # Sample
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Scan failed: {e}")
