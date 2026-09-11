# Voyant v3.0.0 — Deployment and Operations Guide

**Document ID:** VOYANT-DEPLOYMENT-3.0.0
**Status:** Active
**Date:** 2026-09-04
**Compliance:** ISO/IEC 12207, ISO/IEC 27001

---

## 1. Deployment Modes

Voyant supports two deployment modes controlled by `VOYANT_DEPLOYMENT_MODE`:

| Mode | Services | Use Case |
|------|----------|----------|
| **Standalone** | 20 services | Full self-contained infrastructure |
| **Integrated** | 3 services | Connects to external SomaAgentHub |

---

## 2. Standalone Deployment (Production-Ready)

### 2.1 Services (20)

| Category | Service | Image | Port |
|----------|---------|-------|------|
| Core | voyant_api | Custom Dockerfile | 45000:8000 |
| Core | voyant_worker | Custom Dockerfile | 45090:9090 |
| Data | voyant_postgres | postgres:16 | 45432:5432 |
| Cache | voyant_redis | redis:7 | 45379:6379 |
| Messaging | voyant_kafka | bitnami/kafka | 45092:9092 |
| Object Storage | voyant_minio | minio/minio | 45900:9000, 45901:9001 |
| SQL Engine | voyant_trino | trinodb/trino | 45080:8080 |
| Vector DB | voyant_milvus | milvusdb/milvus | 19530 |
| Vector Meta | voyant_etcd | quay.io/coreos/etcd | internal |
| Workflow | voyant_temporal | temporalio/server | 45233:7233 |
| Workflow UI | voyant_temporal_ui | temporalio/ui | 45089:8080 |
| Identity | voyant_keycloak | keycloak/keycloak | 45180:8080 |
| Secrets | voyant_vault | hashicorp/vault | 45820:8200 |
| Authorization | voyant_spicedb | authzed/spicedb | 50051, 50052, 8443 |
| Search | voyant_searxng | searxng/searxng | 45088:8080 |
| Governance | voyant_elasticsearch | elasticsearch | 45200:9200 |
| Streaming | voyant_flink_jobmanager | flink:1.18.1 | 45082:8081 |
| Streaming | voyant_flink_taskmanager | flink:1.18.1 | internal |
| Anti-bot | voyant_browserless | browserless/chrome | 45300:3000 |
| Anti-bot | voyant_flaresolverr | flaresolverr | 45191:8191 |

### 2.2 Startup

```bash
cd infra/standalone
docker compose up -d
```

Startup order is managed by `depends_on` with healthchecks:
1. etcd, redis, postgres, minio (infrastructure)
2. vault, kafka (messaging/secrets)
3. spicedb, keycloak, elasticsearch (security/governance)
4. trino, milvus, flink_jobmanager (analytics)
5. flink_taskmanager (depends on jobmanager healthcheck)
6. voyant_api, voyant_worker (application — depend on postgres, redis, kafka, vault)
7. temporal, temporal_ui (workflow — depends on postgres)

### 2.3 Health Checks

All critical services have Docker healthchecks:

| Service | Healthcheck | Interval |
|---------|------------|----------|
| voyant_api | `curl -f http://localhost:8000/healthz` | 30s |
| voyant_worker | `curl -f http://localhost:9090/metrics` | 30s |
| voyant_postgres | `pg_isready` | 10s |
| voyant_redis | `redis-cli ping` | 10s |
| voyant_minio | `curl -f http://localhost:9000/minio/health/live` | 30s |
| voyant_etcd | `etcdctl endpoint health` | 10s |
| voyant_flink_jobmanager | `curl -f http://localhost:8081/overview` | 10s |

---

## 3. Secrets Architecture

### 3.1 Source of Truth: HashiCorp Vault

All sensitive credentials are stored in Vault KV v2 at the `secret/` mount point. Vault is the single source of truth — no secrets in `.env` files, no secrets in Docker Compose environment blocks.

### 3.2 Bootstrap Flow

```
1. Docker secrets (/run/secrets/) provide Vault URL + token only
2. _resolve_docker_secrets() in config.py reads _FILE env vars at import time
3. Settings model constructs with basic config from env vars
4. _resolve_vault_secrets() fetches all SECRET_KEYS from Vault
5. Vault values override any env var values
```

### 3.3 Secret Keys (fetched from Vault)

| Key | Purpose |
|-----|---------|
| `secret_key` | Django SECRET_KEY |
| `database_url` | PostgreSQL connection string |
| `redis_url` | Redis connection string |
| `minio_access_key` | MinIO access key |
| `minio_secret_key` | MinIO secret key |
| `keycloak_client_secret` | Keycloak auth |
| `spicedb_grpc_preshared_key` | SpiceDB auth |
| `vault_token` | Vault self-token |
| `mcp_api_token` | MCP API bearer token |
| `serper_api_key` | Search API |
| `unstructured_api_key` | Document processing |
| `motherduck_token` | Cloud DuckDB |

### 3.4 Non-Secret Configuration (.env)

The `.env` file in `infra/standalone/` contains ONLY non-secret parameters:

```
VOYANT_ENV=local
VOYANT_DEBUG=false
VOYANT_SECRETS_BACKEND=vault
VOYANT_DEPLOYMENT_MODE=standalone
POSTGRES_HOST=voyant_postgres
TEMPORAL_HOST=voyant_temporal:7233
...
```

### 3.5 Config Field Resolution

All config fields use the `VOYANT_` prefix via pydantic-settings (`env_prefix="VOYANT_"`). Infrastructure fields that need unprefixed names use `alias=` (e.g., `database_url` has `alias="DATABASE_URL"`).

For Docker deployment, topology values are set in the docker-compose `environment:` block:

```yaml
environment:
  VOYANT_TRINO_HOST: voyant_trino
  VOYANT_TRINO_PORT: 8080
  VOYANT_TRINO_USER: voyant
  VOYANT_TRINO_CATALOG: iceberg
```

---

## 4. Database Migrations

```bash
docker compose exec voyant_api python manage.py migrate
```

25 migrations across all apps. Run after first deployment or after model changes.

---

## 5. API Endpoints

### 5.1 Operational

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | Liveness probe (lightweight) |
| `GET /ready` | Readiness probe (checks DuckDB, Temporal, circuit breakers) |
| `GET /status` | Administrative status report |
| `GET /version` | API version metadata |

### 5.2 REST API (199 endpoints under `/v1/`)

| Router | Path Prefix | Endpoints |
|--------|-------------|-----------|
| sources_router | `/v1/sources` | CRUD + discover |
| jobs_router | `/v1/jobs` | ingest, profile, quality, analyze, cancel |
| sql_router | `/v1/sql` | query, tables, columns |
| governance_router | `/v1/governance` | lineage, schema, quotas, search |
| presets_router | `/v1/presets` | list, execute, kpi_templates |
| artifacts_router | `/v1/artifacts` | list, download |
| analyze_router | `/v1/analyze` | create analysis job |
| discovery_router | `/v1/discovery` | services CRUD, scan |
| search_router | `/v1/search` | query, index |
| scrape_router | `/v1/scrape` | fetch, extract, ocr, parse_pdf, transcribe, deep_archive, start, status, cancel |
| capsules_router | `/v1/capsules` | create, install, run, registry, export, import |
| ingestion_router | `/v1/ingestion` | connect, provision-destination |

### 5.3 MCP Server (67 tools at `/mcp`)

MCP is mounted via Django ASGI at `/mcp` using `django-mcp`. Transport: SSE (Server-Sent Events).

---

## 6. Observability

### 6.1 Metrics

Prometheus metrics exposed at `:9090/metrics` (worker) and via `apps/core/lib/metrics.py`. Mode-gated: off, basic, full.

### 6.2 Logging

Four log channels: console, file (10MB rotation), security (30-day retention), audit (365-day retention).

### 6.3 Tracing

OpenTelemetry with SkyWalking OTLP exporter. Initialized via `apps/core/lib/skywalking.py`.

---

## 7. Scaling

### 7.1 Horizontal

- voyant_api: Add replicas behind load balancer
- voyant_worker: Add replicas (Temporal handles distribution)
- voyant_trino: Add worker nodes
- voyant_kafka: Add brokers

### 7.2 Vertical

Resource limits defined in docker-compose `deploy.resources.limits`:

| Service | CPU | Memory |
|---------|-----|--------|
| voyant_api | 1.0 | 768M |
| voyant_worker | 1.0 | 512M |
| voyant_flink_* | 0.5 | 512M |

---

## 8. Troubleshooting

### 8.1 Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| SQL queries fail with empty host | Trino env vars not set with `VOYANT_` prefix | Set `VOYANT_TRINO_HOST` in docker-compose environment |
| Vault authentication failed | Vault not sealed or token wrong | Check `vault status`, verify `/run/secrets/vault_token` |
| Flink TaskManager restart loop | Race condition with JobManager | TaskManager has healthcheck dependency — wait for JobManager |
| Milvus connection timeout | Milvus still starting | Milvus health check takes ~60s on first boot |
| 500 on API endpoints | Migrations not applied | Run `python manage.py migrate` |

### 8.2 Logs

```bash
docker compose logs voyant_api --tail 50
docker compose logs voyant_worker --tail 50
docker compose logs voyant_vault --tail 20
```

---

**Document Version:** 3.0.0
**Last Updated:** 2026-09-04
