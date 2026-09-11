"""Voyant Admin Panel — REST API endpoints.

All endpoints require voyant-admin role. Provides management interfaces
for every Voyant domain: jobs, sources, governance, capsules, ontology,
audit, system config, SQL console, search, and scraper.
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime

from ninja import Router
from ninja.errors import HttpError

from apps.admin_panel.schemas import (
    AuditLogItem,
    CapsuleActionRequest,
    CapsuleListItem,
    ContractListItem,
    DashboardStats,
    JobActionResponse,
    JobDetail,
    JobListItem,
    ObjectTypeListItem,
    PolicyListItem,
    PropertyListItem,
    QuotaInfo,
    ScraperJobListItem,
    SearchIndexItem,
    SearchIndexRequest,
    ServiceHealth,
    SourceCreateRequest,
    SourceListItem,
    SqlExecuteRequest,
    SqlResult,
    SystemOverview,
    SystemSettingItem,
    SystemSettingUpdate,
    TableInfo,
    TenantInfo,
)
from apps.core.config import get_settings
from apps.core.lib.circuit_breaker import _circuit_breakers
from apps.core.lib.trino import get_trino_client
from apps.core.middleware import get_tenant_id
from apps.core.security.auth import require_role

logger = logging.getLogger(__name__)
settings = get_settings()

admin_router = Router(tags=["admin"], auth=require_role("voyant-admin"))

_BOOT_TIME = time.time()


# ── Dashboard ────────────────────────────────────────────────────────────────


@admin_router.get("/dashboard", response=SystemOverview)
def get_dashboard(request):
    """System overview with health, stats, and service status."""
    from apps.core.models import AuditLog
    from apps.discovery.models import Source
    from apps.workflows.models import Job

    # Job stats
    jobs = Job.objects.all()
    total = jobs.count()
    running = jobs.filter(status="running").count()
    queued = jobs.filter(status="queued").count()
    failed = jobs.filter(status="failed").count()
    completed = jobs.filter(status="completed").count()

    # Source stats
    sources = Source.objects.all()
    total_sources = sources.count()
    active_sources = sources.filter(status="connected").count()

    # Artifact count
    from apps.workflows.models import Artifact

    total_artifacts = Artifact.objects.count()

    # Capsule count
    from apps.capsules.models import Capsule

    total_capsules = Capsule.objects.count()

    # Tenant stats
    tenant_ids = set(Job.objects.values_list("tenant_id", flat=True).distinct())
    total_tenants = len(tenant_ids)
    day_ago = datetime.now(UTC)
    active_tenants = (
        Job.objects.filter(created_at__gte=day_ago)
        .values("tenant_id")
        .distinct()
        .count()
    )

    # Audit stats
    audit_24h = AuditLog.objects.filter(created_at__gte=day_ago).count()
    violations = AuditLog.objects.filter(
        created_at__gte=day_ago,
        action__contains="policy",
        outcome="denied",
    ).count()

    # Service health (map circuit breaker states to frontend-expected health status)
    _cb_state_to_status = {
        "closed": "healthy",
        "half_open": "degraded",
        "open": "down",
    }
    services = []
    for name, cb in _circuit_breakers.items():
        cb_state = cb.get_state().value
        services.append(
            ServiceHealth(
                name=name,
                status=_cb_state_to_status.get(cb_state, "unknown"),
                circuit_breaker_state=cb_state,
            )
        )

    # Infrastructure health
    infra_checks = {
        "postgres": _check_postgres,
        "redis": _check_redis,
        "vault": _check_vault,
        "temporal": _check_temporal,
        "minio": _check_minio,
        "kafka": _check_kafka,
        "milvus": _check_milvus,
        "trino": _check_trino,
    }
    for name, check_fn in infra_checks.items():
        try:
            ok, detail = check_fn()
            services.append(
                ServiceHealth(
                    name=name,
                    status="healthy" if ok else "down",
                    details=detail,
                )
            )
        except Exception as exc:
            services.append(
                ServiceHealth(
                    name=name,
                    status="down",
                    details=str(exc),
                )
            )

    return SystemOverview(
        version="3.0.0",
        env=settings.env,
        debug=settings.debug,
        uptime_seconds=int(time.time() - _BOOT_TIME),
        services=services,
        stats=DashboardStats(
            total_jobs=total,
            jobs_running=running,
            jobs_queued=queued,
            jobs_failed=failed,
            jobs_completed=completed,
            total_sources=total_sources,
            sources_active=active_sources,
            total_artifacts=total_artifacts,
            total_capsules=total_capsules,
            total_tenants=total_tenants,
            active_tenants=active_tenants,
            audit_events_24h=audit_24h,
            policy_violations_24h=violations,
        ),
    )


# ── Jobs ─────────────────────────────────────────────────────────────────────


@admin_router.get("/jobs", response=list[JobListItem])
def list_jobs(
    request,
    status: str | None = None,
    job_type: str | None = None,
    tenant_id: str | None = None,
    limit: int = 100,
):
    """List all jobs across all tenants (admin view)."""
    from apps.workflows.models import Job

    qs = Job.objects.all()
    if status:
        qs = qs.filter(status=status)
    if job_type:
        qs = qs.filter(job_type=job_type)
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)

    return [
        JobListItem(
            job_id=str(j.job_id),
            tenant_id=j.tenant_id,
            job_type=j.job_type,
            status=j.status,
            progress=j.progress,
            source_id=j.source_id,
            created_at=j.created_at.isoformat(),
            started_at=j.started_at.isoformat() if j.started_at else None,
            completed_at=j.completed_at.isoformat() if j.completed_at else None,
            error_message=j.error_message,
        )
        for j in qs.order_by("-created_at")[:limit]
    ]


@admin_router.get("/jobs/{job_id}", response=JobDetail)
def get_job_detail(request, job_id: str):
    """Get full job details including parameters and artifacts."""
    from apps.workflows.models import Artifact, Job

    job = Job.objects.filter(id=job_id).first()
    if not job:
        raise HttpError(404, "Job not found")

    artifacts = Artifact.objects.filter(job_id=job_id)
    return JobDetail(
        job_id=str(job.job_id),
        tenant_id=job.tenant_id,
        job_type=job.job_type,
        status=job.status,
        progress=job.progress,
        source_id=job.source_id,
        soma_session_id=job.soma_session_id,
        parameters=job.parameters,
        result_summary=job.result_summary,
        error_message=job.error_message,
        created_at=job.created_at.isoformat(),
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        artifacts=[
            {
                "artifact_id": a.artifact_id,
                "artifact_type": a.artifact_type,
                "format": a.format,
                "storage_path": a.storage_path,
                "size_bytes": a.size_bytes,
            }
            for a in artifacts
        ],
    )


@admin_router.post("/jobs/{job_id}/cancel", response=JobActionResponse)
def cancel_job(request, job_id: str):
    """Cancel a running job."""
    from apps.core.api_utils import run_async
    from apps.core.lib.temporal_client import get_temporal_client
    from apps.workflows.models import Job

    job = Job.objects.filter(id=job_id).first()
    if not job:
        raise HttpError(404, "Job not found")

    if job.status not in ("running", "queued"):
        return JobActionResponse(
            job_id=job_id,
            action="cancel",
            status="skipped",
            message=f"Job is {job.status}, not cancellable",
        )

    # Cancel Temporal workflow
    try:
        client = run_async(get_temporal_client)
        for prefix in (
            "ingest",
            "profile",
            "quality",
            "analyze",
            "capsule",
            "scrape",
            "streaming",
            "benchmark",
            "segment",
            "regression",
        ):
            try:
                handle = client.get_workflow_handle(f"{prefix}-{job_id}")
                run_async(handle.cancel)
                break
            except Exception:
                continue
    except Exception as exc:
        logger.warning("Failed to cancel Temporal workflow for %s: %s", job_id, exc)

    job.status = "cancelled"
    job.save(update_fields=["status"])

    return JobActionResponse(
        job_id=job_id,
        action="cancel",
        status="cancelled",
    )


@admin_router.post("/jobs/{job_id}/reset", response=JobActionResponse)
def reset_job(request, job_id: str):
    """Reset a failed job back to queued for retry."""
    from apps.workflows.models import Job

    job = Job.objects.filter(id=job_id).first()
    if not job:
        raise HttpError(404, "Job not found")

    if job.status != "failed":
        return JobActionResponse(
            job_id=job_id,
            action="reset",
            status="skipped",
            message=f"Job is {job.status}, only failed jobs can be reset",
        )

    job.status = "queued"
    job.progress = 0
    job.error_message = None
    job.started_at = None
    job.completed_at = None
    job.save()

    return JobActionResponse(
        job_id=job_id,
        action="reset",
        status="queued",
        message="Job reset to queued. It will be picked up by the worker.",
    )


# ── Sources ──────────────────────────────────────────────────────────────────


@admin_router.get("/sources", response=list[SourceListItem])
def list_sources(request, tenant_id: str | None = None):
    """List all data sources across tenants."""
    from apps.discovery.models import Source

    qs = Source.objects.all()
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)

    return [
        SourceListItem(
            source_id=str(s.id),
            tenant_id=s.tenant_id,
            name=s.name,
            source_type=s.source_type,
            status=s.status,
            created_at=s.created_at.isoformat(),
            datahub_urn=s.datahub_urn,
            connection_config=s.connection_config,
        )
        for s in qs.order_by("-created_at")
    ]


@admin_router.post("/sources", response=SourceListItem)
def create_source(request, payload: SourceCreateRequest):
    """Create a new data source (admin override — no tenant check)."""
    from apps.discovery.models import Source

    tenant_id = get_tenant_id(request) or "default"
    source = Source.objects.create(
        tenant_id=tenant_id,
        name=payload.name,
        source_type=payload.source_type,
        connection_config=payload.connection_config,
        credentials=payload.credentials,
        sync_schedule=payload.sync_schedule,
        status="pending",
    )
    return SourceListItem(
        source_id=str(source.id),
        tenant_id=tenant_id,
        name=source.name,
        source_type=source.source_type,
        status=source.status,
        created_at=source.created_at.isoformat(),
        connection_config=source.connection_config,
    )


@admin_router.delete("/sources/{source_id}")
def delete_source(request, source_id: str):
    """Delete a data source."""
    from apps.discovery.models import Source

    source = Source.objects.filter(id=source_id).first()
    if not source:
        raise HttpError(404, "Source not found")
    source.delete()
    return {"status": "deleted", "source_id": source_id}


# ── Governance ───────────────────────────────────────────────────────────────


@admin_router.get("/governance/policies", response=list[PolicyListItem])
def list_policies(request, tenant_id: str | None = None):
    """List all governance policies."""
    from apps.governance.models import Policy

    qs = Policy.objects.all()
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)

    return [
        PolicyListItem(
            id=str(p.id),
            name=p.name,
            policy_type=p.policy_type,
            status=p.status,
            enforcement_level=p.enforcement_level,
            tenant_id=p.tenant_id,
            created_at=p.created_at.isoformat(),
        )
        for p in qs.order_by("-created_at")
    ]


@admin_router.get("/governance/contracts", response=list[ContractListItem])
def list_contracts(request, tenant_id: str | None = None):
    """List all data contracts."""
    from apps.governance.models import DataContract

    qs = DataContract.objects.all()
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)

    return [
        ContractListItem(
            id=str(c.id),
            name=c.name,
            dataset_urn=c.dataset_urn,
            status=c.status,
            version=c.version,
            tenant_id=c.tenant_id,
            created_at=c.created_at.isoformat(),
        )
        for c in qs.order_by("-created_at")
    ]


@admin_router.get("/governance/quotas", response=list[QuotaInfo])
def list_quotas(request):
    """List quota usage for all tenants."""
    from apps.core.lib.tenant_quotas import (
        ResourceType,
        get_quota_manager,
        get_usage_stats,
    )

    manager = get_quota_manager()
    from apps.workflows.models import Job

    tenant_ids = list(Job.objects.values_list("tenant_id", flat=True).distinct()[:50])

    result = []
    for tid in tenant_ids:
        tier = manager.get_tenant_tier(tid)
        policy = manager.get_policy(tid)
        usage_map = {s.resource.value: s for s in get_usage_stats(tid)}

        jobs_limit = policy.get_limit(ResourceType.JOBS_PER_DAY)
        artifacts_limit = policy.get_limit(ResourceType.TOTAL_STORAGE_MB)
        sources_limit = policy.get_limit(ResourceType.WORKFLOWS_PER_DAY)

        class _DefaultUsage:
            current_usage = 0
        _default = _DefaultUsage()

        result.append(
            QuotaInfo(
                tenant_id=tid,
                tier=tier.value,
                jobs_today=int(
                    usage_map.get(
                        ResourceType.JOBS_PER_DAY.value,
                        _default,
                    ).current_usage  # type: ignore[attr-defined]
                ),
                jobs_limit=int(jobs_limit.limit) if jobs_limit else 0,
                artifacts_gb=round(
                    float(
                        usage_map.get(
                            ResourceType.TOTAL_STORAGE_MB.value,
                            _default,
                        ).current_usage  # type: ignore[attr-defined]
                    )
                    / 1024,
                    3,
                ),
                artifacts_limit_gb=(
                    round(float(artifacts_limit.limit) / 1024, 3)
                    if artifacts_limit
                    else 0
                ),
                sources_count=int(
                    usage_map.get(
                        ResourceType.WORKFLOWS_PER_DAY.value,
                        _default,
                    ).current_usage  # type: ignore[attr-defined]
                ),
                sources_limit=int(sources_limit.limit) if sources_limit else 0,
            )
        )

    return result


# ── Capsules ─────────────────────────────────────────────────────────────────


@admin_router.get("/capsules", response=list[CapsuleListItem])
def list_capsules(request, status: str | None = None):
    """List all capsules across tenants."""
    from apps.capsules.models import Capsule

    qs = Capsule.objects.all()
    if status:
        qs = qs.filter(status=status)

    return [
        CapsuleListItem(
            id=str(c.id),
            name=c.name,
            version=c.version,
            status=c.status,
            capsule_type=c.capsule_type,
            tenant_id=c.tenant_id,
            install_count=c.install_count,
            execution_count=c.execution_count,
            created_at=c.created_at.isoformat(),
        )
        for c in qs.order_by("-created_at")
    ]


@admin_router.post("/capsules/{capsule_id}/activate")
def activate_capsule(request, capsule_id: str):
    """Activate a certified capsule."""
    from apps.capsules.models import Capsule
    from apps.capsules.services.capsule_core import activate_capsule

    capsule = Capsule.objects.filter(id=capsule_id).first()
    if not capsule:
        raise HttpError(404, "Capsule not found")
    result = activate_capsule(capsule)
    return {"id": str(result.id), "status": result.status}


@admin_router.post("/capsules/{capsule_id}/suspend")
def suspend_capsule(request, capsule_id: str, payload: CapsuleActionRequest):
    """Suspend a capsule."""
    from apps.capsules.models import Capsule
    from apps.capsules.services.capsule_core import suspend_capsule

    capsule = Capsule.objects.filter(id=capsule_id).first()
    if not capsule:
        raise HttpError(404, "Capsule not found")
    result = suspend_capsule(capsule, payload.reason)
    return {"id": str(result.id), "status": result.status}


@admin_router.post("/capsules/{capsule_id}/archive")
def archive_capsule(request, capsule_id: str):
    """Archive a capsule."""
    from apps.capsules.models import Capsule
    from apps.capsules.services.capsule_core import archive_capsule

    capsule = Capsule.objects.filter(id=capsule_id).first()
    if not capsule:
        raise HttpError(404, "Capsule not found")
    result = archive_capsule(capsule)
    return {"id": str(result.id), "status": result.status}


# ── Ontology ─────────────────────────────────────────────────────────────────


@admin_router.get("/ontology/types", response=list[ObjectTypeListItem])
def list_object_types(request, tenant_id: str | None = None):
    """List all ontology object types."""
    from apps.ontology.models import Object, ObjectType, Property

    qs = ObjectType.objects.filter(deleted_at__isnull=True)
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)

    result = []
    for ot in qs.order_by("name"):
        prop_count = Property.objects.filter(object_type=ot).count()
        instance_count = Object.objects.filter(
            object_type=ot, deleted_at__isnull=True
        ).count()
        result.append(
            ObjectTypeListItem(
                id=str(ot.id),
                name=ot.name,
                description=ot.description,
                version=ot.version,
                property_count=prop_count,
                instance_count=instance_count,
                tenant_id=ot.tenant_id,
                created_at=ot.created_at.isoformat(),
            )
        )
    return result


@admin_router.get(
    "/ontology/types/{type_id}/properties", response=list[PropertyListItem]
)
def list_properties(request, type_id: str):
    """List properties for an object type."""
    from apps.ontology.models import ObjectType, Property

    ot = ObjectType.objects.filter(id=type_id).first()
    if not ot:
        raise HttpError(404, "Object type not found")

    return [
        PropertyListItem(
            id=str(p.id),
            name=p.name,
            property_type=p.property_type,
            required=p.required,
            object_type_name=ot.name,
        )
        for p in Property.objects.filter(object_type=ot).order_by("name")
    ]


@admin_router.get("/ontology/links")
def list_link_types(request, tenant_id: str | None = None):
    """List all link types."""
    from apps.ontology.models import LinkType

    qs = LinkType.objects.filter(deleted_at__isnull=True)
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)

    return [
        {
            "id": str(lt.id),
            "name": lt.name,
            "source_type": lt.source_object_type.name,
            "target_type": lt.target_object_type.name,
            "cardinality": lt.cardinality,
            "tenant_id": lt.tenant_id,
        }
        for lt in qs.order_by("name")
    ]


# ── Audit Log ────────────────────────────────────────────────────────────────


@admin_router.get("/audit", response=list[AuditLogItem])
def list_audit_logs(
    request,
    action: str | None = None,
    actor: str | None = None,
    resource_type: str | None = None,
    tenant_id: str | None = None,
    limit: int = 100,
):
    """List audit log entries with filtering."""
    from apps.core.models import AuditLog

    qs = AuditLog.objects.all()
    if action:
        qs = qs.filter(action__icontains=action)
    if actor:
        qs = qs.filter(actor__icontains=actor)
    if resource_type:
        qs = qs.filter(resource_type=resource_type)
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)

    return [
        AuditLogItem(
            id=str(a.id),
            actor=a.actor,
            action=a.action,
            resource_type=a.resource_type,
            resource_id=a.resource_id,
            outcome=a.outcome,
            details=a.details,
            ip_address=str(a.ip_address) if a.ip_address else None,
            created_at=a.created_at.isoformat(),
        )
        for a in qs.order_by("-created_at")[:limit]
    ]


# ── System Settings ──────────────────────────────────────────────────────────


@admin_router.get("/settings", response=list[SystemSettingItem])
def list_settings(request):
    """List all system settings."""
    from apps.core.models import SystemSetting

    return [
        SystemSettingItem(
            key=s.key,
            value="***" if s.is_secret else s.value,
            value_type=s.value_type,
            description=s.description,
            is_secret=s.is_secret,
        )
        for s in SystemSetting.objects.order_by("key")
    ]


@admin_router.put("/settings/{key}")
def update_setting(request, key: str, payload: SystemSettingUpdate):
    """Update a system setting."""
    from apps.core.models import SystemSetting

    setting = SystemSetting.objects.filter(key=key).first()
    if not setting:
        raise HttpError(404, f"Setting '{key}' not found")

    setting.value = payload.value
    setting.save(update_fields=["value", "updated_at"])
    return {"key": key, "status": "updated"}


# ── SQL Console ──────────────────────────────────────────────────────────────


@admin_router.post("/sql/execute", response=SqlResult)
def execute_sql(request, payload: SqlExecuteRequest):
    """Execute a read-only SQL query via Trino."""
    try:
        client = get_trino_client()
        result = client.execute(payload.sql, limit=payload.limit)
        return SqlResult(
            columns=result.columns,
            rows=result.rows,
            row_count=result.row_count,
            truncated=result.truncated,
            execution_time_ms=result.execution_time_ms,
            query_id=result.query_id,
        )
    except ValueError as exc:
        raise HttpError(400, str(exc))
    except Exception as exc:
        logger.exception("SQL execution failed")
        raise HttpError(500, str(exc))


@admin_router.get("/sql/tables", response=list[TableInfo])
def list_tables(request, schema: str | None = None):
    """List all available tables."""
    try:
        client = get_trino_client()
        tables = client.get_tables(schema)
        return [
            TableInfo(name=t if isinstance(t, str) else t.get("name", str(t)))  # type: ignore[reportCallIssue]
            for t in tables
        ]
    except Exception as exc:
        logger.exception("Failed to list tables")
        raise HttpError(500, str(exc))


# ── Search Index ─────────────────────────────────────────────────────────────


@admin_router.post("/search/index", response=dict)
def index_document(request, payload: SearchIndexRequest):
    """Index a document for semantic search."""
    import uuid

    from apps.core.middleware import get_tenant_id
    from apps.search.lib.embeddings import get_embedding_extractor, get_sparse_embedder
    from apps.search.lib.milvus_store import get_vector_store

    tenant_id = get_tenant_id(request) or "default"
    store = get_vector_store()
    dense = get_embedding_extractor(model="dense", dimensions=1536)
    sparse = get_sparse_embedder()

    dense_vec = dense.embed([payload.text])
    if not dense_vec.embeddings:
        raise HttpError(400, "Embedding extraction failed")

    sparse_vec = sparse.embed([payload.text])[0]
    item_id = payload.item_id or str(uuid.uuid4())
    metadata = payload.metadata or {}
    metadata["tenant_id"] = tenant_id
    metadata["text_preview"] = payload.text[:200]

    store.add(
        id=item_id,
        vector=dense_vec.embeddings[0],
        metadata=metadata,
        sparse_vector=sparse_vec,
    )
    return {"id": item_id, "status": "indexed"}


@admin_router.get("/search/query", response=list[SearchIndexItem])
def search_index(request, q: str, limit: int = 10):
    """Search the vector index."""
    from apps.search.lib.embeddings import get_embedding_extractor, get_sparse_embedder
    from apps.search.lib.milvus_store import get_vector_store

    store = get_vector_store()
    dense = get_embedding_extractor(model="dense", dimensions=1536)
    sparse = get_sparse_embedder()

    dense_vec = dense.embed([q])
    if not dense_vec.embeddings:
        return []

    sparse_vec = sparse.embed([q])[0]
    results = store.search(
        query_vector=dense_vec.embeddings[0],
        k=limit,
        query_sparse_vector=sparse_vec,
    )

    return [
        SearchIndexItem(
            id=item.id,
            score=round(score, 6),
            metadata=item.metadata,
            text_preview=item.metadata.get("text_preview", "")[:200],
        )
        for item, score in results
    ]


@admin_router.delete("/search/{item_id}")
def delete_index_item(request, item_id: str):
    """Delete an item from the search index."""
    from apps.search.lib.milvus_store import get_vector_store

    store = get_vector_store()
    store.delete(item_id)
    return {"status": "deleted", "id": item_id}


# ── Scraper ──────────────────────────────────────────────────────────────────


@admin_router.get("/scraper/jobs", response=list[ScraperJobListItem])
def list_scraper_jobs(request, status: str | None = None, limit: int = 50):
    """List scrape jobs."""
    from apps.scraper.models import ScrapeJob

    qs = ScrapeJob.objects.all()
    if status:
        qs = qs.filter(status=status)

    return [
        ScraperJobListItem(
            job_id=str(j.job_id),
            status=j.status,
            tenant_id=j.tenant_id,
            pages_fetched=j.pages_fetched,
            bytes_processed=j.bytes_processed,
            artifact_count=j.artifact_count,
            error_count=j.error_count,
            created_at=j.created_at.isoformat(),
            started_at=j.started_at.isoformat() if j.started_at else None,
            finished_at=j.finished_at.isoformat() if j.finished_at else None,
        )
        for j in qs.order_by("-created_at")[:limit]
    ]


# ── Tenants ──────────────────────────────────────────────────────────────────


@admin_router.get("/tenants", response=list[TenantInfo])
def list_tenants(request):
    """List all known tenants with activity summary."""
    from apps.discovery.models import Source
    from apps.workflows.models import Artifact, Job

    tenant_ids = list(Job.objects.values_list("tenant_id", flat=True).distinct()[:100])

    result = []
    for tid in tenant_ids:
        job_count = Job.objects.filter(tenant_id=tid).count()
        source_count = Source.objects.filter(tenant_id=tid).count()
        artifact_count = Artifact.objects.filter(tenant_id=tid).count()
        last_job = Job.objects.filter(tenant_id=tid).order_by("-created_at").first()

        result.append(
            TenantInfo(
                tenant_id=tid,
                realm="default",
                job_count=job_count,
                source_count=source_count,
                artifact_count=artifact_count,
                last_activity=last_job.created_at.isoformat() if last_job else None,
            )
        )

    return result


# ── Health Checks (internal) ─────────────────────────────────────────────────


def _check_postgres() -> tuple[bool, str]:
    from django.db import connection

    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return True, "Connected"


def _check_redis() -> tuple[bool, str]:
    from django.core.cache import cache

    cache.set("_health_check", "ok", 10)
    val = cache.get("_health_check")
    return val == "ok", "Connected"


def _check_vault() -> tuple[bool, str]:
    import httpx

    resp = httpx.get(f"{settings.secrets_vault_url}/v1/sys/health", timeout=5.0)
    return resp.status_code == 200, f"Status {resp.status_code}"


def _check_temporal() -> tuple[bool, str]:
    if not settings.temporal_host:
        return False, "Not configured"
    import socket

    host, port = settings.temporal_host.rsplit(":", 1)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    try:
        sock.connect((host, int(port)))
        return True, "Connected"
    except Exception:
        return False, "Unreachable"
    finally:
        sock.close()


def _check_minio() -> tuple[bool, str]:
    import httpx

    resp = httpx.get(f"http://{settings.minio_endpoint}/minio/health/live", timeout=5.0)
    return resp.status_code == 200, f"Status {resp.status_code}"


def _check_kafka() -> tuple[bool, str]:
    if not settings.kafka_bootstrap_servers:
        return False, "Not configured"
    import socket

    host, port = settings.kafka_bootstrap_servers.split(",")[0].rsplit(":", 1)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    try:
        sock.connect((host, int(port)))
        return True, "Connected"
    except Exception:
        return False, "Unreachable"
    finally:
        sock.close()


def _check_milvus() -> tuple[bool, str]:
    import httpx

    uri = settings.milvus_uri or f"http://{settings.milvus_host}:{settings.milvus_port}"
    try:
        resp = httpx.get(f"{uri}/healthz", timeout=3.0)
        return resp.status_code == 200, f"Status {resp.status_code}"
    except Exception:
        return False, "Unreachable"


def _check_trino() -> tuple[bool, str]:
    if not settings.trino_host:
        return False, "Not configured"
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(3)
    try:
        sock.connect((settings.trino_host, settings.trino_port))
        return True, "Connected"
    except Exception:
        return False, "Unreachable"
    finally:
        sock.close()
