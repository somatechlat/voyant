"""Voyant Admin Panel — Pydantic schemas for admin API."""

from __future__ import annotations

from typing import Any

from ninja import Field, Schema

# ── Dashboard ────────────────────────────────────────────────────────────────


class DashboardStats(Schema):
    total_jobs: int = 0
    jobs_running: int = 0
    jobs_queued: int = 0
    jobs_failed: int = 0
    jobs_completed: int = 0
    total_sources: int = 0
    sources_active: int = 0
    total_artifacts: int = 0
    total_capsules: int = 0
    total_tenants: int = 0
    active_tenants: int = 0
    audit_events_24h: int = 0
    policy_violations_24h: int = 0


class ServiceHealth(Schema):
    name: str
    status: str  # healthy | degraded | down | unknown
    details: str = ""
    circuit_breaker_state: str = ""
    last_check: str = ""


class SystemOverview(Schema):
    version: str
    env: str
    debug: bool
    uptime_seconds: int = 0
    services: list[ServiceHealth] = []
    stats: DashboardStats


# ── Jobs ─────────────────────────────────────────────────────────────────────


class JobListItem(Schema):
    job_id: str
    tenant_id: str
    job_type: str
    status: str
    progress: int
    source_id: str | None = None
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    error_message: str | None = None


class JobDetail(Schema):
    job_id: str
    tenant_id: str
    job_type: str
    status: str
    progress: int
    source_id: str | None = None
    soma_session_id: str | None = None
    parameters: dict[str, Any] = {}
    result_summary: dict[str, Any] | None = None
    error_message: str | None = None
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    artifacts: list[dict[str, Any]] = []


class JobActionResponse(Schema):
    job_id: str
    action: str
    status: str
    message: str = ""


# ── Sources ──────────────────────────────────────────────────────────────────


class SourceListItem(Schema):
    source_id: str
    tenant_id: str
    name: str
    source_type: str
    status: str
    created_at: str
    datahub_urn: str | None = None


class SourceCreateRequest(Schema):
    name: str
    source_type: str
    connection_config: dict[str, Any]
    credentials: dict[str, Any] | None = None
    sync_schedule: str | None = None


# ── Governance ───────────────────────────────────────────────────────────────


class PolicyListItem(Schema):
    id: str
    name: str
    policy_type: str
    status: str
    enforcement_level: str
    tenant_id: str
    created_at: str


class ContractListItem(Schema):
    id: str
    name: str
    dataset_urn: str
    status: str
    version: int
    tenant_id: str
    created_at: str


class QuotaInfo(Schema):
    tenant_id: str
    tier: str
    jobs_today: int
    jobs_limit: int
    artifacts_gb: float
    artifacts_limit_gb: float
    sources_count: int
    sources_limit: int


# ── Capsules ─────────────────────────────────────────────────────────────────


class CapsuleListItem(Schema):
    id: str
    name: str
    version: str
    status: str
    capsule_type: str
    tenant_id: str
    install_count: int
    execution_count: int
    created_at: str


class CapsuleActionRequest(Schema):
    reason: str = ""


# ── Ontology ─────────────────────────────────────────────────────────────────


class ObjectTypeListItem(Schema):
    id: str
    name: str
    description: str
    version: int
    property_count: int
    instance_count: int
    tenant_id: str
    created_at: str


class PropertyListItem(Schema):
    id: str
    name: str
    property_type: str
    required: bool
    object_type_name: str


class LinkTypeListItem(Schema):
    id: str
    name: str
    source_type: str
    target_type: str
    cardinality: str
    tenant_id: str


# ── Audit ────────────────────────────────────────────────────────────────────


class AuditLogItem(Schema):
    id: str
    actor: str
    action: str
    resource_type: str
    resource_id: str
    outcome: str
    details: dict[str, Any] = {}
    ip_address: str | None = None
    created_at: str


# ── System ───────────────────────────────────────────────────────────────────


class SystemSettingItem(Schema):
    key: str
    value: str
    value_type: str
    description: str
    is_secret: bool


class SystemSettingUpdate(Schema):
    value: str


# ── SQL Console ──────────────────────────────────────────────────────────────


class SqlExecuteRequest(Schema):
    sql: str
    limit: int = Field(1000, ge=1, le=10000)


class SqlResult(Schema):
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    truncated: bool
    execution_time_ms: int
    query_id: str | None = None


class TableInfo(Schema):
    name: str
    table_schema: str | None = Field(None, alias="schema")
    type: str = "table"


# ── Search ───────────────────────────────────────────────────────────────────


class SearchIndexItem(Schema):
    id: str
    score: float
    metadata: dict[str, Any] = {}
    text_preview: str = ""


class SearchIndexRequest(Schema):
    text: str
    metadata: dict[str, Any] | None = None
    item_id: str | None = None


# ── Scraper ──────────────────────────────────────────────────────────────────


class ScraperJobListItem(Schema):
    job_id: str
    status: str
    tenant_id: str
    pages_fetched: int
    bytes_processed: int
    artifact_count: int
    error_count: int
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None


# ── Users / Tenants ─────────────────────────────────────────────────────────


class TenantInfo(Schema):
    tenant_id: str
    realm: str
    job_count: int = 0
    source_count: int = 0
    artifact_count: int = 0
    last_activity: str | None = None
