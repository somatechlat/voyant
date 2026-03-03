"""
Voyant MCP — Core Operational Tools.

Primary agent-facing tools for the main Voyant data pipeline:
discover, connect, ingest, profile, quality, analyze, kpi, status, artifact,
sql, and search. These are the highest-frequency tool calls in normal operation.

Extracted from mcp/tools.py (Rule 245 compliance — 723-line split).
"""

from django_mcp import mcp_app

from apps.core.api_utils import run_async
from apps.core.config import get_settings
from apps.core.lib.temporal_client import get_temporal_client
from apps.core.lib.trino import get_trino_client
from apps.core.lib.workflow_utils import dispatch_workflow
from apps.discovery.models import Source
from apps.discovery.source_detection import detect_source_type
from apps.search.lib.embeddings import get_embedding_extractor
from apps.search.lib.vector_store import get_vector_store
from apps.worker.workflows.analyze_workflow import AnalyzeWorkflow
from apps.worker.workflows.ingest_workflow import IngestDataWorkflow
from apps.worker.workflows.profile_workflow import ProfileWorkflow
from apps.worker.workflows.quality_workflow import QualityWorkflow
from apps.workflows.models import Artifact, Job

settings = get_settings()


def _tenant(tenant_id):
    """Resolve tenant_id: returns the provided value or the configured default."""
    return tenant_id or settings.default_tenant_id


def _start_workflow(workflow_cls, workflow_id, payload):
    """Launch a Temporal workflow and return immediately (fire-and-forget)."""
    client = run_async(get_temporal_client)
    run_async(
        client.start_workflow,
        workflow_cls.run,
        payload,
        id=workflow_id,
        task_queue=settings.temporal_task_queue,
    )


@mcp_app.tool(name="voyant.discover")
def tool_discover(hint: str):
    """Auto-detect the source type for a connection hint (URL, DSN, file path)."""
    return detect_source_type(hint)


@mcp_app.tool(name="voyant.connect")
def tool_connect(
    name: str,
    source_type: str,
    connection_config,
    credentials=None,
    sync_schedule=None,
    tenant_id=None,
):
    """Register a new data source. Returns source_id and initial status."""
    source = Source.objects.create(
        tenant_id=_tenant(tenant_id),
        name=name,
        source_type=source_type,
        status="pending",
        connection_config=connection_config,
        credentials=credentials,
        sync_schedule=sync_schedule,
    )
    return {"source_id": str(source.id), "status": source.status}


@mcp_app.tool(name="voyant.ingest")
def tool_ingest(source_id: str, mode: str = "full", tables=None, tenant_id=None):
    """Start a data ingestion job for the given source. Returns job_id."""
    job = dispatch_workflow(
        workflow_cls=IngestDataWorkflow,
        job_type="ingest",
        source_id=source_id,
        parameters={"mode": mode, "tables": tables},
        tenant_id=_tenant(tenant_id),
    )
    return {"job_id": str(job.job_id), "status": job.status}


@mcp_app.tool(name="voyant.profile")
def tool_profile(source_id: str, table=None, sample_size: int = 10000, tenant_id=None):
    """Start a data profiling job. Returns job_id."""
    job = dispatch_workflow(
        workflow_cls=ProfileWorkflow,
        job_type="profile",
        source_id=source_id,
        parameters={"table": table, "sample_size": sample_size},
        tenant_id=_tenant(tenant_id),
    )
    return {"job_id": str(job.job_id), "status": job.status}


@mcp_app.tool(name="voyant.quality")
def tool_quality(source_id: str, table=None, checks=None, tenant_id=None):
    """Start a data quality check job. Returns job_id."""
    job = dispatch_workflow(
        workflow_cls=QualityWorkflow,
        job_type="quality",
        source_id=source_id,
        parameters={"table": table, "checks": checks or []},
        tenant_id=_tenant(tenant_id),
    )
    return {"job_id": str(job.job_id), "status": job.status}


@mcp_app.tool(name="voyant.analyze")
def tool_analyze(
    source_id: str,
    table=None,
    analyzers=None,
    sample_size: int = 10000,
    tenant_id=None,
):
    """Start an analysis job (stats, correlation, outlier detection). Returns job_id."""
    job = dispatch_workflow(
        workflow_cls=AnalyzeWorkflow,
        job_type="analyze",
        source_id=source_id,
        parameters={
            "table": table,
            "analyzers": analyzers or [],
            "sample_size": sample_size,
        },
        tenant_id=_tenant(tenant_id),
    )
    return {"job_id": str(job.job_id), "status": job.status}


@mcp_app.tool(name="voyant.kpi")
def tool_kpi(kpis, limit: int = 1000):
    """Execute a list of KPI SQL queries against Trino. Returns combined results."""
    client = get_trino_client()
    results = []
    for item in kpis:
        sql = item.get("sql") if isinstance(item, dict) else None
        if not sql:
            continue
        res = client.execute(sql, limit=limit)
        results.append(
            {
                "name": item.get("name", "kpi"),
                "columns": res.columns,
                "rows": res.rows,
                "row_count": res.row_count,
            }
        )
    return {"results": results}


@mcp_app.tool(name="voyant.status")
def tool_status(job_id: str, tenant_id=None):
    """Get the current status, progress, and result summary of a job."""
    job = Job.objects.filter(id=job_id, tenant_id=_tenant(tenant_id)).first()
    if not job:
        raise ValueError("Job not found")
    return {
        "job_id": str(job.job_id),
        "status": job.status,
        "progress": job.progress,
        "result_summary": job.result_summary,
        "error_message": job.error_message,
    }


@mcp_app.tool(name="voyant.artifact")
def tool_artifact(artifact_id: str, tenant_id=None):
    """Retrieve artifact metadata and storage path by artifact_id."""
    artifact = Artifact.objects.filter(
        artifact_id=artifact_id, tenant_id=_tenant(tenant_id)
    ).first()
    if not artifact:
        raise ValueError("Artifact not found")
    return {
        "artifact_id": artifact.artifact_id,
        "job_id": artifact.job_id,
        "artifact_type": artifact.artifact_type,
        "format": artifact.format,
        "storage_path": artifact.storage_path,
        "size_bytes": artifact.size_bytes,
    }


@mcp_app.tool(name="voyant.sql")
def tool_sql(sql: str, limit: int = 1000):
    """Execute raw SQL against the Trino analytical engine. Returns columns + rows."""
    res = get_trino_client().execute(sql, limit=limit)
    return {
        "columns": res.columns,
        "rows": res.rows,
        "row_count": res.row_count,
        "truncated": res.truncated,
        "query_id": res.query_id,
    }


@mcp_app.tool(name="voyant.search")
def tool_search(query: str, limit: int = 5, tenant_id=None):
    """Semantic vector search over indexed tenant data. Returns ranked results."""
    store = get_vector_store()
    extractor = get_embedding_extractor(model="tfidf", dimensions=128)
    vec = extractor.embed([query]).embeddings[0]
    results = store.search(
        query_vector=vec, k=limit, filter_metadata={"tenant_id": _tenant(tenant_id)}
    )
    return [
        {"id": item.id, "score": score, "metadata": item.metadata}
        for item, score in results
    ]
