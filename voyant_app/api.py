"""Django Ninja API for Voyant."""
from __future__ import annotations

import io
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from asgiref.sync import async_to_sync
from django.http import StreamingHttpResponse
from ninja import NinjaAPI, Router, Schema
from ninja.errors import HttpError
from pydantic import Field

from voyant.api.middleware import get_soma_session_id, get_tenant_id
from voyant.core.config import get_settings
from voyant.core.namespace_analyzer import NamespaceViolationError, validate_table_access
from voyant.core.trino import get_trino_client
from voyant.core.temporal_client import get_temporal_client
from voyant.integrations.soma import (
    SomaContextError,
    SomaPolicyDenied,
    SomaPolicyUnavailable,
    create_task_for_job,
    enforce_policy,
    remember_summary,
    update_task_status,
)
from voyant.workflows.analyze_workflow import AnalyzeWorkflow
from voyant.workflows.ingest_workflow import IngestDataWorkflow
from voyant.workflows.profile_workflow import ProfileWorkflow
from voyant.workflows.types import IngestParams
from voyant_app.models import Artifact, Job, PresetJob, Source

logger = logging.getLogger(__name__)
settings = get_settings()

api = NinjaAPI(
    title="Voyant API",
    description="Autonomous Data Intelligence for AI Agents",
    version="3.0.0",
)

sources_router = Router()
jobs_router = Router()
sql_router = Router()
governance_router = Router()
presets_router = Router()
artifacts_router = Router()
analyze_router = Router()
discovery_router = Router()
search_router = Router()


def _run_async(func, *args, **kwargs):
    return async_to_sync(func)(*args, **kwargs)


def _apply_policy(action: str, prompt: str, metadata: Dict[str, Any]) -> None:
    try:
        _run_async(enforce_policy, action, prompt, metadata)
    except SomaContextError as exc:
        raise HttpError(400, str(exc)) from exc
    except SomaPolicyDenied as exc:
        raise HttpError(403, exc.details or {"reason": str(exc)}) from exc
    except SomaPolicyUnavailable as exc:
        raise HttpError(503, str(exc)) from exc


# =============================================================================
# Sources
# =============================================================================

class DiscoverRequest(Schema):
    hint: str = Field(..., description="Data source hint (URL, path, connection string)")


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


def _detect_source_type(hint: str) -> Dict[str, Any]:
    hint_lower = hint.lower()

    if hint_lower.startswith("postgresql://") or hint_lower.startswith("postgres://"):
        return {
            "source_type": "postgresql",
            "connector": "airbyte/source-postgres",
            "properties": {"host": hint.split("@")[-1].split("/")[0] if "@" in hint else "unknown"},
            "confidence": 0.95,
        }
    if hint_lower.startswith("mysql://"):
        return {
            "source_type": "mysql",
            "connector": "airbyte/source-mysql",
            "properties": {},
            "confidence": 0.95,
        }
    if hint_lower.startswith("mongodb://") or hint_lower.startswith("mongodb+srv://"):
        return {
            "source_type": "mongodb",
            "connector": "airbyte/source-mongodb-v2",
            "properties": {},
            "confidence": 0.95,
        }
    if "snowflake" in hint_lower:
        return {
            "source_type": "snowflake",
            "connector": "airbyte/source-snowflake",
            "properties": {},
            "confidence": 0.9,
        }
    if hint_lower.endswith(".csv"):
        return {
            "source_type": "csv",
            "connector": "file",
            "properties": {"format": "csv"},
            "confidence": 0.9,
        }
    if hint_lower.endswith(".parquet"):
        return {
            "source_type": "parquet",
            "connector": "file",
            "properties": {"format": "parquet"},
            "confidence": 0.9,
        }
    if hint_lower.endswith(".json") or hint_lower.endswith(".jsonl"):
        return {
            "source_type": "json",
            "connector": "file",
            "properties": {"format": "json"},
            "confidence": 0.9,
        }
    if "s3://" in hint_lower:
        return {
            "source_type": "s3",
            "connector": "airbyte/source-s3",
            "properties": {"bucket": hint.split("/")[2] if len(hint.split("/")) > 2 else ""},
            "confidence": 0.9,
        }
    if "sheets.google.com" in hint_lower or "docs.google.com/spreadsheets" in hint_lower:
        return {
            "source_type": "google_sheets",
            "connector": "airbyte/source-google-sheets",
            "properties": {},
            "confidence": 0.9,
        }
    if hint_lower.startswith("http://") or hint_lower.startswith("https://"):
        return {
            "source_type": "api",
            "connector": "airbyte/source-http",
            "properties": {"url": hint},
            "confidence": 0.5,
        }
    return {
        "source_type": "unknown",
        "connector": "unknown",
        "properties": {},
        "confidence": 0.1,
    }


@sources_router.post("/discover", response=DiscoverResponse)
def discover_source(_request, payload: DiscoverRequest):
    detected = _detect_source_type(payload.hint)
    return DiscoverResponse(
        source_type=detected["source_type"],
        detected_properties=detected["properties"],
        suggested_connector=detected["connector"],
        confidence=detected["confidence"],
    )


@sources_router.post("", response=SourceResponse)
def create_source(_request, payload: CreateSourceRequest):
    tenant_id = get_tenant_id()
    source = Source.objects.create(
        tenant_id=tenant_id,
        name=payload.name,
        source_type=payload.source_type,
        connection_config=payload.connection_config,
        credentials=payload.credentials,
        sync_schedule=payload.sync_schedule,
        status="pending",
    )
    return SourceResponse(
        source_id=str(source.source_id),
        tenant_id=tenant_id,
        name=source.name,
        source_type=source.source_type,
        status=source.status,
        created_at=source.created_at.isoformat(),
        datahub_urn=source.datahub_urn,
    )


@sources_router.get("", response=List[SourceResponse])
def list_sources(_request):
    tenant_id = get_tenant_id()
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
def get_source(_request, source_id: str):
    source = Source.objects.filter(source_id=source_id).first()
    if not source:
        raise HttpError(404, "Source not found")
    tenant_id = get_tenant_id()
    if source.tenant_id != tenant_id:
        raise HttpError(403, "Access denied")
    return SourceResponse(
        source_id=str(source.source_id),
        tenant_id=source.tenant_id,
        name=source.name,
        source_type=source.source_type,
        status=source.status,
        created_at=source.created_at.isoformat(),
        datahub_urn=source.datahub_urn,
    )


@sources_router.delete("/{source_id}")
def delete_source(_request, source_id: str):
    source = Source.objects.filter(source_id=source_id).first()
    if not source:
        raise HttpError(404, "Source not found")
    tenant_id = get_tenant_id()
    if source.tenant_id != tenant_id:
        raise HttpError(403, "Access denied")
    source.delete()
    return {"status": "deleted", "source_id": str(source.source_id)}


# =============================================================================
# Jobs
# =============================================================================

class IngestRequest(Schema):
    source_id: str
    mode: str = Field(default="full", description="full or incremental")
    tables: Optional[List[str]] = None


class ProfileRequest(Schema):
    source_id: str
    table: Optional[str] = None
    sample_size: int = Field(default=10000, ge=100, le=1000000)


class QualityRequest(Schema):
    source_id: str
    table: Optional[str] = None
    checks: Optional[List[str]] = None


class JobResponse(Schema):
    job_id: str
    tenant_id: str
    job_type: str
    status: str
    progress: int
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result_summary: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


def _create_job(job_type: str, source_id: str, params: Dict[str, Any]) -> Job:
    tenant_id = get_tenant_id()
    soma_session_id = get_soma_session_id() or None
    job = Job.objects.create(
        tenant_id=tenant_id,
        job_type=job_type,
        source_id=source_id,
        soma_session_id=soma_session_id,
        status="queued",
        progress=0,
        parameters=params,
    )
    logger.info("Created %s job %s for source %s", job_type, job.job_id, source_id)
    return job


@jobs_router.post("/ingest", response=JobResponse)
def trigger_ingest(_request, payload: IngestRequest):
    try:
        tenant_id = get_tenant_id()
        if payload.tables:
            for table in payload.tables:
                validate_table_access(tenant_id, table)
    except NamespaceViolationError as exc:
        raise HttpError(403, str(exc)) from exc

    policy_prompt = (
        f"voyant ingest source_id={payload.source_id} "
        f"mode={payload.mode} tables={payload.tables or []}"
    )
    _apply_policy(
        "ingest",
        policy_prompt,
        {"source_id": payload.source_id, "mode": payload.mode, "tables": payload.tables},
    )

    job = _create_job(
        "ingest",
        payload.source_id,
        {"mode": payload.mode, "tables": payload.tables},
    )

    soma_task_id = _run_async(
        create_task_for_job,
        str(job.job_id),
        job.job_type,
        job.source_id,
        policy_prompt,
    )
    if soma_task_id:
        Job.objects.filter(job_id=job.job_id).update(soma_task_id=soma_task_id)

    try:
        client = _run_async(get_temporal_client)
        _run_async(
            client.start_workflow,
            IngestDataWorkflow.run,
            IngestParams(
                job_id=str(job.job_id),
                source_id=payload.source_id,
                mode=payload.mode,
                tables=payload.tables,
            ),
            id=f"ingest-{job.job_id}",
            task_queue=settings.temporal_task_queue,
        )
        job.status = "running"
        job.save(update_fields=["status"])
        if soma_task_id:
            _run_async(update_task_status, soma_task_id, "running")
    except Exception as exc:
        logger.error("Failed to start workflow: %s", exc)
        job.status = "failed"
        job.error_message = str(exc)
        job.save(update_fields=["status", "error_message"])
        if soma_task_id:
            _run_async(update_task_status, soma_task_id, "failed", reason=str(exc))

    return JobResponse(
        job_id=str(job.job_id),
        tenant_id=job.tenant_id,
        job_type=job.job_type,
        status=job.status,
        progress=job.progress,
        created_at=job.created_at.isoformat(),
    )


@jobs_router.post("/profile", response=JobResponse)
def trigger_profile(_request, payload: ProfileRequest):
    try:
        tenant_id = get_tenant_id()
        if payload.table:
            validate_table_access(tenant_id, payload.table)
    except NamespaceViolationError as exc:
        raise HttpError(403, str(exc)) from exc

    policy_prompt = (
        f"voyant profile source_id={payload.source_id} "
        f"table={payload.table or ''} sample_size={payload.sample_size}"
    )
    _apply_policy(
        "profile",
        policy_prompt,
        {
            "source_id": payload.source_id,
            "table": payload.table,
            "sample_size": payload.sample_size,
        },
    )

    job = _create_job(
        "profile",
        payload.source_id,
        {"table": payload.table, "sample_size": payload.sample_size},
    )

    soma_task_id = _run_async(
        create_task_for_job,
        str(job.job_id),
        job.job_type,
        job.source_id,
        policy_prompt,
    )
    if soma_task_id:
        Job.objects.filter(job_id=job.job_id).update(soma_task_id=soma_task_id)

    try:
        client = _run_async(get_temporal_client)
        _run_async(
            client.start_workflow,
            ProfileWorkflow.run,
            {
                "source_id": payload.source_id,
                "table": payload.table,
                "sample_size": payload.sample_size,
                "job_id": str(job.job_id),
                "tenant_id": job.tenant_id,
            },
            id=f"profile-{job.job_id}",
            task_queue=settings.temporal_task_queue,
        )
        job.status = "running"
        job.save(update_fields=["status"])
        if soma_task_id:
            _run_async(update_task_status, soma_task_id, "running")
    except Exception as exc:
        logger.error("Failed to start profile workflow: %s", exc)
        job.status = "failed"
        job.error_message = str(exc)
        job.save(update_fields=["status", "error_message"])
        if soma_task_id:
            _run_async(update_task_status, soma_task_id, "failed", reason=str(exc))

    return JobResponse(
        job_id=str(job.job_id),
        tenant_id=job.tenant_id,
        job_type=job.job_type,
        status=job.status,
        progress=job.progress,
        created_at=job.created_at.isoformat(),
    )


@jobs_router.post("/quality", response=JobResponse)
def trigger_quality(_request, payload: QualityRequest):
    try:
        tenant_id = get_tenant_id()
        if payload.table:
            validate_table_access(tenant_id, payload.table)
    except NamespaceViolationError as exc:
        raise HttpError(403, str(exc)) from exc

    policy_prompt = (
        f"voyant quality source_id={payload.source_id} "
        f"table={payload.table or ''} checks={payload.checks or []}"
    )
    _apply_policy(
        "quality",
        policy_prompt,
        {
            "source_id": payload.source_id,
            "table": payload.table,
            "checks": payload.checks,
        },
    )

    job = _create_job(
        "quality",
        payload.source_id,
        {"table": payload.table, "checks": payload.checks},
    )

    soma_task_id = _run_async(
        create_task_for_job,
        str(job.job_id),
        job.job_type,
        job.source_id,
        policy_prompt,
    )
    if soma_task_id:
        Job.objects.filter(job_id=job.job_id).update(soma_task_id=soma_task_id)

    return JobResponse(
        job_id=str(job.job_id),
        tenant_id=job.tenant_id,
        job_type=job.job_type,
        status=job.status,
        progress=job.progress,
        created_at=job.created_at.isoformat(),
    )


@jobs_router.get("", response=List[JobResponse])
def list_jobs(
    _request,
    status: Optional[str] = None,
    job_type: Optional[str] = None,
    limit: int = 50,
):
    tenant_id = get_tenant_id()
    query = Job.objects.filter(tenant_id=tenant_id)
    if status:
        query = query.filter(status=status)
    if job_type:
        query = query.filter(job_type=job_type)

    jobs = query.order_by("-created_at")[:limit]
    return [
        JobResponse(
            job_id=str(job.job_id),
            tenant_id=job.tenant_id,
            job_type=job.job_type,
            status=job.status,
            progress=job.progress,
            created_at=job.created_at.isoformat(),
            started_at=job.started_at.isoformat() if job.started_at else None,
            completed_at=job.completed_at.isoformat() if job.completed_at else None,
            result_summary=job.result_summary,
            error_message=job.error_message,
        )
        for job in jobs
    ]


@jobs_router.get("/{job_id}", response=JobResponse)
def get_job(_request, job_id: str):
    job = Job.objects.filter(job_id=job_id).first()
    if not job:
        raise HttpError(404, "Job not found")
    tenant_id = get_tenant_id()
    if job.tenant_id != tenant_id:
        raise HttpError(403, "Access denied")
    return JobResponse(
        job_id=str(job.job_id),
        tenant_id=job.tenant_id,
        job_type=job.job_type,
        status=job.status,
        progress=job.progress,
        created_at=job.created_at.isoformat(),
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        result_summary=job.result_summary,
        error_message=job.error_message,
    )


@jobs_router.post("/{job_id}/cancel")
def cancel_job(_request, job_id: str):
    job = Job.objects.filter(job_id=job_id).first()
    if not job:
        raise HttpError(404, "Job not found")
    tenant_id = get_tenant_id()
    if job.tenant_id != tenant_id:
        raise HttpError(403, "Access denied")
    if job.status not in ("queued", "running"):
        raise HttpError(400, "Job cannot be cancelled")

    job.status = "cancelled"
    job.completed_at = datetime.utcnow()
    job.save(update_fields=["status", "completed_at"])

    if job.soma_task_id:
        _run_async(update_task_status, job.soma_task_id, "cancelled", reason="cancelled")

    logger.info("Cancelled job %s", job_id)
    return {"status": "cancelled", "job_id": str(job.job_id)}


# =============================================================================
# SQL
# =============================================================================

class SqlRequest(Schema):
    sql: str = Field(..., description="SQL query (SELECT only)")
    limit: int = Field(default=1000, ge=1, le=10000)
    parameters: Optional[Dict[str, Any]] = None


class SqlResponse(Schema):
    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    truncated: bool
    execution_time_ms: int
    query_id: Optional[str] = None


@sql_router.post("/query", response=SqlResponse)
def execute_sql(_request, payload: SqlRequest):
    try:
        client = get_trino_client()
        result = client.execute(payload.sql, limit=payload.limit)
        return SqlResponse(
            columns=result.columns,
            rows=result.rows,
            row_count=result.row_count,
            truncated=result.truncated,
            execution_time_ms=result.execution_time_ms,
            query_id=result.query_id,
        )
    except ValueError as exc:
        raise HttpError(400, str(exc)) from exc
    except RuntimeError as exc:
        raise HttpError(503, str(exc)) from exc
    except Exception as exc:
        logger.exception("SQL execution failed")
        raise HttpError(500, f"Query failed: {exc}") from exc


@sql_router.get("/tables")
def list_tables(_request, schema: Optional[str] = None):
    try:
        client = get_trino_client()
        tables = client.get_tables(schema)
        return {"tables": tables, "schema": schema or client.schema}
    except Exception as exc:
        logger.exception("Failed to list tables")
        raise HttpError(500, str(exc)) from exc


@sql_router.get("/tables/{table}/columns")
def get_columns(_request, table: str, schema: Optional[str] = None):
    try:
        client = get_trino_client()
        columns = client.get_columns(table, schema)
        return {"table": table, "columns": columns}
    except Exception as exc:
        logger.exception("Failed to get columns for %s", table)
        raise HttpError(500, str(exc)) from exc


# =============================================================================
# Governance
# =============================================================================

class GovernanceSearchResult(Schema):
    urn: str
    name: str
    type: str
    description: Optional[str] = None
    platform: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class SearchResponse(Schema):
    results: List[GovernanceSearchResult]
    total: int


class LineageNode(Schema):
    urn: str
    name: str
    type: str
    platform: Optional[str] = None


class LineageEdge(Schema):
    source: str
    target: str
    type: str


class LineageResponse(Schema):
    nodes: List[LineageNode]
    edges: List[LineageEdge]


class SchemaField(Schema):
    name: str
    type: str
    nullable: bool = True
    description: Optional[str] = None


class SchemaResponse(Schema):
    urn: str
    fields: List[SchemaField]


DATAHUB_SEARCH_QUERY = """
query search($input: SearchInput!) {
  search(input: $input) {
    total
    searchResults {
      entity {
        urn
        type
        ... on Dataset {
          name
          description
          platform {
            name
          }
          tags {
            tags {
              tag {
                name
              }
            }
          }
        }
      }
    }
  }
}
"""

DATAHUB_LINEAGE_QUERY = """
query lineage($urn: String!, $direction: LineageDirection!, $depth: Int!) {
  entity(urn: $urn) {
    urn
    ... on Dataset {
      name
    }
  }
  lineage(input: { urn: $urn, direction: $direction, depth: $depth }) {
    relationships {
      entity {
        urn
        type
        ... on Dataset {
          name
          platform { name }
        }
      }
      type
    }
  }
}
"""


def _datahub_graphql(query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
    import httpx

    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            f"{settings.datahub_gms_url}/api/graphql",
            json={"query": query, "variables": variables},
        )
        response.raise_for_status()
        data = response.json()

    if "errors" in data:
        logger.error("DataHub GraphQL errors: %s", data["errors"])
        raise HttpError(500, "DataHub query failed")

    return data.get("data", {})


@governance_router.get("/search", response=SearchResponse)
def search_metadata(_request, query: str, types: Optional[str] = None, limit: int = 10):
    try:
        data = _datahub_graphql(
            DATAHUB_SEARCH_QUERY,
            {
                "input": {
                    "type": "DATASET",
                    "query": query,
                    "start": 0,
                    "count": limit,
                }
            },
        )

        results = []
        search_data = data.get("search", {})

        for item in search_data.get("searchResults", []):
            entity = item.get("entity", {})
            tags = []
            if entity.get("tags"):
                tags = [t["tag"]["name"] for t in entity["tags"].get("tags", [])]

            results.append(
                GovernanceSearchResult(
                    urn=entity.get("urn", ""),
                    name=entity.get("name", ""),
                    type=entity.get("type", "DATASET"),
                    description=entity.get("description"),
                    platform=entity.get("platform", {}).get("name") if entity.get("platform") else None,
                    tags=tags,
                )
            )

        return SearchResponse(results=results, total=search_data.get("total", 0))
    except HttpError:
        raise
    except Exception as exc:
        logger.exception("Search failed")
        raise HttpError(500, str(exc)) from exc


@governance_router.get("/lineage/{urn:path}", response=LineageResponse)
def get_lineage(_request, urn: str, direction: str = "both", depth: int = 3):
    try:
        nodes = [LineageNode(urn=urn, name=urn.split(",")[1] if "," in urn else urn, type="dataset")]
        edges = []

        directions = ["UPSTREAM", "DOWNSTREAM"] if direction == "both" else [direction.upper()]
        for dir_enum in directions:
            data = _datahub_graphql(
                DATAHUB_LINEAGE_QUERY,
                {"urn": urn, "direction": dir_enum, "depth": min(depth, 10)},
            )
            lineage = data.get("lineage", {})
            for rel in lineage.get("relationships", []):
                entity = rel.get("entity", {})
                node_urn = entity.get("urn", "")
                nodes.append(
                    LineageNode(
                        urn=node_urn,
                        name=entity.get("name", node_urn),
                        type=entity.get("type", "dataset").lower(),
                        platform=entity.get("platform", {}).get("name") if entity.get("platform") else None,
                    )
                )
                if dir_enum == "UPSTREAM":
                    edges.append(LineageEdge(source=node_urn, target=urn, type=rel.get("type", "PRODUCES")))
                else:
                    edges.append(LineageEdge(source=urn, target=node_urn, type=rel.get("type", "PRODUCES")))

        seen = set()
        unique_nodes = []
        for node in nodes:
            if node.urn not in seen:
                seen.add(node.urn)
                unique_nodes.append(node)

        return LineageResponse(nodes=unique_nodes, edges=edges)
    except HttpError:
        raise
    except Exception as exc:
        logger.exception("Lineage failed")
        raise HttpError(500, str(exc)) from exc


@governance_router.get("/schema/{urn:path}", response=SchemaResponse)
def get_schema(_request, urn: str):
    import httpx

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{settings.datahub_gms_url}/aspects/{urn}?aspect=schemaMetadata",
            )
        if response.status_code == 404:
            raise HttpError(404, "Schema not found")
        response.raise_for_status()
        data = response.json()

        fields = []
        schema_data = data.get("value", {}).get("schemaMetadata", {})
        for field in schema_data.get("fields", []):
            fields.append(
                SchemaField(
                    name=field.get("fieldPath", ""),
                    type=field.get("nativeDataType", "unknown"),
                    nullable=field.get("nullable", True),
                    description=field.get("description"),
                )
            )
        return SchemaResponse(urn=urn, fields=fields)
    except HttpError:
        raise
    except httpx.HTTPError as exc:
        logger.error("DataHub request failed: %s", exc)
        raise HttpError(503, "DataHub unavailable") from exc


from voyant.core.quotas import (
    get_quota_limits as _get_quota_limits,
    get_usage_status as _get_usage_status,
    list_tiers as _list_tiers,
    set_tenant_tier as _set_tenant_tier,
)


class QuotaTierInfo(Schema):
    tier_id: str
    name: str
    max_jobs_per_day: int
    max_artifacts_gb: float
    max_sources: int
    max_concurrent_jobs: int


class QuotaUsageStatus(Schema):
    tenant_id: str
    tier: str
    jobs_today: int
    jobs_limit: int
    jobs_remaining: int
    artifacts_gb: float
    artifacts_limit_gb: float
    sources_count: int
    sources_limit: int
    concurrent_jobs: int
    concurrent_limit: int


class SetTierRequest(Schema):
    tier: str


@governance_router.get("/quotas/tiers", response=List[QuotaTierInfo])
def list_quota_tiers(_request):
    tiers = _list_tiers()
    return [
        QuotaTierInfo(
            tier_id=tier_id,
            name=info["name"],
            max_jobs_per_day=info["max_jobs_per_day"],
            max_artifacts_gb=info["max_artifacts_gb"],
            max_sources=info["max_sources"],
            max_concurrent_jobs=info["max_concurrent_jobs"],
        )
        for tier_id, info in tiers.items()
    ]


@governance_router.get("/quotas/usage", response=QuotaUsageStatus)
def get_quota_usage(_request):
    tenant_id = get_tenant_id()
    status = _get_usage_status(tenant_id)
    return QuotaUsageStatus(**status)


@governance_router.get("/quotas/limits")
def get_quota_limits(_request):
    tenant_id = get_tenant_id()
    return _get_quota_limits(tenant_id)


@governance_router.post("/quotas/tier")
def set_quota_tier(_request, payload: SetTierRequest):
    tenant_id = get_tenant_id()
    try:
        _set_tenant_tier(tenant_id, payload.tier)
        return {"status": "updated", "tenant_id": tenant_id, "tier": payload.tier}
    except ValueError as exc:
        raise HttpError(400, str(exc)) from exc


# =============================================================================
# Presets
# =============================================================================

PRESETS = {
    "financial.revenue_analysis": {
        "name": "Revenue Analysis",
        "category": "financial",
        "description": "Analyze revenue trends, growth rates, and segmentation",
        "parameters": ["date_column", "amount_column", "segment_columns"],
        "output_artifacts": ["profile", "kpi", "chart"],
    },
    "financial.expense_tracking": {
        "name": "Expense Tracking",
        "category": "financial",
        "description": "Track and categorize expenses with anomaly detection",
        "parameters": ["date_column", "amount_column", "category_column"],
        "output_artifacts": ["profile", "kpi", "chart"],
    },
    "financial.margin_analysis": {
        "name": "Margin Analysis",
        "category": "financial",
        "description": "Calculate and analyze profit margins",
        "parameters": ["revenue_column", "cost_column", "segment_columns"],
        "output_artifacts": ["kpi", "chart"],
    },
    "customer.churn_analysis": {
        "name": "Churn Analysis",
        "category": "customer",
        "description": "Analyze customer churn patterns",
        "parameters": ["customer_id", "event_date", "churn_indicator"],
        "output_artifacts": ["profile", "kpi", "model"],
    },
    "customer.segmentation": {
        "name": "Customer Segmentation",
        "category": "customer",
        "description": "RFM analysis and customer clustering",
        "parameters": ["customer_id", "transaction_date", "amount"],
        "output_artifacts": ["profile", "kpi", "chart"],
    },
    "customer.ltv_prediction": {
        "name": "LTV Prediction",
        "category": "customer",
        "description": "Predict customer lifetime value",
        "parameters": ["customer_id", "revenue_history"],
        "output_artifacts": ["kpi", "model"],
    },
    "quality.data_profiling": {
        "name": "Data Profiling",
        "category": "quality",
        "description": "Comprehensive data profiling with statistics",
        "parameters": ["sample_size"],
        "output_artifacts": ["profile"],
    },
    "quality.anomaly_detection": {
        "name": "Anomaly Detection",
        "category": "quality",
        "description": "Detect data anomalies and outliers",
        "parameters": ["numeric_columns", "threshold"],
        "output_artifacts": ["quality", "chart"],
    },
    "quality.schema_validation": {
        "name": "Schema Validation",
        "category": "quality",
        "description": "Validate data against expected schema",
        "parameters": ["expected_schema"],
        "output_artifacts": ["quality"],
    },
    "ops.inventory_analysis": {
        "name": "Inventory Analysis",
        "category": "operations",
        "description": "Analyze inventory levels and turnover",
        "parameters": ["product_id", "quantity", "date"],
        "output_artifacts": ["profile", "kpi", "chart"],
    },
    "ops.supply_chain": {
        "name": "Supply Chain Analysis",
        "category": "operations",
        "description": "Analyze supply chain performance",
        "parameters": ["supplier_id", "lead_time", "cost"],
        "output_artifacts": ["kpi", "chart"],
    },
}


class PresetInfo(Schema):
    name: str
    category: str
    description: str
    parameters: List[str]
    output_artifacts: List[str]


class PresetExecuteRequest(Schema):
    source_id: str
    parameters: Dict[str, Any] = Field(default_factory=dict)


class PresetExecuteResponse(Schema):
    job_id: str
    preset_name: str
    status: str
    created_at: str


@presets_router.get("", response=Dict[str, List[PresetInfo]])
def list_presets(_request, category: Optional[str] = None):
    presets = []
    for key, preset in PRESETS.items():
        if category and preset["category"] != category:
            continue
        presets.append(
            PresetInfo(
                name=key,
                category=preset["category"],
                description=preset["description"],
                parameters=preset["parameters"],
                output_artifacts=preset["output_artifacts"],
            )
        )

    grouped: Dict[str, List[PresetInfo]] = {}
    for preset in presets:
        grouped.setdefault(preset.category, []).append(preset)
    return grouped


from voyant.core.kpi_templates import (
    get_categories as _get_kpi_categories,
    get_template as _get_kpi_template,
    list_templates as _list_kpi_templates,
    render_template as _render_kpi_template,
)


class KPITemplateInfo(Schema):
    name: str
    category: str
    description: str
    required_columns: List[str]
    optional_columns: Dict[str, str] = Field(default_factory=dict)
    output_columns: List[str] = Field(default_factory=list)


class KPIRenderRequest(Schema):
    parameters: Dict[str, str]


class KPIRenderResponse(Schema):
    template_name: str
    sql: str


@presets_router.get("/kpi-templates", response=List[KPITemplateInfo])
def list_kpi_templates(_request, category: Optional[str] = None):
    templates = _list_kpi_templates(category=category)
    return [KPITemplateInfo(**template) for template in templates]


@presets_router.get("/kpi-templates/categories", response=List[str])
def list_kpi_categories(_request):
    return _get_kpi_categories()


@presets_router.get("/kpi-templates/{template_name}", response=KPITemplateInfo)
def get_kpi_template(_request, template_name: str):
    template = _get_kpi_template(template_name)
    if not template:
        raise HttpError(404, f"Template not found: {template_name}")
    return KPITemplateInfo(
        name=template.name,
        category=template.category,
        description=template.description,
        required_columns=template.required_columns,
        optional_columns=template.optional_columns,
        output_columns=template.output_columns,
    )


@presets_router.post("/kpi-templates/{template_name}/render", response=KPIRenderResponse)
def render_kpi_template(_request, template_name: str, payload: KPIRenderRequest):
    try:
        sql = _render_kpi_template(template_name, payload.parameters)
        return KPIRenderResponse(template_name=template_name, sql=sql)
    except ValueError as exc:
        raise HttpError(400, str(exc)) from exc


@presets_router.get("/{preset_name}", response=PresetInfo)
def get_preset(_request, preset_name: str):
    if preset_name not in PRESETS:
        raise HttpError(404, f"Preset not found: {preset_name}")
    preset = PRESETS[preset_name]
    return PresetInfo(
        name=preset_name,
        category=preset["category"],
        description=preset["description"],
        parameters=preset["parameters"],
        output_artifacts=preset["output_artifacts"],
    )


@presets_router.post("/{preset_name}/execute", response=PresetExecuteResponse)
def execute_preset(_request, preset_name: str, payload: PresetExecuteRequest):
    if preset_name not in PRESETS:
        raise HttpError(404, f"Preset not found: {preset_name}")

    job = PresetJob.objects.create(
        tenant_id=get_tenant_id(),
        preset_name=preset_name,
        source_id=payload.source_id,
        parameters=payload.parameters,
        status="queued",
    )

    return PresetExecuteResponse(
        job_id=str(job.job_id),
        preset_name=preset_name,
        status=job.status,
        created_at=job.created_at.isoformat(),
    )


# =============================================================================
# Artifacts
# =============================================================================

class ArtifactInfo(Schema):
    artifact_id: str
    job_id: str
    artifact_type: str
    format: str
    storage_path: str
    size_bytes: Optional[int] = None
    created_at: str


class ArtifactListResponse(Schema):
    artifacts: List[ArtifactInfo]


_minio_client = None


def get_minio_client():
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
            logger.info("MinIO client connected to %s", settings.minio_endpoint)
        except ImportError:
            logger.warning("minio package not installed")
        except Exception as exc:
            logger.error("MinIO connection failed: %s", exc)
    return _minio_client


@artifacts_router.get("/{job_id}", response=ArtifactListResponse)
def list_artifacts(_request, job_id: str):
    _apply_policy(
        "artifact",
        f"voyant artifact list job_id={job_id}",
        {"job_id": job_id},
    )
    client = get_minio_client()
    if not client:
        rows = Artifact.objects.filter(job_id=job_id)
        if not rows:
            raise HttpError(503, "Storage unavailable")
        artifacts = [
            ArtifactInfo(
                artifact_id=row.artifact_id,
                job_id=row.job_id,
                artifact_type=row.artifact_type,
                format=row.format,
                storage_path=row.storage_path,
                size_bytes=row.size_bytes,
                created_at=row.created_at.isoformat(),
            )
            for row in rows
        ]
        return ArtifactListResponse(artifacts=artifacts)

    try:
        prefix = f"artifacts/{job_id}/"
        objects = client.list_objects("artifacts", prefix=prefix, recursive=True)
        artifacts = []
        for obj in objects:
            path_parts = obj.object_name.split("/")
            filename = path_parts[-1] if path_parts else ""
            name_parts = filename.rsplit(".", 1)
            artifacts.append(
                ArtifactInfo(
                    artifact_id=obj.object_name,
                    job_id=job_id,
                    artifact_type=name_parts[0] if name_parts else "unknown",
                    format=name_parts[1] if len(name_parts) > 1 else "bin",
                    storage_path=obj.object_name,
                    size_bytes=obj.size,
                    created_at=obj.last_modified.isoformat() if obj.last_modified else "",
                )
            )
        return ArtifactListResponse(artifacts=artifacts)
    except Exception as exc:
        logger.exception("Failed to list artifacts for %s", job_id)
        raise HttpError(500, str(exc)) from exc


@artifacts_router.get("/{job_id}/{artifact_type}")
def get_artifact(_request, job_id: str, artifact_type: str, format: str = "json"):
    _apply_policy(
        "artifact",
        f"voyant artifact access job_id={job_id} artifact_type={artifact_type} format={format}",
        {"job_id": job_id, "artifact_type": artifact_type, "format": format},
    )
    client = get_minio_client()
    if not client:
        raise HttpError(503, "Storage unavailable")

    object_name = f"artifacts/{job_id}/{artifact_type}.{format}"

    try:
        url = client.presigned_get_object("artifacts", object_name, expires=3600)
        return {
            "job_id": job_id,
            "artifact_type": artifact_type,
            "format": format,
            "download_url": url,
            "expires_in_seconds": 3600,
        }
    except Exception as exc:
        logger.error("Artifact not found: %s", object_name)
        raise HttpError(404, "Artifact not found") from exc


@artifacts_router.get("/{job_id}/{artifact_type}/download")
def download_artifact(_request, job_id: str, artifact_type: str, format: str = "json"):
    _apply_policy(
        "artifact",
        f"voyant artifact download job_id={job_id} artifact_type={artifact_type} format={format}",
        {"job_id": job_id, "artifact_type": artifact_type, "format": format},
    )
    client = get_minio_client()
    if not client:
        raise HttpError(503, "Storage unavailable")

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
        streaming = StreamingHttpResponse(
            response.stream(),
            content_type=content_type_map.get(format, "application/octet-stream"),
        )
        streaming["Content-Disposition"] = f"attachment; filename={artifact_type}.{format}"
        return streaming
    except Exception as exc:
        logger.error("Failed to download: %s", object_name)
        raise HttpError(404, "Artifact not found") from exc


# =============================================================================
# Analyze
# =============================================================================

class KPIQuery(Schema):
    name: str
    sql: str


class AnalyzeRequest(Schema):
    source_id: Optional[str] = None
    table: Optional[str] = None
    tables: Optional[List[str]] = None
    sample_size: int = Field(default=10000, ge=100, le=1000000)
    kpis: Optional[List[KPIQuery]] = None
    analyzers: Optional[List[str]] = None
    analyzer_context: Optional[Dict[str, Any]] = None
    profile: bool = True
    run_analyzers: bool = True
    generate_artifacts: bool = True


class AnalyzeResponse(Schema):
    job_id: str
    tenant_id: str
    status: str
    summary: Dict[str, Any]
    artifacts: Dict[str, Any]
    manifest: List[Dict[str, Any]]


def _resolve_table(payload: AnalyzeRequest) -> Optional[str]:
    if payload.table:
        return payload.table
    if payload.source_id:
        return payload.source_id
    if payload.tables:
        return payload.tables[0]
    return None


def _ensure_artifacts_bucket(client) -> None:
    if not client.bucket_exists("artifacts"):
        client.make_bucket("artifacts")


def _store_json_artifact(client, job_id: str, name: str, data: Any) -> str:
    payload = json.dumps(data, default=str).encode("utf-8")
    object_name = f"artifacts/{job_id}/{name}.json"
    _ensure_artifacts_bucket(client)
    client.put_object(
        "artifacts",
        object_name,
        io.BytesIO(payload),
        length=len(payload),
        content_type="application/json",
    )
    return object_name


@analyze_router.post("", response=AnalyzeResponse)
def analyze(_request, payload: AnalyzeRequest):
    table = _resolve_table(payload)
    if not table:
        raise HttpError(400, "table or source_id is required")

    tenant_id = get_tenant_id()
    try:
        validate_table_access(tenant_id, table)
    except NamespaceViolationError as exc:
        raise HttpError(403, str(exc)) from exc

    policy_prompt = (
        f"voyant analyze table={table} source_id={payload.source_id or ''} "
        f"tables={payload.tables or []} sample_size={payload.sample_size}"
    )
    _apply_policy(
        "analyze",
        policy_prompt,
        {
            "source_id": payload.source_id,
            "table": table,
            "tables": payload.tables,
            "sample_size": payload.sample_size,
        },
    )

    job = _create_job(
        "analyze",
        payload.source_id or table,
        {"table": table, "tables": payload.tables, "sample_size": payload.sample_size},
    )

    job_id = str(job.job_id)
    soma_task_id = _run_async(
        create_task_for_job,
        job_id,
        job.job_type,
        job.source_id,
        policy_prompt,
    )
    if soma_task_id:
        Job.objects.filter(job_id=job.job_id).update(soma_task_id=soma_task_id)

    job.status = "running"
    job.started_at = datetime.utcnow()
    job.save(update_fields=["status", "started_at"])
    if soma_task_id:
        _run_async(update_task_status, soma_task_id, "running")

    artifacts: Dict[str, Any] = {}
    manifest: List[Dict[str, Any]] = []

    try:
        client = _run_async(get_temporal_client)
        workflow_result = _run_async(
            client.execute_workflow,
            AnalyzeWorkflow.run,
            {
                "source_id": payload.source_id,
                "table": table,
                "tables": payload.tables,
                "sample_size": payload.sample_size,
                "kpis": [kpi.model_dump() for kpi in payload.kpis] if payload.kpis else None,
                "analyzers": payload.analyzers,
                "analyzer_context": payload.analyzer_context or {},
                "profile": payload.profile,
                "run_analyzers": payload.run_analyzers,
                "generate_artifacts": payload.generate_artifacts,
                "job_id": job_id,
                "tenant_id": tenant_id,
            },
            id=f"analyze-{job_id}",
            task_queue=settings.temporal_task_queue,
        )

        profile_summary = workflow_result.get("profile")
        analyzer_results = workflow_result.get("analyzers", {})
        kpi_results = workflow_result.get("kpis", [])
        generator_results = workflow_result.get("generators", {})

        minio = get_minio_client()
        if minio:
            if profile_summary is not None:
                path = _store_json_artifact(minio, job_id, "profile", profile_summary)
                artifacts["profile"] = {"storage_path": path}
                manifest.append({"type": "profile", "format": "json", "storage_path": path})
            if kpi_results:
                path = _store_json_artifact(minio, job_id, "kpis", kpi_results)
                artifacts["kpis"] = {"storage_path": path}
                manifest.append({"type": "kpis", "format": "json", "storage_path": path})
            if analyzer_results:
                path = _store_json_artifact(minio, job_id, "analyzers", analyzer_results)
                artifacts["analyzers"] = {"storage_path": path}
                manifest.append({"type": "analyzers", "format": "json", "storage_path": path})
            if generator_results:
                path = _store_json_artifact(minio, job_id, "generators", generator_results)
                artifacts["generators"] = {"storage_path": path}
                manifest.append({"type": "generators", "format": "json", "storage_path": path})
        else:
            if profile_summary is not None:
                artifacts["profile"] = {"inline": True, "data": profile_summary}
                manifest.append({"type": "profile", "format": "json", "inline": True})
            if kpi_results:
                artifacts["kpis"] = {"inline": True, "data": kpi_results}
                manifest.append({"type": "kpis", "format": "json", "inline": True})
            if analyzer_results:
                artifacts["analyzers"] = {"inline": True, "data": analyzer_results}
                manifest.append({"type": "analyzers", "format": "json", "inline": True})
            if generator_results:
                artifacts["generators"] = {"inline": True, "data": generator_results}
                manifest.append({"type": "generators", "format": "json", "inline": True})

        artifact_rows = []
        for entry in manifest:
            storage_path = entry.get("storage_path")
            if not storage_path:
                continue
            artifact_rows.append(
                Artifact(
                    artifact_id=storage_path,
                    job_id=job_id,
                    tenant_id=tenant_id,
                    artifact_type=entry.get("type", "unknown"),
                    format=entry.get("format", "json"),
                    storage_path=storage_path,
                    size_bytes=None,
                )
            )

        if artifact_rows:
            Artifact.objects.bulk_create(artifact_rows)

        summary = workflow_result.get(
            "summary",
            {
                "table": table,
                "kpi_count": len(kpi_results),
                "analyzer_count": len(analyzer_results) if analyzer_results else 0,
            },
        )
        summary["artifact_count"] = len(manifest)

        job.status = "completed"
        job.completed_at = datetime.utcnow()
        job.result_summary = summary
        job.save(update_fields=["status", "completed_at", "result_summary"])
        if soma_task_id:
            _run_async(update_task_status, soma_task_id, "completed")

        _run_async(remember_summary, job_id, job.status, summary, manifest)

        return AnalyzeResponse(
            job_id=job_id,
            tenant_id=tenant_id,
            status=job.status,
            summary=summary,
            artifacts=artifacts,
            manifest=manifest,
        )
    except HttpError:
        job.status = "failed"
        job.error_message = "analysis_failed"
        job.save(update_fields=["status", "error_message"])
        if soma_task_id:
            _run_async(update_task_status, soma_task_id, "failed", reason=job.error_message)
        raise
    except Exception as exc:
        logger.exception("Analyze failed")
        job.status = "failed"
        job.error_message = str(exc)
        job.save(update_fields=["status", "error_message"])
        if soma_task_id:
            _run_async(update_task_status, soma_task_id, "failed", reason=job.error_message)
        raise HttpError(500, str(exc)) from exc


# =============================================================================
# Discovery
# =============================================================================

class ServiceRegisterRequest(Schema):
    name: str
    base_url: str
    spec_url: Optional[str] = None
    version: str = "1.0.0"
    owner: str = "unknown"
    tags: List[str] = Field(default_factory=list)


class SpecScanRequest(Schema):
    url: str


from voyant.discovery.catalog import DiscoveryRepo, ServiceDef
from voyant.discovery.spec_parser import SpecParser

_discovery_repo = DiscoveryRepo()
_spec_parser = SpecParser()


@discovery_router.post("/services", response=ServiceDef)
def register_service(_request, payload: ServiceRegisterRequest):
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
            except Exception:
                pass

        _discovery_repo.register(service)
        return service
    except Exception as exc:
        raise HttpError(500, str(exc)) from exc


@discovery_router.get("/services", response=List[ServiceDef])
def list_services(_request, tag: Optional[str] = None):
    if tag:
        return _discovery_repo.search(tag)
    return _discovery_repo.list_services()


@discovery_router.get("/services/{name}", response=ServiceDef)
def get_service(_request, name: str):
    service = _discovery_repo.get(name)
    if not service:
        raise HttpError(404, "Service not found")
    return service


@discovery_router.post("/scan")
def scan_spec(_request, payload: SpecScanRequest):
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


# =============================================================================
# Search
# =============================================================================

class SearchQuery(Schema):
    query: str
    limit: int = 5
    filters: Optional[Dict[str, Any]] = None


class SemanticSearchResult(Schema):
    id: str
    score: float
    text: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


@search_router.post("/query", response=List[SemanticSearchResult])
def search(_request, payload: SearchQuery):
    try:
        from voyant.core.embeddings import get_embedding_extractor
        from voyant.core.vector_store import get_vector_store

        store = get_vector_store()
        extractor = get_embedding_extractor()
        query_vector = extractor.extract_text_embedding(payload.query)
        results = store.search(
            query_vector=query_vector,
            limit=payload.limit,
            filters=payload.filters,
        )
        return [
            SemanticSearchResult(id=item.id, score=item.score, text=item.text, metadata=item.metadata)
            for item in results
        ]
    except Exception as exc:
        raise HttpError(500, str(exc)) from exc


class IndexRequest(Schema):
    text: str
    metadata: Optional[Dict[str, Any]] = None


@search_router.post("/index")
def index_item(_request, payload: IndexRequest):
    try:
        from voyant.core.embeddings import get_embedding_extractor
        from voyant.core.vector_store import VectorItem, get_vector_store

        store = get_vector_store()
        extractor = get_embedding_extractor()
        vector = extractor.extract_text_embedding(payload.text)
        item_id = str(uuid.uuid4())
        item = VectorItem(
            id=item_id,
            vector=vector,
            text=payload.text,
            metadata=payload.metadata or {},
        )
        store.add_item(item)
        return {"id": item_id, "status": "indexed"}
    except Exception as exc:
        raise HttpError(500, str(exc)) from exc


api.add_router("/sources", sources_router, tags=["sources"])
api.add_router("/jobs", jobs_router, tags=["jobs"])
api.add_router("/sql", sql_router, tags=["sql"])
api.add_router("/governance", governance_router, tags=["governance"])
api.add_router("/presets", presets_router, tags=["presets"])
api.add_router("/artifacts", artifacts_router, tags=["artifacts"])
api.add_router("/analyze", analyze_router, tags=["analyze"])
api.add_router("/discovery", discovery_router, tags=["discovery"])
api.add_router("/search", search_router, tags=["search"])

# DataScraper Module
from voyant.scraper.api import scrape_router
api.add_router("", scrape_router, tags=["scrape"])
