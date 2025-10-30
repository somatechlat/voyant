# Roadmap (Rapid Development Sprints)

This roadmap is optimized for accelerated, incremental delivery without mocks. Each phase has crisp acceptance criteria.

## Phase 0 – Baseline Hardening (Current)
Goals: Fail-fast dependency validation; clean metrics & logs.
Deliverables:
- Dependency self-check module with /startupz.
- Prometheus gauges udb_dependency_up{component="..."}.
- Strict startup mode (UDB_STRICT_STARTUP=1) aborts on failed required dependency.
- Lint/import hygiene; Postgres manifest resource limits.

## Phase 1 – Real E2E Enforcement
Goals: Guarantee no mocks in critical paths and validate event/metric outputs.
Deliverables:
- Pytest plugin forbidding monkeypatch of network clients.
- Kafka event consumption test validates schema.
- Metrics contract test (sufficiency histogram, job counters after analyze).
- docker-compose stack (Airbyte, Kafka KRaft, Redis, Kestra, API) + wait script.

## Phase 2 – Developer Experience & Documentation
Goals: Onboard new contributors in <15 minutes.
Deliverables:
- Expanded README real-mode quickstart.
- CONTRIBUTING.md & CODE_OF_CONDUCT.md.
- Architecture diagram (mermaid) and data flow narrative.
- CHANGELOG versioned release 0.2.0.

## Phase 3 – Operational Maturity
Goals: Observability & resilience.
Deliverables:
- OTEL collector example & tracing enable docs.
- Airbyte & Kestra client retry/backoff.
- Helm ServiceMonitor template (optional).
- Prune CronJob invoking internal endpoint.

## Phase 4 – Performance & Scale Prep
Goals: Concurrency safety & artifact insights.
Deliverables:
- DuckDB write serialization & queue metrics.
- KPI execution latency histogram.
- Artifact size gauge & per-job artifact count metrics.
- Scaling guidance doc (DuckDB -> external warehouse, object storage).

## Backlog / Stretch
- Multi-tenant RBAC policy engine (attribute-based).
- Encrypted secrets via KMS plugin.
- Multi-node Kafka with persistent storage.
- Data lineage capture (OpenLineage emission).

---
Roadmap is living; update when scope or priorities shift.
# UDB Roadmap (Rapid Development Sprints)

Status legend: 🟢 Planned | 🟡 In Progress | 🔴 Blocked | ✅ Complete
Target: Functional v1 alpha in ~8 weeks (adjust as needed).

## Sprint 0 (Week 0.5) – Repository & Scaffolding (1/2 week)
Goals:
- Repo structure, core docs (Architecture, Roadmap, Security, Operations, Kubernetes, MCP Interface).
- FastAPI skeleton with health endpoint.
- Requirements pinned; Makefile/dev script.
Deliverables:
- `udb_api` package skeleton.
- CI stub (lint/test placeholder).
Acceptance:
- `uvicorn udb_api.app:app` runs; `/healthz` returns 200.

## Sprint A (Week 1) – Foundations & Ingestion Core
Goals:
- Implement `/sources/discover_connect`, `/status/{jobId}`, `/artifact/**`.
- Airbyte client wrapper; create + sync for simple REST & OneDrive (placeholder) connectors.
- DuckDB initialization & simple table listing endpoint (internal).
Deliverables:
- Source/destination/connection provisioning.
- Job status persisted (in-memory first, Redis optional).
Acceptance:
- Manually trigger mock connection & see job lifecycle JSON.
Checklist:
- [ ] Airbyte client real endpoints (create source)
- [ ] Destination ensure logic
- [ ] Connection create + sync trigger
- [ ] Job polling loop
- [ ] Status caching abstraction

## Sprint B (Week 2) – Auto-Detection & OAuth
Goals:
- Heuristics for REST, OneDrive/SharePoint, Google Drive, Postgres, S3/WebDAV (pattern-level only initially).
- OAuth flow (device code or standard) with callback endpoint.
- Credential storage via K8s Secrets abstraction.
Deliverables:
- `autodetect()` returning structured provider info.
- OAuth handshake returning `oauthUrl` where needed.
Acceptance:
- Provide hints for each supported provider and receive valid mapping + (if needed) auth redirect.
Checklist:
- [ ] Pattern library (regex + scoring)
- [ ] Confidence scoring & ambiguity flag
- [ ] OAuth redirect endpoint
- [ ] OAuth callback endpoint
- [ ] Secret storage abstraction

## Sprint C (Weeks 3-4) – Analysis & Artifacts
Goals:
- Implement `/analyze` with profiling (ydata-profiling) & quality (Evidently) on selected tables.
- Support uploaded file ingestion & simple join SQL.
- KPI SQL execution + chart rendering (Plotly) + artifact storage (HTML/JSON/PNG).
Deliverables:
- Artifact index & retrieval; summary object.
- Basic narrative summarizer stub.
Acceptance:
- End-to-end run from discover → sync → analyze returning artifact links.
Checklist:
- [x] Profiling integration (ydata-profiling)
- [x] Quality suite (Evidently) baseline
- [x] KPI engine + default templates
- [x] Chart renderer
- [x] Artifact writer + index
- [ ] Summary narrative generator stub

## Sprint D (Week 5) – Hardening & Observability
Goals:
- Structured logging, correlation IDs, Prometheus metrics, OpenTelemetry traces.
- Kafka event emission for job states.
- Basic security guard: PII masking stub, rate limits, `/sql` guard.
Deliverables:
- Metrics endpoint; sample Grafana dashboard JSON (optional).
- Kafka topics created & events visible.
Acceptance:
- Metrics show at least job counters; logs correlate job IDs.
Checklist:
- [x] Structured logging (correlation IDs)
- [x] Prometheus metrics endpoint
- [x] OpenTelemetry tracing spans
- [x] Kafka producer wrapper
- [x] PII masking stub
- [ ] Rate limit decorator stub

## Sprint E (Week 6) – Orchestration & Unstructured Docs
Goals:
- Integrate Unstructured for PDF/DOCX/HTML → tabular ingestion.
- Add optional Dagster pipeline wiring (feature flag / config toggle).
Deliverables:
- Document ingestion path & new table creation.
- Dagster job definition for full pipeline.
Acceptance:
- Upload PDF creates text fragments table & can be analyzed.
Checklist:
- [ ] Unstructured ingestion pipeline
- [ ] Table creation strategy for fragments
- [ ] Dagster job definition
- [ ] Feature flag for orchestrator

## Sprint F (Week 7) – Security & Multi-Tenancy Prep
Goals:
- Namespace / tenant scoping in naming (job IDs, schemas, artifact paths).
- RBAC stubs for MCP tools; per-tenant secrets prefixing.
- NetworkPolicy manifests (deny-all + allowlist CRD idea stub).
Deliverables:
- Updated schema naming convention (`tenant_src_shortname__table`).
- Security doc updates.
Acceptance:
- Two tenants simulated with isolated artifacts & schemas.
Checklist:
- [ ] Tenant context propagation
- [ ] Schema prefixing strategy
- [ ] Artifact path isolation
- [ ] RBAC role model stub
- [ ] NetworkPolicy manifests

## Sprint G (Week 8) – Stabilization & Alpha Release
Goals:
- End-to-end test suite (pytest) covering major flows.
- CI pipeline (lint, type check, test) + container image build + Helm chart draft.
- Documentation polish & quickstart.
Deliverables:
- Helm chart initial version.
- Alpha release tag `v0.1.0-alpha`.
Acceptance:
- Clean CI run; helm install yields functioning basic pipeline.
Checklist:
- [ ] Pytest coverage > baseline (core paths)
- [ ] CI: lint + type + test + build + scan
- [ ] Helm chart values review
- [ ] Load test (small dataset) smoke
- [ ] v0.1.0-alpha tag

## Stretch / Parallel Tracks
- Superset/Metabase integration for manual exploration.
- Great Expectations data contracts.
- Device-code OAuth fallback.
- Iceberg/Parquet lake experiment branch.
- Parallel Batch Doc: see `SPRINT_ANALYSIS_GUARDRAILS.md` for merged C/D execution details.

## Milestones
1. M1 (End Sprint C): Functional ingestion + analysis path (manual trigger) ✅ criteria.
2. M2 (End Sprint D): Observability + hardened endpoints.
3. M3 (End Sprint G): Alpha release (Helm + docs + tests).

## Risk Tracking (Top 5)
| Risk | Impact | Mitigation |
|------|--------|------------|
| Ambiguous auto-detection | Medium | Interactive MCP prompts, fallback selection API | 
| OAuth provider complexity | High | Start with limited scope & device code fallback | 
| Large artifact sizes | Medium | Streaming writes, compression, size caps | 
| DuckDB concurrency | Medium | Connection pooling + serialized write sections | 
| Schema drift | Medium | Evidently schema checks + versioned views | 

## KPIs (Engineering)
- Mean time discover→analyze < 4 min for small sources (<1M rows).
- P95 sync job success > 95% for test connectors.
- Artifact generation time < 90s for profiling baseline dataset (≤500k rows).

---
Iterate roadmap as scope evolves; keep this file updated each sprint.
