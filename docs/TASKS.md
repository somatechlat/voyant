# Voyant v3 Production Readiness Task Plan

Document ID: VOYANT-TASKS-3.0.0
Status: Draft for execution
Date: 2025-12-17

## 0. Tracking Conventions
- [ ] Not started
- [~] In progress
- [x] Complete

## 1. Core Agent Flow (Analyze One-Call)
- [x] Add REST endpoint `/v1/analyze` to execute full pipeline and return summary + artifact manifest.  
  Files: `voyant_app/api.py`, `voyant_project/urls.py`
- [x] Add MCP tool `voyant.analyze` and map to REST endpoint.  
  Files: `voyant/mcp/server.py`
- [x] Implement Analyze Workflow (Temporal) with steps: normalize → profile → quality → KPI → charts → narrative.  
  Files: `voyant/workflows/analyze_workflow.py` (new), `voyant/activities/analysis_activities.py`, `voyant/activities/generation_activities.py`
- [x] Create artifact manifest structure and return with job summary.  
  Files: `voyant/core/artifact_store.py`, `voyant_app/api.py`

Definition of Done: Agent can call `voyant.analyze` and get artifacts + summary in one call.

## 2. Persistence (Jobs, Sources, Presets, Artifacts)
- [x] Add Django ORM models for Source, Job, Preset, Artifact.  
  Files: `voyant_app/models.py` (new)
- [x] Add migrations (Django) and bootstrapping.  
  Files: `voyant_app/migrations/`
- [x] Replace in-memory stores with DB-backed CRUD.  
  Files: `voyant_app/api.py`

Definition of Done: Jobs and sources persist across restarts.

## 3. Connector Provisioning (Airbyte)
- [ ] Implement connect/provision flow: create source, destination, connection, trigger sync.  
  Files: `voyant/ingestion/airbyte_client.py`, `voyant_app/api.py`
- [ ] Store Airbyte IDs and sync state in DB.  
  Files: `voyant_app/models.py`, `voyant_app/api.py`

Definition of Done: `voyant.connect` provisions real Airbyte connections.

## 4. Ingestion Workflow Completion
- [ ] Update ingestion workflow to use Airbyte sync when source type is connector-based.  
  Files: `voyant/workflows/ingest_workflow.py`, `voyant/activities/ingest_activities.py`
- [ ] Add ingestion metadata persistence (row counts, tables).  
  Files: `voyant_app/models.py`, `voyant/activities/ingest_activities.py`

Definition of Done: Ingest is real and tracked with job state + events.

## 5. Quality & Drift Pipeline
- [ ] Implement quality workflow execution for `/v1/jobs/quality`.  
  Files: `voyant/workflows/quality_workflow.py` (new), `voyant/activities/quality_activities.py` (new)
- [ ] Add Evidently integration or rule-based checks for quality and drift.  
  Files: `voyant/core/quality_rules.py`, `voyant/core/baseline_store.py`
- [ ] Persist quality artifacts and update manifest.  
  Files: `voyant/core/artifact_store.py`, `voyant_app/api.py`

Definition of Done: Quality jobs generate artifacts and status updates.

## 6. Predictive Analytics (Regression, Forecasting, Anomaly)
- [ ] Expose regression and forecasting workflows via REST + MCP.  
  Files: `voyant_app/api.py`, `voyant/mcp/server.py`, `voyant/workflows/operational_workflows.py`
- [ ] Add preset: `benchmark.brand` with KPI + comparison logic.  
  Files: `voyant_app/api.py`, `voyant/workflows/benchmark_workflow.py`

Definition of Done: Agent can trigger regression/forecast/anomaly from MCP.

## 7. Artifacts & Manifest Standardization
- [ ] Standardize artifact types and names (profile, quality, drift, charts, narrative, kpi).  
  Files: `voyant/core/artifact_store.py`, `voyant/core/plugin_registry.py`
- [ ] Add manifest endpoint `/v1/artifacts/{job_id}/manifest`.  
  Files: `voyant_app/api.py`

Definition of Done: All analysis outputs traceable in manifest.

## 8. Governance, Contracts, Lineage
- [ ] Enforce contract validation pre-ingest and pre-analyze.  
  Files: `voyant/core/contracts.py`, `voyant/activities/ingest_activities.py`
- [ ] Persist lineage graph to storage or emit to DataHub.  
  Files: `voyant/core/lineage.py`, `voyant_app/api.py`

Definition of Done: Contracts enforced and lineage queryable.

## 9. Security & Auth Enforcement
- [ ] Add Keycloak auth dependency to protected routes.  
  Files: `voyant/security/auth.py`, `voyant_app/api.py`
- [ ] Add tenant enforcement to SQL and artifact access.  
  Files: `voyant_app/api.py`

Definition of Done: All sensitive routes require JWT and tenant scoping.

## 10. Observability
- [ ] Expose `/metrics` in API and unify metric names.  
  Files: `voyant_app/api.py`, `voyant/core/metrics.py`, `voyant/core/monitoring.py`
- [ ] Add tracing spans across API → workflow → activity.  
  Files: `voyant/core/structured_logging.py`, workflow/activity modules

Definition of Done: Metrics and traces available in production stack.

## 11. Reliability & Resilience
- [ ] Add circuit breakers around DataHub, MinIO, Trino.  
  Files: `voyant/core/circuit_breaker.py`, respective clients
- [ ] Add retry and timeout policies for all external calls.  
  Files: `voyant/core/retry_config.py`

Definition of Done: External failures are isolated and observable.

## 12. Rate Limiting and Quotas
- [ ] Implement rate limiting middleware on high-cost endpoints.  
  Files: `voyant/api/middleware.py`, `voyant/core/tenant_quotas.py`

Definition of Done: Excessive requests receive 429 with error codes.

## 13. Error Contract Adoption
- [ ] Make API responses return structured error codes (`VYNT-XXXX`).  
  Files: `voyant/core/errors.py`, `voyant_app/api.py`

Definition of Done: All error responses contain error code and message.

## 14. Test Coverage (Production Grade)
- [ ] Add end-to-end tests for analyze pipeline and artifacts.  
  Files: `tests/test_analyze_failure.py`, `tests/test_e2e_smoke.py`
- [ ] Add integration tests for Airbyte, DataHub, MinIO flows.  
  Files: `tests/integration/*`

Definition of Done: CI validates core agent journey.

## 15. Deployment Hardening
- [ ] Validate docker-compose healthchecks and dependency order.  
  Files: `docker-compose.yml`
- [ ] Helm chart values updated for new endpoints and services.  
  Files: `helm/*`

Definition of Done: Stack starts cleanly and supports production defaults.

## 16. Milestones
- M1: One-call analyze with artifacts + manifest
- M2: Persistence + real connectors
- M3: Quality + predictive workflows
- M4: Security + observability + reliability
- M5: Production hardening + tests
- M6: Apache platform integration (Iceberg, Ranger, Atlas, SkyWalking, NiFi, Superset, Druid/Pinot, Tika, Flink)

## 17. Apache Platform Integration
- [ ] Integrate Apache Iceberg as the lakehouse storage layer.  
  Files: `voyant/core/iceberg.py` (new), `config/iceberg/*` (new)
- [ ] Add Apache Flink streaming pipelines for continuous KPIs and anomalies.  
  Files: `voyant/streaming/*` (new), `config/flink/*` (new)
- [ ] Enforce Apache Ranger policies at query and artifact access.  
  Files: `voyant/security/policy.py` (new), `voyant_app/api.py`
- [ ] Publish metadata and lineage to Apache Atlas.  
  Files: `voyant/governance/atlas.py` (new), `voyant/core/lineage.py`
- [ ] Add Apache SkyWalking tracing export for API and workflows.  
  Files: `voyant/observability/skywalking.py` (new), `voyant_project/urls.py`, workflow/activity modules
- [ ] Add Apache NiFi ingestion adapters and flow registration.  
  Files: `voyant/ingestion/nifi.py` (new), `voyant_app/api.py`
- [ ] Add Apache Superset integration for curated datasets and artifacts.  
  Files: `voyant/bi/superset.py` (new)
- [ ] Add Apache Druid and Pinot export pipelines for OLAP workloads.  
  Files: `voyant/olap/druid.py` (new), `voyant/olap/pinot.py` (new)
- [ ] Add Apache Tika document extraction path for unstructured ingestion.  
  Files: `voyant/ingestion/tika.py` (new), `voyant/ingestion/unstructured_utils.py`

Definition of Done: All Apache integrations are configured, testable, and wired into core agent workflows.

## 18. Soma Stack Integration (SomaAgentHub + SomaAgent01)
- [ ] Add Soma context middleware to accept `X-Soma-Session-ID`, `X-User-ID`, and `traceparent`.  
  Files: `voyant/api/middleware.py`
- [ ] Persist `soma_session_id` on Job records and include in status callbacks.  
  Files: `voyant_app/models.py`, `voyant_app/api.py`
- [ ] Add Soma policy client to call Policy Engine `/v1/evaluate` for sensitive actions (ingest, analyze, artifact download).  
  Files: `voyant/integrations/soma.py` (new), `voyant_app/api.py`
- [ ] Add Memory Gateway client to persist analysis summaries via `/v1/remember` and optional `/v1/rag/retrieve`.  
  Files: `voyant/integrations/soma.py` (new), `voyant/workflows/analyze_workflow.py`
- [ ] Add Orchestrator callback publishing job status updates to `/v1/sessions/*` when `X-Soma-Session-ID` is present.  
  Files: `voyant/integrations/soma.py` (new), `voyant_app/api.py`
- [ ] Add tool metadata export for SomaAgent01 tool registry (MCP schema and health).  
  Files: `voyant/mcp/server.py`, `voyant_project/urls.py`
- [ ] Add integration tests against SomaAgentHub local stack (gateway, policy, memory).  
  Files: `tests/integration/*`

Definition of Done: SomaAgentHub can orchestrate Voyant workflows with policy and memory integration, and SomaAgent01 can register Voyant tools.
