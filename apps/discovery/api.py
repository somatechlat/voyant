
import logging
from typing import Any, Dict, List, Optional
from ninja import Router, Schema, Field
from ninja.errors import HttpError
from apps.core.api_utils import auth_guard
from apps.core.config import get_settings
from apps.discovery.models import ServiceDefinition, Source
from apps.core.middleware import get_tenant_id
from apps.discovery.lib.catalog import DiscoveryRepo, ServiceDef
from apps.discovery.lib.spec_parser import SpecParser
from apps.discovery.source_detection import detect_source_type

logger = logging.getLogger(__name__)
settings = get_settings()

sources_router = Router(tags=["sources"])
discovery_router = Router(tags=["discovery"])

_discovery_repo = DiscoveryRepo()
_spec_parser = SpecParser()

# =============================================================================
# Sources Router
# =============================================================================

class DiscoverRequest(Schema):
    hint: str = Field(..., description="A string that provides a hint about the data source.")

class DiscoverResponse(Schema):
    source_type: str
    detected_properties: Dict[str, Any]
    suggested_connector: str
    confidence: float

class CreateSourceRequest(Schema):
    name: str
    source_type: str
    connection_config: Dict[str, Any]
    credentials: Optional[Dict[str, Any]] = None
    sync_schedule: Optional[str] = None

class SourceResponse(Schema):
    source_id: str
    tenant_id: str
    name: str
    source_type: str
    status: str
    created_at: str
    datahub_urn: Optional[str] = None

@sources_router.post("/discover", response=DiscoverResponse)
def discover_source(request, payload: DiscoverRequest):
    detected = detect_source_type(payload.hint)
    return DiscoverResponse(
        source_type=detected["source_type"],
        detected_properties=detected["properties"],
        suggested_connector=detected["connector"],
        confidence=detected["confidence"],
    )

@sources_router.post("", response={201: SourceResponse})
def create_source(request, payload: CreateSourceRequest):
    tenant_id = get_tenant_id(request)
    source = Source.objects.create(
        tenant_id=tenant_id,
        name=payload.name,
        source_type=payload.source_type,
        connection_config=payload.connection_config,
        credentials=payload.credentials,
        sync_schedule=payload.sync_schedule,
        status="pending",
    )
    return 201, SourceResponse(
        source_id=str(source.source_id),
        tenant_id=tenant_id,
        name=source.name,
        source_type=source.source_type,
        status=source.status,
        created_at=source.created_at.isoformat(),
        datahub_urn=source.datahub_urn,
    )

@sources_router.get("", response=List[SourceResponse])
def list_sources(request):
    tenant_id = get_tenant_id(request)
    sources = Source.objects.filter(tenant_id=tenant_id).order_by("-created_at")
    return [
        SourceResponse(
            source_id=str(source.source_id),
            tenant_id=source.tenant_id,
            name=source.name,
            source_type=source.source_type,
            status=source.status,
            created_at=source.created_at.isoformat(),
            datahub_urn=source.datahub_urn,
        )
        for source in sources
    ]

@sources_router.get("/{source_id}", response=SourceResponse)
def get_source(request, source_id: str):
    source = Source.objects.filter(source_id=source_id).first()
    if not source:
        raise HttpError(404, "Source not found")
    tenant_id = get_tenant_id(request)
    if source.tenant_id != tenant_id:
        raise HttpError(403, "Access to this resource is denied.")
    return SourceResponse(
        source_id=str(source.source_id),
        tenant_id=source.tenant_id,
        name=source.name,
        source_type=source.source_type,
        status=source.status,
        created_at=source.created_at.isoformat(),
        datahub_urn=source.datahub_urn,
    )

@sources_router.delete("/{source_id}", response={200: Dict[str, str]})
def delete_source(request, source_id: str):
    source = Source.objects.filter(source_id=source_id).first()
    if not source:
        raise HttpError(404, "Source not found")
    tenant_id = get_tenant_id(request)
    if source.tenant_id != tenant_id:
        raise HttpError(403, "Access to this resource is denied.")
    source.delete()
    return {"status": "deleted", "source_id": str(source_id)}

# =============================================================================
# Discovery Router
# =============================================================================

class ServiceRegisterRequest(Schema):
    name: str
    base_url: str
    spec_url: Optional[str] = None
    version: str = "1.0.0"
    owner: str = "unknown"
    tags: List[str] = []

class SpecScanRequest(Schema):
    url: str

@discovery_router.post("/services", response=ServiceDef)
def register_service(request, payload: ServiceRegisterRequest):
    try:
        service = ServiceDef(
            name=payload.name,
            base_url=payload.base_url,
            spec_url=payload.spec_url,
            version=payload.version,
            owner=payload.owner,
            tags=payload.tags,
            endpoints=[],
        )
        if payload.spec_url:
            try:
                spec = _spec_parser.parse_from_url(payload.spec_url)
                service.endpoints = spec.endpoints
                service.version = spec.version or service.version
            except Exception as e:
                logger.warning(f"Failed to parse OpenAPI spec: {e}")
        _discovery_repo.register(service)
        return service
    except Exception as exc:
        logger.exception("Failed to register service")
        raise HttpError(500, f"Failed to register service: {exc}") from exc

@discovery_router.get("/services", response=List[ServiceDef])
def list_services(request, tag: Optional[str] = None):
    try:
        if tag:
            return _discovery_repo.search(tag)
        return _discovery_repo.list_services()
    except Exception as exc:
        raise HttpError(500, f"Failed to list services: {exc}") from exc

@discovery_router.get("/services/{name}", response=ServiceDef)
def get_service(request, name: str):
    try:
        service = _discovery_repo.get(name)
        if not service:
            raise HttpError(404, "Service not found")
        return service
    except HttpError:
        raise
    except Exception as exc:
        raise HttpError(500, f"Failed to retrieve service: {exc}") from exc

@discovery_router.post("/scan", response=Dict[str, Any])
def scan_spec(request, payload: SpecScanRequest):
    try:
        spec = _spec_parser.parse_from_url(payload.url)
        return {
            "title": spec.title,
            "version": spec.version,
            "endpoint_count": len(spec.endpoints),
            "endpoints": [endpoint.path for endpoint in spec.endpoints[:10]],
        }
    except Exception as exc:
        raise HttpError(400, f"Scan failed: {exc}") from exc
