# Changelog

All notable changes to this project will be documented in this file. The format loosely follows Keep a Changelog; versioning will adopt SemVer after initial stabilization.

## [Unreleased]
### Added
- Startup: (Planned) dependency self-check framework (`/startupz`) with strict mode.
- Metrics: (Planned) dependency health gauges and failure counters.
- Metrics: Airbyte & Kestra retry counters, ServiceMonitor template.
- Metrics: KPI exec latency, artifact size gauge, duckdb queue length.
- Endpoint: /events/recent exposing last 100 lifecycle events.
- Docs: OBSERVABILITY.md and SCALING.md.
- Endpoint: /metrics/select core mode for reduced cardinality scraping.
- Docs: OTEL_COLLECTOR_SAMPLE.yaml (collector example) & retry jitter details.
- Events: traceId/spanId enrichment when tracing enabled.
- Endpoint: /lineage/{job_id} basic lineage graph.
- Security: ABAC header-based helper `require_abac`.
- Secrets: Optional Fernet encryption when UDB_SECRET_KEY set.
- Orchestration: Kestra integration client and `/kestra/trigger` endpoint.
- Events: Kafka KRaft single-node deployment & Helm templates.
- Analysis: Sufficiency scoring with artifact (`sufficiency.json`) & histogram metric.
- Feature Flags: quality, charts, unstructured, events, tracing, rbac, narrative, kestra, metrics mode.
- Narrative summarizer for KPI + artifact context.
- SQL endpoint validation returning 422 on disallowed statements.
- Pruning subsystem & `/admin/prune` endpoint.
- Helm chart initial (api, prune CronJob, Redis, Kafka KRaft, persistence, feature-driven env injection).

### Changed
- Migrated configuration to Pydantic v2 (`pydantic-settings`).
- Converted Kafka deployment from ZooKeeper to KRaft (no external dependency).
- Stabilized analyze endpoint: optional body, multi-KPI input, join view materialization.
- Rate limiting: dynamic env-based window, disable flag for controlled environments.

### Fixed
- KPI narrative crash on tuple-based rows.
- Import timing issues by avoiding env resolution at module import in config.
- Quality/Drift artifact presence tracking & metrics increments.

### Security / Hardening
- SQL allowlist (SELECT/WITH/CREATE VIEW) enforcement.
- PII masking for KPI rows.
- Tenant namespacing of artifacts & tables.

## 0.1.0 - Initial Scaffold
- Core FastAPI service skeleton.
- Airbyte client integration (create source, destination, connection, trigger sync, poll job).
- DuckDB storage integration.
- Basic artifact generation pipeline (profiling, quality placeholder, chart scaffolding).
- Metrics endpoint exposure & initial counters.
- Kubernetes raw manifests (api, airbyte, postgres, redis, ingress, network policies).

---
Unreleased section accumulates changes; cut a tagged release once startup self-checks, docker compose dev stack, and no-mock enforcement plugin land.
