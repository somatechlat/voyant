# AGENT CONTINUITY JOURNAL

Document ID: VOYANT-AGENT-CONTINUITY
Status: Active
Date: 2025-12-17

## 1) Repository Locations
- Voyant: `/Users/macbookpro201916i964gb1tb/Documents/GitHub/voyant`
- SomaAgentHub: `/Users/macbookpro201916i964gb1tb/Documents/GitHub/somaAgentHub`
- SomaAgent01: `/Users/macbookpro201916i964gb1tb/Documents/GitHub/somaAgent01`

## 2) Current Objective
Integrate Voyant as the agent-first data intelligence box within the Soma stack:
- SomaAgentHub = orchestration/runtime hub.
- SomaAgent01 = cognitive operating system (Django monolith).
- Voyant = data analysis and prediction box exposed via MCP and REST.

## 3) Voyant Current State (Reality from Code)
### 3.1 Architecture Summary
- Django Ninja REST API: health, sources, jobs, SQL, artifacts, presets, discovery, governance, search.
- MCP server: `voyant.*` tools proxy to REST.
- One-call analyze flow: `/v1/analyze` + `voyant.analyze` backed by Temporal workflow.
- Temporal workflows: ingest, profile, operational workflows (anomaly, sentiment, forecast, quality fix).
- SQL: Trino-only guarded queries.
- Artifacts: MinIO presigned URLs.
- Persistence: sources/jobs/presets/artifacts stored in PostgreSQL via Django ORM.
- Governance: DataHub GraphQL search and lineage.
- Events: Kafka event emission with schema registry.
- Secrets: env/k8s/vault/file/in-memory backends.
- Auth: Keycloak JWT module exists but not enforced on routes.

### 3.2 Key Gaps (Core)
- Quality job is queued only (no workflow execution).
- Airbyte connect/provision flow is not implemented end-to-end.
- Metrics are fragmented and not exposed via API.
- Auth is present but not enforced on routes.
- Soma stack integration is wired in API (policy, memory, orchestrator callbacks) but needs end-to-end validation.

### 3.3 New Canonical Documentation
- `docs/SRS.md` – single canonical SRS, expanded to include Apache platform and Soma stack integration.
- `docs/TASKS.md` – full task plan with milestones, Apache integration, and Soma integration tasks.
- `docs/DESIGN.md` – architecture/design aligned to agent-first execution with Soma stack flow.

### 3.4 Repo Modifications in This Session
- Canonical docs created/maintained:
  - `docs/SRS.md`, `docs/TASKS.md`, `docs/DESIGN.md`, `AGENT_CONTINUITY.md`.
- One-call analyze flow and MCP tool:
  - API route: `/v1/analyze` (`voyant_app/api.py`).
  - MCP tool: `voyant.analyze` in `voyant/mcp/server.py`.
  - Temporal workflow + activities: `voyant/workflows/analyze_workflow.py`,
    `voyant/activities/analysis_activities.py`, `voyant/activities/kpi_activities.py`.
- Job status endpoint for MCP `voyant.status`: `/v1/jobs/{job_id}` (`voyant_app/api.py`).
- Soma context + integration wiring:
  - Middleware captures `X-Soma-Session-ID`, `X-User-ID`, `traceparent` (`voyant/api/middleware.py`).
  - Policy/memory/orchestrator client (`voyant/integrations/soma.py`).
  - Policy gates in analyze/jobs/artifact access + orchestrator task updates.
  - Memory write-back for analyze summaries (`remember_summary`).
- Django migration (FastAPI/SQLAlchemy/Alembic removed):
  - Added Django project/app: `manage.py`, `voyant_project/`, `voyant_app/`.
  - Django Ninja API: `voyant_app/api.py` mounted at `/v1/`.
  - Django ORM models + migrations: `voyant_app/models.py`, `voyant_app/migrations/0001_initial.py`.
  - Removed legacy FastAPI routes/app and SQLAlchemy/Alembic artifacts.
  - Updated Docker/compose/dev scripts to run `voyant_project.asgi:application`.
  - Keycloak auth rewritten for Django Ninja (`voyant/security/auth.py`).
  - Tests updated to use Django client; legacy FastAPI/UDB tests removed.

## 4) SomaAgentHub Summary (from repo docs)
### 4.1 Purpose
Production-ready orchestration platform for autonomous agents (gateway, orchestrator, policy, identity, memory, Helm/K8s).

### 4.2 Core Services and Ports
- Gateway API (10000): wizard flows, session management, policy/identity checks, `/metrics`.
- Orchestrator (10001): Temporal-backed sessions, policy + identity integration, `/metrics`.
- Identity Service (10002): token issuance/validation.
- Memory Gateway (10021 external / 8000 internal): Qdrant-backed memory APIs.
- Policy Engine (10020): rules evaluation via `/v1/evaluate`.
Key API surfaces:
- Gateway: `/v1/wizards/*`, `/healthz`, `/ready`, `/metrics`.
- Orchestrator: `/v1/sessions`, `/v1/sessions/{session_id}`, `/v1/sessions/{session_id}/actions/{action}`.
- Memory Gateway: `/v1/remember`, `/v1/recall/{key}`, `/v1/rag/retrieve`.

### 4.3 Observability
- Prometheus `/metrics` exposed for gateway/orchestrator/policy/memory.
- OpenTelemetry support across services.

### 4.4 Integration Implication
Voyant should integrate as a downstream service (tool provider) called from Orchestrator or via Gateway wizard flows. Required hooks:
- Accept `X-Tenant-ID`, `X-User-ID`, `X-Soma-Session-ID`, and `traceparent` from Gateway/Orchestrator.
- Call Policy Engine `/v1/evaluate` before ingest/analyze/artifact download when enabled.
- Write analysis summaries to Memory Gateway `/v1/remember` for recall in agent sessions.
- Publish job status updates back to Orchestrator session endpoints.

## 5) SomaAgent01 Summary (from repo README)
### 5.1 Purpose
Enterprise multi-agent cognitive OS built on Django 5; modular monolith with 17 admin apps.

### 5.2 Core Pillars
- Agents, Brain, Voice, LLM, Orchestrator, Tools, SaaS, Gateway.
- Multimodal (voice + vision), RAG, vector stores.
- Strict VIBE coding compliance, no mocks.

### 5.3 Integration Implication
Voyant should be exposed to SomaAgent01 as a tool provider for data analysis workflows (via REST or MCP), registered in the tool catalog and available to the Tools/Orchestrator modules.

## 6) Target Integration Strategy (High-Level)
1) **Register Voyant as a tool provider** in SomaAgentHub (Gateway/Orchestrator routing to Voyant).
2) **Expose Voyant MCP tools** for agent orchestration and wiring in SomaAgent01 tool registry.
3) **Standardize identity and tenant context** across all three layers (Identity Service JWTs + `X-Tenant-ID` + `X-Soma-Session-ID`).
4) **Policy gate** ingest/analyze/artifact access via Policy Engine `/v1/evaluate`.
5) **Memory write-back** of summaries/artifact pointers via Memory Gateway `/v1/remember`.
6) **Unify observability**: propagate `traceparent` from SomaAgentHub -> Voyant -> downstream services.

## 7) Open Decisions
- Final auth model between SomaAgentHub and Voyant (service-to-service JWT or mTLS).
- Data governance source of truth (DataHub vs Atlas vs dual).
- Streaming requirements (Flink needed only if real-time stream analytics required).
- Tool registry integration path for SomaAgent01 (MCP server registration vs direct REST tool definitions).

## 8) Next Agent Execution Path
- Use `docs/TASKS.md` as the authoritative execution plan.
- Start with M1/M2: analyze flow + persistence + real connectors.
- After core stability, proceed with Apache integrations (Iceberg, Ranger, Atlas, SkyWalking, NiFi, Superset, Druid/Pinot, Tika, Flink).
- Execute Soma stack integration tasks (Section 18 in `docs/TASKS.md`) alongside security/observability work.

## 9) Files to Read First (Next Agent)
- Voyant: `docs/SRS.md`, `docs/TASKS.md`, `docs/DESIGN.md`.
- SomaAgentHub: `README.md`, `docs/README.md`, `services/gateway-api/README.md`, `services/orchestrator/README.md`, `services/memory-gateway/README.md`, `services/policy-engine/README.md`.
- SomaAgent01: `README.md`, `DEPLOYMENT.md`, `ONBOARDING_AGENT.md`.
