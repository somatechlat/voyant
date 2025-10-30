# Project Status: Universal Data Box (UDB)

_Last updated: 2025-10-02_

## Capability Overview

| Domain | Status | Notes |
|--------|--------|-------|
| Core API (FastAPI) | ✅ Complete | Health, readiness, status, artifacts, schema, RBAC-secured endpoints |
| Ingestion (Airbyte sync trigger) | ✅ Functional | Real REST client; polling loop; emits lifecycle events |
| Analytical Storage (DuckDB) | ✅ Stable | Single-file DB path configurable; view creation for joins |
| KPI Engine | ✅ Complete | Multi or single KPI input; timing + masking + narrative summary |
| Data Profiling | ✅ Complete | ydata-profiling HTML + JSON artifacts |
| Data Quality / Drift | ✅ Complete | Evidently reports, baseline reuse; status metrics |
| Charts | ✅ Complete | Plotly chart artifacts (spec or heuristic) |
| Unstructured Ingestion | ✅ Complete | `unstructured` -> fragment table with tenant scoping |
| Tenant Isolation | ✅ Implemented | Job IDs & artifact roots namespaced; table name prefix helper |
| PII Masking | ✅ Implemented | Regex-based masking for KPI row values |
| Security / Guardrails | ✅ Strong | SQL validation, rate limiting, RBAC (viewer/analyst/admin) |
| Secrets Storage | ✅ Implemented | In-memory/file with optional Fernet encryption (`UDB_SECRET_KEY`) |
| OAuth Skeleton | ✅ Prototype | Initiate + callback storing token placeholder |
| Events (Kafka optional) | ✅ Implemented | job.created/state.changed/analyze.completed/failed enriched |
| Event Schema Endpoint | ✅ Added | `/events/schema` documents envelope & types |
| Metrics (Prometheus) | ✅ Extensive | Job counts, durations, KPI size, quality/drift, OAuth, ingest, prune |
| Tracing (OpenTelemetry) | ✅ Added | Spans for analyze pipeline segments |
| Retention / Pruning | ✅ Implemented | `/admin/prune` removes aged artifact dirs + metric |
| CI Pipeline | ✅ Implemented | Lint (Ruff), tests, Docker build, security scan (pip-audit) |
| Lint / Style | ✅ Enforced | Ruff E,F,I; auto-fix imports; line length 120 |
| Testing Coverage | ✅ Growing | Core guardrails, RBAC, metrics, failure, prune, artifacts |
| Documentation | ✅ Solid | Architecture, operations, events, security, roadmap, status |
| Observability (Logging) | ✅ Structured | JSON logs w/ correlation & tenant fields |

## Recent Enhancements
- Added failure path emission (`job.analyze.failed`) + test.
- Added prune metrics counter & validation test.
- Added STATUS.md (this file) summarizing capability & gaps.
- Auto import sorting via Ruff with dev dependency.
- Added event schema entry for failed analyze jobs.

## Key Metrics Footprint
- `job_counter{type,state}`: sync, analyze, ingest lifecycle counts.
- `job_duration{type}`: histogram for durations (s).
- `analyze_kpi_count`: distribution of KPI rowset counts.
- `quality_runs{status}` / `drift_runs{status}`: success/error/skipped counters.
- `ingest_fragments`: fragment counts per unstructured ingest.
- `oauth_initiations{provider}`: initiation counts.
- `artifacts_pruned`: number of artifact directories removed.

## Security Posture
- Input SQL validated; only SELECT + safe clauses.
- Rate limiting (configurable window & bucket).
- RBAC header-driven with role hierarchy (viewer < analyst < admin).
- Tenant isolation for artifacts & temp tables.
- Optional symmetric encryption for secrets via Fernet (`UDB_SECRET_KEY`).

## Remaining Gaps / Recommended Next Steps
1. OAuth Full Integration: Implement real provider flows (PKCE, token refresh, expiry handling).
2. Secrets Backend Abstraction: Pluggable Vault / AWS KMS / GCP Secret Manager providers.
3. Schema Evolution Handling: Persistent baseline management for quality/drift versioning.
4. Multi-Node Coordination: External job store (Redis) stress tests; potential leader election for pruning.
5. Horizontal Scaling: Document and test concurrency for DuckDB (read/write serialization strategy or migration to MotherDuck / warehouse abstraction).
6. Advanced Access Control: Fine-grained dataset/table permissions & per-tenant quotas.
7. Data Lineage Tracking: Capture source-to-artifact lineage graph for transparency.
8. Alerting & SLOs: Define SLIs (job success rate, p95 analyze latency) + alerting hooks.
9. Artifact Preview API: Lightweight HTML snippet or JSON summary endpoints for large artifacts.
10. Caching Layer: Result caching for repeated KPI queries with invalidation semantics.
11. Automated Baseline Refresh: Schedule periodic re-baselining for drift/quality.
12. Helm Chart Hardening: Add pod security context, resource limits, liveness/readiness probes.
13. Structured Event Contracts: Versioned schema registry or JSON Schema publication.
14. Additional Connectors: Expand Airbyte orchestrations (parameterized destination config for DuckDB, S3, etc.).
15. Data Governance: Column-level classification & propagation of sensitivity tags.

## Operational Runbook (Quick)
- Health: `/healthz` (liveness), `/readyz` (readiness).
- Trigger Sync + Analyze: POST `/sources/discover_connect` then `/analyze` with `connectionIds`.
- Inspect KPI + Artifacts: `/artifact_manifest/{jobId}` + specific `/artifact/...` routes.
- SQL Exploration: POST `/sql` (analyst+ role, validates and auto-limits).
- Unstructured Upload: POST `/ingest/upload` (analyst+).
- Prune Old Artifacts: POST `/admin/prune` (admin, respects `UDB_ARTIFACT_RETENTION_DAYS`).
- Metrics: `/metrics` Prometheus scrape endpoint.
- Events: Kafka (if configured) + `/events/schema` for contract.

## Quality & Reliability Notes
- Analyze pipeline errors are captured and surfaced via failed events and job store.
- Tests ensure guardrails (RBAC, rate limit, SQL validation) remain intact.
- Retention pruning is explicit (no cron yet) to avoid surprise deletions; next step is scheduled job.

## Versioning & Release Readiness
Current version: `0.0.1` (functional MVP+). Ready for internal pilot. Before external GA:
- Harden OAuth & secrets backend
- Add lineage & governance roadmap slices
- Formalize event schemas (schema registry)
- Expand test suite to cover high cardinality KPI & large artifact edge cases.

## Contact & Ownership
- Primary module owners: API (app.py), Analytics (analyze.py, kpi.py), Observability (metrics.py, events.py), Security (security.py, rbac.py).

## Canonical Documentation
- See `docs/CANONICAL_ARCHITECTURE.md` for the authoritative layered model, feature flag matrix, plugin registry design, and scaling/failure patterns.
- See `docs/CANONICAL_ROADMAP.md` for phased delivery strategy, milestones, KPIs, and risk register.
- This STATUS file summarizes current implementation vs. canonical intent; any divergence should be reconciled during the next sprint.

---
Generated automatically as part of polishing pass.
