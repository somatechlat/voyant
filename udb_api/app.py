import asyncio
import logging
import os
import re
import time
import uuid
from collections import defaultdict, deque
from functools import wraps
from typing import Any, Callable, List, Optional

import duckdb
import asyncio as _asyncio_duck
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from opentelemetry import trace  # type: ignore
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter  # type: ignore
from opentelemetry.sdk.resources import Resource  # type: ignore
from opentelemetry.sdk.trace import TracerProvider  # type: ignore
from opentelemetry.sdk.trace.export import BatchSpanProcessor  # type: ignore
from pydantic import BaseModel

from .airbyte_client import get_airbyte_client
from .analyze import generate_artifacts
from .autodetect import autodetect
from .charts import build_charts
from .config import get_settings
from .events import emit_job_event, get_emitter
from .events import recent_events
from .events import get_emitter
from .ingest import ingest_file
from .job_store import get_job_store
from . import kpi  # use module import so tests can monkeypatch kpi.execute_kpis
from .logging_mw import CorrelationIdMiddleware
from .logging_setup import configure_json_logging
from .masking import mask_kpi_rows
from .metrics import (
    analyze_kpi_count,
    artifacts_pruned,
    drift_runs,
    ingest_fragments,
    job_counter,
    job_duration,
    oauth_initiations,
    quality_runs,
    sufficiency_scores,
    duckdb_queue_length,
    artifact_size_bytes,
    kpi_exec_latency,
)
from .metrics import (
    router as metrics_router,
)
from .narrative import summarize as narrative_summarize
from .rbac import require_role
from .secret_store import get_secret_store
from .security import validate_sql
from .sufficiency import compute_sufficiency
from .startup_checks import ensure_startup, latest as startup_latest, run_checks
from .kestra_client import get_kestra_client

# Environment / config (lightweight for now)
settings = get_settings()
AIRBYTE_URL = settings.airbyte_url
DUCKDB_PATH = settings.duckdb_path
ARTIFACTS_ROOT = settings.artifacts_root
# Ensure local writable directories exist (especially in test env)
try:
    os.makedirs(os.path.dirname(DUCKDB_PATH) or ".", exist_ok=True)
    os.makedirs(ARTIFACTS_ROOT, exist_ok=True)
except Exception:
    pass

app = FastAPI(title="Universal Data Box API", version="0.0.1")
app.add_middleware(CorrelationIdMiddleware)
app.include_router(metrics_router)

job_store = get_job_store(settings.redis_url)
_DUCK_LOCK = _asyncio_duck.Lock()
_DUCK_WAITERS: list = []

class DiscoverConnectRequest(BaseModel):
    hint: str
    credentials: Optional[dict] = None
    destination: str = "duckdb"
    options: Optional[dict] = None

class DiscoverConnectResponse(BaseModel):
    sourceId: str
    destinationId: str
    connectionId: str
    jobId: str
    oauthUrl: Optional[str] = None

class AnalyzeRequest(BaseModel):
    connectionIds: Optional[List[str]] = None
    uploads: Optional[List[str]] = None
    joins: Optional[List[str]] = None
    kpiSql: Optional[str] = None  # backward compat single KPI
    kpis: Optional[List[dict]] = None  # new multi KPI: list of {name, sql}
    profile: Optional[bool] = True
    quality: Optional[bool] = True
    chartsSpec: Optional[dict] = None
    joinViews: Optional[List[dict]] = None  # each: {name, sql}

class AnalyzeResponse(BaseModel):
    jobId: str
    summary: str
    kpis: list
    artifacts: dict

class IngestUploadResponse(BaseModel):
    table: str
    fragments: int
    jobId: str

class StatusResponse(BaseModel):
    state: str
    progress: int
    logsUrl: Optional[str] = None

class SqlRequest(BaseModel):
    sql: str
    limit: Optional[int] = None

class SqlResponse(BaseModel):
    columns: List[str]
    rows: List[list]
    rowCount: int
    truncated: bool

class ArtifactFile(BaseModel):
    path: str
    size: int
    mime: Optional[str]

class ArtifactManifestResponse(BaseModel):
    jobId: str
    files: List[ArtifactFile]

class OAuthInitiateRequest(BaseModel):
    provider: str
    scopes: Optional[List[str]] = None
    redirectUrl: Optional[str] = None

class OAuthInitiateResponse(BaseModel):
    authUrl: str
    state: str

class OAuthCallbackRequest(BaseModel):
    state: str
    code: str

class OAuthCallbackResponse(BaseModel):
    status: str
    stored: bool

class EventsSchemaResponse(BaseModel):
    envelope: dict
    types: dict

class KestraTriggerRequest(BaseModel):
    namespace: str
    flowId: str
    inputs: Optional[dict] = None

class KestraTriggerResponse(BaseModel):
    executionId: str
    state: str
    flowId: str
    namespace: str

class LineageNode(BaseModel):
    id: str
    type: str
    label: str

class LineageEdge(BaseModel):
    source: str
    target: str
    kind: str

class LineageResponse(BaseModel):
    jobId: str
    nodes: List[LineageNode]
    edges: List[LineageEdge]

@app.post("/kestra/trigger", response_model=KestraTriggerResponse)
async def kestra_trigger(req: KestraTriggerRequest):
    if not settings.enable_kestra:
        raise HTTPException(status_code=400, detail="Kestra integration disabled")
    client = get_kestra_client()
    try:
        result = await client.trigger_flow(req.namespace, req.flowId, req.inputs)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"Kestra trigger failed: {e}") from e
    # Expect result contains an id field
    execution_id = result.get("id") or result.get("executionId") or "unknown"
    state = result.get("state", "unknown")
    return KestraTriggerResponse(executionId=execution_id, state=state, flowId=req.flowId, namespace=req.namespace)

# Tracing setup (idempotent)
if not isinstance(trace.get_tracer_provider(), TracerProvider):  # basic guard
    resource = Resource.create({"service.name": "udb-api"})
    provider = TracerProvider(resource=resource)
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if endpoint:
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(provider)

tracer = trace.get_tracer("udb-api")
configure_json_logging()
logger = logging.getLogger("udb")

def _tenant_from_request(req: Request | None) -> str | None:
    if not req:
        return None
    header_name = settings.tenant_header
    t = req.headers.get(header_name)
    if t:
        return t.strip()
    return None

def _namespaced_job_id(base: str, tenant: str | None) -> str:
    return f"{tenant}__{base}" if tenant else base

def _tenant_artifact_root(tenant: str | None) -> str:
    return os.path.join(ARTIFACTS_ROOT, tenant) if tenant else ARTIFACTS_ROOT

def _tenant_table(base: str, tenant: str | None) -> str:
    if tenant:
        return f"t_{tenant}__{base}"
    return base


_RATE_BUCKETS: dict[str, deque] = defaultdict(deque)

def _current_rate_limits() -> tuple[int, int]:
    return int(os.getenv("UDB_RATE_LIMIT", "60")), int(os.getenv("UDB_RATE_WINDOW", "60"))

def rate_limited(endpoint: str) -> Callable:
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any):
            request: Optional[Request] = kwargs.get("request")
            if not request:
                # search positional args
                for a in args:
                    if isinstance(a, Request):
                        request = a  # type: ignore
                        break
            key_ip = "anonymous"
            if request is not None:
                client_host = request.client.host if request.client else "anonymous"  # type: ignore
                key_ip = client_host
            bucket_key = f"{endpoint}:{key_ip}"
            now = time.time()
            if os.getenv("UDB_DISABLE_RATE_LIMIT") == "1":
                return await fn(*args, **kwargs)
            RATE_LIMIT, RATE_WINDOW_SECONDS = _current_rate_limits()
            dq = _RATE_BUCKETS[bucket_key]
            while dq and now - dq[0] > RATE_WINDOW_SECONDS:
                dq.popleft()
            if len(dq) >= RATE_LIMIT:
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
            dq.append(now)
            return await fn(*args, **kwargs)
        return wrapper
    return decorator

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.get("/readyz")
async def readyz():
    info = startup_latest()
    errors = info["summary"]["error"] if info.get("summary") else {}
    status = "ready" if not errors else "degraded"
    return {"status": status, **info}

@app.get("/startupz")
async def startupz():
    return startup_latest()

async def _poll_job(job_id: str):
    client = get_airbyte_client()
    # Poll until terminal state or timeout
    for _ in range(300):  # ~300 * 2s = 10min max
        status = await client.job_status(job_id)
        state = status.get("state")
        if state in {"succeeded", "failed", "cancelled"}:
            existing = job_store.get(job_id) or {"type": "sync"}
            job_counter.labels(existing.get("type", "sync"), state).inc()
            job_store.set(job_id, {"state": state, "progress": 100, "type": existing.get("type", "sync")})
            await emit_job_event("job.state.changed", job_id, existing.get("type", "sync"), state)
            return
        await asyncio.sleep(2)
    existing = job_store.get(job_id) or {"type": "sync"}
    job_counter.labels(existing.get("type", "sync"), "timeout").inc()
    job_store.set(job_id, {"state": "timeout", "progress": 100, "type": existing.get("type", "sync")})
    await emit_job_event("job.state.changed", job_id, existing.get("type", "sync"), "timeout")

@app.post("/sources/discover_connect", response_model=DiscoverConnectResponse)
async def discover_connect(req: DiscoverConnectRequest, background: BackgroundTasks):
    detection = autodetect(req.hint)
    best = detection.best
    client = get_airbyte_client()
    # Create source
    source_id = await client.create_source(
        name=f"src_{best.provider}_{uuid.uuid4().hex[:4]}",
        source_def_id=best.airbyte_source_def or "",
        config=best.config_template,
    )
    # Destination: placeholder using a generic destination definition ID (to be parameterized)
    destination_id = await client.ensure_destination(
        name="duckdb-dest", destination_def_id="00000000-0000-0000-0000-000000000000", config={}
    )
    # Discover schema for the new source
    catalog = await client.discover_schema(source_id)
    streams = catalog.get("streams", [])
    # Build sync catalog enabling all streams in full_refresh overwrite mode initially
    sync_catalog = {
        "streams": [
            {
                "stream": s.get("stream"),
                "config": {
                    "syncMode": "full_refresh",
                    "destinationSyncMode": "overwrite",
                    "selected": True,
                },
            }
            for s in streams
        ]
    }
    connection_id = await client.create_connection(
        source_id=source_id,
        destination_id=destination_id,
        stream_config=sync_catalog,
    )
    job_id = await client.trigger_sync(connection_id)
    job_store.set(job_id, {"state": "running", "progress": 5, "connectionId": connection_id, "type": "sync"})
    await emit_job_event(
        "job.created",
        job_id,
        "sync",
        state="running",
        extra={"connectionId": connection_id, "sourceId": source_id},
    )
    background.add_task(_poll_job, job_id)
    return DiscoverConnectResponse(
        sourceId=source_id,
        destinationId=destination_id,
        connectionId=connection_id,
        jobId=job_id,
        oauthUrl=best.oauth_url,
    )

@app.post("/oauth/initiate", response_model=OAuthInitiateResponse)
async def oauth_initiate(req: OAuthInitiateRequest, request: Request):
    tenant = _tenant_from_request(request) or "default"
    # Generate simple state token
    state = f"st_{uuid.uuid4().hex[:16]}"
    # Mock auth URL (in real flow would be provider specific)
    auth_url = f"https://auth.example.com/authorize?client_id=dummy&state={state}&provider={req.provider}"
    # Persist minimal pending record in secret store with placeholder
    store = get_secret_store()
    store.set_secret(
        tenant,
        f"oauth_state_{state}",
        {"provider": req.provider, "scopes": req.scopes or [], "redirect": req.redirectUrl},
    )
    oauth_initiations.labels(req.provider).inc()
    return OAuthInitiateResponse(authUrl=auth_url, state=state)

@app.post("/oauth/callback", response_model=OAuthCallbackResponse)
async def oauth_callback(req: OAuthCallbackRequest, request: Request):
    tenant = _tenant_from_request(request) or "default"
    store = get_secret_store()
    pending = store.get_secret(tenant, f"oauth_state_{req.state}")
    if not pending:
        raise HTTPException(status_code=400, detail="Invalid state")
    # Store token placeholder (code -> token simulation)
    token_key = f"oauth_token_{pending['provider']}"
    store.set_secret(tenant, token_key, {"access_token": f"tok_{req.code}", "provider": pending["provider"]})
    return OAuthCallbackResponse(status="ok", stored=True)

@app.post("/analyze", response_model=AnalyzeResponse)
@rate_limited("analyze")
async def analyze(req: AnalyzeRequest | None, request: Request):
    if req is None:
        req = AnalyzeRequest()  # type: ignore
    with tracer.start_as_current_span("analyze.request") as span:  # type: ignore
        span.set_attribute("kpi.mode", "multi" if req.kpis else ("single" if req.kpiSql else "none"))
        tenant = _tenant_from_request(request)
        job_id = _namespaced_job_id(f"job_{uuid.uuid4().hex[:8]}", tenant)
        job_store.set(job_id, {"state": "running", "progress": 5, "type": "analyze"})
        await emit_job_event("job.created", job_id, "analyze", state="running", extra={"tenant": tenant})
        logger.info("analyze job started", extra={"correlation_id": job_id, "tenant": tenant})
        waiter = _asyncio_duck.get_event_loop().create_future()
        _DUCK_WAITERS.append(waiter)
        duckdb_queue_length.set(len(_DUCK_WAITERS))
        async with _DUCK_LOCK:
            _DUCK_WAITERS.remove(waiter)
            duckdb_queue_length.set(len(_DUCK_WAITERS))
            con = duckdb.connect(DUCKDB_PATH)
        try:
            # Materialize join views if provided
            if req.joinViews:
                for jv in req.joinViews:
                    name = jv.get("name")
                    sql = jv.get("sql")
                    if not name or not sql:
                        continue
                    safe_name = re.sub(r"[^A-Za-z0-9_]", "_", name)
                    if not safe_name or safe_name[0].isdigit():
                        continue  # skip unsafe
                    validate_sql(sql)
                    con.execute(f"CREATE OR REPLACE VIEW {safe_name} AS {sql}")
            kpi_input = req.kpis if req.kpis else req.kpiSql
            with tracer.start_as_current_span("kpi.execute"):
                import time as _t
                _k_start = _t.time()
                kpis = kpi.execute_kpis(con, kpi_input)
                kpi_exec_latency.observe(_t.time() - _k_start)
            with tracer.start_as_current_span("kpi.mask"):
                kpis = mask_kpi_rows(kpis)
            quality_status = "skipped"
            drift_status = "skipped"
            start_time = time.time()
            with tracer.start_as_current_span("artifacts.generate"):
                # Treat None as True (default) to allow empty payloads
                want_quality = True if req.quality is None else req.quality
                effective_quality = settings.enable_quality and want_quality
                artifacts = generate_artifacts(job_id, con, _tenant_artifact_root(tenant), quality=effective_quality)
                if effective_quality:
                    if artifacts.get("qualityHtml"):
                        quality_status = "success"
                    else:
                        quality_status = "error"
                    if artifacts.get("driftHtml"):
                        drift_status = "success"
                    else:
                        drift_status = "error"
            duration = time.time() - start_time
            job_duration.labels("analyze").observe(duration)
            if settings.enable_charts:
                with tracer.start_as_current_span("charts.build"):
                    charts = build_charts(kpis, ARTIFACTS_ROOT, job_id, req.chartsSpec)
                if charts:
                    artifacts.setdefault("charts_extra", charts)
            # Sufficiency scoring (tables referenced: all tables in DuckDB for now)
            with tracer.start_as_current_span("sufficiency.compute"):
                tbls = [r[0] for r in con.execute("SHOW TABLES").fetchall()]
                suff = compute_sufficiency(con, tbls)
                sufficiency_scores.observe(suff.score)
                # Persist artifact
                suff_dir = os.path.join(ARTIFACTS_ROOT, job_id)
                os.makedirs(suff_dir, exist_ok=True)
                import json
                with open(os.path.join(suff_dir, "sufficiency.json"), "w") as sf:
                    json.dump({"score": suff.score, "components": suff.components, "needs": suff.needs}, sf, indent=2)
                artifacts["sufficiencyJson"] = f"/artifact/{job_id}/sufficiency.json"
            if settings.enable_narrative:
                summary = narrative_summarize(kpis, artifacts)
            else:
                summary = "Analysis completed"
            job_art_dir = os.path.join(ARTIFACTS_ROOT, job_id)
            total_size = 0
            for root, _, files in os.walk(job_art_dir):
                for f in files:
                    fpath = os.path.join(root, f)
                    try:
                        total_size += os.path.getsize(fpath)
                    except Exception:
                        pass
            artifact_size_bytes.labels(jobId=job_id).set(total_size)
            job_counter.labels("analyze", "succeeded").inc()
            analyze_kpi_count.observe(len(kpis))
            quality_runs.labels(quality_status).inc()
            drift_runs.labels(drift_status).inc()
            job_store.set(job_id, {"state": "succeeded", "progress": 100, "type": "analyze"})
            await emit_job_event(
                "job.analyze.completed", job_id, "analyze", state="succeeded",
                extra={
                    "kpiRows": len(kpis),
                    "tenant": tenant,
                    "durationSec": round(duration, 3),
                    "qualityStatus": quality_status,
                    "driftStatus": drift_status,
                    "sufficiencyScore": suff.score,
                    "sufficiencyNeeds": len(suff.needs),
                    "artifactCounts": {
                        "hasProfile": bool(artifacts.get("profileHtml")),
                        "hasQuality": bool(artifacts.get("qualityHtml")),
                        "hasDrift": bool(artifacts.get("driftHtml")),
                        "chartsExtra": len(artifacts.get("charts_extra", [])),
                        "hasSufficiency": True,
                    }
                }
            )
            logger.info("analyze job completed", extra={"correlation_id": job_id, "tenant": tenant})
            span.set_attribute("kpi.count", len(kpis))
            return AnalyzeResponse(jobId=job_id, summary=summary, kpis=kpis, artifacts=artifacts)
        except Exception as e:  # failure path
            job_counter.labels("analyze", "failed").inc()
            job_store.set(job_id, {"state": "failed", "progress": 100, "type": "analyze"})
            await emit_job_event(
                "job.analyze.failed", job_id, "analyze", state="failed",
                extra={
                    "tenant": tenant,
                    "errorType": e.__class__.__name__,
                    "message": str(e)[:500],
                }
            )
            logger.error("analyze job failed", extra={"correlation_id": job_id, "tenant": tenant})
            raise

@app.on_event("startup")
async def _startup_events():  # pragma: no cover
    # Initialize event emitter if brokers configured
    emitter = get_emitter()
    await emitter.start()
    strict = os.getenv("UDB_STRICT_STARTUP") == "1"
    try:
        await ensure_startup(strict=strict)
    except Exception as e:  # noqa: BLE001
        logger.error("startup dependency failure", extra={"error": str(e)})
        if strict:
            # Force process stop by re-raising (uvicorn will log and exit)
            raise
    # Optionally schedule periodic background re-check
    interval = int(os.getenv("UDB_DEP_CHECK_INTERVAL", "0"))
    if interval > 0:
        async def _periodic():  # pragma: no cover
            while True:
                try:
                    await run_checks()
                except Exception as e:  # noqa: BLE001
                    logger.error("periodic dependency check error", extra={"error": str(e)})
                await asyncio.sleep(interval)
        asyncio.create_task(_periodic())

@app.on_event("shutdown")
async def _shutdown_events():  # pragma: no cover
    emitter = get_emitter()
    await emitter.stop()

@app.get("/status/{job_id}", response_model=StatusResponse)
async def status(job_id: str):
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return StatusResponse(state=job["state"], progress=job.get("progress", 0), logsUrl=None)

@app.get("/artifact/{job_id}/{path:path}")
async def artifact(job_id: str, path: str):
    # Serve static artifact if exists
    full_path = os.path.join(ARTIFACTS_ROOT, job_id, path)
    if not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail="Artifact not found")
    return FileResponse(full_path)

@app.get("/artifact_manifest/{job_id}", response_model=ArtifactManifestResponse)
async def artifact_manifest(job_id: str):
    job_dir = os.path.join(ARTIFACTS_ROOT, job_id)
    if not os.path.isdir(job_dir):
        raise HTTPException(status_code=404, detail="Job directory not found")
    exts_mime = {
        ".html": "text/html",
        ".json": "application/json",
        ".png": "image/png",
        ".csv": "text/csv",
    }
    files: List[ArtifactFile] = []
    for root, _, fnames in os.walk(job_dir):
        for fname in fnames:
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, job_dir)
            ext = os.path.splitext(fname)[1].lower()
            files.append(
                ArtifactFile(
                    path=f"/artifact/{job_id}/{rel}",
                    size=os.path.getsize(fpath),
                    mime=exts_mime.get(ext),
                )
            )
    return ArtifactManifestResponse(jobId=job_id, files=files)

@app.get("/events/schema", response_model=EventsSchemaResponse)
async def events_schema():
    envelope = {
        "type": "string",
        "jobId": "string",
        "jobType": "sync|analyze|ingest",
        "state": "string",
        "timestamp": "ISO8601",
        "extra": "object",
    }
    types = {
        "job.created": {"extra": ["connectionId", "sourceId", "tenant", "table", "fragments"]},
        "job.state.changed": {"extra": []},
        "job.analyze.completed": {
            "extra": [
                "kpiRows",
                "tenant",
                "durationSec",
                "qualityStatus",
                "driftStatus",
                "artifactCounts",
            ]
        },
        "job.analyze.failed": {
            "extra": [
                "tenant",
                "errorType",
                "message",
            ]
        },
    }
    return EventsSchemaResponse(envelope=envelope, types=types)

@app.get("/events/recent")
async def events_recent(limit: int = 50):
    evs = recent_events(limit)
    return {"events": evs, "count": len(evs)}

@app.get("/lineage/{job_id}", response_model=LineageResponse)
async def lineage(job_id: str):
    # Build basic lineage: nodes for job, source/destination if present, artifacts
    evs = recent_events(100)
    related = [e for e in evs if e.get("jobId") == job_id]
    if not related:
        raise HTTPException(status_code=404, detail="No events for job")
    nodes: dict[str, LineageNode] = {}
    edges: List[LineageEdge] = []
    nodes[job_id] = LineageNode(id=job_id, type="job", label=job_id)
    for ev in related:
        extra = ev
        if "connectionId" in extra:
            cid = extra["connectionId"]
            if cid not in nodes:
                nodes[cid] = LineageNode(id=cid, type="connection", label=cid)
            edges.append(LineageEdge(source=cid, target=job_id, kind="feeds"))
        if "sourceId" in extra:
            sid = extra["sourceId"]
            if sid not in nodes:
                nodes[sid] = LineageNode(id=sid, type="source", label=sid)
            edges.append(LineageEdge(source=sid, target=job_id, kind="origin"))
    # Artifact node if exists
    art_dir = os.path.join(ARTIFACTS_ROOT, job_id)
    if os.path.isdir(art_dir):
        aid = f"artifacts:{job_id}"
        nodes[aid] = LineageNode(id=aid, type="artifacts", label="Artifacts")
        edges.append(LineageEdge(source=job_id, target=aid, kind="produces"))
    return LineageResponse(jobId=job_id, nodes=list(nodes.values()), edges=edges)

@app.post("/sql", response_model=SqlResponse)
@rate_limited("sql")
@require_role("analyst")
async def sql(req: SqlRequest, request: Request):
    statement = req.sql.strip()
    try:
        validate_sql(statement)
    except ValueError as e:
        # Return validation errors as 422 for client handling
        raise HTTPException(status_code=422, detail=str(e)) from e
    soft_limit = req.limit or 500
    if "limit" not in statement.lower():
        statement = f"{statement}\nLIMIT {soft_limit}"
    con = duckdb.connect(DUCKDB_PATH)
    df = con.execute(statement).df()
    truncated = False
    if len(df) > soft_limit:
        df = df.head(soft_limit)
        truncated = True
    return SqlResponse(
        columns=list(df.columns),
        rows=df.to_records(index=False).tolist(),
        rowCount=len(df),
        truncated=truncated,
    )

@app.post("/ingest/upload", response_model=IngestUploadResponse)
@rate_limited("ingest")
@require_role("analyst")
async def ingest_upload(file: UploadFile = File(...), table: Optional[str] = Form(None), request: Request = None):
    # Persist temp file
    tenant = _tenant_from_request(request)
    tmp_root = _tenant_artifact_root(tenant)
    tmp_path = os.path.join(tmp_root, f"tmp_{uuid.uuid4().hex}_{file.filename}")
    os.makedirs(os.path.dirname(tmp_path), exist_ok=True)
    with open(tmp_path, "wb") as f:
        f.write(await file.read())
    waiter = _asyncio_duck.get_event_loop().create_future()
    _DUCK_WAITERS.append(waiter)
    duckdb_queue_length.set(len(_DUCK_WAITERS))
    async with _DUCK_LOCK:
        _DUCK_WAITERS.remove(waiter)
        duckdb_queue_length.set(len(_DUCK_WAITERS))
        con = duckdb.connect(DUCKDB_PATH)
        target_table = _tenant_table(table or "doc_fragments", tenant)
        ingest_result = ingest_file(tmp_path, con, target_table)
    os.remove(tmp_path)
    job_id = _namespaced_job_id(f"ing_{uuid.uuid4().hex[:8]}", tenant)
    job_store.set(job_id, {"state": "succeeded", "progress": 100, "type": "ingest"})
    await emit_job_event(
        "job.created", job_id, "ingest", state="succeeded",
        extra={
            "table": ingest_result["table"],
            "fragments": ingest_result["fragments"],
            "tenant": tenant,
        }
    )
    logger.info("ingest completed", extra={"correlation_id": job_id, "tenant": tenant})
    ingest_fragments.observe(ingest_result["fragments"])
    return IngestUploadResponse(table=ingest_result["table"], fragments=ingest_result["fragments"], jobId=job_id)

@app.post("/admin/prune")
@require_role("admin")
async def admin_prune(request: Request):
    removed, days = _prune_now()
    return {"removed": removed, "retentionDays": days}


def _prune_now() -> tuple[int, int]:
    """Perform pruning of old artifact directories.

    Returns (removed_count, retention_days).
    """
    days = int(os.getenv("UDB_ARTIFACT_RETENTION_DAYS", "7"))
    cutoff = time.time() - days * 86400
    removed = 0
    if os.path.isdir(ARTIFACTS_ROOT):
        for entry in os.listdir(ARTIFACTS_ROOT):
            path = os.path.join(ARTIFACTS_ROOT, entry)
            if not os.path.isdir(path):  # skip files
                continue
            try:
                mtime = os.path.getmtime(path)
                if mtime < cutoff:
                    # remove directory tree
                    for root, dirs, files in os.walk(path, topdown=False):
                        for f in files:
                            try:
                                os.remove(os.path.join(root, f))
                            except Exception:
                                pass
                        for d in dirs:
                            try:
                                os.rmdir(os.path.join(root, d))
                            except Exception:
                                pass
                    try:
                        os.rmdir(path)
                        removed += 1
                    except Exception:
                        pass
            except Exception:
                continue
    artifacts_pruned.inc(removed)
    if removed:
        logger.info("prune completed", extra={"removed": removed})
    return removed, days


async def _prune_scheduler():  # pragma: no cover - background maintenance
    interval = int(os.getenv("UDB_PRUNE_INTERVAL_SECONDS", "0"))
    if interval <= 0:
        return
    logger.info("prune scheduler started", extra={"interval": interval})
    while True:
        try:
            _prune_now()
        except Exception as e:  # noqa: BLE001
            logger.error("prune scheduler error", extra={"error": str(e)})
        await asyncio.sleep(interval)
