# Helm Chart Values Reference (UDB API)

This document summarizes configurable deployment values and their effects.

## Core Image & Replica Settings
- `image.repository`: Container image repo.
- `image.tag`: Version tag (pin for reproducibility).
- `replicaCount`: API pod replicas (>=2 recommended for HA after session stickiness solved).

## Resource Requests
- `resources.requests.cpu` / `memory`: Baseline for scheduling.
- `resources.limits.cpu` / `memory`: Upper bounds; profiling & Evidently can spike memory.

## Environment Variables (ConfigMap / Secret)
| Variable | Purpose | Default | Notes |
|----------|---------|---------|-------|
| `AIRBYTE_URL` | Airbyte server base URL | `http://airbyte-server:8001` | Adjust if using external Airbyte. |
| `AIRBYTE_WORKSPACE_ID` | Workspace override | auto-discover | Provide to avoid extra lookup. |
| `DUCKDB_PATH` | Warehouse file path | `/data/warehouse.duckdb` | Backed by PVC mount. |
| `ARTIFACTS_ROOT` | Artifact storage root | `/artifacts` | Must be writable volume. |
| `REDIS_URL` | Redis job store | unset | Enables persistence across restarts. |
| `KAFKA_BROKERS` | Kafka bootstrap servers | unset | Enables event emission. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP HTTP traces endpoint | unset | Set for tracing export. |
| `UDB_RATE_LIMIT` | Requests per window | `60` | Applies to analyze/sql/ingest endpoints. |
| `UDB_RATE_WINDOW` | Rate limit window seconds | `60` | Combined with limit above. |
| `UDB_TENANT_HEADER` | Request header for tenant | `X-UDB-Tenant` | Namespaces jobs & artifacts. |

## Persistence
- `persistence.enabled`: Enable PVC.
- `persistence.size`: Size for DuckDB + artifacts (increase if many profiles or documents).
- `persistence.storageClass`: Storage class selection.

## Service
- `service.type`: ClusterIP / LoadBalancer / NodePort.
- `service.port`: Default 8000 (FastAPI via uvicorn).

## Ingress
- `ingress.enabled`: Enable external exposure.
- `ingress.className`: Ingress class (e.g., nginx).
- `ingress.hosts`: Host definitions.
- `ingress.tls`: TLS secret references.

## Security
- NetworkPolicy: Deny-all baseline; allow Airbyte, Kafka, Redis, OTLP endpoints explicitly.
- PodSecurityContext / SecurityContext: Run as non-root recommended.

## Observability
- Prometheus: Scrape target exposes `/metrics` (port 8000). Add serviceMonitor if using kube-prometheus-stack.
- Traces: Provide OTEL endpoint; optionally add OTEL resource attrs via env `OTEL_RESOURCE_ATTRIBUTES`.
- Dashboards: Import `grafana_dashboard_example.json` for starter dashboard.

## Scaling Considerations
- DuckDB is file-based: prefer vertical scaling first; future multi-writer coordination needed for scale-out.
- Rate limits can protect CPU during simultaneous heavy profiling.
- Consider separating ingestion & analysis into different deployments when workload increases.

## Upgrade Strategy
- Pin image tags; run schema drift checks (Evidently) after upgrade.
- Backup PVC prior to major version bump.

## Future Values (Placeholders)
| Value | Purpose |
|-------|---------|
| `multiTenancy.enabled` | Toggle tenant isolation features. |
| `egress.allowDomains` | Whitelist for outbound network calls. |
| `events.enabled` | Gate Kafka emission for simpler deployments. |

---
Keep this file synchronized with any new environment variable or chart value additions.
