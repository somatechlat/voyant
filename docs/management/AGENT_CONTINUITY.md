# AGENT CONTINUITY JOURNAL

Document ID: VOYANT-AGENT-CONTINUITY
Status: Active
Date: 2026-01-12 (Updated)

---

## ⚠️ WORKSPACE BOUNDARY (CRITICAL)

| Repository | Status | Action |
|------------|--------|--------|
| **Voyant** | ✅ ACTIVE | Work here |
| **SomaAgentHub** | ✅ ACTIVE | Work here (as needed for Voyant) |
| **SomaAgent01** | 🔒 READ-ONLY | Reference only—DO NOT MODIFY |

> **SomaAgent01 is the Layer 4 cognitive operating system.** 
> It is a mature Django monolith with 62+ apps, 50+ API routers, Lit 3 UI.
> We read it for architectural reference but **ALL WORK HAPPENS IN Voyant AND SomaAgentHub**.

---

## 🔗 SomaAgent01 SaaS Mode Reference (READ-ONLY)

### Branches (Reference)
| Branch | Purpose |
|--------|---------|
| `SAAS-PRODUCTIONREADY` | Production SaaS configuration |
| `feature/saas-settings-centralization` | Settings centralization |
| `django` | Django migration |
| `main` | Stable main branch |

### Critical Files (Reference)
| File | Purpose |
|------|---------|
| `saas/config.py` | SaaSConfig dataclass with `SOMA_SAAS_MODE` env var |
| `saas/brain.py` | SomaBrain in-process integration |
| `saas/memory.py` | FractalMemory in-process integration |
| `docs/deployment/SOFTWARE_DEPLOYMENT_MODES.md` | StandAlone vs SomaStackClusterMode docs |
| `admin/saas/` | SaaS admin app (tenants, tiers, billing, features, audit) |

### Deployment Modes (SomaAgent01 Reference)
| Mode | Description |
|------|-------------|
| **StandAlone** | Each service runs independently, local auth/storage |
| **SomaStackClusterMode** | Unified SaaS, shared tenant identity, Brain+Memory paired |

### Key Environment Variables (Reference)
```bash
SOMASTACK_SOFTWARE_MODE=StandAlone|SomaStackClusterMode
SOMA_SAAS_MODE=true|false
SA01_DEPLOYMENT_MODE=DEV|PROD
```

> **SomaAgentHub serves ANY agent.**
> In SomaStackClusterMode, SomaBrain + SomaFractalMemory are inseparable.
> SomaAgent01 is the control plane (tenants, users, agents, billing).

---

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
- 11 of 29 MCP tools still to be implemented per SRS specification.

### 3.2.1 DataScraper Module (COMPLETED)
- Core infrastructure: models, API, workflow, activities ✓
- Parsing stack: HTML, PDF, OCR, transcription ✓
- Browser clients: Playwright, Selenium, Scrapy, BeautifulSoup ✓
- MCP tools: scrape.fetch, scrape.extract, scrape.ocr, scrape.parse_pdf, scrape.transcribe ✓
- Remaining: Django INSTALLED_APPS registration, migrations, integration tests

### 3.3 New Canonical Documentation
- `docs/SRS.md` – single canonical SRS, expanded to include Apache platform and Soma stack integration.
- `docs/TASKS.md` – full task plan with milestones, Apache integration, and Soma integration tasks.
- `docs/DESIGN.md` – architecture/design aligned to agent-first execution with Soma stack flow.

### 3.4 Repo Modifications in This Session
- Canonical docs created/maintained:
  - `docs/SRS.md`, `docs/TASKS.md`, `docs/DESIGN.md`, `AGENT_CONTINUITY.md`.
- One-call analyze flow and MCP tool:
  - API route: `/v1/analyze` (`apps/core/api.py`).
  - MCP tool: `voyant.analyze` in `apps/mcp/tools.py`.
  - Temporal workflow + activities: `apps/worker/workflows/analyze_workflow.py`,
    `apps/worker/activities/analysis_activities.py`, `apps/worker/activities/kpi_activities.py`.
- Job status endpoint for MCP `voyant.status`: `/v1/jobs/{job_id}` (`apps/core/api.py`).
- Soma context + integration wiring:
  - Middleware captures `X-Soma-Session-ID`, `X-User-ID`, `traceparent` (`apps/core/middleware.py`).
  - Policy/memory/orchestrator client (`apps/integrations/soma.py`).
  - Policy gates in analyze/jobs/artifact access + orchestrator task updates.
  - Memory write-back for analyze summaries (`remember_summary`).
- Django migration (FastAPI/SQLAlchemy/Alembic removed):
  - Added Django project/app: `manage.py`, `voyant_project/`, `apps/`.
  - Django Ninja API: `apps/core/api.py` mounted at `/v1/`.
  - Django ORM models + migrations: `apps/workflows/models.py`, `apps/workflows/models.py`.
  - Removed legacy FastAPI routes/app and SQLAlchemy/Alembic artifacts.
  - Updated Docker/compose/dev scripts to run `voyant_project.asgi:application`.
  - Keycloak auth rewritten for Django Ninja (`apps/core/security/auth.py`).
  - Tests updated to use Django client; legacy FastAPI/UDB tests removed.
- DataScraper module implementation (2026-01-12):
  - Parser stack: `apps/scraper/parsing/html_parser.py`, `pdf_parser.py`, `ocr_processor.py`.
  - Media processing: `apps/scraper/media/ocr.py`, `transcription.py`.
  - Browser clients: `apps/scraper/browser/playwright_client.py`, `beautifulsoup_client.py`, `scrapy_client.py`, `selenium_client.py`.
  - MCP tools registered: `scrape.fetch`, `scrape.extract`, `scrape.ocr`, `scrape.parse_pdf`, `scrape.transcribe`.

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

## 5) SomaAgent01 Summary (READ-ONLY REFERENCE)

> ⚠️ **DO NOT MODIFY SOMAAGENT01** — This repository is for architectural reference ONLY.
> All work happens in **Voyant** and **SomaAgentHub**.

### 5.1 Purpose
Enterprise multi-agent cognitive OS built on Django 5; modular monolith with 62+ admin apps, 50+ API routers, Lit 3 UI.

### 5.2 Architecture (Reference)
- **Port Namespace**: 20xxx (API: 20020, Frontend: 20080)
- **Stack**: Django 5 + Django Ninja, Lit 3.x, Keycloak, SpiceDB, Milvus, Kafka
- **Layers**: Agents, Brain, Voice, LLM, Orchestrator, Tools, SaaS, Capsules
- **Status**: 18% implemented (12/66 screens), 18 P0 tasks remaining

### 5.3 Integration Implication (How We USE It)
Voyant exposes MCP tools that SomaAgent01 can consume—we don't modify SomaAgent01, we integrate WITH it.

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
