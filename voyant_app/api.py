"""
Voyant Main REST API

This module defines the primary REST API endpoints for the Voyant platform,
built using the Django-Ninja framework. It serves as the main entry point for all
user- and agent-driven interactions, orchestrating backend services like Temporal
workflows, data queries via Trino, and interactions with the data governance layer.

The API is organized into logical sections using Ninja Routers, each corresponding
to a major resource or functional area (e.g., sources, jobs, sql).

Architectural Notes:
- Asynchronous Offloading: Most long-running operations (e.g., ingestion, analysis)
  are non-blocking. The API endpoint creates a job record and immediately triggers
  a Temporal workflow, ensuring the API remains responsive.
- Multi-Tenancy: All resources are isolated by a `tenant_id`, which is extracted
  from the request by middleware.
- Policy Enforcement: Key operations are gated by a policy enforcement check
  (`_apply_policy`), which can integrate with external policy engines.
"""

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
from voyant.core.namespace_analyzer import (
    NamespaceViolationError,
    validate_table_access,
)
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
from voyant.security.auth import get_current_user, get_optional_user
from voyant.workflows.analyze_workflow import AnalyzeWorkflow
from voyant.workflows.ingest_workflow import IngestDataWorkflow
from voyant.workflows.profile_workflow import ProfileWorkflow
from voyant.workflows.quality_workflow import QualityWorkflow
from voyant.workflows.types import IngestParams
from voyant_app.models import Artifact, Job, PresetJob, Source

logger = logging.getLogger(__name__)
settings = get_settings()

# =============================================================================
# API Initialization & Routers
# =============================================================================

import sys

# Use a unique namespace during testing to avoid NinjaAPI registry collisions
# when modules are reloaded by pytest-django.
urls_namespace = "v1"
if "pytest" in sys.modules:
    # Aggressively clear registry to handle potential test environment reloading
    try:
        NinjaAPI._registry.clear()
    except Exception:
        pass

    import uuid
    urls_namespace = f"v1_{uuid.uuid4().hex}"

api = NinjaAPI(
    title="Voyant API",
    description="Autonomous Data Intelligence for AI Agents",
    version="3.0.0",
    urls_namespace=urls_namespace,
)

# Routers for organizing endpoints into logical groups
sources_router = Router()
jobs_router = Router()
sql_router = Router()
governance_router = Router()
presets_router = Router()
artifacts_router = Router()
analyze_router = Router()
discovery_router = Router()
search_router = Router()


# =============================================================================
# Helper Functions
# =============================================================================


def _run_async(func, *args, **kwargs):
    """Run an async function from a sync context."""
    return async_to_sync(func)(*args, **kwargs)


def _auth_guard(request):
    """
    Enforce authentication outside local environments.

    In local mode we allow missing tokens for developer ergonomics; in other
    environments we require a valid Keycloak JWT.
    
    Returns:
        User object or True (to allow access in local mode without token)
    """
    if settings.env == "local":
        user = get_optional_user(request)
        # In local mode, if no token is provided, allow access by returning True
        # Django Ninja accepts True as "authenticated"
        return user if user is not None else True
    return get_current_user(request)


def _apply_policy(action: str, prompt: str, metadata: Dict[str, Any]) -> None:
    """
    A wrapper to enforce policy checks for an action.

    Raises:
        HttpError: With status 400, 403, or 503 depending on the policy outcome.
    """
    try:
        _run_async(enforce_policy, action, prompt, metadata)
    except SomaContextError as exc:
        raise HttpError(400, f"Invalid policy context: {exc}") from exc
    except SomaPolicyDenied as exc:
        raise HttpError(403, exc.details or {"reason": str(exc)}) from exc
    except SomaPolicyUnavailable as exc:
        raise HttpError(503, f"Policy engine unavailable: {exc}") from exc


# =============================================================================
# Sources Router: Managing Data Sources
# =============================================================================


class DiscoverRequest(Schema):
    """The request schema for discovering a data source type from a hint."""

    hint: str = Field(
        ...,
        description="A string that provides a hint about the data source, such as a URL, a file path, or a database connection string.",
        example="postgresql://user:pass@host:port/db",
    )


class DiscoverResponse(Schema):
    """The response schema after discovering a data source."""

    source_type: str = Field(..., description="The detected type of the source (e.g., 'postgresql', 'csv').")
    detected_properties: Dict[str, Any] = Field(..., description="A dictionary of properties inferred from the hint.")
    suggested_connector: str = Field(..., description="The suggested connector to use for this source (e.g., 'airbyte/source-postgres').")
    confidence: float = Field(..., description="A score from 0.0 to 1.0 indicating the confidence in the detection.")


class CreateSourceRequest(Schema):
    """The request schema for creating a new data source."""

    name: str = Field(..., description="A unique, human-readable name for the data source.")
    source_type: str = Field(..., description="The type of the source, matching a value from the discovery endpoint.")
    connection_config: Dict[str, Any] = Field(..., description="A dictionary containing the specific configuration needed to connect to the source.")
    credentials: Optional[Dict[str, Any]] = Field(None, description="A dictionary containing sensitive credentials. This will be encrypted.")
    sync_schedule: Optional[str] = Field(None, description="An optional cron string for scheduling data synchronization.")


class SourceResponse(Schema):
    """The response schema representing a data source resource."""

    source_id: str = Field(..., description="The unique identifier for the data source.")
    tenant_id: str = Field(..., description="The tenant that owns this data source.")
    name: str = Field(..., description="The human-readable name of the data source.")
    source_type: str = Field(..., description="The type of the source.")
    status: str = Field(..., description="The current status of the source (e.g., 'pending', 'active', 'error').")
    created_at: str = Field(..., description="The ISO 8601 timestamp of when the source was created.")
    datahub_urn: Optional[str] = Field(None, description="The unique URN for this source in the DataHub governance platform.")


def _detect_source_type(hint: str) -> Dict[str, Any]:
    """A simple heuristic-based function to detect source type from a hint string."""
    hint_lower = hint.lower()

    if hint_lower.startswith("postgresql://") or hint_lower.startswith("postgres://"):
        return {
            "source_type": "postgresql",
            "connector": "airbyte/source-postgres",
            "properties": {"host": hint.split("@")[-1].split("/")[0] if "@" in hint else "unknown"},
            "confidence": 0.95,
        }
    if hint_lower.startswith("mysql://"):
        return {"source_type": "mysql", "connector": "airbyte/source-mysql", "properties": {}, "confidence": 0.95}
    if hint_lower.startswith("mongodb://") or hint_lower.startswith("mongodb+srv://"):
        return {"source_type": "mongodb", "connector": "airbyte/source-mongodb-v2", "properties": {}, "confidence": 0.95}
    if "snowflake" in hint_lower:
        return {"source_type": "snowflake", "connector": "airbyte/source-snowflake", "properties": {}, "confidence": 0.9}
    if hint_lower.endswith(".csv"):
        return {"source_type": "csv", "connector": "file", "properties": {"format": "csv"}, "confidence": 0.9}
    if hint_lower.endswith(".parquet"):
        return {"source_type": "parquet", "connector": "file", "properties": {"format": "parquet"}, "confidence": 0.9}
    if hint_lower.endswith(".json") or hint_lower.endswith(".jsonl"):
        return {"source_type": "json", "connector": "file", "properties": {"format": "json"}, "confidence": 0.9}
    if "s3://" in hint_lower:
        return {
            "source_type": "s3",
            "connector": "airbyte/source-s3",
            "properties": {"bucket": hint.split("/")[2] if len(hint.split("/")) > 2 else ""},
            "confidence": 0.9,
        }
    if "sheets.google.com" in hint_lower or "docs.google.com/spreadsheets" in hint_lower:
        return {"source_type": "google_sheets", "connector": "airbyte/source-google-sheets", "properties": {}, "confidence": 0.9}
    if hint_lower.startswith("http://") or hint_lower.startswith("https://"):
        return {"source_type": "api", "connector": "airbyte/source-http", "properties": {"url": hint}, "confidence": 0.5}

    return {"source_type": "unknown", "connector": "unknown", "properties": {}, "confidence": 0.1}


@sources_router.post("/discover", response=DiscoverResponse, summary="Discover Data Source Type")
def discover_source(request, payload: DiscoverRequest):
    """
    Analyzes a hint (like a URL or file path) to detect the data source type.

    This endpoint uses a set of heuristics to infer the source type, suggested
    connector, and connection properties from a single string.

    Args:
        request: The HTTP request.
        payload: A request body containing the data source hint.

    Returns:
        A DiscoverResponse object with the detected information.
    """
    detected = _detect_source_type(payload.hint)
    return DiscoverResponse(
        source_type=detected["source_type"],
        detected_properties=detected["properties"],
        suggested_connector=detected["connector"],
        confidence=detected["confidence"],
    )


@sources_router.post("", response={201: SourceResponse}, summary="Create a New Data Source")
def create_source(request, payload: CreateSourceRequest):
    """
    Registers a new data source in the system for the current tenant.

    This endpoint creates a new `Source` record in the database. The actual data
    ingestion is handled separately by triggering an 'ingest' job.

    Args:
        request: The HTTP request.
        payload: The configuration for the new data source.

    Returns:
        A SourceResponse object representing the newly created source, with an HTTP 201 status.
    """
    tenant_id = get_tenant_id(request)
    source = Source.objects.create(
        tenant_id=tenant_id,
        name=payload.name,
        source_type=payload.source_type,
        connection_config=payload.connection_config,
        credentials=payload.credentials,
        sync_schedule=payload.sync_schedule,
        status="pending",  # All new sources start as pending until first ingestion.
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


@sources_router.get("", response=List[SourceResponse], summary="List All Data Sources")
def list_sources(request):
    """
    Retrieves a list of all data sources belonging to the current tenant.

    Args:
        request: The HTTP request.

    Returns:
        A list of SourceResponse objects.
    """
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


@sources_router.get("/{source_id}", response=SourceResponse, summary="Get a Specific Data Source")
def get_source(request, source_id: str):
    """
    Retrieves the details of a single data source by its ID.

    Args:
        request: The HTTP request.
        source_id: The UUID of the source to retrieve.

    Returns:
        A SourceResponse object for the requested source.

    Raises:
        HttpError 404: If no source with the given ID is found.
        HttpError 403: If the source does not belong to the current tenant.
    """
    source = Source.objects.filter(source_id=source_id).first()
    if not source:
        raise HttpError(404, "Source not found")

    # Verification: Ensure the source belongs to the requesting tenant for access control.
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


@sources_router.delete("/{source_id}", response={200: Dict[str, str]}, summary="Delete a Data Source")
def delete_source(request, source_id: str):
    """
    Deletes a data source from the system.

    Args:
        request: The HTTP request.
        source_id: The UUID of the source to delete.

    Returns:
        A confirmation message upon successful deletion.

    Raises:
        HttpError 404: If no source with the given ID is found.
        HttpError 403: If the source does not belong to the current tenant.
    """
    source = Source.objects.filter(source_id=source_id).first()
    if not source:
        raise HttpError(404, "Source not found")

    # Verification: Ensure the source belongs to the requesting tenant for access control.
    tenant_id = get_tenant_id(request)
    if source.tenant_id != tenant_id:
        raise HttpError(403, "Access to this resource is denied.")

    source.delete()
    return {"status": "deleted", "source_id": str(source_id)}


# =============================================================================
# Jobs Router: Managing Asynchronous Data Processing Jobs
# =============================================================================


class IngestRequest(Schema):
    """Request schema for starting a data ingestion job."""
    source_id: str = Field(..., description="The ID of the data source to ingest from.")
    mode: str = Field("full", description="The ingestion mode: 'full' for a full refresh or 'incremental' for new data.")
    tables: Optional[List[str]] = Field(None, description="An optional list of specific tables to ingest. If empty, all tables are ingested.")


class ProfileRequest(Schema):
    """Request schema for starting a data profiling job."""
    source_id: str = Field(..., description="The ID of the data source to profile.")
    table: Optional[str] = Field(None, description="An optional specific table to profile within the source.")
    sample_size: int = Field(10000, ge=100, le=1000000, description="The number of rows to sample for profiling.")


class QualityRequest(Schema):
    """Request schema for starting a data quality check job."""
    source_id: str = Field(..., description="The ID of the data source to check.")
    table: Optional[str] = Field(None, description="An optional specific table to check.")
    checks: Optional[List[str]] = Field(None, description="An optional list of specific quality checks to run.")


class JobResponse(Schema):
    """The response schema representing a job's status and details."""
    job_id: str = Field(..., description="The unique identifier for the job.")
    tenant_id: str = Field(..., description="The tenant that owns this job.")
    job_type: str = Field(..., description="The type of job (e.g., 'ingest', 'profile').")
    status: str = Field(..., description="The current status of the job (e.g., 'queued', 'running', 'completed', 'failed').")
    progress: int = Field(..., description="An integer from 0 to 100 representing job progress.")
    created_at: str = Field(..., description="The ISO 8601 timestamp of when the job was created.")
    started_at: Optional[str] = Field(None, description="The ISO 8601 timestamp of when the job started running.")
    completed_at: Optional[str] = Field(None, description="The ISO 8601 timestamp of when the job finished.")
    result_summary: Optional[Dict[str, Any]] = Field(None, description="A summary of the job's results upon completion.")
    error_message: Optional[str] = Field(None, description="An error message if the job failed.")


def _create_job(job_type: str, source_id: str, params: Dict[str, Any]) -> Job:
    """
    A helper function to create a new Job record in the database.

    Args:
        job_type: The type of job to create (e.g., 'ingest').
        source_id: The source the job is associated with.
        params: A dictionary of parameters specific to this job run.

    Returns:
        The newly created `Job` model instance.
    """
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


@jobs_router.post("/ingest", response=JobResponse, summary="Trigger a Data Ingestion Job")
def trigger_ingest(request, payload: IngestRequest):
    """
    Creates and starts a new data ingestion job for a given data source.

    This endpoint creates a job record, applies any relevant security policies,
    and then asynchronously starts a Temporal workflow to perform the actual
    data ingestion.

    Args:
        request: The HTTP request.
        payload: The ingestion request details.

    Returns:
        A JobResponse object representing the newly created job.

    Raises:
        HttpError 403: If access to the specified tables is denied.
        HttpError 500: If the workflow fails to start.
    """
    try:
        tenant_id = get_tenant_id(request)
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
        {
            "source_id": payload.source_id,
            "mode": payload.mode,
            "tables": payload.tables,
        },
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


@jobs_router.post("/profile", response=JobResponse, summary="Trigger a Data Profiling Job")
def trigger_profile(request, payload: ProfileRequest):
    """
    Creates and starts a new data profiling job for a given data source.

    This endpoint initiates an asynchronous Temporal workflow to compute
    descriptive statistics and generate a profile of the specified data.

    Args:
        request: The HTTP request.
        payload: The profiling request details.

    Returns:
        A JobResponse object representing the newly created job.

    Raises:
        HttpError 403: If access to the specified table is denied.
        HttpError 500: If the workflow fails to start.
    """
    try:
        tenant_id = get_tenant_id(request)
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


@jobs_router.post("/quality", response=JobResponse, summary="Trigger a Data Quality Job")
def trigger_quality(request, payload: QualityRequest):
    """
    Creates and starts a data quality job.

    Args:
        request: The HTTP request.
        payload: The quality check request details.

    Returns:
        A JobResponse object representing the newly created job.

    Raises:
        HttpError 403: If access to the specified table is denied.
    """
    try:
        tenant_id = get_tenant_id(request)
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

    try:
        client = _run_async(get_temporal_client)
        _run_async(
            client.start_workflow,
            QualityWorkflow.run,
            {
                "source_id": payload.source_id,
                "table": payload.table,
                "checks": payload.checks,
                "job_id": str(job.job_id),
                "tenant_id": job.tenant_id,
            },
            id=f"quality-{job.job_id}",
            task_queue=settings.temporal_task_queue,
        )
        job.status = "running"
        job.save(update_fields=["status"])
        if soma_task_id:
            _run_async(update_task_status, soma_task_id, "running")
    except Exception as exc:
        logger.error("Failed to start quality workflow: %s", exc)
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


@jobs_router.get("", response=List[JobResponse], summary="List Jobs")
def list_jobs(
    request,
    status: Optional[str] = None,
    job_type: Optional[str] = None,
    limit: int = 50,
):
    """
    Retrieves a list of jobs for the current tenant, with optional filters.

    Args:
        request: The HTTP request.
        status: An optional filter for job status (e.g., 'completed', 'failed').
        job_type: An optional filter for job type (e.g., 'ingest').
        limit: The maximum number of jobs to return.

    Returns:
        A list of JobResponse objects.
    """
    tenant_id = get_tenant_id(request)
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


@jobs_router.get("/{job_id}", response=JobResponse, summary="Get Job Status")
def get_job(request, job_id: str):
    """
    Retrieves the status and details of a single job by its ID.

    Args:
        request: The HTTP request.
        job_id: The UUID of the job to retrieve.

    Returns:
        A JobResponse object for the requested job.

    Raises:
        HttpError 404: If no job with the given ID is found.
        HttpError 403: If the job does not belong to the current tenant.
    """
    job = Job.objects.filter(job_id=job_id).first()
    if not job:
        raise HttpError(404, "Job not found")

    # Verification: Ensure the job belongs to the requesting tenant for access control.
    tenant_id = get_tenant_id(request)
    if job.tenant_id != tenant_id:
        raise HttpError(403, "Access to this resource is denied.")

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


@jobs_router.post("/{job_id}/cancel", response={200: Dict[str, str]}, summary="Cancel a Job")
def cancel_job(request, job_id: str):
    """
    Cancels a job that is currently in a 'queued' or 'running' state.

    Args:
        request: The HTTP request.
        job_id: The UUID of the job to cancel.

    Returns:
        A confirmation message upon successful cancellation.

    Raises:
        HttpError 404: If no job with the given ID is found.
        HttpError 403: If the job does not belong to the current tenant.
        HttpError 400: If the job is not in a cancellable state.
    """
    job = Job.objects.filter(job_id=job_id).first()
    if not job:
        raise HttpError(404, "Job not found")

    # Verification: Ensure the job belongs to the requesting tenant for access control.
    tenant_id = get_tenant_id(request)
    if job.tenant_id != tenant_id:
        raise HttpError(403, "Access to this resource is denied.")

    if job.status not in ("queued", "running"):
        raise HttpError(400, f"Job is in '{job.status}' state and cannot be cancelled.")

    job.status = "cancelled"
    job.completed_at = datetime.utcnow()
    job.save(update_fields=["status", "completed_at"])

    if job.soma_task_id:
        _run_async(
            update_task_status, job.soma_task_id, "cancelled", reason="User requested cancellation"
        )

    logger.info("Cancelled job %s by user request", job_id)
    return {"status": "cancelled", "job_id": str(job_id)}


# =============================================================================
# SQL Router: Ad-Hoc Query Execution
# =============================================================================


class SqlRequest(Schema):
    """Request schema for executing an ad-hoc SQL query."""
    sql: str = Field(..., description="The SQL query string to execute. Only SELECT queries are permitted.")
    limit: int = Field(1000, ge=1, le=10000, description="The maximum number of rows to return from the query.")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Optional parameters to pass to the SQL query (e.g., for parameterized queries).")


class SqlResponse(Schema):
    """Response schema for the result of an executed SQL query."""
    columns: List[str] = Field(..., description="A list of column names returned by the query.")
    rows: List[List[Any]] = Field(..., description="A list of lists, where each inner list represents a row of data.")
    row_count: int = Field(..., description="The total number of rows returned.")
    truncated: bool = Field(..., description="True if the result set was truncated due to the specified limit.")
    execution_time_ms: int = Field(..., description="The time taken to execute the query in milliseconds.")
    query_id: Optional[str] = Field(None, description="The unique ID assigned to the query by the Trino engine.")


@sql_router.post("/query", response=SqlResponse, summary="Execute Ad-Hoc SQL Query", auth=_auth_guard)
def execute_sql(request, payload: SqlRequest):
    """
    Executes an ad-hoc SQL query against the Trino engine for the current tenant.

    This endpoint strictly enforces a read-only policy via the underlying `TrinoClient`
    to prevent any data modification or destructive operations.

    Args:
        request: The HTTP request object.
        payload: The SQL query request details, including the query string and limits.

    Returns:
        A SqlResponse object containing the query results.

    Raises:
        HttpError 400: If the SQL query is invalid or contains forbidden keywords.
        HttpError 503: If the Trino service is unavailable.
        HttpError 500: For any unexpected internal server errors during query execution.
    """
    # Security: Tenant validation and SQL query safety are handled by underlying TrinoClient.
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
        # This typically catches forbidden SQL keywords or invalid query types from _validate_sql.
        raise HttpError(400, str(exc)) from exc
    except RuntimeError as exc:
        # This catches issues like Trino client not installed from _get_connection.
        raise HttpError(503, str(exc)) from exc
    except Exception as exc:
        logger.exception("SQL execution failed for tenant %s", get_tenant_id(request))
        raise HttpError(500, f"Query failed due to internal error: {exc}") from exc


@sql_router.get("/tables", response=Dict[str, Any], summary="List Available Tables", auth=_auth_guard)
def list_tables(request, schema: Optional[str] = None):
    """
    Retrieves a list of all tables accessible via the Trino engine for the current tenant.

    Args:
        request: The HTTP request object.
        schema: An optional schema name to filter the tables. If not provided,
                the default schema configured for Trino is used.

    Returns:
        A dictionary containing a list of table names and the schema they belong to.

    Raises:
        HttpError 500: For any internal server errors during table listing.
    """
    try:
        client = get_trino_client()
        tables = client.get_tables(schema)
        return {"tables": tables, "schema": schema or client.schema}
    except Exception as exc:
        logger.exception("Failed to list tables for tenant %s", get_tenant_id(request))
        raise HttpError(500, f"Failed to list tables: {exc}") from exc


@sql_router.get("/tables/{table}/columns", response=Dict[str, Any], summary="Get Table Columns", auth=_auth_guard)
def get_columns(request, table: str, schema: Optional[str] = None):
    """
    Retrieves the column details for a specific table accessible via the Trino engine.

    Args:
        request: The HTTP request object.
        table: The name of the table to describe.
        schema: An optional schema name where the table resides. If not provided,
                the default schema configured for Trino is used.

    Returns:
        A dictionary containing the table name and a list of its columns with their types.

    Raises:
        HttpError 500: For any internal server errors during column retrieval.
    """
    try:
        client = get_trino_client()
        columns = client.get_columns(table, schema)
        return {"table": table, "columns": columns}
    except Exception as exc:
        logger.exception("Failed to get columns for table '%s' for tenant %s", table, get_tenant_id(request))
        raise HttpError(500, f"Failed to get columns for table '{table}': {exc}") from exc


# =============================================================================
# Governance Router: Data Governance and Metadata
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


@governance_router.get("/search", response=SearchResponse, auth=_auth_guard)
def search_metadata(request, query: str, types: Optional[str] = None, limit: int = 10):
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
                    platform=(
                        entity.get("platform", {}).get("name")
                        if entity.get("platform")
                        else None
                    ),
                    tags=tags,
                )
            )

        return SearchResponse(results=results, total=search_data.get("total", 0))
    except HttpError:
        raise
    except Exception as exc:
        logger.exception("Search failed")
        raise HttpError(500, str(exc)) from exc


@governance_router.get("/lineage/{urn}", response=LineageResponse, auth=_auth_guard)
def get_lineage(request, urn: str, direction: str = "both", depth: int = 3):
    try:
        nodes = [
            LineageNode(
                urn=urn, name=urn.split(",")[1] if "," in urn else urn, type="dataset"
            )
        ]
        edges = []

        directions = (
            ["UPSTREAM", "DOWNSTREAM"] if direction == "both" else [direction.upper()]
        )
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
                        platform=(
                            entity.get("platform", {}).get("name")
                            if entity.get("platform")
                            else None
                        ),
                    )
                )
                if dir_enum == "UPSTREAM":
                    edges.append(
                        LineageEdge(
                            source=node_urn,
                            target=urn,
                            type=rel.get("type", "PRODUCES"),
                        )
                    )
                else:
                    edges.append(
                        LineageEdge(
                            source=urn,
                            target=node_urn,
                            type=rel.get("type", "PRODUCES"),
                        )
                    )

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


@governance_router.get("/schema/{urn}", response=SchemaResponse, auth=_auth_guard)
def get_schema(request, urn: str):
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


@governance_router.get("/quotas/tiers", response=List[QuotaTierInfo], auth=_auth_guard)
def list_quota_tiers(request):
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


@governance_router.get("/quotas/usage", response=QuotaUsageStatus, auth=_auth_guard)
def get_quota_usage(request):
    tenant_id = get_tenant_id()
    status = _get_usage_status(tenant_id)
    return QuotaUsageStatus(**status)


@governance_router.get("/quotas/limits", auth=_auth_guard)
def get_quota_limits(request):
    tenant_id = get_tenant_id()
    return _get_quota_limits(tenant_id)


@governance_router.post("/quotas/tier")
def set_quota_tier(request, payload: SetTierRequest):
    tenant_id = get_tenant_id()
    try:
        _set_tenant_tier(tenant_id, payload.tier)
        return {"status": "updated", "tenant_id": tenant_id, "tier": payload.tier}
    except ValueError as exc:
        raise HttpError(400, str(exc)) from exc


# =============================================================================
# Presets Router: Pre-configured Analysis Workflows
# =============================================================================

# A registry of pre-defined analysis presets. Each preset specifies:
# - name: A human-readable name.
# - category: For grouping in UIs.
# - description: What the preset does.
# - parameters: A list of expected input parameters.
# - output_artifacts: A list of expected artifacts generated.
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
    """Schema for displaying information about a pre-configured analysis preset."""
    name: str = Field(..., description="The unique name of the preset.")
    category: str = Field(..., description="The category the preset belongs to (e.g., 'financial', 'customer').")
    description: str = Field(..., description="A brief description of what the preset does.")
    parameters: List[str] = Field(..., description="A list of required input parameters for the preset.")
    output_artifacts: List[str] = Field(..., description="A list of expected output artifact types.")


class PresetExecuteRequest(Schema):
    """Request schema for executing a pre-configured analysis preset."""
    source_id: str = Field(..., description="The ID of the data source to run the preset on.")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="A dictionary of key-value pair parameters required by the preset.")


class PresetExecuteResponse(Schema):
    """Response schema after successfully initiating a preset execution."""
    job_id: str = Field(..., description="The ID of the job created to execute the preset.")
    preset_name: str = Field(..., description="The name of the executed preset.")
    status: str = Field(..., description="The initial status of the job (e.g., 'queued').")
    created_at: str = Field(..., description="The ISO 8601 timestamp of when the job was created.")


@presets_router.get("", response=Dict[str, List[PresetInfo]], summary="List All Presets")
def list_presets(request, category: Optional[str] = None):
    """
    Retrieves a list of all available analysis presets, optionally filtered by category.

    Args:
        request: The HTTP request object.
        category: An optional category name to filter presets by.

    Returns:
        A dictionary where keys are categories and values are lists of PresetInfo objects.
    """
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


# Lazy imports for KPI template functions to avoid circular dependencies
# and ensure settings are loaded before KPI template logic is accessed.
from voyant.core.kpi_templates import (
    get_categories as _get_kpi_categories,
    get_template as _get_kpi_template,
    list_templates as _list_kpi_templates,
    render_template as _render_kpi_template,
)


class KPITemplateInfo(Schema):
    """Schema for displaying information about a Key Performance Indicator (KPI) SQL template."""
    name: str = Field(..., description="The unique name of the KPI template.")
    category: str = Field(..., description="The category the KPI belongs to (e.g., 'financial', 'operational').")
    description: str = Field(..., description="A brief description of the KPI and what it measures.")
    required_columns: List[str] = Field(..., description="A list of column names that must be present in the data for this KPI.")
    optional_columns: Dict[str, str] = Field(default_factory=dict, description="A dictionary of optional column names and their descriptions.")
    output_columns: List[str] = Field(default_factory=list, description="A list of column names that the rendered SQL query will output.")


class KPIRenderRequest(Schema):
    """Request schema for rendering a KPI SQL template with specific parameters."""
    parameters: Dict[str, str] = Field(..., description="A dictionary of key-value pairs to substitute into the SQL template.")


class KPIRenderResponse(Schema):
    """Response schema containing the rendered SQL query for a KPI template."""
    template_name: str = Field(..., description="The name of the KPI template that was rendered.")
    sql: str = Field(..., description="The fully rendered SQL query string.")


@presets_router.get("/kpi-templates", response=List[KPITemplateInfo], summary="List All KPI Templates")
def list_kpi_templates(request, category: Optional[str] = None):
    """
    Retrieves a list of all available KPI SQL templates, optionally filtered by category.

    These templates are pre-defined SQL queries that can be rendered with specific
    parameters to calculate common KPIs.

    Args:
        request: The HTTP request object.
        category: An optional category name to filter KPI templates by.

    Returns:
        A list of KPITemplateInfo objects.
    """
    templates = _list_kpi_templates(category=category)
    return [KPITemplateInfo(**template) for template in templates]


@presets_router.get("/kpi-templates/categories", response=List[str], summary="List KPI Categories")
def list_kpi_categories(request):
    """
    Retrieves a list of all available categories for KPI templates.

    Args:
        request: The HTTP request object.

    Returns:
        A list of string category names.
    """
    return _get_kpi_categories()


@presets_router.get("/kpi-templates/{template_name}", response=KPITemplateInfo, summary="Get KPI Template Details")
def get_kpi_template(request, template_name: str):
    """
    Retrieves the details of a specific KPI SQL template by its name.

    Args:
        request: The HTTP request object.
        template_name: The unique name of the KPI template.

    Returns:
        A KPITemplateInfo object for the requested template.

    Raises:
        HttpError 404: If the specified KPI template is not found.
    """
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


@presets_router.post(
    "/kpi-templates/{template_name}/render", response=KPIRenderResponse, summary="Render KPI SQL Template"
)
def render_kpi_template(request, template_name: str, payload: KPIRenderRequest):
    """
    Renders a KPI SQL template by substituting provided parameters into its definition.

    This allows clients to dynamically generate executable SQL queries for KPIs.

    Args:
        request: The HTTP request object.
        template_name: The name of the KPI template to render.
        payload: A request body containing the parameters for the template.

    Returns:
        A KPIRenderResponse object containing the rendered SQL query.

    Raises:
        HttpError 400: If the parameters provided are insufficient or incorrect for the template.
        HttpError 404: If the specified KPI template is not found.
    """
    try:
        sql = _render_kpi_template(template_name, payload.parameters)
        return KPIRenderResponse(template_name=template_name, sql=sql)
    except ValueError as exc:
        raise HttpError(400, str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to render KPI template '%s'", template_name)
        raise HttpError(500, f"Failed to render KPI template: {exc}") from exc


@presets_router.get("/{preset_name}", response=PresetInfo, summary="Get Preset Details")
def get_preset(request, preset_name: str):
    """
    Retrieves the details of a specific pre-configured analysis preset.

    Args:
        request: The HTTP request object.
        preset_name: The unique name of the preset.

    Returns:
        A PresetInfo object for the requested preset.

    Raises:
        HttpError 404: If the specified preset is not found.
    """
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


@presets_router.post("/{preset_name}/execute", response=PresetExecuteResponse, summary="Execute a Preset")
def execute_preset(request, preset_name: str, payload: PresetExecuteRequest):
    """
    Executes a pre-configured analysis preset on a specified data source.

    This endpoint creates a `PresetJob` record, marking it as 'queued'.
    The actual execution of the preset (which may involve triggering a Temporal
    workflow) is handled by a separate background process or service.

    Args:
        request: The HTTP request object, from which tenant ID is extracted.
        preset_name: The unique name of the preset to execute.
        payload: The execution request details, including source ID and parameters.

    Returns:
        A PresetExecuteResponse object representing the newly created preset job.

    Raises:
        HttpError 404: If the specified preset is not found.
    """
    if preset_name not in PRESETS:
        raise HttpError(404, f"Preset not found: {preset_name}")

    job = PresetJob.objects.create(
        tenant_id=get_tenant_id(request),
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
# Artifacts Router: Managing Generated Artifacts
# =============================================================================


class ArtifactInfo(Schema):
    """Schema for displaying information about a single generated artifact."""
    artifact_id: str = Field(..., description="The unique identifier (object name) of the artifact in storage.")
    job_id: str = Field(..., description="The ID of the job that generated this artifact.")
    artifact_type: str = Field(..., description="The type of artifact (e.g., 'profile', 'chart', 'report').")
    format: str = Field(..., description="The format of the artifact (e.g., 'json', 'png', 'pdf').")
    storage_path: str = Field(..., description="The full path or key to the artifact in the object storage.")
    size_bytes: Optional[int] = Field(None, description="The size of the artifact file in bytes.")
    created_at: str = Field(..., description="The ISO 8601 timestamp of when the artifact was created.")


class ArtifactListResponse(Schema):
    """Response schema for listing artifacts associated with a job."""
    artifacts: List[ArtifactInfo] = Field(..., description="A list of ArtifactInfo objects for the job.")


_minio_client = None


def get_minio_client():
    """
    Retrieves the singleton instance of the MinIO client.

    This function attempts to initialize a connection to MinIO if one does not
    already exist, using the settings configured in `voyant.core.config`.
    """
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
            logger.warning("MinIO client not available: 'minio' package not installed.")
            # Do not re-raise, allow client to be None, then check in endpoints
        except Exception as exc:
            logger.error("MinIO connection failed: %s", exc)
            # Do not re-raise, allow client to be None, then check in endpoints
    return _minio_client


@artifacts_router.get("/{job_id}", response=ArtifactListResponse, summary="List Artifacts for a Job", auth=_auth_guard)
def list_artifacts(request, job_id: str):
    """
    Lists all artifacts generated by a specific job.

    Args:
        request: The HTTP request object.
        job_id: The UUID of the job to list artifacts for.

    Returns:
        An ArtifactListResponse object containing a list of artifacts.

    Raises:
        HttpError 503: If the MinIO storage service is unavailable.
        HttpError 500: For any unexpected internal server errors.
    """
    _apply_policy(
        "artifact_list", # Policy action for listing artifacts
        f"voyant artifact list job_id={job_id}",
        {"job_id": job_id},
    )
    client = get_minio_client()
    if not client:
        # Fallback if MinIO client is not initialized, check DB for artifacts.
        # This can occur if MinIO is not correctly configured or available.
        # This fallback mechanism ensures some level of artifact visibility
        # even without direct MinIO access, though download will fail.
        rows = Artifact.objects.filter(job_id=job_id)
        if not rows:
            raise HttpError(503, "Storage unavailable or no artifacts found in DB.")
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
        objects = client.list_objects(settings.minio_bucket_name, prefix=prefix, recursive=True)
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
                    created_at=(
                        obj.last_modified.isoformat() if obj.last_modified else ""
                    ),
                )
            )
        return ArtifactListResponse(artifacts=artifacts)
    except Exception as exc:
        logger.exception("Failed to list artifacts for job %s", job_id)
        raise HttpError(500, f"Failed to list artifacts: {exc}") from exc


@artifacts_router.get("/{job_id}/{artifact_type}", response={200: Dict[str, Any]}, summary="Get Artifact Download Link", auth=_auth_guard)
def get_artifact(request, job_id: str, artifact_type: str, format: str = "json"):
    """
    Retrieves a time-limited, pre-signed URL to download a specific artifact.

    Args:
        request: The HTTP request object.
        job_id: The UUID of the job that generated the artifact.
        artifact_type: The type of the artifact (e.g., 'profile', 'chart').
        format: The desired format of the artifact (e.g., 'json', 'png', 'pdf').

    Returns:
        A dictionary containing the pre-signed `download_url` and its expiration time.

    Raises:
        HttpError 503: If the MinIO storage service is unavailable.
        HttpError 404: If the specified artifact is not found.
    """
    _apply_policy(
        "artifact_access", # Policy action for accessing artifacts
        f"voyant artifact access job_id={job_id} artifact_type={artifact_type} format={format}",
        {"job_id": job_id, "artifact_type": artifact_type, "format": format},
    )
    client = get_minio_client()
    if not client:
        raise HttpError(503, "Storage unavailable")

    object_name = f"artifacts/{job_id}/{artifact_type}.{format}"

    try:
        # Security: Pre-signed URLs grant temporary, limited access for secure artifact retrieval.
        url = client.presigned_get_object(settings.minio_bucket_name, object_name, expires=3600)
        return {
            "job_id": job_id,
            "artifact_type": artifact_type,
            "format": format,
            "download_url": url,
            "expires_in_seconds": 3600,
        }
    except Exception as exc:
        logger.error("Artifact not found: %s", object_name)
        raise HttpError(404, f"Artifact '{artifact_type}.{format}' for job '{job_id}' not found or accessible.") from exc


@artifacts_router.get("/{job_id}/{artifact_type}/download", summary="Download Artifact Directly", auth=_auth_guard)
def download_artifact(request, job_id: str, artifact_type: str, format: str = "json"):
    """
    Directly streams the content of a generated artifact.

    This endpoint is suitable for direct consumption in browsers or applications
    that can handle streaming responses.

    Args:
        request: The HTTP request object.
        job_id: The UUID of the job that generated the artifact.
        artifact_type: The type of the artifact (e.g., 'profile', 'chart').
        format: The format of the artifact (e.g., 'json', 'png', 'pdf').

    Returns:
        A StreamingHttpResponse containing the artifact's content.

    Raises:
        HttpError 503: If the MinIO storage service is unavailable.
        HttpError 404: If the specified artifact is not found.
    """
    _apply_policy(
        "artifact_download", # Policy action for downloading artifacts
        f"voyant artifact download job_id={job_id} artifact_type={artifact_type} format={format}",
        {"job_id": job_id, "artifact_type": artifact_type, "format": format},
    )
    client = get_minio_client()
    if not client:
        raise HttpError(503, "Storage unavailable")

    object_name = f"artifacts/{job_id}/{artifact_type}.{format}"

    try:
        response = client.get_object(settings.minio_bucket_name, object_name)
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
        streaming["Content-Disposition"] = (
            f"attachment; filename={artifact_type}.{format}"
        )
        return streaming
    except Exception as exc:
        logger.error("Failed to download artifact '%s' for job '%s': %s", object_name, job_id, exc)
        raise HttpError(404, f"Artifact '{artifact_type}.{format}' for job '{job_id}' not found or accessible.") from exc


# =============================================================================
# Analyze Router: Triggering Data Analysis Workflows
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
def analyze(request, payload: AnalyzeRequest):
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
                "kpis": (
                    [kpi.model_dump() for kpi in payload.kpis] if payload.kpis else None
                ),
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
                manifest.append(
                    {"type": "profile", "format": "json", "storage_path": path}
                )
            if kpi_results:
                path = _store_json_artifact(minio, job_id, "kpis", kpi_results)
                artifacts["kpis"] = {"storage_path": path}
                manifest.append(
                    {"type": "kpis", "format": "json", "storage_path": path}
                )
            if analyzer_results:
                path = _store_json_artifact(
                    minio, job_id, "analyzers", analyzer_results
                )
                artifacts["analyzers"] = {"storage_path": path}
                manifest.append(
                    {"type": "analyzers", "format": "json", "storage_path": path}
                )
            if generator_results:
                path = _store_json_artifact(
                    minio, job_id, "generators", generator_results
                )
                artifacts["generators"] = {"storage_path": path}
                manifest.append(
                    {"type": "generators", "format": "json", "storage_path": path}
                )
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
                manifest.append(
                    {"type": "generators", "format": "json", "inline": True}
                )

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
            _run_async(
                update_task_status, soma_task_id, "failed", reason=job.error_message
            )
        raise
    except Exception as exc:
        logger.exception("Analyze failed")
        job.status = "failed"
        job.error_message = str(exc)
        job.save(update_fields=["status", "error_message"])
        if soma_task_id:
            _run_async(
                update_task_status, soma_task_id, "failed", reason=job.error_message
            )
        raise HttpError(500, str(exc)) from exc


# =============================================================================
# Discovery Router: Service and API Discovery
# =============================================================================


class ServiceRegisterRequest(Schema):
    """Request schema for registering a new service in the discovery catalog."""
    name: str = Field(..., description="A unique name for the service.")
    base_url: str = Field(..., description="The base URL where the service can be accessed.")
    spec_url: Optional[str] = Field(None, description="An optional URL to the service's OpenAPI specification.")
    version: str = Field("1.0.0", description="The version of the service.")
    owner: str = Field("unknown", description="The team or individual responsible for the service.")
    tags: List[str] = Field(default_factory=list, description="A list of tags for categorizing the service.")


class SpecScanRequest(Schema):
    """Request schema for scanning an external API specification."""
    url: str = Field(..., description="The URL to the OpenAPI specification (e.g., Swagger, YAML).")


# Lazy imports to prevent circular dependencies if discovery is not actively used.
from voyant.discovery.catalog import DiscoveryRepo, ServiceDef
from voyant.discovery.spec_parser import SpecParser

_discovery_repo = DiscoveryRepo()
_spec_parser = SpecParser()


@discovery_router.post("/services", response=ServiceDef, summary="Register a New Service")
def register_service(request, payload: ServiceRegisterRequest):
    """
    Registers a new service and its metadata in the internal discovery catalog.

    If a `spec_url` is provided, the service's OpenAPI specification will be
    parsed to extract endpoint details and enrich the service definition.

    Args:
        request: The HTTP request object.
        payload: The request body containing service registration details.

    Returns:
        A `ServiceDef` object representing the newly registered service.

    Raises:
        HttpError 500: For any unexpected internal server errors during registration or spec parsing.
    """
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
                # Attempt to parse the OpenAPI spec to extract endpoint details.
                spec = _spec_parser.parse_from_url(payload.spec_url)
                service.endpoints = spec.endpoints
                service.version = spec.version or service.version # Update version from spec if available
            except Exception as e:
                logger.warning(f"Failed to parse OpenAPI spec for service '{payload.name}': {e}")
                # Continue registration even if spec parsing fails, but log a warning.

        _discovery_repo.register(service)
        return service
    except Exception as exc:
        logger.exception("Failed to register service '%s'", payload.name)
        raise HttpError(500, f"Failed to register service: {exc}") from exc


@discovery_router.get("/services", response=List[ServiceDef], summary="List Registered Services")
def list_services(request, tag: Optional[str] = None):
    """
    Retrieves a list of all services registered in the discovery catalog.

    Args:
        request: The HTTP request object.
        tag: An optional tag to filter the list of services by.

    Returns:
        A list of `ServiceDef` objects.

    Raises:
        HttpError 500: For any unexpected internal server errors.
    """
    try:
        if tag:
            return _discovery_repo.search(tag)
        return _discovery_repo.list_services()
    except Exception as exc:
        logger.exception("Failed to list services with tag '%s'", tag)
        raise HttpError(500, f"Failed to list services: {exc}") from exc


@discovery_router.get("/services/{name}", response=ServiceDef, summary="Get Service Details")
def get_service(request, name: str):
    """
    Retrieves the full details of a specific service from the discovery catalog.

    Args:
        request: The HTTP request object.
        name: The unique name of the service to retrieve.

    Returns:
        A `ServiceDef` object for the requested service.

    Raises:
        HttpError 404: If the service with the given name is not found.
        HttpError 500: For any unexpected internal server errors.
    """
    try:
        service = _discovery_repo.get(name)
        if not service:
            raise HttpError(404, f"Service '{name}' not found in discovery catalog.")
        return service
    except HttpError: # Re-raise HttpErrors from internal logic
        raise
    except Exception as exc:
        logger.exception("Failed to get service '%s'", name)
        raise HttpError(500, f"Failed to retrieve service '{name}': {exc}") from exc


@discovery_router.post("/scan", response=Dict[str, Any], summary="Scan API Specification")
def scan_spec(request, payload: SpecScanRequest):
    """
    Scans an external OpenAPI specification from a given URL and returns a summary.

    This endpoint does not register the service but provides a preview of what
    would be discovered from the specification.

    Args:
        request: The HTTP request object.
        payload: A request body containing the URL of the API specification.

    Returns:
        A dictionary summarizing the scanned specification, including title,
        version, and a sample of discovered endpoints.

    Raises:
        HttpError 400: If the provided URL is invalid or the spec cannot be parsed.
        HttpError 500: For any unexpected internal server errors.
    """
    try:
        spec = _spec_parser.parse_from_url(payload.url)
        return {
            "title": spec.title,
            "version": spec.version,
            "endpoint_count": len(spec.endpoints),
            "endpoints": [endpoint.path for endpoint in spec.endpoints[:10]], # Return first 10 endpoints for brevity
        }
    except Exception as exc:
        logger.exception("Failed to scan API specification from URL '%s'", payload.url)
        raise HttpError(400, f"Scan failed: {exc}") from exc


# =============================================================================
# Search Router: Semantic Search Capabilities
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
def search(request, payload: SearchQuery):
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
            SemanticSearchResult(
                id=item.id, score=item.score, text=item.text, metadata=item.metadata
            )
            for item in results
        ]
    except Exception as exc:
        raise HttpError(500, str(exc)) from exc


class IndexRequest(Schema):
    text: str
    metadata: Optional[Dict[str, Any]] = None


@search_router.post("/index")
def index_item(request, payload: IndexRequest):
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

# DataScraper Module - Pure Execution Tools (Production Compliant)
from voyant.scraper.api import scrape_router

api.add_router("/scrape", scrape_router, tags=["scrape"])
